# -*- coding: utf-8 -*-
"""DAC package system for Hacker Terminal.

A .dac file is a ZIP archive with a manifest.json + script entries.
Installed packages become terminal commands:  <pkgname> [subcommand] [args]
"""

import json
import os
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

import colors
import h as h_module

if getattr(sys, "frozen", False):
    _base = Path(sys.executable).resolve().parent
else:
    _base = Path(__file__).resolve().parent.parent

DAC_DIR = _base / "dac"
REGISTRY = DAC_DIR / "registry.json"
CACHE = DAC_DIR / "_cache"

MANIFEST_TEMPLATE = {
    "name": "",
    "version": "0.1.0",
    "desc": "A Hacker DAC package",
    "entry": "main.ke",
    "commands": {},
}


def _load_registry():
    if REGISTRY.is_file():
        try:
            return json.loads(REGISTRY.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
    return {}


def has(name):
    """True if a DAC package with this name is installed (name acts as a command)."""
    return name.lower() in _load_registry()


def _save_registry(registry):
    DAC_DIR.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")


def build(arguments):
    parts = arguments.split()
    if not parts:
        print("Usage: dac build <folder> [-o out.dac]")
        return
    folder = Path(parts[0]).expanduser()
    out_name = None
    if "-o" in parts:
        index = parts.index("-o")
        if index + 1 < len(parts):
            out_name = parts[index + 1]
    if not folder.is_dir():
        print(f"Folder not found: {folder}")
        return
    manifest_path = folder / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = dict(MANIFEST_TEMPLATE)
        manifest["name"] = folder.name.lower()
    if not manifest.get("name"):
        manifest["name"] = folder.name.lower()
    out_path = Path(out_name).expanduser() if out_name else DAC_DIR.parent / f"{manifest['name']}.dac"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for item in sorted(folder.rglob("*")):
            if item.is_file() and item.name != "manifest.json":
                zf.write(item, item.relative_to(folder).as_posix())
    print(colors.green(f"Built {out_path.name} ({out_path.stat().st_size} bytes)"))
    print(f"Install with: dac install {out_path}")


def install(arguments):
    target = arguments.strip()
    if not target:
        print("Usage: dac install <file.dac>")
        return
    source = Path(target).expanduser()
    if not source.is_file():
        print(f"Package file not found: {source}")
        return
    registry = _load_registry()
    try:
        with zipfile.ZipFile(source) as zf:
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            name = manifest.get("name", source.stem)
            dest = DAC_DIR / name
            dest.mkdir(parents=True, exist_ok=True)
            for member in zf.namelist():
                if member == "manifest.json":
                    continue
                zf.extract(member, dest)
    except (KeyError, ValueError, zipfile.BadZipFile) as error:
        print(f"Invalid .dac package: {error}")
        return
    registry[name] = {
        "version": manifest.get("version", "0.1.0"),
        "desc": manifest.get("desc", ""),
        "entry": manifest.get("entry", "main.ke"),
        "commands": manifest.get("commands", {}),
    }
    _save_registry(registry)
    print(colors.green(f"Installed {name} v{registry[name]['version']}"))
    print(f"Run it now with: {name}")


def list_packages(arguments):
    registry = _load_registry()
    if not registry:
        print("No DAC packages installed. Use 'dac install <file.dac>'.")
        return
    print("Installed DAC packages:")
    for name in sorted(registry):
        info = registry[name]
        print(f"  {name} v{info['version']} - {info['desc']}")
    print(f"({len(registry)} package(s))")


def info(arguments):
    name = arguments.strip()
    registry = _load_registry()
    if name not in registry:
        print(f"Package not installed: {name}")
        return
    info = registry[name]
    dest = DAC_DIR / name
    print(f"Name    : {name}")
    print(f"Version : {info['version']}")
    print(f"Desc    : {info['desc']}")
    print(f"Entry   : {info['entry']}")
    sub_commands = info.get("commands") or {}
    if sub_commands:
        print("Commands:")
        for cmd, script in sorted(sub_commands.items()):
            print(f"  {name} {cmd}  ->  {script}")
    print(f"Location: {dest}")


def remove(arguments):
    name = arguments.strip()
    registry = _load_registry()
    if name not in registry:
        print(f"Package not installed: {name}")
        return
    dest = DAC_DIR / name
    try:
        answer = input(f"Remove DAC package {name}? [y/N] ").strip().lower()
    except EOFError:
        answer = ""
    if answer not in ("y", "yes"):
        print("Aborted.")
        return
    shutil.rmtree(dest, ignore_errors=True)
    del registry[name]
    _save_registry(registry)
    print(f"Removed: {name}")


def fetch(arguments):
    parts = arguments.split(None, 1)
    if not parts:
        print("Usage: dac fetch <name> [source-url-or-path]")
        return
    name = parts[0].lower()
    source = parts[1].strip() if len(parts) > 1 else f"https://hacker.example.com/dac/{name}.dac"
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = CACHE / f"{name}.dac"
    try:
        if source.startswith(("http://", "https://")):
            print(f"Fetching {source} ...")
            with urllib.request.urlopen(source, timeout=20) as resp:
                cached.write_bytes(resp.read())
        else:
            local = Path(source).expanduser()
            if not local.is_file():
                print(f"Source not found: {local}")
                return
            shutil.copy2(local, cached)
    except Exception as error:
        print(f"Fetch failed: {type(error).__name__}: {error}")
        return
    print(colors.green(f"Downloaded {cached.name} ({cached.stat().st_size} bytes)"))
    install(str(cached))


def _resolve_script(pkg_name, sub):
    registry = _load_registry()
    if pkg_name not in registry:
        return None
    info = registry[pkg_name]
    commands_map = info.get("commands") or {}
    if sub and sub in commands_map:
        return DAC_DIR / pkg_name / commands_map[sub]
    if sub and sub.lower() not in ("run", "start"):
        return None
    return DAC_DIR / pkg_name / info.get("entry", "main.ke")


def run(pkg_name, rest):
    parts = rest.split(None, 1)
    sub = parts[0].strip().lower() if parts else ""
    argv = parts[1].split() if len(parts) > 1 else []
    script = _resolve_script(pkg_name, sub)
    if script is None or not script.is_file():
        print(f"No such command in {pkg_name}. Use 'dac info {pkg_name}'.")
        return
    print(colors.cyan(f"[{pkg_name}] running {script.name} ..."))
    try:
        source = script.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        print(f"Cannot read script: {error}")
        return
    if script.suffix.lower() == ".ke":
        h_module.execute_lines(source.splitlines(), display_prefix=False)
    else:
        namespace = {"__name__": "__main__", "args": argv}
        try:
            exec(compile(source, str(script), "exec"), namespace)
        except SystemExit:
            pass
        except Exception as error:
            print(f"Package error: {type(error).__name__}: {error}")


def handle(arguments):
    parts = arguments.split(None, 1)
    action = parts[0].lower() if parts else "help"
    rest = parts[1].strip() if len(parts) > 1 else ""
    if action == "build":
        build(rest)
    elif action == "install":
        install(rest)
    elif action == "fetch":
        fetch(rest)
    elif action == "list":
        list_packages(rest)
    elif action == "info":
        info(rest)
    elif action == "remove":
        remove(rest)
    elif action == "run":
        name, _, subrest = rest.partition(" ")
        if name:
            run(name, subrest)
        else:
            print("Usage: dac run <name> [command] [args...]")
    else:
        print(colors.white("DAC package system (.dac files):"))
        print(colors.white("  dac build <folder> [-o out.dac] - Build a package"))
        print(colors.white("  dac install <file.dac> - Install a package"))
        print(colors.white("  dac fetch <name> [source] - Download & install from a source"))
        print(colors.white("  dac list - List installed packages"))
        print(colors.white("  dac info <name> - Show package details"))
        print(colors.white("  dac remove <name> - Uninstall a package"))
        print(colors.white("Installed packages are commands: <name> [command] [args]"))

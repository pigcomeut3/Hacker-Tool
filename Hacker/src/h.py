import base64
import datetime
import hashlib
import json
import math
import os
import platform
import random
import re
import shutil
import socket
import string
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import colors
import hacklib

if getattr(sys, "frozen", False):
    # packaged: scripts live next to the exe (user-writable, persistent)
    _base = Path(sys.executable).resolve().parent
else:
    # dev: scripts live in the project root (one level above src/)
    _base = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = _base / "hscripts"
SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

# first run after packaging: seed sample scripts + icons from bundled data
_bundled = Path(getattr(sys, "_MEIPASS", "")) / "hscripts"
if getattr(sys, "frozen", False) and _bundled.is_dir():
    for _item in _bundled.rglob("*"):
        if _item.is_file():
            _target = SCRIPTS_DIR / _item.relative_to(_bundled)
            if not _target.exists():
                _target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(_item, _target)

TEMPLATE = (
    "# {name}.ke - Hacker script\n"
    "# Run it with: h run {name}\n"
    "\n"
    'print("Hello from Hacker!")\n'
    'print("MD5 of hacker:", md5("hacker"))\n'
    'print("Base64 of hacker:", enc_base64("hacker"))\n'
)

_RUN_NAMESPACE = {
    "os": os,
    "sys": sys,
    "math": math,
    "random": random,
    "datetime": datetime,
    "json": json,
    "re": re,
    "socket": socket,
    "time": time,
    "base64": base64,
    "hashlib": hashlib,
    "urllib": urllib,
    "uuid": uuid,
    "platform": platform,
    "shutil": shutil,
    "subprocess": subprocess,
    "string": string,
    "Path": Path,
}

_ACTIONS = {}


def _action(*names):
    def decorator(func):
        for name in names:
            _ACTIONS[name] = func
        return func

    return decorator


def handle(arguments):
    parts = arguments.split(None, 1)
    action = parts[0].lower() if parts else ""
    rest = parts[1].strip() if len(parts) > 1 else ""
    handler = _ACTIONS.get(action, show_help)
    handler(rest)


def _script_path(name):
    if name.endswith(".ke"):
        return SCRIPTS_DIR / name
    return SCRIPTS_DIR / f"{name}.ke"


@_action("new")
def new_script(rest):
    name = rest.split()[0] if rest.split() else ""
    if not name:
        print("Usage: h new <name>")
        return
    path = _script_path(name)
    if path.exists():
        print(f"Script already exists: {path}")
        return
    path.write_text(TEMPLATE.format(name=path.stem), encoding="utf-8")
    print(f"Created: {path}")
    print(f"Edit it with: h edit {path.stem}")


@_action("edit")
def edit_script(rest):
    name = rest.split()[0] if rest.split() else ""
    if not name:
        print("Usage: h edit <name>")
        return
    path = _script_path(name)
    if not path.exists():
        print(f"Script not found: {path}")
        return
    subprocess.Popen(["notepad.exe", str(path)])
    print(f"Opened in Notepad: {path}")


@_action("run")
def run_script(rest):
    parts = rest.split(None, 1)
    name = parts[0] if parts else ""
    script_args = parts[1].split() if len(parts) > 1 else []
    if not name:
        print("Usage: h run <name> [args...]")
        return
    path = _script_path(name)
    if not path.is_file():
        print(f"Script not found: {path}")
        return
    source = path.read_text(encoding="utf-8", errors="replace")
    namespace = dict(hacklib.HACKLIB)
    namespace.update(_RUN_NAMESPACE)
    namespace.update(
        {
            "__name__": "__main__",
            "args": script_args,
            "argc": len(script_args),
        }
    )
    print(colors.white(f"Running {path.name} ..."))
    try:
        exec(compile(source, str(path), "exec"), namespace)
    except SystemExit:
        pass
    except Exception as error:
        print(f"Script error: {type(error).__name__}: {error}")


@_action("list")
def list_scripts(rest):
    scripts = sorted(SCRIPTS_DIR.glob("*.ke"))
    if not scripts:
        print("No scripts yet. Create one with: h new <name>")
        return
    print("Hacker scripts:")
    for script in scripts:
        print(f"  {script.stem}  ({script.stat().st_size} bytes)")
    count = len(scripts)
    plural = "s" if count != 1 else ""
    print(f"({count} script{plural})")


@_action("lib")
def show_lib(rest):
    keyword = rest.strip().lower()
    total = hacklib.total_count()
    if keyword:
        matches = sorted(name for name in hacklib.HACKLIB if keyword in name)
        if not matches:
            print(f"No functions match '{rest}'.")
            return
        for name in matches:
            print(name)
        count = len(matches)
        plural = "s" if count != 1 else ""
        print(f"({count} matching function{plural})")
        return
    stats = hacklib.group_stats()
    print(f"Hacker native library: {total} functions")
    for group in sorted(stats):
        print(f"  {group}: {stats[group]}")
    print("Use 'h lib <keyword>' to list matching functions, e.g. h lib sha")


@_action("del")
def delete_script(rest):
    name = rest.split()[0] if rest.split() else ""
    if not name:
        print("Usage: h del <name>")
        return
    path = _script_path(name)
    if not path.exists():
        print(f"Script not found: {path}")
        return
    try:
        answer = input(f"Delete script {path.name}? [y/N] ").strip().lower()
    except EOFError:
        print("Aborted.")
        return
    if answer not in ("y", "yes"):
        print("Aborted.")
        return
    path.unlink()
    print(f"Deleted: {path}")


@_action("help", "")
def show_help(rest=None):
    print(colors.white("Hacker script system (.ke files):"))
    print(colors.white("  h new <name> - Create a new script"))
    print(colors.white("  h edit <name> - Open a script in Notepad"))
    print(colors.white("  h run <name> [args...] - Run a script"))
    print(colors.white("  h list - List all scripts"))
    print(colors.white("  h lib [keyword] - Show the Hacker native library"))
    print(colors.white("  h del <name> - Delete a script"))
    print(colors.white("Scripts are stored in: " + str(SCRIPTS_DIR)))

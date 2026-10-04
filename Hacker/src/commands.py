import ast
import base64
import binascii
import builtins
import codecs
import csv
import ctypes
import datetime
import difflib
import hashlib
import io
import json
import math
import os
import platform
import random
import re
import shlex
import shutil
import socket
import string
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import zlib
from concurrent.futures import ThreadPoolExecutor
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import banner as banner_module
import colors
import pkgcore
import time as _time

COMMANDS = {}
_HISTORY = []


def register(name, description):
    def decorator(func):
        COMMANDS[name] = (func, description)
        return func

    return decorator


def record_history(line):
    _HISTORY.append(line)


def _strip_quotes(text):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    return text


def _parse_int(text, default, maximum=None):
    try:
        value = int(text)
    except ValueError:
        return default
    if maximum is not None:
        value = min(value, maximum)
    return max(1, value)


def _format_bytes(size):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            if unit == "B":
                return f"{int(size)} B"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def _read_text(path):
    for encoding in ("utf-8", "gbk", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except (UnicodeDecodeError, OSError):
            continue
    return ""


def _write_lines(path, lines):
    try:
        with path.open("w", encoding="utf-8", newline="") as handle:
            for line in lines:
                handle.write(line + "\n")
    except OSError as error:
        print(f"Could not save file: {error}")
        return False
    return True


def _ed_resolve(address, current, lines):
    if not address:
        return current
    if address == "$":
        return len(lines)
    if address == ".":
        return current
    if address.startswith(("+", "-")):
        try:
            return current + int(address)
        except ValueError:
            return 0
    if address.isdigit():
        return int(address)
    return 0


def _read_edit_line():
    """Read one line for the editor. Returns (text, quit_request).
    Interactive: supports Backspace; Ctrl+Q requests quit.
    Piped or non-terminal: falls back to plain input()."""
    try:
        import msvcrt
    except ImportError:
        return input(), False
    if not sys.stdin.isatty():
        return input(), False
    chars = []
    while True:
        char = msvcrt.getwch()
        if char == "\x11":
            return "", True
        if char in ("\r", "\n"):
            return "".join(chars), False
        if char in ("\x08", "\x7f"):
            if chars:
                chars.pop()
        elif char in ("\xe0", "\x00"):
            msvcrt.getwch()
        elif char == "\x03":
            raise KeyboardInterrupt
        elif char == "\x1b":
            pass
        else:
            chars.append(char)


def _looks_binary(path):
    try:
        with path.open("rb") as handle:
            return b"\x00" in handle.read(1024)
    except OSError:
        return True


_HOST_PATTERN = re.compile(r"^[A-Za-z0-9.\-_:\]\[%]+$")


@register("sysinfo", "Show system information")
def sysinfo(arguments):
    print(f"System: {platform.system()} {platform.release()}")
    print(f"Version: {platform.version()}")
    print(f"Machine: {platform.machine()}")
    print(f"Processor: {platform.processor() or 'Unknown'}")
    print(f"Hostname: {platform.node()}")
    print(f"Python: {sys.version.split()[0]}")


@register("whoami", "Show current user")
def whoami(arguments):
    user = os.environ.get("USERNAME") or os.environ.get("USER") or "Unknown"
    domain = os.environ.get("USERDOMAIN")
    print(colors.white(f"{domain}\\{user}" if domain else user))


@register("cpu", "Show CPU information")
def cpu(arguments):
    print(f"Processor: {platform.processor() or 'Unknown'}")
    print(f"Logical cores: {os.cpu_count() or 'Unknown'}")
    print(f"Architecture: {platform.architecture()[0]}")
    print(f"Identifier: {os.environ.get('PROCESSOR_IDENTIFIER', 'Unknown')}")


class _MemoryStatus(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


@register("mem", "Show memory usage")
def mem(arguments):
    status = _MemoryStatus()
    status.dwLength = ctypes.sizeof(_MemoryStatus)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        print("Could not read memory status.")
        return
    total = status.ullTotalPhys
    used = total - status.ullAvailPhys
    print(f"Total: {_format_bytes(total)}")
    print(f"Used: {_format_bytes(used)} ({status.dwMemoryLoad}%)")
    print(f"Available: {_format_bytes(status.ullAvailPhys)}")


@register("disk", "Show disk usage")
def disk(arguments):
    found = False
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if os.path.exists(root):
            found = True
            usage = shutil.disk_usage(root)
            percent = usage.used * 100 // usage.total
            print(
                f"{root} Total: {_format_bytes(usage.total)}, "
                f"Used: {_format_bytes(usage.used)} ({percent}%), "
                f"Free: {_format_bytes(usage.free)}"
            )
    if not found:
        print("No disk drives found.")


@register("uptime", "Show system uptime")
def uptime(arguments):
    millis = ctypes.windll.kernel32.GetTickCount64()
    seconds = millis // 1000
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    print(f"Uptime: {days} days, {hours} hours, {minutes} minutes, {seconds} seconds")


class _PowerStatus(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_ubyte),
        ("BatteryFlag", ctypes.c_ubyte),
        ("BatteryLifePercent", ctypes.c_ubyte),
        ("SystemStatusFlag", ctypes.c_ubyte),
        ("BatteryLifeTime", ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong),
    ]


@register("battery", "Show battery status")
def battery(arguments):
    status = _PowerStatus()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
        print("Could not read battery status.")
        return
    if status.BatteryLifePercent == 255:
        print("No battery detected.")
        return
    power = {0: "On battery", 1: "On AC power", 2: "Unknown"}.get(
        status.ACLineStatus, "Unknown"
    )
    print(f"Power: {power}")
    print(f"Battery: {status.BatteryLifePercent}%")


@register("ver", "Show Windows version")
def ver(arguments):
    print(platform.platform())
    print(f"Version: {platform.version()}")
    print(f"OS: {os.environ.get('OS', 'Unknown')}")


@register("env", "Show environment variables")
def env(arguments):
    name = _strip_quotes(arguments)
    if name:
        value = os.environ.get(name)
        if value is None:
            print(f"{name} is not set.")
        else:
            print(f"{name}={value}")
        return
    for key in sorted(os.environ):
        print(f"{key}={os.environ[key]}")


@register("date", "Show current date")
def date(arguments):
    print(datetime.date.today().isoformat())


@register("time", "Show current time")
def time(arguments):
    print(datetime.datetime.now().strftime("%H:%M:%S"))


@register("banner", "Show the banner again")
def banner(arguments):
    banner_module.show()


@register("ip", "Show IP configuration")
def ip(arguments):
    pkgcore.run_process(["ipconfig"])


@register("myip", "Show public IP address")
def myip(arguments):
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=8) as response:
            address = response.read().decode("utf-8", errors="replace").strip()
        print(f"Public IP: {address}")
    except (OSError, urllib.error.URLError) as error:
        print(f"Could not determine public IP: {error}")


@register("ping", "Ping a host")
def ping(arguments):
    host = _strip_quotes(arguments) or "127.0.0.1"
    if not _HOST_PATTERN.fullmatch(host):
        print("Invalid host.")
        return
    pkgcore.run_process(["ping", host])


@register("nslookup", "Query DNS for a host")
def nslookup(arguments):
    host = _strip_quotes(arguments) or "127.0.0.1"
    if not _HOST_PATTERN.fullmatch(host):
        print("Invalid host.")
        return
    pkgcore.run_process(["nslookup", host])


@register("netstat", "Show network connections")
def netstat(arguments):
    pkgcore.run_process(["netstat", "-ano"])


@register("scan", "Scan common ports of a host")
def scan(arguments):
    host = _strip_quotes(arguments) or "127.0.0.1"
    if not _HOST_PATTERN.fullmatch(host):
        print("Invalid host.")
        return
    try:
        socket.getaddrinfo(host, None)
    except socket.gaierror:
        print(f"Could not resolve host: {host}")
        return
    ports = [
        21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 993, 995,
        1080, 1433, 1521, 3306, 3389, 5432, 6379, 8080, 8443, 8888, 27017,
    ]
    print(f"Scanning {host} ({len(ports)} common ports)...")
    open_ports = []
    for port in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.4)
        try:
            if sock.connect_ex((host, port)) == 0:
                open_ports.append(port)
        finally:
            sock.close()
    if open_ports:
        print("Open ports: " + ", ".join(str(port) for port in open_ports))
    else:
        print("No open ports found.")


@register("mac", "Show MAC addresses")
def mac(arguments):
    pkgcore.run_process(["getmac"])


@register("route", "Show routing table")
def route(arguments):
    pkgcore.run_process(["route", "print", "-4"])


@register("wifi", "Show Wi-Fi information")
def wifi(arguments):
    if not pkgcore.run_process(["netsh", "wlan", "show", "interfaces"]):
        print("Wi-Fi is not available on this system.")


@register("tree", "Show directory tree")
def tree(arguments):
    parts = arguments.split()
    max_depth = 2
    if parts:
        try:
            max_depth = max(1, min(int(parts[0]), 6))
        except ValueError:
            pass
    root = Path.cwd()
    print(f"{root.name}\\")

    def walk(directory, depth, prefix):
        try:
            entries = sorted(
                directory.iterdir(),
                key=lambda entry: (not entry.is_dir(), entry.name.casefold()),
            )
        except OSError:
            return
        for index, entry in enumerate(entries):
            last = index == len(entries) - 1
            connector = "`-- " if last else "|-- "
            print(prefix + connector + entry.name + ("\\" if entry.is_dir() else ""))
            if entry.is_dir() and depth < max_depth:
                extension = "    " if last else "|   "
                walk(entry, depth + 1, prefix + extension)

    walk(root, 1, "")


@register("find", "Find files by name")
def find(arguments):
    name = _strip_quotes(arguments).casefold()
    if not name:
        print("Usage: find <name>")
        return
    matches = []
    for current, directories, files in os.walk(
        Path.cwd(), onerror=lambda error: None
    ):
        directories[:] = [directory for directory in directories if not directory.startswith(".")]
        for entry_name in files + directories:
            if name in entry_name.casefold():
                matches.append(Path(current) / entry_name)
                if len(matches) >= 100:
                    break
        if len(matches) >= 100:
            break
    if not matches:
        print("No matches found.")
        return
    for match in matches:
        print(match)
    plural = "es" if len(matches) != 1 else ""
    print(f"({len(matches)} match{plural})")


@register("cat", "Show file content")
def cat(arguments):
    if not arguments.strip():
        print("Usage: cat <file>")
        return
    path = Path(_strip_quotes(arguments)).expanduser()
    if not path.is_file():
        print(f"File not found: {path}")
        return
    if _looks_binary(path):
        print("Binary file. Use 'hex' to inspect it.")
        return
    print(_read_text(path), end="")


@register("head", "Show first lines of a file")
def head(arguments):
    parts = arguments.split(None, 1)
    if not parts:
        print("Usage: head <file> [lines]")
        return
    path = Path(_strip_quotes(parts[0])).expanduser()
    count = _parse_int(parts[1].strip() if len(parts) > 1 else "", 10, 10000)
    if not path.is_file():
        print(f"File not found: {path}")
        return
    print("\n".join(_read_text(path).splitlines()[:count]))


@register("tail", "Show last lines of a file")
def tail(arguments):
    parts = arguments.split(None, 1)
    if not parts:
        print("Usage: tail <file> [lines]")
        return
    path = Path(_strip_quotes(parts[0])).expanduser()
    count = _parse_int(parts[1].strip() if len(parts) > 1 else "", 10, 10000)
    if not path.is_file():
        print(f"File not found: {path}")
        return
    lines = _read_text(path).splitlines()
    print("\n".join(lines[-count:]))


@register("touch", "Create an empty file")
def touch(arguments):
    if not arguments.strip():
        print("Usage: touch <file>")
        return
    path = Path(_strip_quotes(arguments)).expanduser()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
    except OSError as error:
        print(f"Could not create file: {error}")
        return
    print(f"Created/updated: {path}")


@register("mkdir", "Create a directory")
def mkdir(arguments):
    if not arguments.strip():
        print("Usage: mkdir <name>")
        return
    path = Path(_strip_quotes(arguments)).expanduser()
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        print(f"Could not create directory: {error}")
        return
    print(f"Created: {path}")


@register("rm", "Delete a file or directory")
def rm(arguments):
    if not arguments.strip():
        print("Usage: rm <path>")
        return
    path = Path(_strip_quotes(arguments)).expanduser()
    if not path.exists():
        print(f"Not found: {path}")
        return
    kind = "directory" if path.is_dir() else "file"
    try:
        answer = input(f"Delete {kind} {path}? [y/N] ").strip().lower()
    except EOFError:
        print("Aborted.")
        return
    if answer not in ("y", "yes"):
        print("Aborted.")
        return
    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    except OSError as error:
        print(f"Could not delete: {error}")
        return
    print(f"Deleted: {path}")


@register("hash", "Hash a file (MD5/SHA1/SHA256)")
def hash(arguments):
    if not arguments.strip():
        print("Usage: hash <file>")
        return
    path = Path(_strip_quotes(arguments)).expanduser()
    if not path.is_file():
        print(f"File not found: {path}")
        return
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 256)
                if not chunk:
                    break
                md5.update(chunk)
                sha1.update(chunk)
                sha256.update(chunk)
    except OSError as error:
        print(f"Could not read file: {error}")
        return
    print(f"MD5:    {md5.hexdigest()}")
    print(f"SHA1:   {sha1.hexdigest()}")
    print(f"SHA256: {sha256.hexdigest()}")


@register("hex", "Show a hex dump of a file")
def hex(arguments):
    parts = arguments.split(None, 1)
    if not parts:
        print("Usage: hex <file> [bytes]")
        return
    path = Path(_strip_quotes(parts[0])).expanduser()
    limit = _parse_int(parts[1].strip() if len(parts) > 1 else "", 256, 65536)
    if not path.is_file():
        print(f"File not found: {path}")
        return
    try:
        with path.open("rb") as handle:
            data = handle.read(limit)
    except OSError as error:
        print(f"Could not read file: {error}")
        return
    for offset in range(0, len(data), 16):
        chunk = data[offset : offset + 16]
        hex_part = " ".join(f"{byte:02X}" for byte in chunk).ljust(47)
        ascii_part = "".join(chr(byte) if 32 <= byte < 127 else "." for byte in chunk)
        print(f"{offset:08X}  {hex_part}  {ascii_part}")
    print(f"({len(data)} bytes shown)")


@register("size", "Show file or directory size")
def size(arguments):
    if arguments.strip():
        path = Path(_strip_quotes(arguments)).expanduser()
    else:
        path = Path.cwd()
    if not path.exists():
        print(f"Not found: {path}")
        return
    if path.is_file():
        total = path.stat().st_size
    else:
        total = 0
        for current, directories, files in os.walk(path, onerror=lambda error: None):
            for name in files:
                try:
                    total += (Path(current) / name).stat().st_size
                except OSError:
                    continue
    print(f"{_format_bytes(total)}  {path}")


@register("ps", "List processes")
def ps(arguments):
    pkgcore.run_process(["tasklist"])


@register("kill", "Kill a process by PID")
def kill(arguments):
    pid = _strip_quotes(arguments)
    if not pid:
        print("Usage: kill <pid>")
        return
    if not pid.isdigit():
        print("Invalid PID.")
        return
    try:
        answer = input(f"Kill process {pid}? [y/N] ").strip().lower()
    except EOFError:
        print("Aborted.")
        return
    if answer not in ("y", "yes"):
        print("Aborted.")
        return
    pkgcore.run_process(["taskkill", "/PID", pid])


@register("matrix", "Matrix rain effect")
def matrix(arguments):
    seconds = _parse_int(_strip_quotes(arguments), 5, 20)
    columns = shutil.get_terminal_size((80, 24)).columns
    end = _time.time() + seconds
    try:
        while _time.time() < end:
            line = "".join(random.choice("01") for _ in range(columns))
            print(colors.green(line))
            _time.sleep(0.02)
    except KeyboardInterrupt:
        pass
    print(colors.white("Matrix effect stopped."))


@register("hack", "Hacker typing effect")
def hack(arguments):
    seconds = _parse_int(_strip_quotes(arguments), 4, 15)
    lines = [
        "Connecting to remote host...",
        "Spoofing MAC address...",
        "Bypassing firewall rules...",
        "Cracking password hash...",
        "Injecting payload...",
        "Access GRANTED",
    ]
    end = _time.time() + seconds
    try:
        while _time.time() < end:
            if random.random() < 0.3:
                print(colors.green(random.choice(lines)))
            else:
                print(
                    colors.green(
                        f"[{random.randint(0, 9999):04d}] "
                        f"0x{random.getrandbits(48):012X} -> 0x{random.getrandbits(48):012X}"
                    )
                )
            _time.sleep(0.12)
    except KeyboardInterrupt:
        pass
    print(colors.white("Hack sequence complete."))


@register("sudo", "Attempt privilege escalation")
def sudo(arguments):
    print(colors.white("Nice try, hacker. This incident will be reported."))


@register("history", "Show command history")
def history(arguments):
    for index, line in enumerate(_HISTORY, 1):
        print(f"{index:4d}  {line}")


@register("commands", "List all available commands")
def commands(arguments):
    print(colors.white("All commands:"))
    for name in sorted(COMMANDS):
        description = COMMANDS[name][1]
        print(f"  {name} - {description}")


@register("pwd", "Show current directory")
def pwd(arguments):
    print(os.getcwd())


@register("echo", "Print text")
def echo(arguments):
    print(arguments)


@register("hostname", "Show host name")
def hostname(arguments):
    print(platform.node())


@register("grep", "Search text in files")
def grep(arguments):
    parts = arguments.split(None, 1)
    if not parts:
        print("Usage: grep <pattern> [file]")
        return
    try:
        regex = re.compile(parts[0])
    except re.error as error:
        print(f"Invalid pattern: {error}")
        return
    if len(parts) > 1:
        path = Path(_strip_quotes(parts[1])).expanduser()
        if not path.is_file():
            print(f"File not found: {path}")
            return
        for index, line in enumerate(_read_text(path).splitlines(), 1):
            if regex.search(line):
                print(f"{index}: {line}")
        return
    for current, directories, files in os.walk(
        Path.cwd(), onerror=lambda error: None
    ):
        directories[:] = [directory for directory in directories if not directory.startswith(".")]
        for file in files:
            path = Path(current) / file
            if _looks_binary(path):
                continue
            for index, line in enumerate(_read_text(path).splitlines(), 1):
                if regex.search(line):
                    print(f"{path}:{index}: {line}")


@register("wc", "Count lines, words and characters")
def wc(arguments):
    if not arguments.strip():
        print("Usage: wc <file>")
        return
    path = Path(_strip_quotes(arguments)).expanduser()
    if not path.is_file():
        print(f"File not found: {path}")
        return
    text = _read_text(path)
    lines = len(text.splitlines())
    words = len(text.split())
    print(f"{lines} lines, {words} words, {len(text)} chars  {path}")


@register("cp", "Copy a file or directory")
def cp(arguments):
    parts = arguments.split(None, 1)
    if len(parts) != 2:
        print("Usage: cp <source> <destination>")
        return
    source = Path(_strip_quotes(parts[0])).expanduser()
    destination = Path(_strip_quotes(parts[1])).expanduser()
    if not source.exists():
        print(f"Not found: {source}")
        return
    try:
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
    except OSError as error:
        print(f"Could not copy: {error}")
        return
    print(f"Copied: {source} -> {destination}")


@register("mv", "Move a file or directory")
def mv(arguments):
    parts = arguments.split(None, 1)
    if len(parts) != 2:
        print("Usage: mv <source> <destination>")
        return
    source = Path(_strip_quotes(parts[0])).expanduser()
    destination = Path(_strip_quotes(parts[1])).expanduser()
    if not source.exists():
        print(f"Not found: {source}")
        return
    try:
        shutil.move(str(source), str(destination))
    except OSError as error:
        print(f"Could not move: {error}")
        return
    print(f"Moved: {source} -> {destination}")


@register("ren", "Rename a file or directory")
def ren(arguments):
    parts = arguments.split(None, 1)
    if len(parts) != 2:
        print("Usage: ren <old> <new>")
        return
    source = Path(_strip_quotes(parts[0])).expanduser()
    destination = Path(_strip_quotes(parts[1])).expanduser()
    if not source.exists():
        print(f"Not found: {source}")
        return
    try:
        source.rename(destination)
    except OSError as error:
        print(f"Could not rename: {error}")
        return
    print(f"Renamed: {source.name} -> {destination.name}")


@register("open", "Open a path with its default application")
def open(arguments):
    if not arguments.strip():
        print("Usage: open <path>")
        return
    path = Path(_strip_quotes(arguments)).expanduser()
    if not path.exists():
        print(f"Not found: {path}")
        return
    try:
        os.startfile(str(path))
    except OSError as error:
        print(f"Could not open: {error}")


@register("clip", "Copy text to the clipboard")
def clip(arguments):
    if not arguments.strip():
        print("Usage: clip <text>")
        return
    try:
        process = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
        process.communicate(_strip_quotes(arguments).encode("utf-16-le"))
    except OSError as error:
        print(f"Could not copy: {error}")
        return
    print("Copied to clipboard.")


@register("b64", "Base64 encode or decode text")
def b64(arguments):
    parts = arguments.split(None, 1)
    if not parts:
        print("Usage: b64 [-d] <text>")
        return
    if parts[0] == "-d":
        if len(parts) < 2:
            print("Usage: b64 -d <encoded>")
            return
        try:
            decoded = base64.b64decode(parts[1].encode()).decode("utf-8", errors="replace")
        except (ValueError, binascii.Error) as error:
            print(f"Invalid base64: {error}")
            return
        print(decoded)
        return
    print(base64.b64encode(parts[0].encode()).decode())


@register("rot13", "ROT13 encode or decode text")
def rot13(arguments):
    if not arguments.strip():
        print("Usage: rot13 <text>")
        return
    print(codecs.encode(arguments, "rot_13"))


@register("md5str", "Hash a string with MD5")
def md5str(arguments):
    if not arguments.strip():
        print("Usage: md5str <text>")
        return
    print(hashlib.md5(arguments.encode()).hexdigest())


@register("calc", "Evaluate a math expression")
def calc(arguments):
    if not arguments.strip():
        print("Usage: calc <expression>")
        return
    expression = arguments.strip()
    allowed_names = {
        "abs": abs, "round": round, "min": min, "max": max,
        "sum": sum, "int": int, "float": float, "str": str,
        "len": len, "range": range, "pi": math.pi, "e": math.e,
        "tau": math.tau, "sqrt": math.sqrt, "log": math.log,
        "log10": math.log10, "log2": math.log2, "exp": math.exp,
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "floor": math.floor, "ceil": math.ceil,
        "factorial": math.factorial, "pow": pow, "gcd": math.gcd,
    }
    allowed_nodes = (
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
        ast.Name, ast.Load, ast.Add, ast.Sub, ast.Mult, ast.Div,
        ast.FloorDiv, ast.Mod, ast.Pow, ast.USub, ast.UAdd,
        ast.Call, ast.Attribute,
    )
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as error:
        print(f"Invalid expression: {error}")
        return
    for node in ast.walk(tree):
        if not isinstance(node, allowed_nodes):
            print("Unsupported expression.")
            return
        if isinstance(node, ast.Name) and node.id not in allowed_names:
            print(f"Unknown name: {node.id}")
            return
    try:
        result = eval(compile(tree, "<calc>", "eval"), {"__builtins__": {}}, allowed_names)
    except Exception as error:
        print(f"Error: {error}")
        return
    print(result)


@register("uuid", "Generate a UUID")
def uuid(arguments):
    import uuid as uuid_module
    print(uuid_module.uuid4())


@register("rand", "Generate a random number")
def rand(arguments):
    parts = arguments.split()
    if not parts:
        low, high = 0, 100
    elif len(parts) == 1:
        low, high = 0, _parse_int(parts[0], 100)
    else:
        low = _parse_int(parts[0], 0)
        high = _parse_int(parts[1], 100)
    if low > high:
        low, high = high, low
    print(random.randint(low, high))


@register("tracert", "Trace the route to a host")
def tracert(arguments):
    host = _strip_quotes(arguments) or "127.0.0.1"
    if not _HOST_PATTERN.fullmatch(host):
        print("Invalid host.")
        return
    pkgcore.run_process(["tracert", host])


@register("sort", "Sort lines of a file")
def sort(arguments):
    if not arguments.strip():
        print("Usage: sort <file>")
        return
    path = Path(_strip_quotes(arguments)).expanduser()
    if not path.is_file():
        print(f"File not found: {path}")
        return
    for line in sorted(_read_text(path).splitlines(), key=str.casefold):
        print(line)


@register("uniq", "Show unique lines of a file")
def uniq(arguments):
    if not arguments.strip():
        print("Usage: uniq <file>")
        return
    path = Path(_strip_quotes(arguments)).expanduser()
    if not path.is_file():
        print(f"File not found: {path}")
        return
    seen = set()
    for line in _read_text(path).splitlines():
        key = line.casefold()
        if key not in seen:
            seen.add(key)
            print(line)


@register("h", "Hacker script system (.ke files)")
def h(arguments):
    import h as h_module
    h_module.handle(arguments)


@register("b32", "Base32 encode or decode text")
def b32(arguments):
    parts = arguments.split(None, 1)
    if not parts:
        print("Usage: b32 [-d] <text>")
        return
    if parts[0] == "-d":
        if len(parts) < 2:
            print("Usage: b32 -d <encoded>")
            return
        try:
            decoded = base64.b32decode(parts[1].encode()).decode("utf-8", errors="replace")
        except (ValueError, binascii.Error) as error:
            print(f"Invalid base32: {error}")
            return
        print(decoded)
        return
    print(base64.b32encode(parts[0].encode()).decode())


@register("urlenc", "URL-encode text")
def urlenc(arguments):
    if not arguments.strip():
        print("Usage: urlenc <text>")
        return
    print(urllib.parse.quote(arguments))


@register("urldec", "URL-decode text")
def urldec(arguments):
    if not arguments.strip():
        print("Usage: urldec <text>")
        return
    print(urllib.parse.unquote(arguments))


@register("hexenc", "Encode text as hex")
def hexenc(arguments):
    if not arguments.strip():
        print("Usage: hexenc <text>")
        return
    print(arguments.encode().hex())


@register("binenc", "Encode text as binary")
def binenc(arguments):
    if not arguments.strip():
        print("Usage: binenc <text>")
        return
    print("".join(f"{ord(char):08b}" for char in arguments))


@register("morse", "Encode or decode Morse code")
def morse(arguments):
    import hacklib
    text = arguments.strip()
    if not text:
        print("Usage: morse [-d] <text>")
        return
    if text.startswith("-d"):
        code = text[2:].strip()
        if not code:
            print("Usage: morse -d <code>")
            return
        print(hacklib.HACKLIB["dec_morse"](code))
        return
    print(hacklib.HACKLIB["enc_morse"](text))


@register("caesar", "Caesar cipher with a shift")
def caesar(arguments):
    parts = arguments.split(None, 1)
    if not parts:
        print("Usage: caesar <shift> <text>")
        return
    try:
        shift = int(parts[0]) % 26
    except ValueError:
        print("Usage: caesar <shift> <text>  (shift 1-25)")
        return
    text = parts[1].strip() if len(parts) > 1 else ""
    if not text:
        print("Usage: caesar <shift> <text>")
        return
    result = []
    for char in text:
        if "a" <= char <= "z":
            result.append(chr((ord(char) - 97 + shift) % 26 + 97))
        elif "A" <= char <= "Z":
            result.append(chr((ord(char) - 65 + shift) % 26 + 65))
        else:
            result.append(char)
    print("".join(result))


_LENGTH_FACTORS = {
    "km": 1000.0, "m": 1.0, "cm": 0.01, "mm": 0.001,
    "mi": 1609.344, "ft": 0.3048, "in": 0.0254, "yd": 0.9144,
}
_MASS_FACTORS = {
    "kg": 1.0, "g": 0.001, "mg": 0.000001, "lb": 0.45359237,
    "oz": 0.028349523125, "t": 1000.0, "st": 6.35029318,
}


@register("convert", "Convert units (temperature, length, mass)")
def convert(arguments):
    parts = arguments.split()
    if len(parts) != 3:
        print("Usage: convert <value> <from> <to>")
        print("  temperature: c f k")
        print("  length: km m cm mm mi ft in yd")
        print("  mass: kg g mg lb oz t st")
        return
    try:
        value = float(parts[0])
    except ValueError:
        print("Invalid number.")
        return
    source = parts[1].lower()
    target = parts[2].lower()
    if source in ("c", "f", "k") and target in ("c", "f", "k"):
        if source == "c":
            celsius = value
        elif source == "f":
            celsius = (value - 32) * 5 / 9
        else:
            celsius = value - 273.15
        if target == "c":
            result = celsius
        elif target == "f":
            result = celsius * 9 / 5 + 32
        else:
            result = celsius + 273.15
        print(f"{value} {source} = {result:.2f} {target}")
        return
    if source in _LENGTH_FACTORS and target in _LENGTH_FACTORS:
        result = value * _LENGTH_FACTORS[source] / _LENGTH_FACTORS[target]
        print(f"{value} {source} = {result:.6g} {target}")
        return
    if source in _MASS_FACTORS and target in _MASS_FACTORS:
        result = value * _MASS_FACTORS[source] / _MASS_FACTORS[target]
        print(f"{value} {source} = {result:.6g} {target}")
        return
    print(f"Unknown unit pair: {source} -> {target}")


@register("case", "Convert text case")
def case(arguments):
    parts = arguments.split(None, 1)
    if len(parts) != 2:
        print("Usage: case <style> <text>")
        print("  styles: upper lower title capitalize swapcase camel snake kebab pascal")
        return
    style = parts[0].lower()
    text = parts[1]
    if style == "upper":
        result = text.upper()
    elif style == "lower":
        result = text.lower()
    elif style == "title":
        result = text.title()
    elif style == "capitalize":
        result = text.capitalize()
    elif style == "swapcase":
        result = text.swapcase()
    elif style == "camel":
        result = re.sub(r"[_\-\s]+(.)", lambda m: m.group(1).upper(), text.lower())
    elif style == "snake":
        result = re.sub(r"[\s\-]+", "_", re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", text)).lower()
    elif style == "kebab":
        result = re.sub(r"[\s_]+", "-", re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", text)).lower()
    elif style == "pascal":
        result = re.sub(r"[_\-\s]+(.)", lambda m: m.group(1).upper(), text.lower())
        result = result[0].upper() + result[1:]
    else:
        print(f"Unknown style: {style}")
        return
    print(result)


@register("rev", "Reverse text")
def rev(arguments):
    if not arguments.strip():
        print("Usage: rev <text>")
        return
    print(arguments[::-1])


@register("nl", "Number the lines of a file")
def nl(arguments):
    if not arguments.strip():
        print("Usage: nl <file>")
        return
    path = Path(_strip_quotes(arguments)).expanduser()
    if not path.is_file():
        print(f"File not found: {path}")
        return
    for index, line in enumerate(_read_text(path).splitlines(), 1):
        print(f"{index:4d}  {line}")


@register("diff", "Compare two files")
def diff(arguments):
    parts = arguments.split(None, 1)
    if len(parts) != 2:
        print("Usage: diff <file1> <file2>")
        return
    first = Path(_strip_quotes(parts[0])).expanduser()
    second = Path(_strip_quotes(parts[1])).expanduser()
    if not first.is_file() or not second.is_file():
        print("Both files must exist.")
        return
    first_lines = _read_text(first).splitlines()
    second_lines = _read_text(second).splitlines()
    differences = list(
        difflib.unified_diff(
            first_lines, second_lines,
            fromfile=first.name, tofile=second.name, lineterm="",
        )
    )
    if not differences:
        print("Files are identical.")
        return
    for line in differences:
        if line.startswith("+"):
            print(colors.green(line))
        elif line.startswith("-"):
            print(colors.red(line))
        else:
            print(line)


@register("jsonfmt", "Pretty-print JSON")
def jsonfmt(arguments):
    if not arguments.strip():
        print("Usage: jsonfmt <json>")
        return
    try:
        data = json.loads(arguments)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON: {error}")
        return
    print(json.dumps(data, indent=2, ensure_ascii=False))


@register("csvview", "View a CSV file as a table")
def csvview(arguments):
    if not arguments.strip():
        print("Usage: csvview <file.csv>")
        return
    path = Path(_strip_quotes(arguments)).expanduser()
    if not path.is_file():
        print(f"File not found: {path}")
        return
    try:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            rows = list(csv.reader(handle))
    except OSError as error:
        print(f"Could not read file: {error}")
        return
    if not rows:
        print("(empty)")
        return
    column_count = max(len(row) for row in rows)
    widths = []
    for column in range(column_count):
        widths.append(max(len(str(row[column])) for row in rows if column < len(row)))
    for index, row in enumerate(rows):
        cells = []
        for column in range(column_count):
            value = str(row[column]) if column < len(row) else ""
            cells.append(value.ljust(widths[column]))
        print(" | ".join(cells).rstrip())
        if index == 0:
            print("-+-".join("-" * width for width in widths))


@register("zip", "Create a zip archive")
def zip_cmd(arguments):
    parts = arguments.split(None, 1)
    if len(parts) != 2:
        print("Usage: zip <archive.zip> <file1> <file2> ...")
        return
    archive_name = _strip_quotes(parts[0])
    file_names = parts[1].split()
    if not archive_name.endswith(".zip"):
        archive_name += ".zip"
    archive_path = Path(archive_name)
    try:
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for name in file_names:
                path = Path(_strip_quotes(name)).expanduser()
                if not path.exists():
                    print(f"Skipping (not found): {path}")
                    continue
                archive.write(path, path.name)
    except OSError as error:
        print(f"Could not create archive: {error}")
        return
    print(f"Created: {archive_path} ({archive_path.stat().st_size} bytes)")


@register("unzip", "Extract a zip archive")
def unzip(arguments):
    parts = arguments.split(None, 1)
    if not parts:
        print("Usage: unzip <archive.zip> [destination]")
        return
    archive_path = Path(_strip_quotes(parts[0])).expanduser()
    destination = Path(_strip_quotes(parts[1])).expanduser() if len(parts) > 1 else Path.cwd()
    if not archive_path.is_file():
        print(f"Not found: {archive_path}")
        return
    root = destination.resolve()
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.infolist():
                target = (destination / member.filename).resolve()
                try:
                    inside = os.path.commonpath((str(root), str(target))) == str(root)
                except ValueError:
                    inside = False
                if not inside:
                    print(f"Rejected unsafe archive path: {member.filename}")
                    return
                archive.extract(member, destination)
    except (OSError, zipfile.BadZipFile) as error:
        print(f"Could not extract: {error}")
        return
    print(f"Extracted to: {destination}")


@register("ziplist", "List files inside a zip archive")
def ziplist(arguments):
    archive_name = _strip_quotes(arguments)
    if not archive_name:
        print("Usage: ziplist <archive.zip>")
        return
    archive_path = Path(archive_name)
    if not archive_path.is_file():
        print(f"Not found: {archive_path}")
        return
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for info in archive.infolist():
                print(f"{info.file_size:>10}  {info.filename}")
    except (OSError, zipfile.BadZipFile) as error:
        print(f"Could not read archive: {error}")


@register("http", "Fetch a URL and show the response")
def http(arguments):
    url = _strip_quotes(arguments)
    if not url:
        print("Usage: http <url>")
        return
    if not url.lower().startswith(("http://", "https://")):
        url = "http://" + url
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            status = response.status
            content_type = response.headers.get("Content-Type", "unknown")
            content = response.read(64 * 1024).decode("utf-8", errors="replace")
    except (OSError, urllib.error.URLError) as error:
        print(f"Request failed: {error}")
        return
    print(f"Status: {status}")
    print(f"Type: {content_type}")
    print("---")
    print(content)
    if len(content) >= 64 * 1024:
        print("... (truncated)")


@register("arp", "Show the ARP table")
def arp(arguments):
    pkgcore.run_process(["arp", "-a"])


@register("webserver", "Start a temporary HTTP server")
def webserver(arguments):
    parts = arguments.split()
    try:
        port = int(parts[0]) if parts else 8000
    except ValueError:
        port = 8000
    seconds = _parse_int(parts[1] if len(parts) > 1 else "", 30, 300)
    if not 0 < port < 65536:
        print("Invalid port.")
        return
    try:
        server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    except OSError as error:
        print(f"Could not start server on port {port}: {error}")
        return
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Serving {Path.cwd()} on http://localhost:{port} for {seconds} seconds...")
    _time.sleep(seconds)
    server.shutdown()
    print("Server stopped.")


@register("ipscan", "Scan a subnet for live hosts")
def ipscan(arguments):
    prefix = _strip_quotes(arguments)
    if not prefix:
        print("Usage: ipscan <prefix>  e.g. ipscan 192.168.3")
        return
    parts = prefix.split(".")
    if len(parts) != 3 or not all(re.fullmatch(r"\d{1,3}", part) for part in parts):
        print("Invalid subnet prefix. Use three octets, e.g. ipscan 192.168.3")
        return

    def alive(host):
        result = subprocess.run(
            ["ping", "-n", "1", "-w", "400", host], capture_output=True
        )
        return host if result.returncode == 0 else None

    base = ".".join(parts)
    hosts = [f"{base}.{i}" for i in range(1, 255)]
    print(f"Scanning {base}.1-254 ...")
    found = []
    with ThreadPoolExecutor(max_workers=64) as pool:
        for result in pool.map(alive, hosts):
            if result:
                found.append(result)
                print(result)
    plural = "s" if len(found) != 1 else ""
    print(f"({len(found)} host{plural} alive)")


@register("top", "Show processes sorted by memory")
def top(arguments):
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 15 Name, Id, @{N='Mem(MB)';E={[math]::Round($_.WorkingSet64/1MB,1)}} | Format-Table -AutoSize",
    ]
    pkgcore.run_process(command)


@register("pkill", "Kill processes by name")
def pkill(arguments):
    name = _strip_quotes(arguments)
    if not name:
        print("Usage: pkill <process-name>")
        return
    if not re.fullmatch(r"[A-Za-z0-9_.\- ]+", name):
        print("Invalid process name.")
        return
    try:
        answer = input(f"Kill all processes named '{name}'? [y/N] ").strip().lower()
    except EOFError:
        print("Aborted.")
        return
    if answer not in ("y", "yes"):
        print("Aborted.")
        return
    pkgcore.run_process(["taskkill", "/IM", name])


@register("where", "Locate a command or program")
def where(arguments):
    name = _strip_quotes(arguments)
    if not name:
        print("Usage: where <name>")
        return
    pkgcore.run_process(["where", name])


@register("drives", "List disk drives")
def drives(arguments):
    found = False
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if os.path.exists(root):
            found = True
            try:
                usage = shutil.disk_usage(root)
                free = f"{usage.free / 1024 ** 3:.1f} GB free"
            except OSError:
                free = "?"
            print(f"{letter}:  {free}")
    if not found:
        print("No drives found.")


@register("title", "Set the console window title")
def title(arguments):
    if not arguments.strip():
        print("Usage: title <text>")
        return
    ctypes.windll.kernel32.SetConsoleTitleW(arguments)


@register("beep", "Make the speaker beep")
def beep(arguments):
    count = _parse_int(_strip_quotes(arguments), 1, 20)
    try:
        import winsound
        for _ in range(count):
            winsound.Beep(800, 150)
            _time.sleep(0.05)
    except (ImportError, OSError):
        print("\a" * count)


@register("sleep", "Wait for a number of seconds")
def sleep(arguments):
    seconds = _parse_int(_strip_quotes(arguments), 1, 3600)
    print(f"Waiting {seconds} seconds...")
    _time.sleep(seconds)
    print("Done.")


@register("py", "Execute a Python one-liner")
def py(arguments):
    code = arguments.strip()
    if not code:
        print("Usage: py <python-code>")
        return
    namespace = {"__builtins__": __builtins__}
    try:
        result = eval(code, namespace)
    except Exception:
        try:
            exec(code, namespace)
        except Exception as error:
            print(f"Error: {type(error).__name__}: {error}")
        return
    if result is not None:
        print(result)


@register("timer", "Countdown timer")
def timer(arguments):
    seconds = _parse_int(_strip_quotes(arguments), 10, 3600)
    print(f"Timer: {seconds} seconds")
    end = _time.time() + seconds
    while True:
        remaining = int(end - _time.time())
        if remaining <= 0:
            break
        print(f"\r{remaining:4d}s left...", end="", flush=True)
        _time.sleep(0.1)
    print("\rTime's up!              ")
    try:
        import winsound
        winsound.Beep(1000, 400)
    except (ImportError, OSError):
        pass


@register("clock", "Show a live clock for a few seconds")
def clock(arguments):
    seconds = _parse_int(_strip_quotes(arguments), 5, 30)
    end = _time.time() + seconds
    while _time.time() < end:
        print(f"\r{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", end="", flush=True)
        _time.sleep(0.2)
    print()


@register("hacksay", "Hacker-style speech bubble")
def hacksay(arguments):
    text = arguments.strip() or "Hack the planet!"
    width = len(text) + 2
    print(" " + "_" * width)
    print(f"< {text} >")
    print(" " + "-" * width)
    print("   \\")
    print("    (o)(o)")
    print("     /||\\")
    print("      /\\")


@register("guess", "Guess the number game")
def guess(arguments):
    target = random.randint(1, 100)
    print("I picked a number between 1 and 100. Guess it!")
    for attempt in range(1, 8):
        try:
            answer = input(f"Guess {attempt}/7: ")
        except EOFError:
            print("\nGame aborted.")
            return
        try:
            number = int(answer)
        except ValueError:
            print("Not a number.")
            continue
        if number < target:
            print("Higher!")
        elif number > target:
            print("Lower!")
        else:
            print(f"Correct! The number was {target}.")
            return
    print(f"Out of guesses. The number was {target}.")


@register("rps", "Rock paper scissors")
def rps(arguments):
    choice = _strip_quotes(arguments).lower()
    if choice not in ("rock", "paper", "scissors"):
        print("Usage: rps <rock|paper|scissors>")
        return
    opponent = random.choice(["rock", "paper", "scissors"])
    if choice == opponent:
        result = "Tie"
    elif (choice, opponent) in (("rock", "scissors"), ("paper", "rock"), ("scissors", "paper")):
        result = "You win!"
    else:
        result = "You lose!"
    print(f"You: {choice}  vs  Hacker: {opponent}  ->  {result}")


@register("dice", "Roll dice")
def dice(arguments):
    count = _parse_int(_strip_quotes(arguments), 1, 20)
    rolls = [random.randint(1, 6) for _ in range(count)]
    print(" ".join(str(roll) for roll in rolls))
    print(f"Total: {sum(rolls)}")


@register("coin", "Flip a coin")
def coin(arguments):
    print(random.choice(["Heads", "Tails"]))


@register("typewriter", "Type text with a typewriter effect")
def typewriter(arguments):
    text = arguments.strip() or "Hack the planet!"
    for char in text:
        print(char, end="", flush=True)
        _time.sleep(0.04)
    print()


@register("edit", "Full-screen terminal editor")
def edit(arguments):
    name = _strip_quotes(arguments)
    if not name:
        print("Usage: edit <file>")
        return
    path = Path(name).expanduser()
    if path.is_dir():
        print(f"Cannot edit a directory: {path}")
        return
    lines = []
    if path.exists():
        try:
            text = _read_text(path)
        except OSError as error:
            print(f"Could not read file: {error}")
            return
        lines = text.splitlines()
    else:
        print(f"{name}: No such file")
    if sys.stdin.isatty() and os.name == "nt":
        _edit_fullscreen(path, lines, name)
    else:
        _edit_line_mode(path, lines)


def _read_key():
    import msvcrt
    char = msvcrt.getwch()
    if char in ("\x00", "\xe0"):
        second = msvcrt.getwch()
        return {
            "H": "up", "P": "down", "K": "left", "M": "right",
            "G": "home", "O": "end", "I": "page_up", "Q": "page_down",
            "S": "delete", "R": "insert",
        }.get(second, "special")
    if char == "\x11":
        return "ctrl_q"
    if char == "\x13":
        return "ctrl_s"
    if char == "\r":
        return "enter"
    if char in ("\x08", "\x7f"):
        return "backspace"
    if char == "\x1b":
        return "escape"
    if char == "\x03":
        return "ctrl_c"
    return char


def _edit_fullscreen(path, lines, name):
    import msvcrt
    changed = False
    row = 0
    col = 0
    top = 0
    message = "Ctrl+S save  Ctrl+Q quit  arrows move  Enter newline"
    while True:
        width, height = shutil.get_terminal_size((80, 25))
        view_height = max(height - 4, 5)
        if not lines:
            row = 0
            col = 0
        else:
            if row >= len(lines):
                row = len(lines) - 1
            if col > len(lines[row]):
                col = len(lines[row])
        top = min(max(top, row - (view_height - 1) // 2), max(0, len(lines) - view_height))
        out = ["\x1b[2J\x1b[H"]
        title = f" Hacker Edit - {name}  {'[+]' if changed else ''}"
        out.append(f"\x1b[7m{title[:width - 1]:<{width - 1}}\x1b[0m")
        for index in range(view_height):
            line_index = top + index
            if line_index < len(lines):
                shown = lines[line_index][:width - 6]
                if line_index == row:
                    out.append(f"{line_index + 1:>4} \x1b[7m{shown:<{width - 6}}\x1b[0m")
                else:
                    out.append(f"{line_index + 1:>4} {shown}")
            else:
                out.append("~")
        status = f" Ln {row + 1}, Col {col + 1}  {len(lines)} lines  {'modified' if changed else ''}"
        out.append(f"\x1b[7m{status[:width - 1]:<{width - 1}}\x1b[0m")
        out.append(f" {message[:width - 1]}")
        sys.stdout.write("\n".join(out))
        sys.stdout.write(f"\x1b[{row - top + 2};{col + 6}H")
        sys.stdout.flush()
        key = _read_key()
        if key == "ctrl_q":
            if changed:
                sys.stdout.write("\r\x1b[2K\x1b[93mSave changes? [y/N] \x1b[0m")
                sys.stdout.flush()
                choice = msvcrt.getwch().lower()
                if choice == "y":
                    _write_lines(path, lines)
                    print("\r\x1b[2K\x1b[92mSaved: " + str(path) + "\x1b[0m")
                elif choice == "n":
                    print("\r\x1b[2K\x1b[91mChanges not saved.\x1b[0m")
                else:
                    message = "Quit cancelled"
                    continue
            break
        if key == "ctrl_s":
            if _write_lines(path, lines):
                changed = False
                message = "Saved (" + str(sum(len(line) + 1 for line in lines)) + " bytes)"
            else:
                message = "Save failed"
            continue
        if key in ("escape", "ctrl_c"):
            message = "Press Ctrl+S to save, Ctrl+Q to quit"
            continue
        if key == "up":
            if not lines:
                continue
            if row > 0:
                row -= 1
            col = min(col, len(lines[row]))
            continue
        if key == "down":
            if not lines:
                continue
            if row < len(lines) - 1:
                row += 1
            col = min(col, len(lines[row]))
            continue
        if key == "left":
            if not lines:
                continue
            col = max(0, col - 1)
            continue
        if key == "right":
            if not lines:
                continue
            col = min(len(lines[row]), col + 1)
            continue
        if key == "home":
            if not lines:
                continue
            col = 0
            continue
        if key == "end":
            if not lines:
                continue
            col = len(lines[row])
            continue
        if key == "page_up":
            if not lines:
                continue
            row = max(0, row - view_height + 1)
            col = min(col, len(lines[row]))
            continue
        if key == "page_down":
            if not lines:
                continue
            row = min(len(lines) - 1, row + view_height - 1)
            col = min(col, len(lines[row]))
            continue
        if key == "backspace":
            if not lines:
                continue
            if col > 0:
                lines[row] = lines[row][:col - 1] + lines[row][col:]
                col -= 1
            elif row > 0:
                col = len(lines[row - 1])
                lines[row - 1] += lines[row]
                del lines[row]
                row -= 1
            else:
                continue
            changed = True
            continue
        if key == "delete":
            if not lines:
                continue
            if col < len(lines[row]):
                lines[row] = lines[row][:col] + lines[row][col + 1:]
            elif row < len(lines) - 1:
                lines[row] += lines[row + 1]
                del lines[row + 1]
            else:
                continue
            changed = True
            continue
        if key == "enter":
            if not lines:
                lines.append("")
            elif col < len(lines[row]):
                lines.insert(row + 1, lines[row][col:])
                lines[row] = lines[row][:col]
                row += 1
            else:
                lines.insert(row + 1, "")
                row += 1
            col = 0
            changed = True
            continue
        if key in ("special", "insert"):
            message = "Unknown key"
            continue
        if not lines:
            lines.append("")
        lines[row] = lines[row][:col] + key + lines[row][col:]
        col += 1
        changed = True
        message = ""
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()


def _edit_line_mode(path, lines):
    current = len(lines)
    changed = False

    def edit_exit():
        nonlocal changed
        if changed:
            try:
                answer = input("Save changes? [y/N] ").strip().lower()
            except EOFError:
                answer = "n"
            if answer in ("y", "yes"):
                _write_lines(path, lines)
                print(f"Saved: {path}")
                return True
            if answer in ("n", "no"):
                print("Changes not saved.")
                return True
            print("Cancelled.")
            return False
        print("Edit closed.")
        return True

    def edit_help():
        print("ed-style editor (GNU ed). Commands:")
        print("  a / i / c     append / insert / change (end with .)")
        print("  N             move to line N")
        print("  $             move to the last line")
        print("  +N / -N       move relative to current line")
        print("  p / n         show current line / with number")
        print("  1,3p          show lines 1 to 3")
        print("  d / 1,3d      delete current / lines 1 to 3")
        print("  0a            append at the very top")
        print("  5a / 5i / 5c  operate on line 5")
        print("  s/old/new     replace in current line")
        print("  1,$s/old/new/g   replace in a range (g = all)")
        print("  w             save (shows byte count)")
        print("  q / Ctrl+Q    quit (asks to save if changed)")
        print("  wq            save and quit")
        print("  = / $=        show current line number / total lines")
        print("  (enter)       show the current line")
        print("  h             this help")
        print("  ?             error (ed tradition)")

    while True:
        try:
            line, quit_request = _read_edit_line()
        except EOFError:
            print()
            if changed:
                print("Changes not saved.")
            print("Edit closed.")
            return
        command = line.strip()
        if quit_request:
            if edit_exit():
                return
            continue
        if not command:
            if current >= 1:
                print(lines[current - 1])
            continue
        if command == "h":
            edit_help()
            continue
        if command == "q":
            if edit_exit():
                return
            continue
        if command == "wq":
            _write_lines(path, lines)
            print("Edit closed.")
            return
        if command == "w":
            if _write_lines(path, lines):
                changed = False
                print(sum(len(line) + 1 for line in lines))
            continue
        if "s/" in command:
            address_part, _, rest = command.partition("s/")
            pieces = rest.split("/")
            if len(pieces) < 2 or not pieces[0]:
                print("?")
                continue
            old = pieces[0]
            new = pieces[1] if len(pieces) > 1 else ""
            global_flag = len(pieces) > 2 and pieces[2] == "g"
            if address_part:
                if "," in address_part:
                    start_text, end_text = address_part.split(",", 1)
                    start = _ed_resolve(start_text, current, lines)
                    end = _ed_resolve(end_text, current, lines)
                else:
                    start = _ed_resolve(address_part, current, lines)
                    end = start
            else:
                start = end = current
            if not 1 <= start <= len(lines) or end < start or end > len(lines):
                print("?")
                continue
            count = 0
            for index in range(start - 1, end):
                updated = re.sub(
                    re.escape(old), new.replace("\\", "\\\\"), lines[index],
                    count=0 if global_flag else 1,
                )
                if updated != lines[index]:
                    lines[index] = updated
                    count += 1
            if count == 0:
                print("?")
            else:
                changed = True
            continue
        match = re.fullmatch(r"([0-9,$\.+\-]*)([a-zA-Z=]?)", command)
        if not match:
            print("?")
            continue
        address_text, letter = match.groups()
        start_text, end_text = address_text, address_text
        if "," in address_text:
            start_text, end_text = address_text.split(",", 1)
        start = _ed_resolve(start_text, current, lines)
        end = _ed_resolve(end_text, current, lines)
        if not letter:
            if 1 <= start <= len(lines):
                current = start
            else:
                print("?")
            continue
        if letter in ("a", "i", "c"):
            if letter == "a":
                if not 0 <= start <= len(lines):
                    print("?")
                    continue
                position = start
            elif letter == "i":
                if not 1 <= start <= len(lines) + 1:
                    print("?")
                    continue
                position = start - 1
            else:
                if not 1 <= start <= len(lines):
                    print("?")
                    continue
                del lines[start - 1]
                position = start - 1
                changed = True
            collected = []
            while True:
                try:
                    line, quit_request = _read_edit_line()
                except EOFError:
                    break
                if quit_request:
                    if edit_exit():
                        return
                    continue
                if line == ".":
                    break
                if line == "\\.":
                    line = "."
                collected.append(line)
            if collected:
                lines[position:position] = collected
                current = position + len(collected)
                changed = True
            continue
        if letter in ("p", "n"):
            if not 1 <= start <= len(lines) or end < start or end > len(lines):
                print("?")
                continue
            for index in range(start, end + 1):
                if letter == "n":
                    print(f"{index}\t{lines[index - 1]}")
                else:
                    print(lines[index - 1])
            current = end
            continue
        if letter == "d":
            if not 1 <= start <= len(lines):
                print("?")
                continue
            if end > len(lines):
                end = len(lines)
            del lines[start - 1:end]
            changed = True
            current = min(start, len(lines))
            continue
        if letter == "=":
            print(start)
            continue
        print("?")


@register("syst", "Run a system command through cmd")
def syst(arguments):
    if not arguments.strip():
        print("Usage: syst <command>")
        return
    try:
        process = subprocess.Popen(
            ["cmd.exe", "/c", arguments],
            stdin=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
    except OSError as error:
        print(f"Could not start command: {error}")
        return
    process.wait()


@register("shell", "Open an interactive cmd.exe shell (type exit to return)")
def shell(arguments):
    try:
        process = subprocess.Popen(["cmd.exe", "/k"])
    except OSError as error:
        print(f"Could not start shell: {error}")
        return
    process.wait()


@register("mkiso", "Create an ISO image from a folder")
def mkiso(arguments):
    parts = arguments.split(None, 1)
    if not parts:
        print("Usage: mkiso <folder> [output.iso]")
        return
    source = Path(_strip_quotes(parts[0])).expanduser()
    if not source.is_dir():
        print(f"Folder not found: {source}")
        return
    if len(parts) > 1:
        output = Path(_strip_quotes(parts[1])).expanduser()
    else:
        output = Path.cwd() / f"{source.name}.iso"
    if output.exists():
        try:
            answer = input(f"Overwrite {output.name}? [y/N] ").strip().lower()
        except EOFError:
            answer = "n"
        if answer not in ("y", "yes"):
            print("Aborted.")
            return
    try:
        import iso_builder
        size = iso_builder.build_iso(str(source), str(output))
    except Exception as error:
        print(f"ISO creation failed: {type(error).__name__}: {error}")
        return
    print(f"Created: {output} ({size} bytes)")


# ========================================================================
# REAL HACKER TOOL PACK (assistant tools, terminal edition)
# Every tool below is real and implemented with the standard library only.
# ========================================================================

# ---- native Windows plumbing (Toolhelp32 / GetSystemTimes / psapi) ----
class _PE32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.c_ulong), ("cntUsage", ctypes.c_ulong),
        ("th32ProcessID", ctypes.c_ulong), ("th32DefaultHeapID", ctypes.c_void_p),
        ("th32ModuleID", ctypes.c_ulong), ("cntThreads", ctypes.c_ulong),
        ("th32ParentProcessID", ctypes.c_ulong), ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", ctypes.c_ulong), ("szExeFile", ctypes.c_wchar * 260),
    ]


class _PMCW(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
    ]


class _MEMSTATUSW(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


_k32 = ctypes.windll.kernel32
_psapi = ctypes.windll.psapi


def _hack_processes():
    results = []
    snap = _k32.CreateToolhelp32Snapshot(0x00000002, 0)
    if snap == -1:
        return results
    try:
        entry = _PE32W()
        entry.dwSize = ctypes.sizeof(_PE32W)
        ok = _k32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            pid = entry.th32ProcessID
            mem = 0
            if pid:
                handle = _k32.OpenProcess(0x1000, 0, pid)
                if handle:
                    pmc = _PMCW()
                    pmc.cb = ctypes.sizeof(_PMCW)
                    if _psapi.GetProcessMemoryInfo(handle, ctypes.byref(pmc),
                                                   ctypes.sizeof(_PMCW)):
                        mem = pmc.WorkingSetSize
                    _k32.CloseHandle(handle)
            results.append((pid, entry.th32ParentProcessID, entry.szExeFile,
                            entry.cntThreads, mem))
            ok = _k32.Process32NextW(snap, ctypes.byref(entry))
    finally:
        _k32.CloseHandle(snap)
    return results


def _cpu_sample():
    idle = ctypes.c_ulonglong()
    kernel = ctypes.c_ulonglong()
    user = ctypes.c_ulonglong()
    if not _k32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel),
                               ctypes.byref(user)):
        return None
    return idle.value, kernel.value, user.value


def _mem_info():
    m = _MEMSTATUSW()
    m.dwLength = ctypes.sizeof(_MEMSTATUSW)
    if _k32.GlobalMemoryStatusEx(ctypes.byref(m)):
        return m
    return None


def _run_cap(cmd):
    """Run a system command, capture stdout as text (tolerate GBK/UTF-8)."""
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=25)
        raw = r.stdout
        for encoding in ("utf-8", "gbk"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")
    except (OSError, subprocess.TimeoutExpired):
        return ""


# ---------------------------------------------------------------- processes
@register("procs", "Native process list (PID/PPID/threads/memory)")
def cmd_procs(arguments):
    rows = _hack_processes()
    if not rows:
        print("Could not enumerate processes.")
        return
    rows.sort(key=lambda r: -r[4])
    print(f"{'PID':>6} {'PPID':>6} {'THR':>4} {'MEM(MB)':>9}  NAME")
    for pid, ppid, name, thr, mem in rows[:40]:
        print(f"{pid:>6} {ppid:>6} {thr:>4} {mem / 1048576:>9.1f}  {name}")
    print(f"({len(rows)} processes, showing top 40 by memory)")


# ---------------------------------------------------------------- monitor
@register("mon", "Live system monitor - CPU / RAM / disk (q to quit)")
def cmd_mon(arguments):
    try:
        import msvcrt
    except ImportError:
        msvcrt = None
    first = _cpu_sample()
    if first is None:
        print("Cannot read CPU times.")
        return
    try:
        while True:
            second = _cpu_sample()
            total = (second[1] - first[1]) + (second[2] - first[2])
            cpu = (100.0 * (1.0 - (second[0] - first[0]) / total)
                   if total else 0.0)
            first = second
            m = _mem_info()
            if m:
                mem = f"RAM {m.dwMemoryLoad:>3}%  {(m.ullTotalPhys - m.ullAvailPhys) / 1073741824:.1f}/{(m.ullTotalPhys / 1073741824):.1f} GB"
            else:
                mem = "RAM n/a"
            try:
                d = shutil.disk_usage(os.path.splitdrive(os.getcwd())[0] + "\\")
                disk = f"DISK {100 * d.used // d.total:>3}%  {d.free / 1073741824:.0f} GB free"
            except OSError:
                disk = "DISK n/a"
            print(f"\rCPU {cpu:5.1f}%  |  {mem}  |  {disk}  ", end="", flush=True)
            if msvcrt is not None and msvcrt.kbhit():
                if msvcrt.getch().lower() in (b"q",):
                    print()
                    return
            _time.sleep(1)
    except KeyboardInterrupt:
        print()


# ---------------------------------------------------------------- portscan
@register("portscan", "Multi-threaded port scan - portscan <host> [start-end]")
def cmd_portscan(arguments):
    parts = arguments.split()
    host = _strip_quotes(parts[0]) if parts else ""
    if not host:
        print("Usage: portscan <host> [start-end]  e.g. portscan 192.168.1.1 1-1024")
        return
    try:
        socket.getaddrinfo(host, None)
    except socket.gaierror:
        print(f"Could not resolve: {host}")
        return
    lo, hi = 1, 1024
    if len(parts) > 1:
        spec = parts[1]
        if "-" in spec:
            try:
                lo, hi = (int(x) for x in spec.split("-", 1))
            except ValueError:
                print("Invalid port range.")
                return
        else:
            try:
                lo = hi = int(spec)
            except ValueError:
                print("Invalid port range.")
                return
    lo = max(1, min(lo, 65535))
    hi = max(lo, min(hi, 65535))
    ports = list(range(lo, hi + 1))
    print(f"Scanning {host} ports {lo}-{hi} ({len(ports)} ports)...")

    def probe(port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.4)
        try:
            return (port, sock.connect_ex((host, port)) == 0)
        except OSError:
            return (port, False)
        finally:
            sock.close()

    open_ports = []
    with ThreadPoolExecutor(max_workers=96) as pool:
        for port, opened in pool.map(probe, ports):
            if opened:
                open_ports.append(port)
                service = {21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp",
                           53: "dns", 80: "http", 110: "pop3", 135: "msrpc",
                           139: "netbios-ssn", 143: "imap", 443: "https",
                           445: "microsoft-ds", 465: "smtps", 587: "submission",
                           993: "imaps", 995: "pop3s", 1080: "socks",
                           1433: "ms-sql", 1521: "oracle", 1723: "pptp",
                           3306: "mysql", 3389: "ms-rdp", 5432: "postgresql",
                           5900: "vnc", 5985: "winrm", 6379: "redis",
                           8080: "http-proxy", 8443: "https-alt",
                           8888: "http-alt", 9200: "elasticsearch",
                           27017: "mongodb"}.get(port, "")
                print(f"  {port:>6}  open   {service}")
    if not open_ports:
        print("No open ports found.")
    else:
        print(f"({len(open_ports)} open port(s))")


# ---------------------------------------------------------------- http
@register("headers", "Show HTTP response headers - headers <url>")
def cmd_headers(arguments):
    url = _strip_quotes(arguments)
    if not url:
        print("Usage: headers <url>  e.g. headers https://example.com")
        return
    if "://" not in url:
        url = "http://" + url
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"{resp.status} {resp.reason}  ({resp.url})")
            for key, value in resp.headers.items():
                print(f"  {key}: {value}")
    except (OSError, urllib.error.URLError) as error:
        print(f"Request failed: {error}")


@register("dns", "DNS resolution - dns <host>")
def cmd_dns(arguments):
    host = _strip_quotes(arguments)
    if not host:
        print("Usage: dns <host>  e.g. dns example.com")
        return
    print(f"Resolving {host} ...")
    try:
        for family, label in ((socket.AF_INET, "A"),
                              (socket.AF_INET6, "AAAA")):
            infos = socket.getaddrinfo(host, None, family)
            for info in infos[:6]:
                print(f"  {label:<5} {info[4][0]}")
    except socket.gaierror:
        print("  no address records found")
    for rtype in ("MX", "TXT"):
        out = _run_cap(["nslookup", "-type=" + rtype, host])
        for line in out.splitlines():
            stripped = line.strip()
            if stripped and (rtype + " preference" in stripped
                             or '"' in stripped or stripped.startswith("        ")):
                print(f"  {rtype:<5} {stripped}")
    print("(A/AAAA from getaddrinfo, MX/TXT from nslookup)")


# ---------------------------------------------------------------- network recon
@register("netrecon", "Network recon summary - adapters / arp / top connections")
def cmd_netrecon(arguments):
    print("== ADAPTERS ==")
    out = _run_cap(["ipconfig"])
    current = None
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.endswith(":") and "IPv4" not in line and "IPv6" not in line:
            current = line.rstrip(":")
            print(f"\n[{current}]")
        elif current and line.lower().startswith(("ipv4", "ipv6")):
            print(f"  {line}")
    print("\n== ARP CACHE ==")
    arp_out = _run_cap(["arp", "-a"])
    for line in arp_out.splitlines():
        if line.strip():
            print(f"  {line.strip()}")
    print("\n== TOP TCP CONNECTIONS ==")
    ns = _run_cap(["netstat", "-ano"])
    conns = []
    for line in ns.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[0].upper() == "TCP":
            conns.append((parts[1], parts[2], parts[3], parts[4]))
    state_counts = {}
    for _l, _r, state, _p in conns:
        state_counts[state] = state_counts.get(state, 0) + 1
    print("  by state:", ", ".join(f"{k}={v}" for k, v in state_counts.items()))
    for local, remote, state, pid in conns[:12]:
        print(f"  {local:<24}{remote:<24}{state:<12}{pid}")


@register("dnsflush", "Flush the DNS resolver cache")
def cmd_dnsflush(arguments):
    try:
        r = subprocess.run(["ipconfig", "/flushdns"],
                           capture_output=True, timeout=20)
        ok = r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        ok = False
    print("DNS cache flushed." if ok else "flush failed (run as administrator?).")


# ---------------------------------------------------------------- system forensics
@register("boot", "Startup entries - registry Run keys + Startup folder")
def cmd_boot(arguments):
    keys = [
        ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Run"),
        ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
        ("HKLM", r"Software\Microsoft\Windows\CurrentVersion\Run"),
        ("HKLM", r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
    ]
    for hive, key in keys:
        print(f"[{hive}\\{key}]")
        out = _run_cap(["reg", "query", f"{hive}\\{key}"])
        entries = [l for l in out.splitlines() if l.strip() and not l.strip().startswith("!")]
        if len(entries) <= 1:
            print("  (empty)")
        else:
            for line in entries[1:]:
                parts = line.split(None, 2)
                if len(parts) >= 3:
                    print(f"  {parts[0]:<28} {parts[2][:90]}")
    startup = os.path.join(os.environ.get("APPDATA", ""),
                           "Microsoft", "Windows", "Start Menu",
                           "Programs", "Startup")
    print(f"[STARTUP FOLDER] {startup}")
    if os.path.isdir(startup):
        items = os.listdir(startup)
        if not items:
            print("  (empty)")
        else:
            for name in items:
                print(f"  {name}")


@register("services", "Service list with status - services [keyword]")
def cmd_services(arguments):
    keyword = arguments.strip().lower()
    out = _run_cap(["sc", "query", "state=", "all"])
    services = []
    current = {}
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("SERVICE_NAME:"):
            if current:
                services.append(current)
            current = {"name": line.split(":", 1)[1].strip()}
        elif line.startswith("DISPLAY_NAME:"):
            current["display"] = line.split(":", 1)[1].strip()
        elif line.startswith("STATE"):
            current["state"] = line.split(":", 1)[1].strip().split()[0]
    if current:
        services.append(current)
    shown = 0
    for s in services:
        if keyword and keyword not in s["name"].lower() and keyword not in s.get("display", "").lower():
            continue
        print(f"  {s['name']:<40} {s.get('state', '?'):<12} {s.get('display', '')}")
        shown += 1
    print(f"({shown} service(s) shown of {len(services)})")


@register("drivers", "Kernel driver list - drivers [keyword]")
def cmd_drivers(arguments):
    keyword = arguments.strip().lower()
    out = _run_cap(["driverquery", "/fo", "csv", "/v"])
    lines = [l for l in out.splitlines() if l.strip()]
    if len(lines) < 2:
        print("Could not enumerate drivers (run as administrator?).")
        return
    header = [h.strip('"') for h in lines[0].split('","')]
    rows = [line.strip('"').split('","') for line in lines[1:]]
    shown = 0
    for row in rows:
        name = row[0] if row else ""
        if keyword and keyword not in name.lower():
            continue
        state = row[5] if len(row) > 5 else "?"
        print(f"  {name:<36} {state}")
        shown += 1
    print(f"({shown} driver(s))")


@register("shares", "Network shares on this machine")
def cmd_shares(arguments):
    out = _run_cap(["net", "share"])
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    if len(lines) < 3:
        print("Could not list shares.")
        return
    for line in lines[3:]:
        print(f"  {line}")
    print(f"({len(lines) - 3} share(s))")


@register("sched", "Scheduled tasks - sched [keyword]")
def cmd_sched(arguments):
    keyword = arguments.strip().lower()
    out = _run_cap(["schtasks", "/fo", "csv", "/nh"])
    tasks = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.strip('"').split('","')
        if len(parts) >= 3:
            tasks.append((parts[0], parts[1], parts[2]))
    shown = 0
    for name, nxt, state in tasks:
        if keyword and keyword not in name.lower():
            continue
        print(f"  {name:<55} {state:<12} next: {nxt}")
        shown += 1
    print(f"({shown} task(s) shown of {len(tasks)})")


@register("eventlog", "Recent event log entries - eventlog <log> [count]")
def cmd_eventlog(arguments):
    parts = arguments.split()
    log = parts[0] if parts else ""
    if not log:
        print("Usage: eventlog <log> [count]  e.g. eventlog System 10")
        print("Common logs: System, Application, Security, Setup")
        return
    count = 10
    if len(parts) > 1:
        try:
            count = max(1, min(int(parts[1]), 50))
        except ValueError:
            count = 10
    out = _run_cap(["wevtutil", "qe", log, "/c:" + str(count),
                    "/rd:true", "/f:text"])
    if not out.strip():
        print(f"No entries (log '{log}' may need administrator rights).")
        return
    chunks = out.split("\n\n")
    for chunk in chunks[:count]:
        chunk = chunk.strip()
        if not chunk:
            continue
        date = ""
        level = ""
        source = ""
        body = []
        for line in chunk.splitlines():
            stripped = line.strip()
            if stripped.startswith("Date:"):
                date = stripped.split("Date:", 1)[1].strip()[:25]
            elif stripped.startswith("Level:"):
                level = stripped.split("Level:", 1)[1].strip()
            elif stripped.startswith("Provider:"):
                source = stripped.split("Provider:", 1)[1].strip()[:40]
            elif stripped.startswith("Event ID:"):
                pass
            elif stripped and not stripped.endswith(":"):
                body.append(stripped)
        print(f"\n[{date}] {level} {source}")
        for b in body[:3]:
            print(f"    {b[:150]}")


@register("recent", "Recently opened files - recent [count]")
def cmd_recent(arguments):
    count = 20
    if arguments.strip():
        try:
            count = max(1, min(int(arguments.strip()), 200))
        except ValueError:
            count = 20
    recent_dir = os.path.join(os.environ.get("APPDATA", ""),
                              "Microsoft", "Windows", "Recent")
    if not os.path.isdir(recent_dir):
        print("Recent folder not found.")
        return
    items = sorted(os.listdir(recent_dir),
                   key=lambda n: os.path.getmtime(os.path.join(recent_dir, n)),
                   reverse=True)[:count]
    for name in items:
        full = os.path.join(recent_dir, name)
        stamp = datetime.datetime.fromtimestamp(os.path.getmtime(full))
        print(f"  {stamp:%Y-%m-%d %H:%M}  {name[:-4] if name.lower().endswith('.lnk') else name}")
    print(f"({len(items)} recent file(s))")


@register("hosts", "Show the hosts file")
def cmd_hosts(arguments):
    hosts = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"),
                         "System32", "drivers", "etc", "hosts")
    if not os.path.isfile(hosts):
        print("hosts file not found.")
        return
    with io.open(hosts, encoding="utf-8", errors="replace") as f:
        content = f.read()
    print(content if content.strip() else "(hosts file is empty)")
    print(f"({os.path.getsize(hosts)} bytes)")


# ---------------------------------------------------------------- file forensics
@register("strings", "Extract printable strings from a file - strings <file> [min]")
def cmd_strings(arguments):
    parts = arguments.split(None, 1)
    path = _strip_quotes(parts[0]) if parts else ""
    if not path:
        print("Usage: strings <file> [min-length]")
        return
    try:
        with io.open(path, "rb") as f:
            data = f.read()
    except OSError as error:
        print(f"Cannot read {path}: {error}")
        return
    min_len = 4
    if len(parts) > 1:
        try:
            min_len = max(1, int(parts[1]))
        except ValueError:
            pass
    current = bytearray()
    found = 0
    for byte in data:
        if 32 <= byte < 127:
            current.append(byte)
        else:
            if len(current) >= min_len:
                print("  " + current.decode("ascii", "replace"))
                found += 1
            current = bytearray()
    if len(current) >= min_len:
        print("  " + current.decode("ascii", "replace"))
        found += 1
    print(f"({found} string(s), min {min_len} chars, {len(data)} bytes)")


@register("largest", "Largest files under a directory - largest [dir] [count]")
def cmd_largest(arguments):
    parts = arguments.split()
    directory = _strip_quotes(parts[0]) if parts else os.getcwd()
    count = 15
    if len(parts) > 1:
        try:
            count = max(1, min(int(parts[1]), 100))
        except ValueError:
            count = 15
    if not os.path.isdir(directory):
        print(f"Not a directory: {directory}")
        return
    found = []
    scanned = 0
    for root, _dirs, files in os.walk(directory):
        for name in files:
            try:
                full = os.path.join(root, name)
                size = os.path.getsize(full)
                scanned += 1
                found.append((size, full))
            except OSError:
                pass
    found.sort(reverse=True)
    print(f"({scanned} files scanned)")
    for size, full in found[:count]:
        print(f"  {size / 1048576:>10.1f} MB  {full}")


@register("dupes", "Find duplicate files by size and hash - dupes [dir]")
def cmd_dupes(arguments):
    directory = _strip_quotes(arguments) if arguments.strip() else os.getcwd()
    if not os.path.isdir(directory):
        print(f"Not a directory: {directory}")
        return
    by_size = {}
    scanned = 0
    for root, _dirs, files in os.walk(directory):
        for name in files:
            try:
                full = os.path.join(root, name)
                size = os.path.getsize(full)
                if size > 0:
                    by_size.setdefault(size, []).append(full)
                scanned += 1
            except OSError:
                pass
    dupes = 0
    for size, paths in by_size.items():
        if len(paths) < 2:
            continue
        groups = {}
        for path in paths:
            try:
                with open(path, "rb") as f:
                    digest = hashlib.md5(f.read()).hexdigest()
            except OSError:
                continue
            groups.setdefault(digest, []).append(path)
        for digest, members in groups.items():
            if len(members) > 1:
                dupes += 1
                print(f"DUPLICATE ({size} bytes, {digest[:10]}...):")
                for member in members:
                    print(f"  {member}")
    print(f"({scanned} files scanned, {dupes} duplicate group(s))")


@register("wipe", "Securely overwrite and delete a file (3 passes)")
def cmd_wipe(arguments):
    path = _strip_quotes(arguments)
    if not path:
        print("Usage: wipe <file>")
        return
    if not os.path.isfile(path):
        print(f"Not a file: {path}")
        return
    size = os.path.getsize(path)
    try:
        answer = input(f"Overwrite 3x and delete {path} ({size} bytes)? [y/N] ").strip().lower()
    except EOFError:
        print("Aborted.")
        return
    if answer not in ("y", "yes"):
        print("Aborted.")
        return
    try:
        with io.open(path, "r+b") as f:
            patterns = (b"\xff" * 65536, b"\x00" * 65536, os.urandom(65536))
            for pattern in patterns:
                f.seek(0)
                written = 0
                while written < size:
                    chunk = pattern[:min(65536, size - written)]
                    f.write(chunk)
                    written += len(chunk)
                f.flush()
                os.fsync(f.fileno())
        os.remove(path)
    except OSError as error:
        print(f"Wipe failed: {error}")
        return
    print(f"Wiped and deleted: {path}")


@register("hashfile", "Hash a file - hashfile <file>")
def cmd_hashfile(arguments):
    path = _strip_quotes(arguments)
    if not path or not os.path.isfile(path):
        print("Usage: hashfile <file>")
        return
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    try:
        with io.open(path, "rb") as f:
            while True:
                chunk = f.read(1 << 20)
                if not chunk:
                    break
                md5.update(chunk)
                sha1.update(chunk)
                sha256.update(chunk)
    except OSError as error:
        print(f"Cannot read: {error}")
        return
    print(f"MD5    {md5.hexdigest()}")
    print(f"SHA1   {sha1.hexdigest()}")
    print(f"SHA256 {sha256.hexdigest()}")


# ---------------------------------------------------------------- crypto toolbox
@register("crypt", "Hash text - crypt <md5|sha1|sha256|sha512|crc32> <text>")
def cmd_crypt(arguments):
    parts = arguments.split(None, 1)
    algo = parts[0].strip().lower() if parts else ""
    text = parts[1] if len(parts) > 1 else ""
    if algo not in ("md5", "sha1", "sha256", "sha512", "crc32"):
        print("Usage: crypt <md5|sha1|sha256|sha512|crc32> <text>")
        return
    if algo == "crc32":
        value = zlib.crc32(text.encode("utf-8")) & 0xFFFFFFFF
        print(f"crc32: {value:08x}")
        return
    digest = getattr(hashlib, algo)(text.encode("utf-8")).hexdigest()
    print(f"{algo}: {digest}")


@register("xor", "XOR a string with a key - xor <key> <text>")
def cmd_xor(arguments):
    parts = arguments.split(None, 1)
    key = parts[0] if parts else ""
    text = parts[1] if len(parts) > 1 else ""
    if not key:
        print("Usage: xor <key> <text>")
        return
    key_bytes = key.encode("utf-8")
    data = text.encode("utf-8")
    out = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data))
    printable = all(32 <= b < 127 for b in out)
    if printable:
        print(out.decode("ascii"))
    else:
        print("hex: " + out.hex())


@register("rc4", "RC4 stream cipher - rc4 <key> <text>")
def cmd_rc4(arguments):
    parts = arguments.split(None, 1)
    key = parts[0] if parts else ""
    text = parts[1] if len(parts) > 1 else ""
    if not key:
        print("Usage: rc4 <key> <text>")
        return

    def rc4(key_bytes, data):
        s = list(range(256))
        j = 0
        for i in range(256):
            j = (j + s[i] + key_bytes[i % len(key_bytes)]) & 0xFF
            s[i], s[j] = s[j], s[i]
        i = j = 0
        out = bytearray()
        for byte in data:
            i = (i + 1) & 0xFF
            j = (j + s[i]) & 0xFF
            s[i], s[j] = s[j], s[i]
            out.append(byte ^ s[(s[i] + s[j]) & 0xFF])
        return bytes(out)

    data = text.encode("utf-8")
    result = rc4(key.encode("utf-8"), data)
    printable = all(32 <= b < 127 for b in result)
    if printable:
        print(result.decode("ascii"))
    else:
        print("hex: " + result.hex())


@register("vigenere", "Vigenere cipher - vigenere <key> <text> [-d]")
def cmd_vigenere(arguments):
    parts = arguments.split(None, 1)
    key = parts[0] if parts else ""
    rest = parts[1].strip() if len(parts) > 1 else ""
    decode = False
    if rest.lower().endswith("-d"):
        decode = True
        rest = rest[:-2].strip()
    text = rest
    if not key or not text:
        print("Usage: vigenere <key> <text> [-d]")
        return
    key = re.sub(r"[^a-zA-Z]", "", key).upper()
    if not key:
        print("Key must contain letters.")
        return
    shifts = [ord(c) - 65 for c in key]
    out = []
    ki = 0
    for ch in text:
        if ch.isalpha():
            base = 65 if ch.isupper() else 97
            shift = shifts[ki % len(shifts)]
            ki += 1
            if decode:
                shift = -shift
            out.append(chr(base + (ord(ch) - base + shift) % 26))
        else:
            out.append(ch)
    print("".join(out))


@register("leet", "Convert text to leetspeak - leet <text>")
def cmd_leet(arguments):
    if not arguments.strip():
        print("Usage: leet <text>")
        return
    table = str.maketrans({
        "a": "4", "e": "3", "i": "1", "o": "0", "s": "5",
        "t": "7", "b": "8", "g": "9", "l": "1", "z": "2",
    })
    print(arguments.translate(table))


# ========================================================================
# INCIDENT RESPONSE KIT (defensive - acts on THIS machine only)
# When a machine is compromised the right counter-move is containment:
# kill the suspicious process, cut the network, scan for traces, harden.
# No offensive payloads: these tools only ever affect the local host.
# ========================================================================

_SUSPICIOUS_DIR_HINTS = (
    "\\temp\\", "\\tmp\\", "\\appdata\\local\\temp", "\\downloads\\",
    "\\programdata\\", "\\public\\",
)

_SUSPICIOUS_NAME_HINTS = (
    "winupdate", "sysupd", "svch0st", "scvhost", "windowsupdate",
    "defenderupd", "powershel1", "cmd1.exe", "spoolsvc.exe ",
    "wscript", "cscript", "mshta", "regsvr32",
)

_SUSPICIOUS_EXTENSIONS = (".ps1", ".vbs", ".bat", ".cmd", ".hta", ".scr", ".js")


def _find_pid(token):
    """Resolve a pid or a process name into (pid, name) or None."""
    token = token.strip()
    if token.isdigit():
        for pid, ppid, name, thr, mem in _hack_processes():
            if pid == int(token):
                return pid, name
        return None
    low = token.lower()
    for pid, ppid, name, thr, mem in _hack_processes():
        if name.lower().startswith(low):
            return pid, name
    return None


@register("quarantine", "Kill a suspicious process - quarantine <pid|name>")
def cmd_quarantine(arguments):
    token = arguments.strip()
    if not token:
        print("Usage: quarantine <pid|name>   e.g. quarantine 4821 or quarantine winupdate.exe")
        return
    found = _find_pid(token)
    if found is None:
        print(f"Nothing running matches: {token}")
        return
    pid, name = found
    try:
        answer = input(f"Terminate {name} (pid {pid})? [y/N] ").strip().lower()
    except EOFError:
        print("Aborted.")
        return
    if answer not in ("y", "yes"):
        print("Aborted.")
        return
    handle = _k32.OpenProcess(0x0001, 0, pid)
    if not handle:
        print(f"pid {pid}: access denied (needs administrator).")
        return
    try:
        ok = _k32.TerminateProcess(handle, 1)
    finally:
        _k32.CloseHandle(handle)
    if not ok:
        print(f"pid {pid}: terminate failed.")
        return
    print(f"pid {pid} ({name}) terminated.")
    # report if it also lives in a startup location
    matches = []
    for hive, key in (("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Run"),
                      ("HKLM", r"Software\Microsoft\Windows\CurrentVersion\Run")):
        out = _run_cap(["reg", "query", f"{hive}\\{key}"])
        for line in out.splitlines():
            if name.split(".")[0].lower() in line.lower():
                matches.append(f"{hive}\\{key} -> {line.strip()}")
    if matches:
        print("WARNING: found in startup entries - remove it with a registry editor:")
        for m in matches:
            print(f"  {m}")


@register("netcut", "Emergency: release all network addresses (y/N confirm)")
def cmd_netcut(arguments):
    try:
        answer = input("Release ALL network addresses (offline now, recover with 'netup')? [y/N] ").strip().lower()
    except EOFError:
        print("Aborted.")
        return
    if answer not in ("y", "yes"):
        print("Aborted.")
        return
    try:
        r = subprocess.run(["ipconfig", "/release"], capture_output=True,
                           timeout=60)
        ok = r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        ok = False
    print("Network released - machine is offline." if ok
          else "release failed (run as administrator?).")
    print("Recover with: netup")


@register("netup", "Restore network addresses after netcut")
def cmd_netup(arguments):
    try:
        r = subprocess.run(["ipconfig", "/renew"], capture_output=True,
                           timeout=90)
        ok = r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        ok = False
    print("Network renewed." if ok
          else "renew failed (run as administrator? check adapters).")


@register("scanmal", "Scan this machine for malware traces (startup/procs/hosts/temp)")
def cmd_scanmal(arguments):
    print("== MALWARE TRACE SCAN ==")
    issues = 0

    # 1. startup entries with suspicious names / locations
    print("\n[STARTUP]")
    suspicious = ("temp", "download", "appdata", "programdata", "public",
                  "winupdate", "sysupd", "update", "svchost", "mshta",
                  "wscript", "cscript", "powershell")
    startup_hits = 0
    for hive, key in (("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Run"),
                      ("HKLM", r"Software\Microsoft\Windows\CurrentVersion\Run")):
        out = _run_cap(["reg", "query", f"{hive}\\{key}"])
        for line in out.splitlines():
            line = line.strip()
            if not line or line.startswith("!"):
                continue
            low = line.lower()
            if any(h in low for h in suspicious):
                print(f"  [SUSPICIOUS] {hive}\\{key}: {line[:110]}")
                startup_hits += 1
    if startup_hits == 0:
        print("  [CLEAN] no suspicious startup entries found")
    else:
        issues += startup_hits

    # 2. processes with suspicious names or working paths
    print("\n[PROCESSES]")
    proc_hits = 0
    for pid, ppid, name, thr, mem in sorted(_hack_processes(),
                                            key=lambda r: -r[4]):
        low = name.lower()
        if any(h in low for h in _SUSPICIOUS_NAME_HINTS):
            print(f"  [SUSPICIOUS] pid {pid}  {name}  ({mem / 1048576:.1f} MB)")
            proc_hits += 1
    if proc_hits == 0:
        print("  [CLEAN] no suspicious process names")
    else:
        issues += proc_hits

    # 3. hosts file tampering
    print("\n[HOSTS]")
    hosts = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"),
                         "System32", "drivers", "etc", "hosts")
    bad_lines = 0
    try:
        with io.open(hosts, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) >= 2 and not parts[0].startswith("#"):
                    if parts[1].lower() not in ("localhost",):
                        print(f"  [CHECK] {line}")
                        bad_lines += 1
    except OSError:
        print("  [CHECK] hosts file unreadable")
        issues += 1
    if bad_lines == 0:
        print("  [CLEAN] hosts file has no custom mappings")
    else:
        issues += bad_lines

    # 4. script droppers in temp
    print("\n[TEMP SCRIPT DROPPERS]")
    temp = os.environ.get("TEMP", "")
    temp_hits = 0
    if temp and os.path.isdir(temp):
        try:
            for name in os.listdir(temp):
                if name.lower().endswith(_SUSPICIOUS_EXTENSIONS):
                    print(f"  [SUSPICIOUS] {os.path.join(temp, name)}")
                    temp_hits += 1
        except OSError:
            pass
    if temp_hits == 0:
        print("  [CLEAN] no script files in %TEMP%")
    else:
        issues += temp_hits

    # 5. suspicious scheduled tasks
    print("\n[SCHEDULED TASKS]")
    sched_hits = 0
    out = _run_cap(["schtasks", "/fo", "csv", "/nh"])
    for line in out.splitlines():
        low = line.lower()
        if any(h in low for h in ("update", "defender", "winupdate",
                                  "powershell", "\\temp", "\\downloads")):
            print(f"  [CHECK] {line.strip('\"')[:100]}")
            sched_hits += 1
    if sched_hits == 0:
        print("  [CLEAN] no suspicious task names")
    else:
        issues += sched_hits

    print(f"\n== SCAN DONE: {issues} item(s) to review ==")
    if issues:
        print("Next: 'quarantine <pid>' to kill a process, 'lockdown' to harden.")


@register("lockdown", "Harden this machine - firewall on / guest off (y/N confirm)")
def cmd_lockdown(arguments):
    try:
        answer = input("Apply hardening (enable firewall, disable Guest)? [y/N] ").strip().lower()
    except EOFError:
        print("Aborted.")
        return
    if answer not in ("y", "yes"):
        print("Aborted.")
        return
    print("Applying hardening ...")
    r = subprocess.run(["netsh", "advfirewall", "set", "allprofiles",
                        "state", "on"], capture_output=True, timeout=30)
    fw = r.returncode == 0
    print(f"  firewall        : {'ON' if fw else 'failed (admin required?)'}")
    r = subprocess.run(["net", "user", "guest", "/active:no"],
                       capture_output=True, timeout=30)
    guest = r.returncode == 0
    print(f"  guest account   : {'disabled' if guest else 'failed (admin required?)'}")
    uac = _run_cap(["reg", "query",
                    r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System",
                    "/v", "EnableLUA"])
    print(f"  UAC (EnableLUA) : {'enabled' if '0x1' in uac else 'check manually'}")
    out = _run_cap(["netsh", "advfirewall", "show", "allprofiles", "state"])
    print("  firewall state  :")
    for line in out.splitlines():
        if "ON" in line or "OFF" in line:
            print(f"    {line.strip()}")
    print("Lockdown done. Re-check with 'scanmal'.")


@register("defender", "Windows Defender status (PowerShell)")
def cmd_defender(arguments):
    script = ("$s = Get-MpComputerStatus; "
              "Write-Output ('RealTimeProtection: ' + $s.RealTimeProtectionEnabled); "
              "Write-Output ('AntivirusEnabled: ' + $s.AntivirusEnabled); "
              "Write-Output ('AntivirusSignatureVersion: ' + $s.AntivirusSignatureVersion); "
              "Write-Output ('AntivirusSignatureAge: ' + $s.AntivirusSignatureAge); "
              "Write-Output ('QuickScanAge: ' + $s.QuickScanAge); "
              "Write-Output ('TamperProtection: ' + $s.IsTamperProtected); "
              "Write-Output ('AMEngineVersion: ' + $s.AMEngineVersion)")
    out = _run_cap(["powershell", "-NoProfile", "-Command", script])
    if not out.strip():
        print("Defender status unavailable (needs administrator?).")
        return
    for line in out.splitlines():
        line = line.strip()
        if line and ":" in line:
            key, value = line.split(":", 1)
            print(f"  {key.strip():<32} {value.strip()}")



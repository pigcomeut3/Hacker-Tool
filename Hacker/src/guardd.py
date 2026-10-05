import json
import os
import subprocess
import sys
import time

STATE_DIR = os.path.join(os.path.expanduser("~"), ".hacker")
STATE_FILE = os.path.join(STATE_DIR, "guard.json")
STOP_FILE = os.path.join(STATE_DIR, "guard.stop")

# Launch every helper process with no console window: it runs in the
# background like the guard itself (task manager only, no popup flashes).
_WIN = sys.platform == "win32"
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _hidden_run(cmd, timeout=25, text=None):
    """subprocess.run with no console window; text=None keeps bytes."""
    kwargs = {"capture_output": True, "timeout": timeout}
    if text is not None:
        kwargs["text"] = text
    if _WIN:
        kwargs["creationflags"] = _NO_WINDOW
    return subprocess.run(cmd, **kwargs)


def _decode_cli(raw):
    """Decode CLI output robustly across encodings Windows may pick."""
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16", "replace")
    for enc in ("gbk", "utf-8"):
        try:
            return raw.decode(enc, "replace")
        except Exception:
            continue
    return raw.decode("utf-8", "replace")


def _firewall_state():
    """Robust firewall state: PowerShell first (works headless), netsh fallback."""
    try:
        out = _hidden_run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-NetFirewallProfile | Where-Object {$_.Enabled -eq $true}).Count"],
            text=True).stdout.strip()
        if out.isdigit():
            return "ON" if int(out) >= 2 else "OFF"
    except Exception:
        pass
    try:
        out = _hidden_run(
            ["netsh", "advfirewall", "show", "allprofiles", "state"]).stdout
        text = _decode_cli(out)
        on_count = text.count("ON") + text.count("打开")
        off_count = text.count("OFF") + text.count("关闭")
        if on_count >= 2:
            return "ON"
        if off_count >= 2:
            return "OFF"
        return "?"
    except Exception:
        pass
    return "?"


def _protection_snapshot():
    """Lightweight, read-only protection status (no side effects)."""
    snap = {"defender": "?", "firewall": "?", "uac": "?"}
    try:
        out = _hidden_run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-MpComputerStatus).RealTimeProtectionEnabled"],
            text=True).stdout.strip()
        snap["defender"] = "ON" if out.lower().startswith("true") else "OFF"
    except Exception:
        pass
    snap["firewall"] = _firewall_state()
    try:
        import winreg
        with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System") as key:
            value, _ = winreg.QueryValueEx(key, "EnableLUA")
            snap["uac"] = "enabled" if value == 1 else "disabled"
    except Exception:
        pass
    return snap


def _write(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
    except OSError:
        pass


def _read_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return None


def run():
    """Background guard loop: heartbeat + periodic protection snapshot."""
    os.makedirs(STATE_DIR, exist_ok=True)
    pid = os.getpid()
    start = time.strftime("%Y-%m-%d %H:%M:%S")
    state = {"pid": pid, "start": start, "last_heartbeat": start,
             "protection": {}, "mode": "guard"}
    _write(state)
    last_check = 0.0
    while True:
        if os.path.exists(STOP_FILE):
            try:
                os.remove(STOP_FILE)
            except OSError:
                pass
            break
        state["last_heartbeat"] = time.strftime("%Y-%m-%d %H:%M:%S")
        now = time.time()
        if now - last_check >= 60:
            state["protection"] = _protection_snapshot()
            last_check = now
        _write(state)
        time.sleep(2)
    try:
        os.remove(STATE_FILE)
    except OSError:
        pass

import ctypes
import os
import sys


def _is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _elevate():
    """Request real administrator privileges via UAC on startup."""
    if _is_admin() or os.environ.get("HACKER_NO_ELEVATE") == "1":
        return
    working_dir = os.getcwd()
    if getattr(sys, "frozen", False):
        target = sys.executable
        args = ""
        if len(sys.argv) > 1:
            args = f'"{os.path.abspath(sys.argv[1])}"'
    else:
        target = sys.executable
        args = f'"{os.path.abspath(__file__)}"'
        if len(sys.argv) > 1:
            args += f' "{os.path.abspath(sys.argv[1])}"'
    result = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", target, args, working_dir, 1
    )
    if result <= 32:
        print("Administrator privileges are required.")
        print("Elevation was cancelled - some commands will not work.")
        try:
            input("Press Enter to exit...")
        except EOFError:
            pass
    sys.exit(0)


if "--guard" not in sys.argv:
    _elevate()

if "--guard" in sys.argv:
    import guardd
    guardd.run()
    sys.exit(0)

import core

SCRIPT_FILE = ""
if len(sys.argv) > 1 and sys.argv[1].lower().endswith(".ke"):
    SCRIPT_FILE = os.path.abspath(sys.argv[1])

os.system("cls")
os.system('color 0A')
os.system('title Hacker Tool')
if SCRIPT_FILE:
    if os.path.isfile(SCRIPT_FILE):
        import h as hacker_h
        try:
            source = open(SCRIPT_FILE, encoding="utf-8", errors="replace").read()
        except OSError as error:
            print(f"Cannot read script: {error}")
        else:
            print(f"Running {os.path.basename(SCRIPT_FILE)} ...")
            try:
                hacker_h.execute_lines(source.splitlines(), display_prefix=False)
            except KeyboardInterrupt:
                print("^C Script interrupted.")
            print()
    else:
        print(f"Script not found: {SCRIPT_FILE}")
core.run()

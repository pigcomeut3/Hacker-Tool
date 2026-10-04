import os
import signal
import sys
import commands
import pkgcore
from pathlib import Path

import banner
import colors
import pkg
import pacho


signal.signal(signal.SIGINT, signal.SIG_IGN)

# tool-pack command groups shown by `help` (names are filtered against the
# live registry so a removed command simply disappears)
TOOL_PACK_GROUPS = [
    ("processes/monitor", ["procs", "mon"]),
    ("network", ["portscan", "headers", "dns", "netrecon", "dnsflush"]),
    ("system forensics", ["boot", "services", "drivers", "shares", "sched",
                          "eventlog", "recent", "hosts"]),
    ("file forensics", ["strings", "largest", "dupes", "wipe", "hashfile"]),
    ("crypto", ["crypt", "xor", "rc4", "vigenere", "leet"]),
    ("incident response", ["scanmal", "quarantine", "netcut", "netup",
                           "lockdown", "defender"]),
]


def change_directory(path):
    if not path:
        print(os.getcwd())
        return

    path = path.strip()
    if len(path) >= 2 and path[0] == path[-1] and path[0] in ("'", '"'):
        path = path[1:-1]
    try:
        os.chdir(Path(path).expanduser())
    except FileNotFoundError:
        print(f"Directory not found: {path}")
    except NotADirectoryError:
        print(f"Not a directory: {path}")
    except OSError as error:
        print(f"Could not change directory: {error}")
    else:
        print(os.getcwd())


def list_directory():
    try:
        entries = sorted(
            Path.cwd().iterdir(),
            key=lambda entry: (not entry.is_dir(), entry.name.casefold()),
        )
    except OSError as error:
        print(f"Could not list directory: {error}")
        return

    for entry in entries:
        suffix = "\\" if entry.is_dir() else ""
        print(f"{entry.name}{suffix}")


def run_program(path):
    if not path:
        print("Usage: run <file>")
        return

    path = path.strip()
    if len(path) >= 2 and path[0] == path[-1] and path[0] in ("'", '"'):
        path = path[1:-1]
    target = Path(path).expanduser()
    if not target.is_file():
        print(f"File not found: {target}")
        return

    suffix = target.suffix.lower()
    if suffix in (".py", ".pyw"):
        command = [sys.executable, str(target.resolve())]
        pkgcore.run_process(command)
        return
    if suffix == ".exe":
        command = [str(target.resolve())]
        pkgcore.run_process(command)
        return

    try:
        os.startfile(str(target.resolve()))
    except (OSError, AttributeError) as error:
        print(f"Could not open file with its Windows application: {error}")


def run():
    os.system("cls")
    banner.show()
    while True:
        try:
            cmd = input(colors.green("root@hacker:~$ "))
        except KeyboardInterrupt:
            continue

        command_text = cmd.strip()
        if command_text:
            commands.record_history(cmd)
        command_parts = command_text.split(None, 1)
        command_name = command_parts[0] if command_parts else ""
        arguments = command_parts[1] if len(command_parts) > 1 else ""
        normalized_cmd = command_name.lower()
        if normalized_cmd == "exit" and not arguments.strip():
            print(colors.white("Exiting the Hacker Tool..."))
            break
        elif normalized_cmd == "cls" and not arguments.strip():
            os.system("cls")
            banner.show()
        elif normalized_cmd == "help" and not arguments.strip():
            print(colors.white("Available commands:"))
            print(colors.white("  help - Show this help message"))
            print(colors.white("  pkg install <name> - Install a custom library or package"))
            print(colors.white("  pkg list - List custom libraries"))
            print(colors.white("  cd <directory> - Change the current directory"))
            print(colors.white("  list - List files in the current directory"))
            print(colors.white("  run <file> - Run or open a file with its associated application"))
            print(colors.white("  pacho <url> - Fetch page title, text, links, and save HTML"))
            print(colors.white("  cls - Clear the screen"))
            print(colors.white("  info - Show information about the Hacker Tool"))
            print(colors.white("  version - Show the version of the Hacker Tool"))
            print(colors.white("  h - Hacker script system (.ke files), try 'h help'"))
            print(colors.white("  commands - List all available commands"))
            print(colors.white("  exit - Exit the Hacker Tool"))
            print(colors.white(""))
            print(colors.white("Real tool pack (type 'commands' for details):"))
            for group, names in TOOL_PACK_GROUPS:
                present = [n for n in names if n in commands.COMMANDS]
                if present:
                    print(colors.white(
                        f"  {group:<18} : {' '.join(present)}"))
        elif normalized_cmd == "cd":
            change_directory(arguments)
        elif normalized_cmd == "list" and not arguments.strip():
            list_directory()
        elif normalized_cmd == "run":
            run_program(arguments)
        elif normalized_cmd == "pacho":
            if arguments.strip():
                pacho.crawl(arguments.strip())
            else:
                print("Usage: pacho <http:// or https:// URL>")
        elif normalized_cmd == "info" and not arguments.strip():
            print(colors.white("Developed by: pig_comeut3"))
            print(colors.white("GitHub: pig_comeut3@163.com"))
        elif normalized_cmd == "version" and not arguments.strip():
            print(colors.white("Hacker Tool v2.0"))
        elif normalized_cmd == "pkg":
            pkg.handle(arguments.split())
        elif normalized_cmd in commands.COMMANDS:
            commands.COMMANDS[normalized_cmd][0](arguments)
        else:
            print(colors.white(f"Unknown command: {cmd}"))

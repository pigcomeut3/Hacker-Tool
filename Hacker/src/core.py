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
import dac


# SIGINT keeps Python's default handler so Ctrl+C raises KeyboardInterrupt,
# which is caught per-command and at the prompt (never kills the console).
if hasattr(signal, "SIGBREAK"):
    signal.signal(signal.SIGBREAK, signal.SIG_IGN)

# full command groups shown by `help` (names are filtered against the live
# registry, and any command not covered is appended automatically, so the
# list can never go stale)
HELP_GROUPS = [
    ("Basics", ["help", "commands", "history", "version", "info", "banner",
                "cls", "sudo", "pkg"]),
    ("Navigation & files", ["cd", "pwd", "list", "tree", "find", "where",
                            "drives", "cat", "head", "tail", "touch", "mkdir",
                            "rm", "cp", "mv", "ren", "size", "open", "run",
                            "hash", "hex", "grep", "wc", "sort", "uniq", "nl",
                            "diff", "zip", "unzip", "ziplist", "erase",
                            "delfolder", "attribf"]),
    ("System", ["sysinfo", "whoami", "cpu", "mem", "disk", "uptime", "battery",
                "ver", "env", "date", "time", "hostname", "title", "beep",
                "sleep", "top", "protect", "path", "poweroff", "reboot",
                "lockpc"]),
    ("Network", ["ip", "myip", "ping", "nslookup", "netstat", "scan", "mac",
                 "route", "wifi", "arp", "tracert", "ipscan", "webserver",
                 "http", "pacho", "weather"]),
    ("Processes", ["ps", "kill", "pkill"]),
    ("Text & data", ["echo", "clip", "b64", "b32", "urlenc", "urldec",
                     "hexenc", "binenc", "morse", "rot13", "md5str", "caesar",
                     "case", "rev", "convert", "jsonfmt", "csvview", "calc",
                     "uuid", "rand", "py", "count", "shuffle", "trim", "pad",
                     "fib", "prime", "pi", "fact", "randpw", "pwstrength",
                     "ts", "date2ts", "ascii", "chr"]),
    ("Editor & utils", ["edit", "timer", "clock", "typewriter"]),
    ("Fun", ["matrix", "hack", "hacksay", "guess", "rps", "dice", "coin",
             "joke", "quote", "facts", "spin", "progress", "typingtest"]),
    ("Script system", ["h"]),
    ("Integration", ["syst", "shell", "mkiso", "guard", "dac", "wsl"]),
]

# tool-pack command groups shown by `help` (names are filtered against the
# live registry so a removed command simply disappears)
TOOL_PACK_GROUPS = [
    ("processes/monitor", ["procs", "mon"]),
    ("network", ["portscan", "headers", "dns", "netrecon", "dnsflush",
                 "vulnscan", "pagelinks"]),
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


def _flush_input():
    """Discard any keys buffered while a command was running, so stray
    keystrokes do not leak into the next prompt."""
    try:
        import msvcrt
        while msvcrt.kbhit():
            msvcrt.getwch()
    except Exception:
        pass


def run():
    os.system("cls")
    banner.show()
    while True:
        _flush_input()
        try:
            cmd = input(colors.green("root@hacker:~$ "))
        except KeyboardInterrupt:
            print()
            continue
        except EOFError:
            print(colors.white("Input closed. Exiting Hacker Tool..."))
            break

        try:
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
                print(colors.white("Available commands (type 'commands' for details):"))
                covered = set()
                for group, names in HELP_GROUPS:
                    present = [n for n in names if n in commands.COMMANDS]
                    if not present:
                        continue
                    covered.update(present)
                    print(colors.white(
                        f"  {group:<18} : {' '.join(present)}"))
                # tool-pack commands are shown in their own section below,
                # so exclude them from the coverage check
                covered.update(n for _, names in TOOL_PACK_GROUPS
                               for n in names)
                # any command still not covered is appended so the list can
                # never go stale
                missing = sorted(set(commands.COMMANDS) - covered)
                if missing:
                    print(colors.white("  Other             : " + " ".join(missing)))
                print(colors.white(""))
                print(colors.white("Built-ins: cd, list, run, pacho, cls, pkg, "
                                   "info, version, exit"))
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
            elif dac.has(normalized_cmd):
                dac.run(normalized_cmd, arguments)
            else:
                print(colors.white(f"Unknown command: {cmd}"))
        except KeyboardInterrupt:
            print(colors.yellow("^C Interrupted."))

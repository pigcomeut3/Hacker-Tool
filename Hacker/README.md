# Custom Terminal for Windows

A hand-built, single-executable custom terminal for Windows with **130 built-in commands**, a native `.ke` script system, and a real tool pack for system reconnaissance, forensics and incident response.

No external dependencies. One exe, everything embedded.

> 中文说明：这是一个面向 Windows 的自制自定义终端，单文件 exe 运行，内置 130 条命令、`.ke` 脚本系统与真工具包（侦察 / 取证 / 应急响应）。详细中文文档见 [GUIDE.md](GUIDE.md)。

---

## Quick Start

```bash
# Run the prebuilt executable (everything is embedded - no other files needed)
Hacker.exe

# Or run from source
python src/main.py
```

Type `help` inside the terminal for the built-in command list, or `commands` for all registered commands.

---

## Command Guide

### Basics

| Command | Description |
|---|---|
| `help` | Show this help message |
| `commands` | List all available commands |
| `version` | Show the version of the Hacker Tool |
| `info` | Show developer information |
| `banner` | Show the banner again |
| `cls` | Clear the screen |
| `exit` | Exit the terminal |
| `history` | Show command history |
| `sudo` | Attempt privilege escalation (real UAC prompt) |
| `pkg install <name>` | Install a custom library or package |

### Navigation & Files

| Command | Description |
|---|---|
| `cd <dir>` | Change the current directory |
| `pwd` | Show the current directory |
| `list` | List files in the current directory |
| `tree` | Show a directory tree |
| `find <name>` | Find files by name |
| `where <cmd>` | Locate a command or program |
| `drives` | List disk drives |
| `cat <file>` | Show file content |
| `head <file>` | Show first lines of a file |
| `tail <file>` | Show last lines of a file |
| `touch <file>` | Create an empty file |
| `mkdir <dir>` | Create a directory |
| `rm <path>` | Delete a file or directory |
| `cp <src> <dst>` | Copy a file or directory |
| `mv <src> <dst>` | Move a file or directory |
| `ren <old> <new>` | Rename a file or directory |
| `size <path>` | Show file or directory size |
| `open <path>` | Open a path with its default application |
| `run <file>` | Run or open a file |
| `hash <file>` | Hash a file (MD5 / SHA1 / SHA256) |
| `hex <file>` | Show a hex dump of a file |
| `grep <pattern> <file>` | Search text in files |
| `wc <file>` | Count lines, words and characters |
| `sort <file>` | Sort lines of a file |
| `uniq <file>` | Show unique lines of a file |
| `nl <file>` | Number the lines of a file |
| `diff <a> <b>` | Compare two files |
| `zip <out> <items>` | Create a zip archive |
| `unzip <file>` | Extract a zip archive |
| `ziplist <file>` | List files inside a zip archive |
| `largest [dir] [count]` | Largest files under a directory |

### System & Hardware

| Command | Description |
|---|---|
| `sysinfo` | Show system information |
| `cpu` | Show CPU information |
| `mem` | Show memory usage |
| `disk` | Show disk usage |
| `uptime` | Show system uptime |
| `battery` | Show battery status |
| `ver` | Show Windows version |
| `env` | Show environment variables |
| `date` | Show the current date |
| `time` | Show the current time |
| `hostname` | Show the host name |
| `title <text>` | Set the console window title |
| `beep` | Make the speaker beep |
| `sleep <sec>` | Wait for a number of seconds |
| `top` | Show processes sorted by memory |

### Network

| Command | Description |
|---|---|
| `ip` | Show IP configuration |
| `myip` | Show public IP address |
| `ping <host>` | Ping a host |
| `nslookup <host>` | Query DNS for a host |
| `netstat` | Show network connections |
| `scan <host>` | Scan common ports of a host |
| `mac` | Show MAC addresses |
| `route` | Show the routing table |
| `wifi` | Show Wi-Fi information |
| `arp` | Show the ARP table |
| `tracert <host>` | Trace the route to a host |
| `ipscan <subnet>` | Scan a subnet for live hosts |
| `webserver [port]` | Start a temporary HTTP server |
| `http <url>` | Fetch a URL and show the response |
| `pacho <url>` | Fetch page title, text, links, and save HTML |

### Processes

| Command | Description |
|---|---|
| `ps` | List processes |
| `kill <pid>` | Kill a process by PID |
| `pkill <name>` | Kill processes by name |
| `procs` | Native process list (PID / PPID / threads / memory) |
| `mon` | Live system monitor - CPU / RAM / disk (q to quit) |

### Text & Encoding

| Command | Description |
|---|---|
| `echo <text>` | Print text |
| `clip <text>` | Copy text to the clipboard |
| `b64 <text>` | Base64 encode or decode text |
| `b32 <text>` | Base32 encode or decode text |
| `urlenc <text>` | URL-encode text |
| `urldec <text>` | URL-decode text |
| `hexenc <text>` | Encode text as hex |
| `binenc <text>` | Encode text as binary |
| `morse <text>` | Encode or decode Morse code |
| `rot13 <text>` | ROT13 encode or decode text |
| `md5str <text>` | Hash a string with MD5 |
| `case <text>` | Convert text case |
| `rev <text>` | Reverse text |
| `convert <val> <from> <to>` | Convert units (temperature, length, mass) |
| `jsonfmt <text>` | Pretty-print JSON |
| `csvview <file>` | View a CSV file as a table |
| `calc <expr>` | Evaluate a math expression |
| `uuid` | Generate a UUID |
| `rand [max]` | Generate a random number |
| `py <code>` | Execute a Python one-liner |

### Editor & Utilities

| Command | Description |
|---|---|
| `edit <file>` | Full-screen terminal editor (nano-style, Ctrl+S save / Ctrl+Q quit) |
| `timer <sec>` | Countdown timer |
| `clock` | Show a live clock for a few seconds |
| `typewriter <text>` | Type text with a typewriter effect |

### Fun

| Command | Description |
|---|---|
| `matrix` | Matrix rain effect |
| `hack <text>` | Hacker typing effect |
| `hacksay <text>` | Hacker-style speech bubble |
| `guess` | Guess the number game |
| `rps` | Rock paper scissors |
| `dice` | Roll dice |
| `coin` | Flip a coin |

---

## Real Tool Pack

Type `commands` inside the terminal and scroll to the tool pack section for the full list with usage hints.

### Network Recon

| Command | Description |
|---|---|
| `portscan <host> [start-end]` | Multi-threaded port scan |
| `headers <url>` | Show HTTP response headers |
| `dns <host>` | DNS resolution |
| `netrecon` | Network recon summary - adapters / arp / top connections |
| `dnsflush` | Flush the DNS resolver cache |

### System Forensics

| Command | Description |
|---|---|
| `boot` | Startup entries - registry Run keys + Startup folder |
| `services [keyword]` | Service list with status |
| `drivers [keyword]` | Kernel driver list |
| `shares` | Network shares on this machine |
| `sched [keyword]` | Scheduled tasks |
| `eventlog <log> [count]` | Recent event log entries |
| `recent [count]` | Recently opened files |
| `hosts` | Show the hosts file |

### File Forensics

| Command | Description |
|---|---|
| `strings <file> [min]` | Extract printable strings from a file |
| `dupes [dir]` | Find duplicate files by size and hash |
| `wipe <file>` | Securely overwrite and delete a file (3 passes) |
| `hashfile <file>` | Hash a file |

### Crypto

| Command | Description |
|---|---|
| `crypt <md5\|sha1\|sha256\|sha512\|crc32> <text>` | Hash text |
| `xor <key> <text>` | XOR a string with a key |
| `rc4 <key> <text>` | RC4 stream cipher |
| `vigenere <key> <text> [-d]` | Vigenere cipher |
| `leet <text>` | Convert text to leetspeak |

### Incident Response (this machine only)

| Command | Description |
|---|---|
| `scanmal` | Scan this machine for malware traces (startup / procs / hosts / temp) |
| `quarantine <pid\|name>` | Kill a suspicious process |
| `netcut` | Emergency: release all network addresses (y/N confirm) |
| `netup` | Restore network addresses after netcut |
| `lockdown` | Harden this machine - firewall on / guest off (y/N confirm) |
| `defender` | Windows Defender status (PowerShell) |

---

## Hacker Script System (.ke)

The `h` command manages `.ke` script files - small Python-style scripts with access to the built-in Hacker native library.

```bash
h help      # Show script system help
h new demo  # Create a new script
h edit demo # Open a script in the editor
h run demo  # Run a script
h list      # List all scripts
h lib       # Show the built-in Hacker native library (hundreds of functions)
h del demo  # Delete a script (asks for confirmation)
```

Scripts are stored in `hscripts/` next to the exe. Sample scripts (`hello.ke`, `matrix.ke`, `sysinfo.ke`) are seeded automatically on first run.

---

## System Integration

```bash
syst <command>   # Run a system command through cmd (e.g. syst ipconfig /all)
shell            # Open an interactive cmd.exe shell (type exit to return)
mkiso <folder> <out>  # Create an ISO 9660 image from a folder
```

---

## Build

Everything is packed into a single self-contained exe - source code, `hscripts/`, icons and `resources.dll` are all embedded. No external files needed at runtime.

```bash
pip install pyinstaller
python -m PyInstaller -F --noconfirm --name Hacker --icon icon.ico --paths src --add-data "hscripts;hscripts" --add-data "icon.ico;." --add-data "resources.dll;." src/main.py
```

The result is `dist/Hacker.exe`. Copy it anywhere and run it.

> Note: a single-file exe may trigger a false positive from Windows Defender. Add an exclusion for the folder if needed.

---

## Disclaimer

This is a personal hobby project built for learning and technical practice. The incident-response commands only act on your own machine. Use it at your own risk.

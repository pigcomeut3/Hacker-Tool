# Hacker Tool 使用与扩展指南

Hacker Tool 是一个运行在 Windows 终端里的黑客风格命令行工具（Python 实现，零第三方依赖）。

本文档写给想使用它、想给它加东西的人。

## 文件结构

所有 Python 源码都在 `src/` 目录：

| 文件                        | 作用                                               |
| ------------------------- | ------------------------------------------------ |
| `src/main.py`            | 入口：清屏、设标题、进入主循环                                  |
| `src/core.py`            | 主循环与命令分发（内置命令 + 自动挂载 `commands.py` 注册的命令）        |
| `src/commands.py`        | 全部扩展命令的注册与实现（新命令加在这里）                            |
| `src/hacklib.py`         | Hacker 原生函数库（1694 个内置函数，供 `.ke` 脚本调用）            |
| `src/h.py`               | `h` 命令：`.ke` 自制脚本系统                              |
| `src/pkg.py` / `src/pkgcore.py` | 包管理（`pkg install`），可安装便携 Python / C++ 工具链 /pip 包 |
| `src/pacho.py`           | `pacho` 网页抓取命令                                   |
| `src/banner.py` / `src/colors.py` | 横幅与 ANSI 颜色工具                            |
| `src/iso_builder.py`     | `mkiso` 的 ISO 9660 生成器                            |
| `src/make_icon.py` / `src/ke_icons.py` | 终端图标 / .ke 脚本图标生成器                |
| `hscripts/`              | `.ke` 脚本存放目录（自动创建）                               |
| `resources.dll`          | 图标资源容器（原生 Win32 图标 + .NET 托管资源，见下文）                     |
| `resources.dll.bak`      | resources.dll 的基础版备份（重建脚本的源）                               |
| `update_res.py`          | 注入 Win32 原生图标的脚本（官方 UpdateResource API）                    |
| `Hacker.exe`             | 打包好的单文件程序（直接运行，自动提权）                           |

## 启动

```
python src/main.py
```

或者直接双击运行打包好的 `Hacker.exe`。

启动时若当前不是管理员，会自动弹出 UAC 请求**真实的管理员权限**（不只是显示 `root@` 标签）；确认后以管理员身份运行。取消提权也能进入，但部分系统命令不可用。调试/自动化时可设环境变量 `HACKER_NO_ELEVATE=1` 跳过提权。

## 全部命令

输入 `commands` 可查看完整清单（自动包含新加的命令），`help` 查看内置命令。

内置命令：`help` `pkg` `cd` `list` `run` `pacho` `cls` `info` `version` `exit`

扩展命令（commands.py 注册，共 130 条）按功能分组：



* 系统信息：`sysinfo` `whoami` `cpu` `mem` `disk` `uptime` `battery` `ver` `env` `date` `time` `banner` `hostname` `pwd` `drives` `title <文本>`

* 网络诊断：`ip` `myip` `ping` `nslookup` `netstat` `scan <主机>` `mac` `route` `wifi` `tracert <主机>` `arp` `http <URL>` `ipscan <网段>` `webserver [端口] [秒]`

* 文件操作：`tree [深度]` `find <名>` `cat` `head` `tail` `touch` `mkdir` `rm`（确认）`cp` `mv` `ren` `open` `edit <文件>` `grep` `wc` `sort` `uniq` `hash` `hex` `size` `rev` `nl <文件>` `diff <文件1> <文件2>` `jsonfmt <json>` `csvview <csv>` `zip <压缩包> <文件...>` `unzip <压缩包> [目录]` `ziplist <压缩包>` `mkiso <文件夹> [输出.iso]`

* 进程管理：`ps` `kill <pid>`（确认）`pkill <进程名>`（确认）`top` `where <程序名>`

* 文本与编码：`echo` `clip` `b64 [-d]` `rot13` `md5str` `calc <表达式>` `uuid` `rand [a] [b]` `b32 [-d]` `urlenc` `urldec` `hexenc` `binenc` `morse [-d]` `caesar <位移> <文本>` `case <风格> <文本>` `convert <数值> <单位> <单位>`

* 执行与工具：`py <Python代码>` `syst <系统命令>` `sleep <秒>` `timer <秒>` `clock [秒]` `beep [次数]`

* 脚本系统：`h`

* 趣味特效：`matrix [秒]` `hack [秒]` `sudo` `history` `commands` `hacksay <文本>` `guess` `rps <rock|paper|scissors>` `dice [次数]` `coin` `typewriter <文本>`

## 终端编辑器 `edit`

`edit <文件>` 是一个**全屏终端编辑器**（类似 Linux 的 nano/vi）：进入时清屏显示完整编辑界面，写完后退出自动清屏回到命令行。文件不存在会显示 `文件名: No such file` 但仍可进入编辑，保存时创建。

界面从上到下：标题栏（文件名 + `[+]` 表示有未保存修改）、带行号的内容区（光标行反白）、状态栏（行/列/总行数）、提示栏。

键盘操作：

| 按键 | 作用 |
|---|---|
| 方向键 | 移动光标 |
| `Home` / `End` | 行首 / 行尾 |
| `PageUp` / `PageDown` | 上下翻页 |
| `Backspace` | 删除光标前字符（行首时合并上一行） |
| `Delete` | 删除光标处字符（行尾时合并下一行） |
| `Enter` | 当前行拆行，光标移到新行 |
| 任意字符 | 在光标处插入（支持中文） |
| `Ctrl+S` | 保存（提示写入字节数） |
| `Ctrl+Q` | 退出：有未保存修改时询问，`y` 保存退出 / `n` 不保存退出 / 其他取消 |

说明：脚本或管道输入（非真实终端）时自动回退到 ed 风格的行编辑模式，命令同 GNU ed（`a` 追加、`.` 结束、`p`/`n`、`1,3p`、`d`、`s/old/new`、`w`、`q`、`wq`、`=`/`$=` 等）。

保存的文件用 UTF-8 编码，每行末尾带换行符。

## 如何添加一条新命令（给别人看的扩展指南）

加命令只需要 3 步，不需要动 `core.py`：



1. 打开 `commands.py`。

2. 在文件末尾写一个函数，用 `@register` 注册：



```
@register("hello", "Say hello")
def hello(arguments):
    print(f"Hello, {arguments or 'world'}!")
```

带参数 / 标志的命令写法（`arguments` 是命令名之后整段文本，自己拆分）：



```
@register("hello2", "Say hello in a style")
def hello2(arguments):
    parts = arguments.split(None, 1)          # 按第一个空格拆成 [标志, 剩余]
    if not parts:
        print("Usage: hello2 [-loud] <name>")
        return
    name = parts[1] if len(parts) > 1 else "world"
    if parts[0] == "-loud":
        print(f"HELLO {name.upper()}!!!")
    else:
        print(f"Hello, {name}!")
```



1. 保存，重新运行 `python src/main.py`。

`@register(命令名, 一句话说明)` 会自动完成三件事：



* 输入 `hello` 时被调用（函数收到一个 `arguments` 字符串参数，即命令后面的内容）；

* 出现在 `commands` 命令的清单里；

* 出现在 `help` 的查询结果中。

补充约定：



* 命令名用小写，多个词用下划线，不要与已有命令重名；

* 函数实现里尽量用标准库，保持零第三方依赖；

* 涉及删除、覆盖等危险操作时，加 `y/N` 确认（参考 `rm` / `kill` / `h del` 的写法）；

* 需要调用系统命令时用 `pkgcore.run_process([...])`（不要用 `shell=True`）。

## `.ke` 自制脚本系统（命令 `h`）

`.ke` 是 Hacker Script 的扩展名（ke = hacker 缩写）。脚本存放在 `hscripts/` 目录。



```
h new <name>          # 新建脚本（自动加 .ke 后缀）
h edit <name>         # 用记事本打开编辑
h run <name> [参数]    # 运行脚本，可传参数
h list                # 列出所有脚本
h lib [关键词]         # 查看内置函数库（h lib sha 筛选）
h del <name>          # 删除脚本（确认后）
```

`.ke` 脚本就是完整的 Python 代码，写法和 `.py` 完全一样，而且额外拥有两样东西：



1. **全部 Python 原生模块**：`os` `sys` `math` `random` `datetime` `json` `re` `socket` `time` `base64` `hashlib` `urllib` `uuid` `platform` `shutil` `subprocess` `string` `Path` 直接可用，不用 import。

2. **1694 个 Hacker 原生函数**：见下一节。

脚本示例 `hello.ke`：



```
# hello.ke
print("Hello from Hacker!")
print("MD5:", md5("hacker"))
print("Base64:", enc_base64("hacker"))
print("大数进制转换 b10_to_b36:", b10_to_b36("999999"))
print("参数:", args)
```

运行：`h run hello a b c`，`args` 就是 `['a', 'b', 'c']`。

脚本出错不会崩掉工具，会打印 `Script error: <类型>: <信息>`。

## Hacker 原生函数库（hacklib.py，共 1694 个）

脚本里可以直接调用，无需前缀。用 `h lib` 看分组统计，`h lib <关键词>` 看具体函数。



| 分组           | 数量   | 例子                                                                                                                                          |
| ------------ | ---- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| types        | 27   | `is_int` `to_bool` `to_hex`                                                                                                                 |
| strings      | 115  | `str_reverse` `case_camel` `pad_left` `only_digits` `count_vowels` `wrap_quotes` `is_palindrome`                                            |
| encode       | 26   | `enc_base64` `dec_base64` `enc_hex` `enc_morse` `dec_morse` `enc_rot47` `enc_url` `enc_bin`                                                 |
| hash         | 15   | `md5` `sha256` `crc32` `hash_file_sha256` `hash_all`                                                                                        |
| math         | 94   | `factorial` `fibonacci` `is_prime` `nth_prime` `gcd` `lcm` `collatz` `divisors` `phi` `is_armstrong` `stddev` `mult_table_9` `squares_upto` |
| random       | 18   | `rand_password` `rand_hex` `coin_flip` `dice`                                                                                               |
| lists        | 28   | `list_unique` `list_flatten` `list_chunk` `list_median` `list_zip`                                                                          |
| dicts        | 13   | `dict_merge` `dict_invert` `dict_sort`                                                                                                      |
| network      | 9    | `net_ping` `net_is_port_open` `net_public_ip` `net_http_get` `net_scan_ports`                                                               |
| system       | 21   | `sys_memory` `sys_uptime` `sys_battery` `sys_disk` `sys_cpu_cores`                                                                          |
| files        | 23   | `file_read` `file_write` `file_find` `dir_size`                                                                                             |
| time         | 17   | `time_now` `time_format` `sleep_ms`                                                                                                         |
| fun          | 18   | `fun_matrix_line` `fun_hack_line` `fun_quote` `ascii_skull` `art_heart`                                                                     |
| colors       | 13   | `color_green` `color_bold` `colorize`                                                                                                       |
| bits         | 15   | `bit_and` `bit_xor` `bit_count` `int_to_bin`                                                                                                |
| base-convert | 1190 | `b10_to_b36` `b2_to_b16` `b36_to_b2` ... 2\~36 进制任意互转                                                                                       |
| caesar       | 52   | `caesar13` `uncaesar5` ... 凯撒加密 / 解密 1\~26 位移                                                                                               |

### 如何添加一个 Hacker 原生函数

打开 `hacklib.py`，用 `_reg(函数名, 函数, 分组)` 注册，比如：



```
_reg("double_it", lambda v: int(v) * 2, "math")
```

或者写普通函数再注册：



```
def shout(text):
    return str(text).upper() + "!!!"

_reg("shout", shout, "strings")
```

保存后 `.ke` 脚本里就能直接调用 `double_it(21)`、`shout("hi")` 了。

## 系统命令 `syst`

`syst <系统命令>` 直接运行系统级命令（空格后输入完整命令，支持引号参数），输出实时显示，等同于在管理员 shell 里执行：

```
syst ipconfig
syst ping -n 4 8.8.8.8
syst whoami
```

工具提权后运行 `syst` 即以管理员身份执行命令。

## 生成 ISO `mkiso`

`mkiso <文件夹> [输出.iso]` 把整个文件夹打包成 ISO 9660 镜像（纯 Python 手写生成器，零依赖），输出文件已存在会先确认覆盖：

```
mkiso C:\myfiles
mkiso C:\myfiles C:\myfiles.iso
```

生成的是标准数据 ISO（文件名自动转大写 8.3），可直接双击挂载或用 `Mount-DiskImage` 读取。

## 终端辅助工具包（真黑客工具）

Hacker 是纯终端操作的工具，没有图形界面。以下命令是内置的**真实工具**（全部用标准库实现，不是表面样子），按功能分组：

**进程与监控**

* `procs` - 原生进程列表（Toolhelp32，PID/PPID/线程/内存，按内存降序）
* `mon` - 实时系统监控（CPU / 内存 / 磁盘，每秒刷新，按 `q` 退出）

**网络侦察**

* `portscan <主机> [起始-结束]` - 多线程 TCP 端口扫描（默认 1-1024，显示服务名）
* `headers <URL>` - 查看 HTTP 响应头
* `dns <域名>` - 解析 A / AAAA（getaddrinfo）+ MX / TXT（nslookup）
* `netrecon` - 网络侦察摘要（网卡 / ARP 缓存 / TCP 连接统计）
* `dnsflush` - 刷新 DNS 解析缓存

**系统取证**

* `boot` - 启动项（注册表 Run / RunOnce ×4 + 启动文件夹）
* `services [关键字]` - 全部服务及状态（`sc query` 解析）
* `drivers [关键字]` - 内核驱动列表（`driverquery` 解析）
* `shares` - 本机网络共享
* `sched [关键字]` - 计划任务列表
* `eventlog <日志名> [条数]` - 最近事件（如 `eventlog System 10`）
* `recent [条数]` - 最近打开的文件
* `hosts` - 查看 hosts 文件

**文件取证**

* `strings <文件> [最小长度]` - 提取文件中的可打印字符串（默认最小 4 字符）
* `largest [目录] [数量]` - 目录下最大的 N 个文件
* `dupes [目录]` - 按大小 + MD5 找重复文件
* `wipe <文件>` - 安全删除（随机 / 0xFF / 0x00 覆写 3 遍后删除，有 y/N 确认）
* `hashfile <文件>` - 计算文件 MD5 / SHA1 / SHA256

**密码学工具箱**

* `crypt <md5|sha1|sha256|sha512|crc32> <文本>` - 哈希文本
* `xor <key> <文本>` - XOR 异或（可打印时输出原文，否则输出 hex）
* `rc4 <key> <文本>` - RC4 流密码（输出 hex）
* `vigenere <key> <文本> [-d]` - 维吉尼亚加密 / 解密
* `leet <文本>` - 转 leetspeak（hacker → h4ck3r）

这些命令全部面向本机 / 授权环境的诊断与练习，危险操作（`wipe`）带确认。

## 应急响应工具包（本机防御）

电脑疑似被入侵时的**防御性处置**工具（只作用于本机，不含任何攻击载荷）：

* `scanmal` - 恶意痕迹扫描：启动项 / 可疑进程名 / hosts 篡改 / %TEMP% 脚本投放 / 可疑计划任务，输出 `[SUSPICIOUS]` / `[CHECK]` / `[CLEAN]`
* `quarantine <pid|进程名>` - 终止可疑进程（y/N 确认），并检查它是否同时存在于启动项
* `netcut` - 紧急断网：释放全部网络地址（y/N 确认），恢复用 `netup`
* `netup` - 断网后重新获取网络地址
* `lockdown` - 加固本机：开启防火墙、禁用 Guest 账户、检查 UAC（y/N 确认）
* `defender` - 查看 Windows Defender 实时防护 / 引擎 / 签名状态

被入侵时的正确处置顺序：`netcut` 断网 → `scanmal` 找出可疑项 → `quarantine` 终止可疑进程 → 清除启动项 → `lockdown` 加固 → `defender` 确认防护在运行。

## 打包成 exe

项目打包成**单个自包含文件** `Hacker.exe`（所有代码 + `hscripts/` 脚本目录 + 图标 + `resources.dll` 全部内嵌，运行时不需要在旁边拖任何依赖文件）：

```
python -m pip install pyinstaller
python -m PyInstaller -F --noconfirm --name Hacker --icon icon.ico --paths src --add-data "hscripts;hscripts" --add-data "icon.ico;." --add-data "resources.dll;." src/main.py
```

产物在 `dist/Hacker.exe`，复制到项目根覆盖旧版即可。

打包后的行为：

* 130 条命令、`help` 分组、`.ke` 脚本系统全部可用，与源码运行一致。
* `.ke` 脚本存放在 **exe 同目录的 `hscripts/`**（可写、持久）；首次运行时如果该目录不存在，会自动从内嵌资源把示例脚本（hello/matrix/sysinfo + 三个图标）播种出来。
* `resources.dll` 一并内嵌，但它是给 Windows"更改图标"对话框用的资源容器，终端运行时本身不读取，保留在项目目录即可。
* 注意：单文件 exe 可能被 Windows Defender 误报，首次运行前建议给目录加排除项。

## 资源 DLL `resources.dll`

图标资源容器（C# 编译的真实 DLL，用系统自带 csc 重建，无需装编译器）：存放 Hacker 终端自己的图标 `icon.ico` 和每个 `.ke` 脚本的配套图标。

**两种图标同时存在：**

1. **Win32 原生图标**（RT_ICON / RT_GROUP_ICON）：Windows 原生识别 —— 在"更改图标"对话框里选 `resources.dll` 能列出 4 个图标（终端 + hello/sysinfo/matrix 三个 .ke 图标），不再报"不包含图标"。用官方 `BeginUpdateResourceW / UpdateResourceW / EndUpdateResourceW` API 注入（Windows 内核自动重建资源树，无需手写 PE）。

2. **.NET 托管资源**：`icon.ico`、`ke_hello.ico`、`ke_sysinfo.ico`、`ke_matrix.ico` 四个，用 `HackerRes.GetIcon / ListIcons / Count` 读取（PowerShell / .NET）：

```powershell
$asm = [Reflection.Assembly]::LoadFrom("resources.dll")
$t = $asm.GetType("HackerRes")
$t.GetMethod("ListIcons").Invoke($null, $null)           # 列出图标
$t.GetMethod("GetIcon").Invoke($null, @("ke_hello.ico")) # 取出图标字节
```

**重建步骤（两步）：**

1. 编译基础 DLL（托管资源 + C# 读取类）：`csc /nologo /target:library /out:resources.dll /resource:icon.ico,icon.ico /resource:hscripts\icons\ke_hello.ico,ke_hello.ico /resource:hscripts\icons\ke_sysinfo.ico,ke_sysinfo.ico /resource:hscripts\icons\ke_matrix.ico,ke_matrix.ico HackerRes.cs`

2. 注入 Win32 原生图标：`python update_res.py`（从 `resources.dll.bak` 恢复基础版 → 注入 4 组 RT_ICON + RT_GROUP_ICON）。成功标准：`ExtractIconExW` 能枚举 4 个图标，且 `LoadFrom` 后 `Count()` 仍为 4。

## 注意事项



* 工具是英文界面，输出保持英文，避免 Windows 控制台乱码。

* `rm` `kill` `h del` 都有 `y/N` 确认，脚本里调用 `file_delete` / `dir_delete` 不会确认，写脚本时自己注意。

* `.ke` 脚本有完整 Python 能力，等于在本机执行任意代码 —— 只运行自己或信任的脚本。

* Ctrl+T 中断功能已移除，长命令用 Ctrl+C 也无法打断（SIGINT 被忽略），需要停止时直接关闭窗口或重启。
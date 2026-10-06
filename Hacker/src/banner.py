import colors

# "WELCOME" drawn with block characters (█) and pipe-style box drawing (║),
# figlet "block" style, 6 lines x 70 columns
ART = [
    "██╗    ██╗███████╗██╗      ██████╗ ██████╗ ███╗   ███╗███████╗",
    "██║    ██║██╔════╝██║     ██╔════╝██╔═══██╗████╗ ████║██╔════╝",
    "██║ █╗ ██║█████╗  ██║     ██║     ██║   ██║██╔████╔██║█████╗  ",
    "██║ ██╗██║██╔══╝  ██║     ██║     ██║   ██║██║╚██╔╝██║██╔══╝  ",
    "╚███╔███╔╝███████╗███████╗╚██████╗╚██████╔╝██║ ╚═╝ ██║███████╗",
    " ╚══╝╚══╝ ╚══════╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝",
]

WIDTH = 70


def show():
    print(colors.cyan("┌" + "─" * WIDTH + "┐"))
    for line in ART:
        print(colors.green(line))
    print(colors.cyan("└" + "─" * WIDTH + "┘"))
    print()

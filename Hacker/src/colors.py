GREEN = '\033[92m'
WHITE = '\033[97m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def green(text):
    return GREEN + text + RESET

def white(text):
    return WHITE + text + RESET

def red(text):
    return RED + text + RESET

def yellow(text):
    return YELLOW + text + RESET
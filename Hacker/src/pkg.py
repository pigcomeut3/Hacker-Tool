import dac


def handle(arguments):
    if not arguments:
        print("Usage: pkg list | pkg install <file.dac> | pkg fetch <name> [source]")
        print("       pkg remove <name> | pkg info <name> | pkg build <folder>")
        return

    action = arguments[0].lower()
    rest = arguments[1:]

    if action == "list" and not rest:
        dac.list_packages("")
        return

    if action == "install" and len(rest) == 1:
        dac.install(rest[0])
        return

    if action == "fetch" and rest:
        dac.fetch(" ".join(rest))
        return

    if action == "remove" and len(rest) == 1:
        dac.remove(rest[0])
        return

    if action == "info" and len(rest) == 1:
        dac.info(rest[0])
        return

    if action == "build" and rest:
        dac.build(" ".join(rest))
        return

    print("Usage: pkg list | pkg install <file.dac> | pkg fetch <name> [source]")
    print("       pkg remove <name> | pkg info <name> | pkg build <folder>")
    print("DAC packages are installed as commands: <name> [command] [args]")

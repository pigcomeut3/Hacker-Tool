import re

import pkgcore


CUSTOM_LIBRARIES = {
    "python": pkgcore.PYTHON_DESCRIPTION,
    "cpp": pkgcore.CPP_DESCRIPTION,
}

_PIP_PACKAGE_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*"
    r"(?:\[[A-Za-z0-9,._-]+\])?"
    r"(?:[<>=!~]{1,2}[A-Za-z0-9.*+!-]+)?$"
)


def show_libraries():
    print("Available packages:")
    for name, description in CUSTOM_LIBRARIES.items():
        print(f"  {name} - {description}")
    print("  pip:<name> - Install a Python package into the PKG kernel, e.g. pip:requests")
    print("Installed Python packages:")
    installed = pkgcore.installed_python_packages()
    if installed:
        for name in installed:
            print(f"  {name}")
    else:
        print("  (none)")


def install(package_name):
    normalized_name = package_name.lower()
    if normalized_name == "python":
        print(f"Installing python: {CUSTOM_LIBRARIES['python']}")
        pkgcore.install_python()
        return

    if normalized_name == "cpp":
        print(f"Installing cpp: {CUSTOM_LIBRARIES['cpp']}")
        pkgcore.install_cpp()
        return

    if normalized_name.startswith("pip:"):
        package_spec = package_name[4:]
        if not _PIP_PACKAGE_PATTERN.fullmatch(package_spec):
            print("Error: invalid pip package specification.")
            return
        pkgcore.install_pip_package(package_spec)
        return

    print(f"Unknown package: {package_name}")
    print("Use 'pkg list' to view packages, or specify pip:<name>.")


def handle(arguments):
    if len(arguments) == 1 and arguments[0].lower() == "list":
        show_libraries()
        return

    if len(arguments) == 2 and arguments[0].lower() == "install":
        install(arguments[1])
        return

    print("Usage: pkg install <name> | pkg list")

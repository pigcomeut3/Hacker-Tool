import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


KERNEL_DIR = Path(__file__).resolve().parent / "pkgcore_data"
HOST_PACKAGES_DIR = (
    KERNEL_DIR
    / "packages"
    / f"python{sys.version_info.major}{sys.version_info.minor}"
)
PYTHON_PACKAGES_DIR = KERNEL_DIR / "packages" / "python313"
TOOLS_DIR = KERNEL_DIR / "tools"
PYTHON_VERSION = "3.13.16"
PYTHON_DESCRIPTION = (
    f"Python {PYTHON_VERSION} portable runtime, installed inside the PKG kernel."
)
CPP_DESCRIPTION = (
    "Zig portable compiler toolchain for C and C++, installed inside the PKG kernel."
)
PYTHON_URLS = {
    "amd64": (
        "https://www.python.org/ftp/python/3.13.16/"
        "python-3.13.16-embed-amd64.zip"
    ),
    "arm64": (
        "https://www.python.org/ftp/python/3.13.16/"
        "python-3.13.16-embed-arm64.zip"
    ),
}

HOST_PACKAGES_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(HOST_PACKAGES_DIR))


def run_process(command):
    try:
        process = subprocess.Popen(
            command,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
    except OSError as error:
        print(f"Could not start command: {error}")
        return False

    process.wait()
    if process.returncode != 0:
        print(f"Command failed with exit code {process.returncode}.")
        return False
    return True


def _download(url, destination, expected_sha256=None):
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            digest = hashlib.sha256()
            with open(destination, "wb") as output:
                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    output.write(chunk)
                    digest.update(chunk)
        if expected_sha256 and digest.hexdigest().lower() != expected_sha256.lower():
            print("Download verification failed: SHA-256 does not match.")
            return False
    except (OSError, urllib.error.URLError) as error:
        print(f"Download failed: {error}")
        return False
    return True


def _extract_zip(archive_path, destination):
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.infolist():
                target = (destination / member.filename).resolve()
                try:
                    inside_destination = (
                        os.path.commonpath((str(root), str(target))) == str(root)
                    )
                except ValueError:
                    inside_destination = False
                if not inside_destination:
                    print(f"Rejected unsafe archive path: {member.filename}")
                    return False
                archive.extract(member, destination)
    except (OSError, zipfile.BadZipFile) as error:
        print(f"Could not extract package archive: {error}")
        return False
    return True


def _install_zip(url, destination, expected_sha256=None):
    KERNEL_DIR.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        print(f"Installation directory already exists: {destination}")
        print("Remove that package directory manually before reinstalling.")
        return False
    with tempfile.TemporaryDirectory(prefix="pkg-") as temporary_directory:
        temporary = Path(temporary_directory)
        archive_path = temporary / "package.zip"
        staging_path = temporary / "unpacked"
        if not _download(url, archive_path, expected_sha256):
            return False
        if not _extract_zip(archive_path, staging_path):
            return False
        entries = list(staging_path.iterdir())
        if len(entries) == 1 and entries[0].is_dir():
            extracted_root = entries[0]
            for child in extracted_root.iterdir():
                shutil.move(str(child), str(staging_path / child.name))
            extracted_root.rmdir()
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staging_path), str(destination))
    return True


def install_python():
    architecture = platform.machine().lower()
    if architecture in ("amd64", "x86_64"):
        architecture = "amd64"
    elif architecture in ("arm64", "aarch64"):
        architecture = "arm64"
    else:
        print(f"Portable Python is not available for architecture: {architecture}")
        return False

    destination = TOOLS_DIR / "python"
    python_executable = destination / "python.exe"
    if not python_executable.exists():
        if destination.exists():
            print(f"Incomplete Python installation found in {destination}")
            print("Remove that package directory manually before reinstalling.")
            return False
        if not _install_zip(PYTHON_URLS[architecture], destination):
            return False
    pth_file = destination / f"python{PYTHON_VERSION.replace('.', '')[:3]}._pth"
    if not pth_file.exists():
        print("Python archive is missing its expected ._pth configuration.")
        return False
    lines = pth_file.read_text(encoding="utf-8").splitlines()
    for path in ("Lib/site-packages", "../../packages/python313"):
        if path not in lines:
            lines.append(path)
    if "import site" not in lines:
        lines.append("import site")
    pth_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    pip_package = destination / "Lib" / "site-packages" / "pip" / "__init__.py"
    if not pip_package.exists():
        with tempfile.TemporaryDirectory(prefix="pkg-pip-") as temporary_directory:
            get_pip = Path(temporary_directory) / "get-pip.py"
            if not _download("https://bootstrap.pypa.io/get-pip.py", get_pip):
                return False
            if not run_process([str(python_executable), str(get_pip)]):
                return False
        if not pip_package.exists():
            print("Python was installed, but pip bootstrap did not create pip.")
            return False

    print(f"Installed portable Python in {destination}")
    print(f"Run it with: \"{destination / 'python.exe'}\"")
    return True


def install_cpp():
    try:
        with urllib.request.urlopen(
            "https://ziglang.org/download/index.json", timeout=30
        ) as response:
            releases = json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        print(f"Could not retrieve the portable C/C++ compiler release list: {error}")
        return False

    architecture = platform.machine().lower()
    target = {
        "amd64": "x86_64-windows",
        "x86_64": "x86_64-windows",
        "arm64": "aarch64-windows",
        "aarch64": "aarch64-windows",
        "x86": "x86-windows",
        "i386": "x86-windows",
        "i686": "x86-windows",
    }.get(architecture)
    if target is None:
        print(f"Portable C/C++ compiler is not available for architecture: {architecture}")
        return False

    stable_versions = sorted(
        (
            tuple(int(part) for part in name.split(".")),
            release_data,
        )
        for name, release_data in releases.items()
        if name.count(".") == 2
        and all(part.isdigit() for part in name.split("."))
        and isinstance(release_data, dict)
        and isinstance(release_data.get(target), dict)
    )
    release = stable_versions[-1][1] if stable_versions else None
    if release is None:
        print(f"No portable compiler build was found for {target}.")
        return False

    build = release[target]
    destination = TOOLS_DIR / "cpp"
    if (destination / "zig.exe").exists():
        print(f"C/C++ compiler is already installed in {destination}")
        return True
    if not _install_zip(
        build["tarball"],
        destination,
        expected_sha256=build.get("shasum"),
    ):
        return False
    print(f"Installed portable C/C++ compiler in {destination}")
    print(f"Compile C++ with: \"{destination / 'zig.exe'}\" c++ <source.cpp> -o <program.exe>")
    return True


def install_pip_package(package_spec):
    portable_python = TOOLS_DIR / "python" / "python.exe"
    if portable_python.exists():
        python_executable = portable_python
        packages_directory = PYTHON_PACKAGES_DIR
    else:
        python_executable = Path(sys.executable)
        packages_directory = HOST_PACKAGES_DIR
    packages_directory.mkdir(parents=True, exist_ok=True)
    return run_process(
        [
            str(python_executable),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--target",
            str(packages_directory),
            package_spec,
        ]
    )


def installed_python_packages():
    portable_python = TOOLS_DIR / "python" / "python.exe"
    packages_directory = (
        PYTHON_PACKAGES_DIR if portable_python.exists() else HOST_PACKAGES_DIR
    )
    try:
        from importlib.metadata import distributions

        return sorted(
            {
                distribution.metadata["Name"]
                for distribution in distributions(path=[str(packages_directory)])
                if distribution.metadata.get("Name")
            },
            key=str.casefold,
        )
    except OSError as error:
        print(f"Could not read installed package metadata: {error}")
        return []

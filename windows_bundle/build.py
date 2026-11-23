"""Build a one-file Windows executable from the Git index and current virtual environment."""

import argparse
import importlib.metadata
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
PROGRAMS = {"server": "SmartSchoolVision-Server", "camera": "SmartSchoolVision-Camera"}


def bundle_assets(directory: Path) -> None:
    tracked = subprocess.check_output(
        ["git", "ls-files", "-z", "--", "site", "static", "templates"], cwd=ROOT
    )
    for name in tracked.decode("utf-8").split("\0"):
        if not name or name.startswith(("static/images/", "static/список/")):
            continue
        target = directory / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(subprocess.check_output(["git", "show", f":{name}"], cwd=ROOT))


def collect_licenses(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "LICENSE", directory / "SmartSchoolVision-LICENSE.txt")
    for distribution in importlib.metadata.distributions():
        notices = [file for file in distribution.files or () if ".dist-info" in str(file)
                   and file.name.lower().startswith(("license", "copying", "notice"))]
        for notice in notices:
            target = directory / distribution.metadata["Name"] / Path(*notice.parts[1:])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(distribution.locate_file(notice), target)


def build(program: str, directory: Path) -> None:
    assets = directory / program / "assets"
    bundle_assets(assets)
    collect_licenses(assets / "third-party-licenses")
    args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--noupx",
            "--name", PROGRAMS[program], "--icon", str(ROOT / "icon.ico"), "--paths", str(ROOT),
            "--workpath", str(directory / program / "work"), "--distpath", str(directory / "dist"),
            "--specpath", str(directory / program), "--collect-submodules", "uvicorn",
            "--log-level", "WARN"]
    for name in ("site", "static", "templates", "third-party-licenses"):
        args.extend(("--add-data", f"{assets / name}:{name}"))
    if program == "camera":
        args.extend(("--collect-data", "facenet_pytorch", "--collect-data", "ultralytics",
                     "--hidden-import", "ultralytics.models", "--copy-metadata", "ultralytics"))
    args.append(str(ROOT / "windows_bundle" / f"{program}.py"))
    subprocess.run(args, cwd=ROOT, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", choices=PROGRAMS)
    parser.add_argument("directory", type=Path)
    parsed = parser.parse_args()
    build(parsed.program, parsed.directory.resolve())

"""Paths shared by the standalone Windows executables."""

import os
from pathlib import Path
import shutil
import sys


BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
LOOPBACK = "127.0.0.1"


def default_data_dir() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    root = Path(local) if local else Path.home() / "AppData" / "Local"
    return root / "SmartSchoolVision"


def resolve_video_source(source: str | None) -> str | None:
    if source is None:
        return None
    path = Path(source).expanduser().resolve(strict=True)
    if not path.is_file():
        raise ValueError(f"Expected a video file: {path}")
    return str(path)


def stage_web_assets(bundle: Path, state: Path) -> None:
    if bundle.resolve() == state.resolve():
        return
    shutil.copytree(bundle / "site", state / "site", dirs_exist_ok=True)
    shutil.copytree(
        bundle / "static", state / "static", dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("images", "список"),
    )


def stage_license_notices(program: str, state: Path) -> None:
    bundled = BUNDLE_ROOT / "third-party-licenses"
    if bundled.is_dir():
        shutil.copytree(bundled, state / "third-party-licenses" / program, dirs_exist_ok=True)


def enter_data_dir(path: Path) -> Path:
    state = path.expanduser().resolve()
    state.mkdir(parents=True, exist_ok=True)
    os.chdir(state)
    return state

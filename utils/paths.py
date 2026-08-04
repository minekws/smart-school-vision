from __future__ import annotations

import os
import re
from pathlib import Path

from config import settings


_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9_.\-:]+$")


def sanitize_camera_id(camera_id: str) -> str:
    if not camera_id or not _SAFE_NAME_RE.match(camera_id):
        raise ValueError(f"Недопустимый camera_id: {camera_id!r}")

    base = Path(settings.base_data_dir).resolve()
    target = (base / camera_id).resolve()

    if not str(target).startswith(str(base)):
        raise ValueError("Path traversal detected")

    return camera_id


def camera_dir(camera_id: str) -> Path:
    safe = sanitize_camera_id(camera_id)
    return Path(settings.base_data_dir) / safe


def days_dir(camera_id: str) -> Path:
    return camera_dir(camera_id) / "days"


def peoples_dir(camera_id: str) -> Path:
    return camera_dir(camera_id) / "peoples"


def accounts_file(camera_id: str) -> Path:
    return camera_dir(camera_id) / "accounts.json"


def day_dir(camera_id: str, date_str: str) -> Path:
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        raise ValueError(f"Недопустимый формат даты: {date_str}")
    return days_dir(camera_id) / date_str


def ensure_camera_structure(camera_id: str) -> Path:
    base = camera_dir(camera_id)
    (base / "days").mkdir(parents=True, exist_ok=True)
    (base / "peoples").mkdir(parents=True, exist_ok=True)

    acc = accounts_file(camera_id)
    if not acc.exists():
        acc.write_text("[]", encoding="utf-8")

    return base
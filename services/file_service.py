from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import aiofiles

logger = logging.getLogger("smartschool.files")
_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


async def read_json(path: Path) -> Any:
    try:
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            content = await f.read()
        return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


async def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2, ensure_ascii=False)
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(content)


async def read_json_safe(path: Path, default: Any = None) -> Any:
    result = await read_json(path)
    return result if result is not None else (default() if callable(default) else default)


async def update_json_atomic(
    path: Path,
    updater: Callable[[Any], Any],
    default: Any = None,
) -> Any:
    key = str(path.resolve())
    async with _locks[key]:
        data = await read_json_safe(path, default=default)
        data = updater(data)
        await write_json(path, data)
        return data


async def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False) + "\n"
    async with aiofiles.open(path, "a", encoding="utf-8") as f:
        await f.write(line)


async def save_image(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(path, "wb") as f:
        await f.write(data)
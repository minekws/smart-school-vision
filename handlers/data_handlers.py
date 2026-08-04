from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import WebSocket

from handlers.registry import ws_action
from models import SessionData
from services.file_service import read_json, read_json_safe
from services.stats_service import build_weekly_charts
from utils.paths import (
    accounts_file,
    day_dir,
    days_dir,
    peoples_dir,
    sanitize_camera_id,
)

logger = logging.getLogger("smartschool.handlers.data")


@ws_action("spisok_inf")
async def handle_spisok_inf(
    ws: WebSocket,
    data: Dict[str, Any],
    sess: Optional[SessionData],
) -> None:
    camera_id = (data.get("data") or {}).get("camera_id")
    if not camera_id:
        await ws.send_json({"action": "error", "error": "Не указан camera_id"})
        return

    sanitize_camera_id(camera_id)
    acc_path = accounts_file(camera_id)
    acc_json = await read_json_safe(acc_path, default=list)
    await ws.send_json({"action": "spisok_list", "data": acc_json})

    # peoples info
    pdir = peoples_dir(camera_id)
    acc_info = []
    if pdir.exists():
        for f in pdir.iterdir():
            if f.suffix == ".json":
                try:
                    file_data = await read_json(f)
                    if file_data:
                        acc_info.append(file_data)
                except Exception as e:
                    logger.error("Ошибка чтения %s: %s", f, e)

    await ws.send_json({"action": "spisok_info_list", "data": acc_info})


@ws_action("get_json_files")
async def handle_get_json_files(
    ws: WebSocket,
    data: Dict[str, Any],
    sess: Optional[SessionData],
) -> None:
    camera_id = data.get("data", {}).get("camera_id")
    if not camera_id:
        await ws.send_json({"action": "json_files_list", "files": []})
        return

    sanitize_camera_id(camera_id)
    ddir = days_dir(camera_id)
    json_files = []

    if ddir.exists():
        dates = sorted(
            [d.name for d in ddir.iterdir() if d.is_dir()],
            reverse=True,
        )
        if dates:
            latest = dates[0]
            date_path = ddir / latest

            static_file = date_path / "static.json"
            obn_file = date_path / "obn.json"

            if static_file.exists():
                tod = await read_json(static_file)
                if tod:
                    json_files.append({"today": tod, "day": str(date_path)})

            if obn_file.exists():
                obn = await read_json(obn_file)
                if obn:
                    json_files.append({"obnaruz": obn, "day": str(date_path)})

    await ws.send_json({"action": "json_files_list", "files": json_files})


@ws_action("get_json_content")
async def handle_get_json_content(
    ws: WebSocket,
    data: Dict[str, Any],
    sess: Optional[SessionData],
) -> None:
    file_data = data.get("data", {})
    filename = file_data.get("filename")
    file_path = file_data.get("path")
    camera_id = file_data.get("camera_id")

    if not filename or not file_path or not camera_id:
        await ws.send_json({
            "action": "json_content_error",
            "error": "Не указаны filename, path или camera_id",
        })
        return

    sanitize_camera_id(camera_id)
    from utils.paths import camera_dir
    base = camera_dir(camera_id)
    full_path = (base / file_path).resolve()

    # Path traversal protection
    if not str(full_path).startswith(str(base.resolve())):
        await ws.send_json({
            "action": "json_content_error",
            "error": "Недопустимый путь",
        })
        return

    if full_path.exists():
        content = await read_json(full_path)
        await ws.send_json({
            "action": "json_file_content",
            "filename": filename,
            "content": content,
        })
    else:
        await ws.send_json({
            "action": "json_content_error",
            "error": "Файл не найден",
        })


@ws_action("get_stats")
async def handle_get_stats(
    ws: WebSocket,
    data: Dict[str, Any],
    sess: Optional[SessionData],
) -> None:
    cam = data.get("camera_id") or (sess.camera_id if sess else None)
    date_str = data.get("date")

    if not cam or not date_str:
        await ws.send_json({"action": "error", "error": "Не указаны camera_id или date"})
        return

    sanitize_camera_id(cam)
    static_path = day_dir(cam, date_str) / "static.json"

    if static_path.exists():
        content = await read_json(static_path)
        await ws.send_json({"action": "stats_data", "data": content})
    else:
        await ws.send_json({"action": "error", "error": "Данные за указанную дату не найдены"})


@ws_action("get_people")
async def handle_get_people(
    ws: WebSocket,
    data: Dict[str, Any],
    sess: Optional[SessionData],
) -> None:
    cam = data.get("camera_id") or (sess.camera_id if sess else None)
    date_str = data.get("date")

    if not cam or not date_str:
        await ws.send_json({"action": "error", "error": "Не указаны camera_id или date"})
        return

    sanitize_camera_id(cam)
    people_path = day_dir(cam, date_str) / "people"

    if people_path.exists():
        people_data = []
        for f in people_path.iterdir():
            if f.suffix == ".json":
                content = await read_json(f)
                if content:
                    people_data.append(content)
        await ws.send_json({"action": "people_list", "people": people_data})
    else:
        await ws.send_json({"action": "error", "error": "Данные не найдены"})


@ws_action("grafiki")
async def handle_grafiki(
    ws: WebSocket,
    data: Dict[str, Any],
    sess: Optional[SessionData],
) -> None:
    payload = data.get("data", {})
    cam = payload.get("camera_id") or (sess.camera_id if sess else None)

    if not cam:
        await ws.send_json({"action": "grafiki_error", "error": "Не указан camera_id"})
        return

    try:
        sanitize_camera_id(cam)
        result = await build_weekly_charts(cam)
        await ws.send_json({"action": "grafiki_data", **result})
    except Exception as e:
        logger.exception("Ошибка генерации графиков: %s", e)
        await ws.send_json({
            "action": "grafiki_error",
            "error": f"Ошибка: {e}",
        })
from __future__ import annotations
import asyncio
import base64
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import WebSocket
from config import settings
from handlers.registry import ws_action
from models import DEFAULT_STATIC, SessionData
from services.camera_service import sync_faces_to_camera
from services.file_service import (
    append_jsonl,
    read_json_safe,
    save_image,
    update_json_atomic,
    write_json,
)
from utils.paths import (
    accounts_file,
    day_dir,
    ensure_camera_structure,
    peoples_dir,
)

logger = logging.getLogger("smartschool.handlers.camera")


def _parse_timestamp(ts_iso: Optional[str]) -> datetime:
    if not ts_iso:
        return datetime.now()
    try:
        return datetime.fromisoformat(ts_iso)
    except ValueError:
        try:
            return datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
        except Exception:
            return datetime.now()

@ws_action("init")
async def handle_init(
    ws: WebSocket,
    data: Dict[str, Any],
    sess: Optional[SessionData],
) -> None:
    camera_host = data.get("camera_id")
    logger.info(camera_host)
    if camera_host:
        logger.info(camera_host)
        asyncio.create_task(sync_faces_to_camera(camera_host))

@ws_action("camera")
async def handle_camera_event(
    ws: WebSocket,
    data: Dict[str, Any],
    sess: Optional[SessionData],
) -> None:
    cam_id = str(data.get("camera_id", ""))
    logger.info(cam_id)
    event_id = data.get("event_id")
    ts_iso = data.get("timestamp")
    person = data.get("person", {})
    img_b64 = data.get("image")

    if not cam_id or not img_b64:
        await ws.send_json({"action": "error", "error": "camera_id и image обязательны"})
        return

    first = person.get("first_name", "").strip()
    last = person.get("last_name", "").strip()
    has_flicker = person.get("flicker", False)
    flicker_confidence = person.get("flicker_confidence", 0.0)
    emotion = person.get("emotion")
    emotion_confidence = person.get("emotion_confidence", 0.0)

    dt = _parse_timestamp(ts_iso)

    ensure_camera_structure(cam_id)
    date_str = dt.date().isoformat()
    ddir = day_dir(cam_id, date_str)
    people_path = ddir / "people"
    images_path = ddir / "images"
    people_path.mkdir(parents=True, exist_ok=True)
    images_path.mkdir(parents=True, exist_ok=True)

    try:
        img_data = base64.b64decode(img_b64.split(",")[-1])
    except Exception:
        await ws.send_json({"action": "error", "error": "Некорректное поле image"})
        return

    img_filename = f"{first}_{last}.jpg".replace(" ", "_")
    await save_image(images_path / img_filename, img_data)
    detection_payload = {
        k: v for k, v in data.items() if k != "image"
    }
    detection_payload["timestamp"] = dt.isoformat()
    detection_payload["detection_details"] = {
        "has_flicker": has_flicker,
        "flicker_confidence": flicker_confidence,
        "emotion": emotion,
        "emotion_confidence": emotion_confidence,
        "detection_time": dt.isoformat(),
    }
    await write_json(people_path / f"{first}_{last}.json", detection_payload)

    static_path = ddir / "static.json"

    def _update_static(s: dict) -> dict:
        if s is None:
            s = {**DEFAULT_STATIC, "camera_id": cam_id}
        s["person_total"] = s.get("person_total", 0) + 1
        if has_flicker:
            s["flicker_total"] = s.get("flicker_total", 0) + 1
        if emotion:
            es = s.setdefault("emotion_stats", {})
            es[emotion] = es.get(emotion, 0) + 1
        slot = f"{dt.hour}:{(dt.minute // 5) * 5:02d}"
        graf = s.setdefault("graf", {})
        if slot in graf:
            graf[slot] = graf[slot] + 1
        if dt.hour > 8 or (dt.hour == 8 and dt.minute > 0):
            s["opoz_total"] = s.get("opoz_total", 0) + 1
        s["last_update"] = dt.isoformat()
        return s

    static_data = await update_json_atomic(static_path, _update_static)
    acc_path = accounts_file(cam_id)
    acc_data = await read_json_safe(acc_path, default=list)
    full_name = f"{first} {last}".strip()

    idd_name = email = acc_type = None
    for account in acc_data:
        if isinstance(account, dict) and account.get("username") == full_name:
            idd_name = account.get("id")
            email = account.get("mail")
            acc_type = account.get("role")
            break

    obn_path = ddir / "obn.json"

    time_obn = f"{dt.hour}:{dt.minute:02d}"
    opoz_obn = "Да" if dt.hour > 8 else "Нет"

    obn_record = {
        "id": idd_name,
        "name": full_name,
        "opoz": opoz_obn,
        "time": time_obn,
        "camera": cam_id,
        "has_flicker": has_flicker,
        "emotion": emotion,
    }

    def _update_obn(obn: list) -> list:
        if obn is None:
            obn = []
        obn.insert(0, obn_record)
        return obn[:6]

    await update_json_atomic(obn_path, _update_obn, default=list)
    list_path = Path(settings.list_dir) / "participants.jsonl"

    await append_jsonl(
        list_path,
        {
            "first_name": first,
            "last_name": last,
            "camera_id": cam_id,
            "timestamp": dt.isoformat(),
            "event_id": event_id,
            "has_flicker": has_flicker,
            "flicker_confidence": flicker_confidence,
            "emotion": emotion,
            "emotion_confidence": emotion_confidence,
        },
    )

    pdir = peoples_dir(cam_id)
    name_info_path = pdir / f"{first}_{last}.json"

    def _update_person_info(info: dict) -> dict:
        if info is None:
            info = {}

        info.update({
            "id": idd_name,
            "first_name": first,
            "last_name": last,
            "mail": email,
            "role": acc_type,
            "username": full_name,
        })

        if has_flicker:
            fh = info.setdefault("flicker_history", [])
            fh.append({
                "date": dt.date().isoformat(),
                "time": dt.strftime("%H:%M"),
                "confidence": flicker_confidence,
            })
            info["flicker_history"] = fh[-30:]

        if emotion:
            eh = info.setdefault("emotion_history", [])
            eh.append({
                "date": dt.date().isoformat(),
                "time": dt.strftime("%H:%M"),
                "emotion": emotion,
                "confidence": emotion_confidence,
            })
            info["emotion_history"] = eh[-50:]
            es = info.setdefault("emotion_statistics", {})
            es[emotion] = es.get(emotion, 0) + 1

        info["current_state"] = {
            "has_flicker": has_flicker,
            "emotion": emotion,
            "last_updated": dt.isoformat(),
        }

        d7 = info.setdefault("detections_last_7_days", {})
        date_key = dt.date().isoformat()
        time_str = dt.strftime("%H:%M")
        if date_key not in d7 or time_str < d7[date_key]:
            d7[date_key] = time_str
        keep = sorted(d7.keys())[-7:]
        info["detections_last_7_days"] = {k: d7[k] for k in keep}

        info["last_detected"] = dt.isoformat()
        info["last_camera_id"] = cam_id
        return info

    try:
        await update_json_atomic(name_info_path, _update_person_info, default=dict)
    except Exception as e:
        logger.error("Ошибка обновления peoples: %s", e)

    await ws.send_json({
        "action": "camera_processed",
        "event_id": event_id,
        "status": "success",
        "person": full_name,
        "has_flicker": has_flicker,
        "emotion": emotion,
    })
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List

import aiohttp
from config import settings
from services.file_service import read_json_safe
import logging, sys

logger = logging.getLogger("smartschool.camera")
def split_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split(maxsplit=1)
    return parts[0] if parts else "", parts[1] if len(parts) > 1 else ""


async def sync_faces_to_camera(camera_host: str) -> None:
    try:
        users = await read_json_safe(settings.users_path, default=[])
        if not users:
            logger.warning("Нет пользователей для синхронизации")
            return

        async with aiohttp.ClientSession() as session:
            for user in users:
                user_id = str(user.get("id", ""))
                username = user.get("username", "")
                first_name, last_name = split_name(username)
                logger.debug(
                        "Фото не найдено для %s %s (id=%s)",
                        first_name, last_name, user_id,
                    )
                image_path = settings.images_path / f"{user_id}.jpg"
                if not image_path.exists():
                    logger.debug(
                        "Фото не найдено для %s %s (id=%s)",
                        first_name, last_name, user_id,
                    )
                    continue

                img_bytes = image_path.read_bytes()

                form = aiohttp.FormData()
                form.add_field(
                    "file",
                    img_bytes,
                    filename=f"{first_name}_{last_name}_{uuid.uuid4().hex[:8]}.jpg",
                    content_type="image/jpeg",
                )
                form.add_field("first_name", first_name)
                form.add_field("last_name", last_name)

                url = "http://127.0.0.1:5000/"+camera_host+"/api/upload_face"
                logger.info(f"Отправляем фото на: {url}")
                try:
                    async with session.post(url, data=form, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            logger.info(
                                "Синхронизировано: %s %s → %s",
                                first_name, last_name, camera_host,
                            )
                        else:
                            txt = await resp.text()
                            logger.error(
                                "Ошибка синхронизации %d: %s",
                                resp.status, txt[:200],
                            )
                except Exception as e:
                    logger.error("Камера %s недоступна: %s", camera_host, e)

    except Exception as e:
        logger.exception("Ошибка синхронизации: %s", e)
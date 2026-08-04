from __future__ import annotations

import base64
import logging
from typing import Any, Dict, Optional

from fastapi import WebSocket

from handlers.registry import ws_action
from models import ManageAccountPayload, SessionData
from services.file_service import save_image, update_json_atomic
from utils.paths import accounts_file, sanitize_camera_id
from utils.security import hash_password
from config import settings

logger = logging.getLogger("smartschool.handlers.admin")


@ws_action("manage_account")
async def handle_manage_account(
    ws: WebSocket,
    data: Dict[str, Any],
    sess: Optional[SessionData],
) -> None:
    payload = data.get("data", {})

    try:
        mp = ManageAccountPayload(**payload)
    except Exception as e:
        await ws.send_json({
            "action": "error",
            "source_action": "manage_account",
            "error": f"Неверные данные: {e}",
        })
        return

    sanitize_camera_id(mp.camera_id)
    acc_path = accounts_file(mp.camera_id)

    if not acc_path.exists():
        await ws.send_json({
            "action": "error",
            "source_action": "manage_account",
            "error": "Файл аккаунтов не найден",
        })
        return

    try:
        if mp.sub_action == "delete":
            await _handle_delete(ws, acc_path, mp)
        elif mp.sub_action == "edit":
            await _handle_edit(ws, acc_path, mp)
    except ValueError as e:
        await ws.send_json({
            "action": "error",
            "source_action": "manage_account",
            "error": str(e),
        })


async def _handle_delete(ws, acc_path, mp: ManageAccountPayload) -> None:
    acc_id = mp.account_id
    if not acc_id:
        raise ValueError("Не указан account_id для удаления")

    deleted_account = None

    def _delete(accounts: list) -> list:
        nonlocal deleted_account
        for i, acc in enumerate(accounts):
            if acc.get("id") == acc_id:
                deleted_account = accounts.pop(i)
                return accounts
        raise ValueError("Аккаунт не найден")

    await update_json_atomic(acc_path, _delete, default=list)

    await ws.send_json({
        "action": "account_deleted",
        "success": True,
        "account_id": acc_id,
    })


async def _handle_edit(ws, acc_path, mp: ManageAccountPayload) -> None:
    acc_id = mp.id
    if acc_id is None:
        raise ValueError("Не указан ID аккаунта")

    if mp.photo:
        try:
            photo_b64 = mp.photo
            if "," in photo_b64:
                photo_b64 = photo_b64.split(",", 1)[1]
            img_bytes = base64.b64decode(photo_b64)
            photo_path = settings.images_path / f"{acc_id}.jpg"
            await save_image(photo_path, img_bytes)
            logger.info("Фото обновлено: %s", photo_path)
        except Exception as e:
            logger.error("Ошибка сохранения фото: %s", e)

    update_fields = {}
    if mp.username is not None:
        update_fields["username"] = mp.username
    if mp.mail is not None:
        update_fields["mail"] = mp.mail
    if mp.role is not None:
        update_fields["role"] = mp.role
    if mp.password is not None and mp.password.strip():
        update_fields["password"] = hash_password(mp.password.strip())

    edited_account = None

    def _edit(accounts: list) -> list:
        nonlocal edited_account
        target = str(acc_id)
        for idx, acc in enumerate(accounts):
            if str(acc.get("id")) == target:
                acc.update(update_fields)
                edited_account = acc
                return accounts
        raise ValueError("Аккаунт не найден")

    await update_json_atomic(acc_path, _edit, default=list)

    if edited_account is None:
        raise ValueError("Аккаунт не найден")

    await ws.send_json({
        "action": "account_edited",
        "success": True,
        "account": edited_account,
    })
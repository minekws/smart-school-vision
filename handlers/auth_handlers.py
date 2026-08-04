from __future__ import annotations
import asyncio
import base64
import logging
from typing import Any, Dict, Optional

from fastapi import WebSocket

from auth import (
    consume_invite_code,
    store_invite_code,
    validate_invite_code,
)
from config import settings
from database import create_session, destroy_session, get_session
from handlers.registry import ws_action
from models import LoginPayload, RegisterPayload, Role, SessionData
from services.file_service import save_image
from services.user_service import (
    check_user_exists,
    create_user,
    save_user_to_camera_file,
    verify_user,
)
from utils.paths import accounts_file, ensure_camera_structure

logger = logging.getLogger("smartschool.handlers.auth")
live_websockets: Dict[str, WebSocket] = {}

def _set_cookie_msg(sid: str) -> dict:
    return {
        "action": "set_cookie",
        "name": settings.session_cookie_name,
        "value": sid,
        "max_age": settings.session_ttl,
        "path": "/",
        "sameSite": "Lax",
        "secure": False,
        "httpOnly": False,
    }

@ws_action("xto_ya")
async def handle_xto_ya(
    ws: WebSocket,
    data: Dict[str, Any],
    sess: Optional[SessionData],
) -> None:
    token = data.get("token")
    found = await get_session(token)
    if found:
        live_websockets[token] = ws
        await ws.send_json({
            "action": "xto_ya",
            "ok": True,
            "name": found.username,
            "role": found.role,
            "camera_id": found.camera_id,
        })
    else:
        await ws.send_json({"action": "xto_ya", "ok": False})

@ws_action("login")
async def handle_login(
    ws: WebSocket,
    data: Dict[str, Any],
    sess: Optional[SessionData],
) -> None:
    payload = data.get("data") or {}

    token = payload.get("token")
    if token:
        existing = await get_session(token)
        if existing:
            live_websockets[token] = ws
            await ws.send_json({
                "action": "login_success",
                "name": existing.username,
                "role": existing.role,
                "token": token,
            })
            return

    try:
        lp = LoginPayload(**payload)
    except Exception as e:
        await ws.send_json({
            "action": "login_failed",
            "error": f"Неверные данные: {e}",
        })
        return

    user = await verify_user(lp.identifier, lp.password)
    if not user:

        await asyncio.sleep(0.3)
        await ws.send_json({
            "action": "login_failed",
            "error": "Неверное имя пользователя или пароль",
        })
        return

    sid = await create_session(
        user["username"],
        user["role"],
        user.get("camera_id"),
    )
    live_websockets[sid] = ws

    await ws.send_json({
        "action": "login_success",
        "name": user["username"],
        "role": user["role"],
        "token": sid,
    })
    await ws.send_json(_set_cookie_msg(sid))

@ws_action("register")
async def handle_register(
    ws: WebSocket,
    data: Dict[str, Any],
    sess: Optional[SessionData],
) -> None:
    payload = data.get("data") or {}

    try:
        rp = RegisterPayload(**payload)
    except Exception as e:
        await ws.send_json({
            "action": "register_failed",
            "error": f"Неверные данные: {e}",
        })
        return

    is_mod_adding = sess and sess.role == Role.MODERATOR
    camera_id: Optional[str] = None

    if rp.role != Role.MODERATOR:
        if is_mod_adding:
            camera_id = payload.get("camera_id")
            logging.info(camera_id)
            if not camera_id:
                await ws.send_json({
                    "action": "register_failed",
                    "error": "Модератору необходимо указать camera_id",
                })
                return
        else:
            if not rp.inviteCode:
                await ws.send_json({
                    "action": "register_failed",
                    "error": "Требуется код-приглашение",
                })
                return

            code_data = validate_invite_code(rp.inviteCode)
            if not code_data:
                await ws.send_json({
                    "action": "register_failed",
                    "error": "Неверный или истёкший код-приглашение",
                })
                return
            camera_id = code_data.get("camera_id")
    else:
        camera_id = rp.cameraId
        if not camera_id:
            await ws.send_json({
                "action": "register_failed",
                "error": "Для модератора необходим camera_id",
            })
            return

    if await check_user_exists(rp.userName, camera_id):
        await ws.send_json({
            "action": "register_failed",
            "error": f"Пользователь уже существует в группе {camera_id}",
        })
        return

    record = await create_user(
        username=rp.userName,
        password=rp.password,
        camera_id=camera_id,
        role=rp.role.value,
        mail=rp.email,
    )
    if not record:
        await ws.send_json({
            "action": "register_failed",
            "error": "Не удалось сохранить пользователя",
        })
        return

    user_id = record["id"]

    if rp.role == Role.MODERATOR and camera_id:
        ensure_camera_structure(camera_id)

    if rp.photo:
        try:
            photo_b64 = rp.photo
            if "," in photo_b64:
                photo_b64 = photo_b64.split(",", 1)[1]
            img_bytes = base64.b64decode(photo_b64)
            photo_path = settings.images_path / f"{user_id}.jpg"
            await save_image(photo_path, img_bytes)
            logger.info("Фото сохранено: %s", photo_path)
        except Exception as e:
            logger.error("Ошибка сохранения фото: %s", e)

    if camera_id:
        ensure_camera_structure(camera_id)
        acc_path = accounts_file(camera_id)
        await save_user_to_camera_file(
            acc_path, user_id, rp.userName,
            camera_id, rp.role.value, rp.email,
        )

    if rp.role != Role.MODERATOR and not is_mod_adding and rp.inviteCode:
        consume_invite_code(rp.inviteCode)
    sid = await create_session(rp.userName, rp.role.value, camera_id)

    await ws.send_json({
        "action": "register_success",
        "success": True,
        "token": sid,
        "username": rp.userName,
        "role": rp.role.value,
        "newUserId": user_id,
    })
    await ws.send_json(_set_cookie_msg(sid))

@ws_action("logout")
async def handle_logout(
    ws: WebSocket,
    data: Dict[str, Any],
    sess: Optional[SessionData],
) -> None:
    if sess:
        await destroy_session(sess.sid)
        live_websockets.pop(sess.sid, None)
    await ws.send_json({
        "action": "clear_cookie",
        "name": settings.session_cookie_name,
        "path": "/",
    })

@ws_action("generate_invite_code")
async def handle_generate_invite(
    ws: WebSocket,
    data: Dict[str, Any],
    sess: Optional[SessionData],
) -> None:
    payload = data.get("data", {})
    camera_id = payload.get("cameraId")
    custom_code = payload.get("code")

    if not camera_id:
        await ws.send_json({"action": "error", "error": "Не указан cameraId"})
        return

    if custom_code and str(custom_code).strip():
        code = str(custom_code).strip()
    else:
        from utils.security import generate_invite_code
        code = generate_invite_code()

    from auth import store_invite_code
    expires_at = store_invite_code(
        code=code,
        camera_id=camera_id,
        generated_by=sess.username if sess else "unknown",
    )

    await ws.send_json({
        "action": "generate_code_success",
        "code": code,
    })
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import settings
from models import Role
from services.file_service import read_json_safe, update_json_atomic
from utils.security import hash_password, verify_password, generate_user_id

logger = logging.getLogger("smartschool.users")


async def load_users() -> List[Dict[str, Any]]:
    data = await read_json_safe(settings.users_path, default=list)
    return data if isinstance(data, list) else []


async def check_user_exists(
    username: str,
    camera_id: Optional[str] = None,
) -> bool:
    users = await load_users()
    for u in users:
        if u.get("username") == username:
            if camera_id is None or u.get("camera_id") == camera_id:
                return True
    return False


async def verify_user(
    identifier: str,
    password: str,
) -> Optional[Dict[str, Any]]:
    users = await load_users()
    for user in users:
        match = (
            user.get("mail") == identifier
            or user.get("camera_id") == identifier
            or user.get("username") == identifier
        )
        if match and verify_password(password, user.get("password", "")):
            return user
    return None


async def create_user(
    username: str,
    password: str,
    camera_id: Optional[str],
    role: str,
    mail: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    
    users = await load_users()
    while True:
        user_id = generate_user_id()
        if not any(u.get("id") == user_id for u in users):
            break
        
    record = {
        "id": user_id,
        "username": username,
        "password": hash_password(password),
        "camera_id": camera_id,
        "mail": mail or "None",
        "role": role,
    }

    def _append(current_users: list) -> list:
        for u in current_users:
            if (
                isinstance(u, dict)
                and u.get("username") == username
                and u.get("camera_id") == camera_id
            ):
                raise ValueError("duplicate")
        current_users.append({
            **record, 
            "registration_time": __import__("datetime").datetime.now().isoformat()
        })
        return current_users

    try:
        await update_json_atomic(settings.users_path, _append, default=list)
    except ValueError:
        return None

    return record


async def save_user_to_camera_file(
    camera_accounts_path: Path,
    user_id: str,
    username: str,
    camera_id: str,
    role: str,
    mail: Optional[str] = None,
) -> bool:
    image_path = f"static/images/{user_id}.jpg"

    def _append(users: list) -> list:
        for u in users:
            if (
                isinstance(u, dict)
                and u.get("username") == username
                and u.get("camera_id") == camera_id
            ):
                raise ValueError("duplicate")
        users.append({
            "id": user_id,
            "username": username,
            "camera_id": camera_id,
            "mail": mail,
            "role": role,
            "registration_time": __import__("datetime").datetime.now().isoformat(),
            "status": "None",
            "image": image_path,
        })
        return users

    try:
        await update_json_atomic(camera_accounts_path, _append, default=list)
        return True
    except ValueError:
        return False
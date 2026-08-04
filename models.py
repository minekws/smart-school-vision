from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator

class Role(str, Enum):
    MODERATOR = "moderator"
    USER = "user"
    CAMERA = "camera"

class LoginPayload(BaseModel):
    identifier: str = Field(..., min_length=1, max_length=200)
    password: str = Field(..., min_length=1, max_length=256)
    camera_id: Optional[str] = None
    token: Optional[str] = None


class RegisterPayload(BaseModel):
    userName: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=6, max_length=128)
    role: Role
    email: Optional[EmailStr] = None
    photo: Optional[str] = None
    inviteCode: Optional[str] = None
    cameraId: Optional[str] = None

    @field_validator("userName")
    @classmethod
    def no_special_chars(cls, v: str) -> str:
        if not re.match(r"^[а-яА-ЯёЁ\s\-]+$", v):
            raise ValueError("Имя должно содержать только русские буквы")
        return v.strip()


class CameraEventPayload(BaseModel):
    camera_id: str
    event_id: Optional[str] = None
    timestamp: Optional[str] = None
    person: Dict[str, Any] = Field(default_factory=dict)
    image: str


class InviteCodePayload(BaseModel):
    code: str = Field(..., min_length=5, max_length=64)
    cameraId: str


class ManageAccountPayload(BaseModel):
    sub_action: Literal["delete", "edit"]
    camera_id: str
    account_id: Optional[Any] = None
    id: Optional[Any] = None
    username: Optional[str] = None
    password: Optional[str] = None
    mail: Optional[str] = None
    role: Optional[str] = None
    photo: Optional[str] = None


class GrafikiPayload(BaseModel):
    camera_id: str

class UserRecord(BaseModel):
    id: str
    username: str
    password: str
    camera_id: Optional[str] = None
    mail: Optional[str] = None
    role: Role
    registration_time: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )


class AccountRecord(BaseModel):
    id: str
    username: str
    camera_id: Optional[str] = None
    mail: Optional[str] = None
    role: str
    registration_time: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )
    status: str = "None"
    image: Optional[str] = None


class SessionData(BaseModel):
    sid: str
    username: str
    role: str
    camera_id: Optional[str] = None
    expires: int
    expires_in: int = 0


DEFAULT_GRAPH = {
    f"{h}:{m:02d}": 0
    for h in range(7, 10)
    for m in range(0, 60, 5)
    if not (h == 9 and m > 0)
}

DEFAULT_STATIC: Dict[str, Any] = {
    "camera_id": None,
    "person_total": 0,
    "flicker_total": 0,
    "depr_total": 0,
    "opoz_total": 0,
    "graf": DEFAULT_GRAPH.copy(),
}
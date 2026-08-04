from __future__ import annotations

import json
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_host: str = "0.0.0.0"
    app_port: int = 8005

    db_path: str = "sessions.db"

    session_ttl: int = 7 * 24 * 60 * 60
    session_renew_threshold: int = 2 * 24 * 60 * 60
    session_cookie_name: str = "session_id"

    invite_code_ttl: int = 10 * 60
    list_dir: str = "lists"
    
    users_file: str = "users/users.json"
    image_folder: str = "static/images"
    base_data_dir: str = "data"
    face_api_base: str = "http://127.0.0.1:5000"

    allowed_origins: List[str] = [
        "http://127.0.0.1:8005",
        "http://localhost:8005",
    ]

    log_level: str = "INFO"

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _parse_origins(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    @property
    def list_file(self) -> Path:
        return Path(self.list_dir) / "participants.jsonl"

    @property
    def images_path(self) -> Path:
        return Path(self.image_folder)

    @property
    def users_path(self) -> Path:
        return Path(self.users_file)

    @property
    def data_path(self) -> Path:
        return Path(self.base_data_dir)


settings = Settings()
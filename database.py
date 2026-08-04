from __future__ import annotations

import logging
import secrets
import time
from typing import Optional

import aiosqlite

from config import settings
from models import SessionData

logger = logging.getLogger("smartschool.db")

_DB_INIT_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    sid        TEXT PRIMARY KEY,
    username   TEXT NOT NULL,
    role       TEXT NOT NULL,
    camera_id  TEXT,
    created_at INTEGER NOT NULL,
    expires    INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires);
"""


async def _conn() -> aiosqlite.Connection:
    db = await aiosqlite.connect(settings.db_path, timeout=30.0)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("PRAGMA synchronous=NORMAL;")
    await db.execute("PRAGMA busy_timeout=5000;")
    await db.execute("PRAGMA foreign_keys=ON;")
    await db.execute("PRAGMA cache_size=-10000;")
    return db


async def init_db() -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.executescript(_DB_INIT_SQL)
        await db.commit()
    logger.info("Database initialised (%s)", settings.db_path)


async def create_session(
    username: str,
    role: str,
    camera_id: Optional[str] = None,
) -> str:
    now = int(time.time())
    sid = secrets.token_urlsafe(32)
    async with aiosqlite.connect(settings.db_path) as db:
        while True:
            try:
                await db.execute(
                    "INSERT INTO sessions "
                    "(sid, username, role, camera_id, created_at, expires) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        sid,
                        username,
                        role,
                        str(camera_id) if camera_id else None,
                        now,
                        now + settings.session_ttl,
                    ),
                )
                await db.commit()
                return sid
            except aiosqlite.IntegrityError:
                sid = secrets.token_urlsafe(32)


async def get_session(sid: Optional[str]) -> Optional[SessionData]:
    if not sid:
        return None
    now = int(time.time())

    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT username, role, camera_id, expires "
            "FROM sessions WHERE sid = ?",
            (sid,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None

        expires = int(row["expires"])
        if expires < now:
            await db.execute(
                "DELETE FROM sessions WHERE sid = ?", (sid,)
            )
            await db.commit()
            return None

        if (expires - now) <= settings.session_renew_threshold:
            expires = now + settings.session_ttl
            await db.execute(
                "UPDATE sessions SET expires = ? WHERE sid = ?",
                (expires, sid),
            )
            await db.commit()

        return SessionData(
            sid=sid,
            username=row["username"],
            role=row["role"],
            camera_id=row["camera_id"],
            expires=expires,
            expires_in=max(0, expires - now),
        )


async def destroy_session(sid: Optional[str]) -> None:
    if not sid:
        return
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("DELETE FROM sessions WHERE sid = ?", (sid,))
        await db.commit()


async def cleanup_expired() -> int:
    now = int(time.time())
    async with aiosqlite.connect(settings.db_path) as db:
        cursor = await db.execute(
            "DELETE FROM sessions WHERE expires < ?", (now,)
        )
        await db.commit()
        return cursor.rowcount
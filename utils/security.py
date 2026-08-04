from __future__ import annotations
import bcrypt
import secrets


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            hashed.encode("utf-8"),
        )
    except Exception:
        return False

def generate_invite_code(length: int = 16) -> str:
    return secrets.token_urlsafe(length)

def generate_user_id() -> str:
    return str(secrets.randbelow(9000) + 1000)

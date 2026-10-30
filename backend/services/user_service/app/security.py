import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from jose import JWTError, jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

_password_hash = PasswordHash.recommended()
_JWT_PLACEHOLDERS = {"", "your_secret_key", "change_me"}


@dataclass(frozen=True)
class JWTSettings:
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int


class JWTConfigurationError(RuntimeError):
    pass


def get_jwt_settings() -> JWTSettings:
    secret_key = os.getenv("JWT_SECRET_KEY", "").strip()
    algorithm = os.getenv("JWT_ALGORITHM", "HS256").strip()
    raw_expiration = os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60").strip()

    if secret_key.lower() in _JWT_PLACEHOLDERS or len(secret_key) < 32:
        raise JWTConfigurationError(
            "JWT_SECRET_KEY must be configured with at least 32 characters"
        )
    if algorithm != "HS256":
        raise JWTConfigurationError("JWT_ALGORITHM must be HS256")
    try:
        expiration = int(raw_expiration)
    except ValueError as error:
        raise JWTConfigurationError(
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be a positive integer"
        ) from error
    if expiration <= 0:
        raise JWTConfigurationError(
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be a positive integer"
        )

    return JWTSettings(secret_key, algorithm, expiration)


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hash.verify(password, password_hash)
    except (UnknownHashError, ValueError, TypeError):
        return False


def create_access_token(user_id: int, role: str) -> str:
    settings = get_jwt_settings()
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {
            "sub": str(user_id),
            "role": role,
            "iat": issued_at,
            "exp": expires_at,
        },
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def decode_access_token(token: str) -> dict[str, object]:
    settings = get_jwt_settings()
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


__all__ = [
    "JWTConfigurationError",
    "JWTError",
    "create_access_token",
    "decode_access_token",
    "get_jwt_settings",
    "hash_password",
    "verify_password",
]

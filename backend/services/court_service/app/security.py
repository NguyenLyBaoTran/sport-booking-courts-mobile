import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from jose import JWTError, jwt

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

ALLOWED_ROLES = frozenset({"USER", "OWNER", "ADMIN"})
JWT_PLACEHOLDERS = {"", "your_secret_key", "change_me", "your_secret_key_here"}


@dataclass(frozen=True)
class JWTSettings:
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int


@dataclass(frozen=True)
class Principal:
    user_id: int
    role: str


class JWTConfigurationError(RuntimeError):
    pass


def get_jwt_settings() -> JWTSettings:
    secret_key = os.getenv("JWT_SECRET_KEY", "").strip()
    algorithm = os.getenv("JWT_ALGORITHM", "HS256").strip()
    raw_expiration = os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60").strip()

    if secret_key.lower() in JWT_PLACEHOLDERS or len(secret_key) < 32:
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


def decode_access_token(token: str) -> Principal:
    settings = get_jwt_settings()
    claims = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.algorithm],
        options={"require_sub": True, "require_iat": True, "require_exp": True},
    )

    subject = claims.get("sub")
    role = claims.get("role")
    issued_at = claims.get("iat")
    expires_at = claims.get("exp")
    if (
        not isinstance(subject, str)
        or not subject.isascii()
        or not subject.isdigit()
        or int(subject) <= 0
        or not isinstance(role, str)
        or role not in ALLOWED_ROLES
        or isinstance(issued_at, bool)
        or not isinstance(issued_at, (int, float))
        or issued_at < 0
        or isinstance(expires_at, bool)
        or not isinstance(expires_at, (int, float))
        or expires_at <= issued_at
    ):
        raise JWTError("Token claims are invalid")

    return Principal(user_id=int(subject), role=role)

import os
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    user_id: int
    role: str


def current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Principal:
    secret = os.getenv("JWT_SECRET_KEY", "").strip()
    if not secret or credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = jwt.decode(credentials.credentials, secret, algorithms=["HS256"])
        principal = Principal(int(claims["sub"]), str(claims["role"]))
    except (JWTError, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    if principal.role not in {"USER", "OWNER", "ADMIN"}:
        raise HTTPException(status_code=401, detail="Invalid bearer token")
    return principal


def require_internal_token(token: str | None) -> None:
    expected = os.getenv("INTERNAL_SERVICE_TOKEN", "").strip()
    if not expected or token != expected:
        raise HTTPException(status_code=403, detail="Internal service access required")


def require_customer(principal: Principal) -> None:
    if principal.role != "USER":
        raise HTTPException(status_code=403, detail="Customer account required")

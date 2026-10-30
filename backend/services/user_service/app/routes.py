from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, TokenResponse, UserCreate, UserResponse
from app.security import (
    create_access_token,
    decode_access_token,
    get_jwt_settings,
    hash_password,
    verify_password,
)

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing bearer token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    try:
        claims = decode_access_token(credentials.credentials)
        user_id = int(claims["sub"])
    except (JWTError, KeyError, TypeError, ValueError):
        raise unauthorized from None

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user


@router.post(
    "/auth/register",
    tags=["auth"],
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    email = str(payload.email)
    existing_user = db.scalar(select(User).where(User.email == email))
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    user = User(
        full_name=payload.full_name,
        email=email,
        password_hash=hash_password(payload.password.get_secret_value()),
        phone=payload.phone,
        role="USER",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from None
    db.refresh(user)
    return user


@router.post("/auth/login", tags=["auth"], response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == str(payload.email)))
    if (
        user is None
        or not user.is_active
        or not verify_password(
            payload.password.get_secret_value(),
            user.password_hash if user is not None else "",
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings = get_jwt_settings()
    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )


@router.get("/users/me", tags=["users"], response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)) -> User:
    return user
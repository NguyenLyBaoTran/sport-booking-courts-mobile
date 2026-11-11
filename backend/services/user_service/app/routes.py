import os
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.database import get_db
from app.models import User
from app.schemas import (
    AdminUserStatusUpdate,
    GoogleLoginRequest,
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserSummaryResponse,
)
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


@router.post("/auth/google", tags=["auth"], response_model=TokenResponse)
def google_login(
    payload: GoogleLoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is not configured",
        )

    try:
        claims = google_id_token.verify_oauth2_token(
            payload.id_token,
            google_requests.Request(),
            client_id,
        )
    except Exception:
        # Google token verification can fail for malformed tokens or when its
        # signing-key endpoint is unavailable. Never trust client-supplied claims.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google ID token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    email = str(claims.get("email", "")).strip().lower()
    google_sub = str(claims.get("sub", "")).strip()
    if not email or not google_sub or claims.get("email_verified") is not True:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google account email is not verified",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.scalar(select(User).where(User.google_sub == google_sub))
    if user is None:
        # Do not silently attach Google to a password account based only on
        # matching email. Existing accounts must be linked through a proven flow.
        existing_email_user = db.scalar(select(User).where(User.email == email))
        if existing_email_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account already uses this email; sign in with password first",
            )

        google_name = str(claims.get("name") or "").strip()
        user = User(
            full_name=(google_name or email.split("@", 1)[0])[:150],
            email=email,
            google_sub=google_sub,
            password_hash=hash_password(secrets.token_urlsafe(48)),
            role="USER",
            is_active=True,
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            # A simultaneous first sign-in may have inserted this Google subject.
            user = db.scalar(select(User).where(User.google_sub == google_sub))
            if user is None:
                raise HTTPException(status_code=409, detail="Google account could not be created") from None
        else:
            db.refresh(user)

    if not user.is_active or user.role != "USER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Google sign-in is available only for active user accounts",
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


def require_admin(user: User) -> None:
    if user.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


@router.get("/admin/users/summary", response_model=UserSummaryResponse, tags=["admin"])
def admin_user_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserSummaryResponse:
    require_admin(current_user)
    total = db.scalar(select(func.count(User.id))) or 0
    active = db.scalar(
        select(func.count(User.id)).where(User.is_active.is_(True))
    ) or 0
    owner_total = db.scalar(
        select(func.count(User.id)).where(User.role == "OWNER")
    ) or 0
    owner_active = db.scalar(
        select(func.count(User.id)).where(
            User.role == "OWNER",
            User.is_active.is_(True),
        )
    ) or 0
    return UserSummaryResponse(
        users={
            "total": int(total),
            "active": int(active),
            "inactive": int(total - active),
        },
        owners={
            "total": int(owner_total),
            "active": int(owner_active),
            "inactive": int(owner_total - owner_active),
        },
    )


@router.get("/admin/users", response_model=UserListResponse, tags=["admin"])
def admin_list_users(
    page: int = 1,
    page_size: int = 25,
    q: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserListResponse:
    require_admin(current_user)
    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(status_code=422, detail="Invalid pagination")
    if role is not None and role not in {"USER", "OWNER", "ADMIN"}:
        raise HTTPException(status_code=422, detail="Invalid role")

    query = select(User)
    if q:
        search = f"%{q.strip()}%"
        query = query.where(User.full_name.ilike(search) | User.email.ilike(search))
    if role is not None:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = list(
        db.scalars(
            query.order_by(User.created_at.desc(), User.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return UserListResponse(
        items=[UserResponse.model_validate(item) for item in items],
        total=int(total),
        page=page,
        page_size=page_size,
    )


@router.get("/admin/users/{user_id}", response_model=UserResponse, tags=["admin"])
def admin_get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    require_admin(current_user)
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/admin/users/{user_id}/status", response_model=UserResponse, tags=["admin"])
def admin_update_user_status(
    user_id: int,
    payload: AdminUserStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    require_admin(current_user)
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id and not payload.is_active:
        raise HTTPException(status_code=409, detail="The acting administrator cannot be deactivated")
    if user.role == "ADMIN" and user.is_active and not payload.is_active:
        active_admin_count = db.scalar(
            select(func.count(User.id)).where(User.role == "ADMIN", User.is_active.is_(True))
        ) or 0
        if active_admin_count <= 1:
            raise HTTPException(status_code=409, detail="The last active administrator cannot be deactivated")
    user.is_active = payload.is_active
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="User status conflict") from None
    db.refresh(user)
    return user

import os
import secrets
import smtplib
import ssl
from email.message import EmailMessage

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
    ForgotPasswordRequest,
    GoogleLoginRequest,
    LoginRequest,
    PasswordResetWithOtpRequest,
    TokenResponse,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserSummaryResponse,
    UserUpdate,
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


def verify_google_identity(id_token: str) -> tuple[str, str, dict]:
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is not configured",
        )

    try:
        claims = google_id_token.verify_oauth2_token(
            id_token,
            google_requests.Request(),
            client_id,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google ID token: {str(e)}",
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
    return email, google_sub, claims


def is_google_email_authoritative(email: str, claims: dict) -> bool:
    # Google is authoritative for Gmail addresses and verified Workspace domains.
    hosted_domain = str(claims.get("hd") or "").strip().lower()
    email_domain = email.rsplit("@", 1)[-1]
    return email.endswith("@gmail.com") or bool(hosted_domain and email_domain == hosted_domain)


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


import time

OTP_STORE: dict[str, dict] = {}


@router.post("/auth/forgot-password", tags=["auth"])
def request_password_reset_otp(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    email = str(payload.email)
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or user.role != "USER":
        return {
            "detail": "If an eligible account exists, a reset code has been sent to its email address."
        }

    otp_code = f"{secrets.randbelow(900000) + 100000}"
    OTP_STORE[email] = {
        "code": otp_code,
        "expires_at": time.time() + 600,
    }

    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_username = os.getenv("SMTP_USERNAME", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM", smtp_username).strip()

    if all((smtp_host, smtp_username, smtp_password, sender)):
        message = EmailMessage()
        message["Subject"] = "Reset your Sports Court Booking password"
        message["From"] = sender
        message["To"] = email
        message.set_content(
            f"Your password reset code is {otp_code}. It expires in 10 minutes. "
            "If you did not request this, you can ignore this email."
        )
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(smtp_host, int(os.getenv("SMTP_PORT", "587")), timeout=15) as smtp:
                smtp.starttls(context=context)
                smtp.login(smtp_username, smtp_password)
                smtp.send_message(message)
        except (OSError, ValueError, smtplib.SMTPException) as err:
            print(f"[SMTP ERROR] {err}")
            if os.getenv("APP_ENV") not in ("development", "test"):
                OTP_STORE.pop(email, None)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Could not send password reset email. Please try again later.",
                ) from None
    else:
        print(f"[OTP DEV] Password reset OTP for {email}: {otp_code}")

    res = {
        "detail": "If an eligible account exists, a reset code has been sent to its email address.",
    }
    if not all((smtp_host, smtp_username, smtp_password, sender)):
        res["otp_debug"] = otp_code
    return res


@router.post("/auth/reset-password", tags=["auth"])
def reset_password_with_otp(
    payload: PasswordResetWithOtpRequest,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    email = str(payload.email)
    otp_info = OTP_STORE.get(email)

    if not otp_info or time.time() > otp_info["expires_at"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP code expired or invalid. Please request a new OTP.",
        )

    if otp_info["code"] != payload.otp_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP code. Please check and try again.",
        )

    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or user.role != "USER":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active user account found with this email",
        )

    user.password_hash = hash_password(payload.new_password.get_secret_value())
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Password reset failed",
        ) from None

    OTP_STORE.pop(email, None)

    return {"detail": "Password updated successfully"}


@router.post("/auth/google", tags=["auth"], response_model=TokenResponse)
def google_login(
    payload: GoogleLoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    email, google_sub, claims = verify_google_identity(payload.id_token)

    user = db.scalar(select(User).where(User.google_sub == google_sub))
    if user is None:
        existing_email_user = db.scalar(select(User).where(User.email == email))
        if existing_email_user is not None:
            if existing_email_user.role != "USER" or not existing_email_user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Google sign-in is available only for active user accounts",
                )
            if not is_google_email_authoritative(email, claims):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This email already has an account; sign in with password",
                )

            user = db.scalar(
                select(User)
                .where(User.id == existing_email_user.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if user is None or not user.is_active or user.role != "USER":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Google sign-in is available only for active user accounts",
                )
            if user.google_sub not in (None, google_sub):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This account is already linked to a different Google account",
                )
            user.google_sub = google_sub
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                user = db.scalar(select(User).where(User.google_sub == google_sub))
                if user is None or user.id != existing_email_user.id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="This Google account is already linked to another user",
                    ) from None
            else:
                db.refresh(user)
        else:
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


@router.patch("/users/me", tags=["users"], response_model=UserResponse)
def update_my_profile(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    user = db.scalar(select(User).where(User.id == current_user.id).with_for_update())
    if user is None or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.phone is not None:
        user.phone = payload.phone

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Profile update conflict") from None
    db.refresh(user)
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

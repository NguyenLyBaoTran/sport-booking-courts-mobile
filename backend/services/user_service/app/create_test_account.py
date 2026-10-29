import getpass
import os

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select

from app.database import SessionLocal, engine
from app.models import User
from app.security import hash_password


def main() -> None:
    if os.getenv("APP_ENV", "").lower() not in {"development", "test"}:
        raise RuntimeError(
            "Privileged test accounts can only be created when APP_ENV is development or test"
        )
    if engine is None:
        raise RuntimeError("USER_DATABASE_URL must be configured")

    role = input("Role (OWNER/ADMIN): ").strip().upper()
    if role not in {"OWNER", "ADMIN"}:
        raise ValueError("Role must be OWNER or ADMIN")
    full_name = input("Full name: ").strip()
    raw_email = input("Email: ").strip()
    password = getpass.getpass("Password (8-128 characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise ValueError("Passwords do not match")
    if not full_name or len(full_name) > 150 or not 8 <= len(password) <= 128:
        raise ValueError("Full name, email, and an 8-128 character password are required")
    try:
        email = str(TypeAdapter(EmailStr).validate_python(raw_email)).lower()
    except ValidationError as error:
        raise ValueError("A valid email address is required") from error

    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)) is not None:
            raise ValueError("Email is already registered")
        user = User(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Created {role} account. User/Owner ID: {user.id}")


if __name__ == "__main__":
    main()

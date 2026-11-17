from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.security import decode_access_token
from app.routes import verify_google_identity


def test_disabled_google_login_rejects_before_token_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_LOGIN_ENABLED", "false")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "123456789-example.apps.googleusercontent.com")
    with pytest.raises(HTTPException) as error:
        verify_google_identity("untrusted-token")
    assert error.value.status_code == 503
    assert error.value.detail == "Google sign-in is not configured"


@pytest.mark.parametrize("flag", [None, "", "false", "0", "no", "enabled"])
def test_google_login_requires_explicit_true_even_with_client_id(monkeypatch: pytest.MonkeyPatch, flag: str | None) -> None:
    if flag is None:
        monkeypatch.delenv("GOOGLE_LOGIN_ENABLED", raising=False)
    else:
        monkeypatch.setenv("GOOGLE_LOGIN_ENABLED", flag)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "123456789-example.apps.googleusercontent.com")
    with pytest.raises(HTTPException) as error:
        verify_google_identity("untrusted-token")
    assert error.value.status_code == 503


def test_google_login_true_requires_client_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_LOGIN_ENABLED", "true")
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    with pytest.raises(HTTPException) as error:
        verify_google_identity("untrusted-token")
    assert error.value.status_code == 503


def test_google_login_true_verifies_with_configured_client_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_LOGIN_ENABLED", "true")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "123456789-example.apps.googleusercontent.com")
    monkeypatch.setattr("app.routes.google_id_token.verify_oauth2_token", lambda *_args: {
        "email": "test@example.com", "sub": "subject-1", "email_verified": True,
    })
    email, subject, claims = verify_google_identity("valid-token")
    assert (email, subject) == ("test@example.com", "subject-1")
    assert claims["email_verified"] is True


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "test-secret-key-with-32-or-more-characters",
    )
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[User.__table__])
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db() -> Generator[Session, None, None]:
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.state.test_session = test_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        del app.state.test_session
        Base.metadata.drop_all(engine, tables=[User.__table__])
        engine.dispose()


def test_register_creates_user_without_exposing_password(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "  Linh Nguyen ",
            "email": "LINH@example.com",
            "password": "strong-pass-123",
            "phone": " 0900000000 ",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["full_name"] == "Linh Nguyen"
    assert body["email"] == "linh@example.com"
    assert body["phone"] == "0900000000"
    assert body["role"] == "USER"
    assert "password" not in body
    assert "password_hash" not in body


def test_register_rejects_duplicate_email_case_insensitively(client: TestClient) -> None:
    payload = {
        "full_name": "Linh Nguyen",
        "email": "linh@example.com",
        "password": "strong-pass-123",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201

    duplicate = {**payload, "email": "LINH@EXAMPLE.COM"}
    response = client.post("/api/v1/auth/register", json=duplicate)

    assert response.status_code == 409


def test_public_registration_cannot_assign_privileged_role(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Linh Nguyen",
            "email": "linh@example.com",
            "password": "strong-pass-123",
            "role": "ADMIN",
        },
    )

    assert response.status_code == 422


def test_login_returns_jwt_with_user_id_role_and_expiry(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Linh Nguyen",
            "email": "linh@example.com",
            "password": "strong-pass-123",
        },
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "LINH@example.com", "password": "strong-pass-123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600
    assert body["user"]["role"] == "USER"
    claims = decode_access_token(body["access_token"])
    assert claims["sub"] == str(body["user"]["id"])
    assert claims["role"] == "USER"
    assert claims["exp"] > claims["iat"]


def test_login_rejects_wrong_password(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Linh Nguyen",
            "email": "linh@example.com",
            "password": "strong-pass-123",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "linh@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_current_user_requires_valid_bearer_token(client: TestClient) -> None:
    assert client.get("/api/v1/users/me").status_code == 401
    assert client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer invalid"},
    ).status_code == 401


@pytest.mark.parametrize("subject", [None, [], {}, True, 1.5])
def test_current_user_rejects_non_string_or_integer_subject(client: TestClient, monkeypatch: pytest.MonkeyPatch, subject: object) -> None:
    monkeypatch.setattr("app.routes.decode_access_token", lambda _token: {"sub": subject})
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 401


def test_current_user_returns_authenticated_account(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Linh Nguyen",
            "email": "linh@example.com",
            "password": "strong-pass-123",
        },
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "linh@example.com", "password": "strong-pass-123"},
    ).json()["access_token"]

    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "linh@example.com"
    assert response.json()["role"] == "USER"


def test_update_my_profile(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Old Name",
            "email": "update@example.com",
            "password": "strong-pass-123",
        },
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "update@example.com", "password": "strong-pass-123"},
    ).json()["access_token"]

    response = client.patch(
        "/api/v1/users/me",
        json={"full_name": "New Name", "phone": "0987654321"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "New Name"
    assert response.json()["phone"] == "0987654321"


def test_reset_password_with_otp(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Reset User",
            "email": "reset@example.com",
            "password": "old-password-123",
        },
    )

    forgot_res = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "reset@example.com"},
    )
    assert forgot_res.status_code == 200
    from app.routes import OTP_STORE
    otp_code = forgot_res.json().get("otp_debug") or OTP_STORE["reset@example.com"]["code"]

    # Wrong OTP should fail
    reset_wrong = client.post(
        "/api/v1/auth/reset-password",
        json={
            "email": "reset@example.com",
            "otp_code": "000000",
            "new_password": "new-password-456",
        },
    )
    assert reset_wrong.status_code == 400

    # Correct OTP should succeed
    reset_res = client.post(
        "/api/v1/auth/reset-password",
        json={
            "email": "reset@example.com",
            "otp_code": otp_code,
            "new_password": "new-password-456",
        },
    )
    assert reset_res.status_code == 200

    login_old = client.post(
        "/api/v1/auth/login",
        json={"email": "reset@example.com", "password": "old-password-123"},
    )
    assert login_old.status_code == 401

    login_new = client.post(
        "/api/v1/auth/login",
        json={"email": "reset@example.com", "password": "new-password-456"},
    )
    assert login_new.status_code == 200


def test_reset_password_sends_to_plaintext_local_smtp_without_auth(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Mailpit User",
            "email": "mailpit@example.com",
            "password": "strong-pass-123",
        },
    )
    monkeypatch.setenv("SMTP_HOST", "mailpit.test")
    monkeypatch.setenv("SMTP_PORT", "1025")
    monkeypatch.setenv("SMTP_USERNAME", "")
    monkeypatch.setenv("SMTP_PASSWORD", "")
    monkeypatch.setenv("SMTP_FROM", "noreply@example.test")
    monkeypatch.setenv("SMTP_STARTTLS", "false")
    calls: dict[str, object] = {}

    class FakeSmtp:
        def __init__(self, host: str, port: int, timeout: int):
            calls["connection"] = (host, port, timeout)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def starttls(self, **_kwargs):
            calls["starttls"] = True

        def login(self, *_args):
            calls["login"] = True

        def send_message(self, message):
            calls["message"] = message

    monkeypatch.setattr("app.routes.smtplib.SMTP", FakeSmtp)

    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "mailpit@example.com"},
    )

    assert response.status_code == 200
    assert "otp_debug" not in response.json()
    assert calls["connection"] == ("mailpit.test", 1025, 15)
    assert "starttls" not in calls
    assert "login" not in calls
    assert calls["message"]["To"] == "mailpit@example.com"


def test_smtp_failure_log_never_includes_configured_app_password(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    client.post(
        "/api/v1/auth/register",
        json={"full_name": "Mail User", "email": "mail-log@example.com", "password": "strong-pass-123"},
    )
    secret = "app-password-never-log-this"
    monkeypatch.setenv("SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "sender@example.test")
    monkeypatch.setenv("SMTP_PASSWORD", secret)
    monkeypatch.setenv("SMTP_FROM", "sender@example.test")
    monkeypatch.setenv("SMTP_STARTTLS", "true")

    class FailingSmtp:
        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def starttls(self, **_kwargs):
            pass

        def login(self, *_args):
            raise __import__("smtplib").SMTPAuthenticationError(535, secret.encode())

    monkeypatch.setattr("app.routes.smtplib.SMTP", FailingSmtp)
    response = client.post("/api/v1/auth/forgot-password", json={"email": "mail-log@example.com"})
    captured = capsys.readouterr()
    assert response.status_code == 200
    assert secret not in captured.out
    assert "SMTPAuthenticationError" in captured.out


def test_admin_users_list_status_and_summary(client: TestClient) -> None:
    from app.security import create_access_token, hash_password

    with app.state.test_session() as db:
        admin = User(
            full_name="Admin One",
            email="admin@example.com",
            password_hash=hash_password("strong-pass-123"),
            role="ADMIN",
            is_active=True,
        )
        user = User(
            full_name="Linh Nguyen",
            email="linh@example.com",
            password_hash=hash_password("strong-pass-123"),
            role="USER",
            is_active=True,
        )
        db.add_all([admin, user])
        db.commit()
        db.refresh(admin)
        db.refresh(user)
        admin_id = admin.id
        user_id = user.id

    token = create_access_token(admin_id, "ADMIN")
    headers = {"Authorization": f"Bearer {token}"}

    listed = client.get("/api/v1/admin/users?q=linh&page=1&page_size=25", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == user_id

    updated = client.patch(
        f"/api/v1/admin/users/{user_id}/status",
        json={"is_active": False},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["is_active"] is False

    summary = client.get("/api/v1/admin/users/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["users"]["inactive"] == 1

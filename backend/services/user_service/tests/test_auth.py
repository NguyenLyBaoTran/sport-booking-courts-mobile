from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.security import decode_access_token


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
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
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

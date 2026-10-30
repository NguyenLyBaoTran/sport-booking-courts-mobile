from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Payment

SECRET = "test-secret-key-with-32-or-more-characters"


def _token(user_id: int = 1, role: str = "USER") -> str:
    return jwt.encode(
        {
            "sub": str(user_id),
            "role": role,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        },
        SECRET,
        algorithm="HS256",
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    monkeypatch.setenv("JWT_SECRET_KEY", SECRET)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
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
        Base.metadata.drop_all(engine)
        engine.dispose()


def _payment_context(user_id: int = 1) -> dict:
    return {
        "booking_id": 5,
        "user_id": user_id,
        "status": "PENDING",
        "total_amount": "150.00",
        "expires_at": None,
    }


def test_successful_mock_payment_confirms_booking_and_is_idempotent(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.routes.integrations.get_payment_context", lambda _: _payment_context()
    )
    confirmations: list[int] = []
    monkeypatch.setattr(
        "app.routes.integrations.confirm_booking",
        lambda booking_id: confirmations.append(booking_id)
        or {"booking_id": booking_id, "status": "CONFIRMED", "qr_token": "opaque-qr"},
    )
    headers = {
        "Authorization": f"Bearer {_token()}",
        "Idempotency-Key": "pay-5-attempt-1",
    }

    first = client.post(
        "/api/v1/payments/process",
        json={"booking_id": 5, "mock_result": "SUCCESS"},
        headers=headers,
    )
    second = client.post(
        "/api/v1/payments/process",
        json={"booking_id": 5, "mock_result": "SUCCESS"},
        headers=headers,
    )

    assert first.status_code == 200
    assert first.json()["status"] == "PAID"
    assert first.json()["booking_status"] == "CONFIRMED"
    assert first.json()["qr_token"] == "opaque-qr"
    assert second.json()["id"] == first.json()["id"]
    assert confirmations == [5]


def test_failed_payment_does_not_confirm_and_can_be_retried(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.routes.integrations.get_payment_context", lambda _: _payment_context()
    )
    confirmations: list[int] = []
    monkeypatch.setattr(
        "app.routes.integrations.confirm_booking",
        lambda booking_id: confirmations.append(booking_id)
        or {"booking_id": booking_id, "status": "CONFIRMED", "qr_token": "qr"},
    )
    auth = {"Authorization": f"Bearer {_token()}"}

    failed = client.post(
        "/api/v1/payments/process",
        json={"booking_id": 5, "mock_result": "FAILED"},
        headers={**auth, "Idempotency-Key": "failed-attempt"},
    )
    successful = client.post(
        "/api/v1/payments/process",
        json={"booking_id": 5, "mock_result": "SUCCESS"},
        headers={**auth, "Idempotency-Key": "retry-attempt"},
    )

    assert failed.json()["status"] == "FAILED"
    assert successful.json()["status"] == "PAID"
    assert confirmations == [5]


def test_customer_cannot_pay_another_users_booking(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.routes.integrations.get_payment_context",
        lambda _: _payment_context(user_id=2),
    )

    response = client.post(
        "/api/v1/payments/process",
        json={"booking_id": 5},
        headers={"Authorization": f"Bearer {_token(user_id=1)}"},
    )

    assert response.status_code == 404


def test_payment_history_is_limited_to_current_customer(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.routes.integrations.get_payment_context", lambda _: _payment_context()
    )
    monkeypatch.setattr(
        "app.routes.integrations.confirm_booking",
        lambda booking_id: {"booking_id": booking_id, "status": "CONFIRMED", "qr_token": "qr"},
    )
    client.post(
        "/api/v1/payments/process",
        json={"booking_id": 5},
        headers={"Authorization": f"Bearer {_token(user_id=1)}"},
    )

    own = client.get(
        "/api/v1/payments", headers={"Authorization": f"Bearer {_token(user_id=1)}"}
    )
    other = client.get(
        "/api/v1/payments", headers={"Authorization": f"Bearer {_token(user_id=2)}"}
    )

    assert len(own.json()) == 1
    assert other.json() == []

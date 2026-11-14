from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
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
    app.state.test_session = test_session

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
        del app.state.test_session
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
    booking_state = {"status": "PENDING"}
    monkeypatch.setattr("app.routes.integrations.get_payment_context", lambda _: {
        **_payment_context(),
        "status": booking_state["status"],
        "qr_token": "opaque-qr" if booking_state["status"] == "CONFIRMED" else None,
    })
    confirmations: list[int] = []
    def confirm_booking(booking_id: int) -> dict:
        confirmations.append(booking_id)
        booking_state["status"] = "CONFIRMED"
        return {"booking_id": booking_id, "status": "CONFIRMED", "qr_token": "opaque-qr"}

    monkeypatch.setattr("app.routes.integrations.confirm_booking", confirm_booking)
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
    assert second.json()["qr_token"] == first.json()["qr_token"]
    assert confirmations == [5]


def test_retry_after_pending_attempt_reuses_key_and_creates_one_payment(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.routes.integrations.get_payment_context", lambda _: _payment_context()
    )
    confirmations = iter([
        HTTPException(status_code=503, detail="Booking service unavailable"),
        {"booking_id": 5, "status": "CONFIRMED", "qr_token": "retry-qr"},
    ])
    def confirm_booking(_: int) -> dict:
        result = next(confirmations)
        if isinstance(result, HTTPException):
            raise result
        return result

    monkeypatch.setattr("app.routes.integrations.confirm_booking", confirm_booking)
    headers = {
        "Authorization": f"Bearer {_token()}",
        "Idempotency-Key": "same-booking-retry-key",
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

    assert first.status_code == 503
    assert second.status_code == 200
    assert second.json()["status"] == "PAID"
    with client.app.state.test_session() as db:
        payments = db.query(Payment).filter(Payment.booking_id == 5).all()
        assert len(payments) == 1
        assert payments[0].idempotency_key == "same-booking-retry-key"


def test_different_bookings_use_different_idempotency_keys(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.routes.integrations.get_payment_context",
        lambda booking_id: {**_payment_context(), "booking_id": booking_id},
    )
    monkeypatch.setattr(
        "app.routes.integrations.confirm_booking",
        lambda booking_id: {
            "booking_id": booking_id,
            "status": "CONFIRMED",
            "qr_token": f"qr-for-{booking_id}",
        },
    )
    auth = {"Authorization": f"Bearer {_token()}"}
    for booking_id, key in ((5, "booking-5-key"), (6, "booking-6-key")):
        response = client.post(
            "/api/v1/payments/process",
            json={"booking_id": booking_id},
            headers={**auth, "Idempotency-Key": key},
        )
        assert response.status_code == 200

    with client.app.state.test_session() as db:
        payments = db.query(Payment).order_by(Payment.booking_id).all()
        assert [payment.booking_id for payment in payments] == [5, 6]
        assert [payment.idempotency_key for payment in payments] == [
            "booking-5-key", "booking-6-key"
        ]


@pytest.mark.parametrize(
    ("booking_status", "expected_qr"),
    [("CONFIRMED", "current-booking-qr"), ("CANCELLED", None), ("EXPIRED", None)],
)
def test_paid_retry_only_returns_qr_for_confirmed_booking(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    booking_status: str,
    expected_qr: str | None,
) -> None:
    with client.app.state.test_session() as db:
        payment = Payment(
            booking_id=5,
            successful_booking_id=5,
            user_id=1,
            provider="MOCK",
            status="PAID",
            amount=Decimal("240.00"),
            idempotency_key="already-paid-key",
            qr_token="stale-payment-qr",
        )
        db.add(payment)
        db.commit()
        payment_id = payment.id
    monkeypatch.setattr(
        "app.routes.integrations.get_payment_context",
        lambda _: {
            **_payment_context(),
            "status": booking_status,
            "qr_token": "current-booking-qr" if booking_status == "CONFIRMED" else None,
        },
    )

    response = client.post(
        "/api/v1/payments/process",
        json={"booking_id": 5},
        headers={"Authorization": f"Bearer {_token()}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "PAID"
    assert response.json()["booking_status"] == booking_status
    assert response.json()["qr_token"] == expected_qr
    history = client.get(
        "/api/v1/payments", headers={"Authorization": f"Bearer {_token()}"}
    )
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["status"] == "PAID"
    assert Decimal(history.json()[0]["amount"]) == Decimal("240.00")
    with client.app.state.test_session() as db:
        unchanged = db.get(Payment, payment_id)
        assert unchanged is not None
        assert unchanged.status == "PAID"
        assert unchanged.amount == Decimal("240.00")
        assert unchanged.qr_token == "stale-payment-qr"


def test_failed_payment_marks_booking_failed_and_releases_slot(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.routes.integrations.get_payment_context", lambda _: _payment_context()
    )
    failures: list[int] = []
    monkeypatch.setattr("app.routes.integrations.fail_booking", lambda booking_id: failures.append(booking_id) or {"status": "FAILED"})
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
    assert failed.json()["status"] == "FAILED"
    assert confirmations == []
    assert failures == [5]
    assert failures == [5]


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

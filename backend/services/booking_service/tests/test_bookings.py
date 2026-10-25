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
from app.models import Booking

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
    monkeypatch.setenv("INTERNAL_SERVICE_TOKEN", "test-internal-token")
    monkeypatch.setenv("BOOKING_HOLD_MINUTES", "10")
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
    app.state.test_session = test_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        del app.state.test_session
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_create_booking_holds_slot_and_calculates_amount(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.routes.integrations.hold_slot",
        lambda slot_id, booking_id: {
            "court_id": 4,
            "venue_id": 2,
            "owner_id": 22,
            "price_per_hour": "120.50",
            "slot_date": "2026-10-26",
            "start_time": "09:00:00",
            "end_time": "10:30:00",
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        },
    )
    response = client.post(
        "/api/v1/bookings",
        json={"time_slot_id": 8},
        headers={"Authorization": f"Bearer {_token()}"},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "PENDING"
    assert Decimal(response.json()["total_amount"]) == Decimal("180.75")
    assert response.json()["time_slot_id"] == 8


def test_invalid_slot_hold_response_is_rolled_back_and_released(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    released: list[tuple[int, int]] = []
    monkeypatch.setattr(
        "app.routes.integrations.hold_slot",
        lambda *_: {"price_per_hour": "100"},
    )
    monkeypatch.setattr(
        "app.routes.integrations.release_slot",
        lambda slot_id, booking_id: released.append((slot_id, booking_id)) or {},
    )

    response = client.post(
        "/api/v1/bookings",
        json={"time_slot_id": 8},
        headers={"Authorization": f"Bearer {_token()}"},
    )

    assert response.status_code == 502
    assert released and released[0][0] == 8
    with app.state.test_session() as db:
        assert db.query(Booking).count() == 0


def test_booking_is_private_and_cancel_releases_pending_slot(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.routes.integrations.hold_slot",
        lambda *_: {
            "court_id": 4,
            "venue_id": 2,
            "owner_id": 22,
            "price_per_hour": "100",
            "slot_date": "2026-10-26",
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        },
    )
    released: list[tuple[int, int]] = []
    monkeypatch.setattr(
        "app.routes.integrations.release_slot",
        lambda slot_id, booking_id: released.append((slot_id, booking_id)) or {},
    )
    created = client.post(
        "/api/v1/bookings",
        json={"time_slot_id": 8},
        headers={"Authorization": f"Bearer {_token()}"},
    ).json()

    forbidden = client.get(
        f"/api/v1/bookings/{created['id']}",
        headers={"Authorization": f"Bearer {_token(user_id=2)}"},
    )
    cancelled = client.post(
        f"/api/v1/bookings/{created['id']}/cancel",
        headers={"Authorization": f"Bearer {_token()}"},
    )

    assert forbidden.status_code == 404
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"
    assert released == [(8, created["id"])]


def test_only_customers_can_create_bookings(client: TestClient) -> None:
    response = client.post(
        "/api/v1/bookings",
        json={"time_slot_id": 8},
        headers={"Authorization": f"Bearer {_token(role='OWNER')}"},
    )

    assert response.status_code == 403


def test_internal_confirmation_is_idempotent_and_issues_qr(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.routes.integrations.hold_slot",
        lambda *_: {
            "court_id": 4,
            "venue_id": 2,
            "owner_id": 22,
            "price_per_hour": "100",
            "slot_date": "2026-10-26",
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        },
    )
    monkeypatch.setattr("app.routes.integrations.confirm_slot", lambda *_: {})
    created = client.post(
        "/api/v1/bookings",
        json={"time_slot_id": 8},
        headers={"Authorization": f"Bearer {_token()}"},
    ).json()
    headers = {"X-Internal-Token": "test-internal-token"}

    first = client.post(
        f"/api/v1/internal/bookings/{created['id']}/confirm", headers=headers
    ).json()
    second = client.post(
        f"/api/v1/internal/bookings/{created['id']}/confirm", headers=headers
    ).json()

    assert first["status"] == "CONFIRMED"
    assert first["qr_token"]
    assert second["qr_token"] == first["qr_token"]


def test_owner_check_in_and_completion_enforce_transitions(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.routes.integrations.hold_slot",
        lambda *_: {
            "court_id": 4,
            "venue_id": 2,
            "owner_id": 22,
            "price_per_hour": "100",
            "slot_date": "2026-10-26",
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        },
    )
    monkeypatch.setattr("app.routes.integrations.confirm_slot", lambda *_: {})
    created = client.post(
        "/api/v1/bookings",
        json={"time_slot_id": 8},
        headers={"Authorization": f"Bearer {_token()}"},
    ).json()
    internal_headers = {"X-Internal-Token": "test-internal-token"}
    confirmed = client.post(
        f"/api/v1/internal/bookings/{created['id']}/confirm",
        headers=internal_headers,
    ).json()

    wrong_owner = client.post(
        "/api/v1/internal/bookings/check-in",
        json={"owner_id": 23, "qr_token": confirmed["qr_token"]},
        headers=internal_headers,
    )
    checked_in = client.post(
        "/api/v1/internal/bookings/check-in",
        json={"owner_id": 22, "qr_token": confirmed["qr_token"]},
        headers=internal_headers,
    )
    repeated_check_in = client.post(
        "/api/v1/internal/bookings/check-in",
        json={"owner_id": 22, "qr_token": confirmed["qr_token"]},
        headers=internal_headers,
    )
    completed = client.post(
        f"/api/v1/internal/bookings/{created['id']}/complete",
        json={"owner_id": 22},
        headers=internal_headers,
    )

    assert wrong_owner.status_code == 404
    assert checked_in.status_code == 200
    assert checked_in.json()["status"] == "CHECKED_IN"
    assert repeated_check_in.status_code == 409
    assert completed.status_code == 200
    assert completed.json()["status"] == "COMPLETED"


def test_expiration_releases_slot(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    released: list[tuple[int, int]] = []
    monkeypatch.setattr(
        "app.routes.integrations.release_slot",
        lambda slot_id, booking_id: released.append((slot_id, booking_id)) or {},
    )
    with app.state.test_session() as db:
        booking = Booking(
            user_id=1,
            time_slot_id=9,
            court_id=4,
            venue_id=2,
            owner_id=22,
            slot_date=datetime.now(timezone.utc).date(),
            start_time=datetime.now(timezone.utc).time(),
            end_time=(datetime.now(timezone.utc) + timedelta(hours=1)).time(),
            status="PENDING",
            total_amount=Decimal("10.00"),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        db.add(booking)
        db.commit()

    result = client.post(
        "/api/v1/internal/bookings/expire",
        headers={"X-Internal-Token": "test-internal-token"},
    )

    assert result.status_code == 200
    assert result.json()["expired"] == 1
    assert released
    expired_booking = client.get(
        "/api/v1/bookings/1",
        headers={"Authorization": f"Bearer {_token()}"},
    )
    assert expired_booking.status_code == 200
    assert expired_booking.json()["status"] == "EXPIRED"

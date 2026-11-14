from collections.abc import Generator
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Booking, BookingTimeSlot
from app import integrations

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
    assert response.json()["confirmed_at"] is None
    assert Decimal(response.json()["total_amount"]) == Decimal("180.75")
    assert response.json()["time_slot_id"] == 8


def test_booking_quote_is_authoritative_and_does_not_create_booking(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.routes.integrations.get_slot_quote",
        lambda slot_id: {
            "price_per_hour": "120.50",
            "slot_date": "2026-10-26",
            "start_time": "09:00:00",
            "end_time": "10:30:00",
            "court_id": 4,
            "venue_id": 2,
            "owner_id": 22,
        },
    )

    response = client.get(
        "/api/v1/booking-quotes/15",
        headers={"Authorization": f"Bearer {_token()}"},
    )

    assert response.status_code == 200
    quote = response.json()
    assert quote["time_slot_id"] == 15
    assert quote["court_id"] == 4
    assert quote["venue_id"] == 2
    assert quote["owner_id"] == 22
    assert quote["slot_date"] == "2026-10-26"
    assert quote["start_time"] == "09:00:00"
    assert quote["end_time"] == "10:30:00"
    assert Decimal(quote["total_amount"]) == Decimal("180.75")
    with app.state.test_session() as db:
        assert db.query(Booking).count() == 0


def test_booking_quote_propagates_unavailable_slot_and_does_not_create_booking(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unavailable(_slot_id: int) -> dict:
        raise HTTPException(status_code=409, detail="Time slot is unavailable")

    monkeypatch.setattr("app.routes.integrations.get_slot_quote", unavailable)

    response = client.get(
        "/api/v1/booking-quotes/15",
        headers={"Authorization": f"Bearer {_token()}"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Time slot is unavailable"
    with app.state.test_session() as db:
        assert db.query(Booking).count() == 0


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
    assert cancelled.json()["qr_token"] is None
    assert released == [(8, created["id"])]
    detail = client.get(f"/api/v1/bookings/{created['id']}", headers={"Authorization": f"Bearer {_token()}"})
    assert detail.status_code == 200
    assert detail.json()["qr_token"] is None


@pytest.mark.parametrize("minutes_after,expected_status", [(29, 200), (30, 200), (31, 409)])
def test_confirmed_booking_cancellation_uses_confirmation_time_boundary(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, minutes_after: int, expected_status: int
) -> None:
    import app.routes as routes

    confirmed_at = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
    fixed_now = confirmed_at + timedelta(minutes=minutes_after)
    with app.state.test_session() as db:
        booking = Booking(
            user_id=1, time_slot_id=909, court_id=4, venue_id=2, owner_id=22,
            slot_date=date.today(), start_time=time(18), end_time=time(19),
            status="CONFIRMED", total_amount=Decimal("100"), qr_token="q" * 32,
            created_at=confirmed_at - timedelta(days=2), confirmed_at=confirmed_at,
        )
        db.add(booking)
        db.commit()
        booking_id = booking.id
    released: list[tuple[int, int]] = []
    fixed_datetime = type("FixedDateTime", (datetime,), {"now": staticmethod(lambda tz=None: fixed_now)})
    monkeypatch.setattr(routes, "datetime", fixed_datetime)
    monkeypatch.setattr("app.routes.integrations.release_slot", lambda slot, owner: released.append((slot, owner)) or {})

    response = client.post(
        f"/api/v1/bookings/{booking_id}/cancel",
        headers={"Authorization": f"Bearer {_token()}"},
    )
    assert response.status_code == expected_status
    with app.state.test_session() as db:
        persisted = db.get(Booking, booking_id)
        assert persisted.status == ("CANCELLED" if expected_status == 200 else "CONFIRMED")
        assert persisted.qr_token == (None if expected_status == 200 else "q" * 32)
        persisted_confirmed_at = persisted.confirmed_at.replace(tzinfo=timezone.utc) if persisted.confirmed_at.tzinfo is None else persisted.confirmed_at
        assert persisted_confirmed_at == confirmed_at
        if expected_status == 409:
            assert persisted.expires_at is None
    assert released == ([(909, booking_id)] if expected_status == 200 else [])


def test_legacy_confirmed_booking_without_timestamp_cannot_be_cancelled(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    with app.state.test_session() as db:
        booking = Booking(user_id=1, time_slot_id=910, court_id=4, venue_id=2, owner_id=22,
                          slot_date=date.today(), start_time=time(18), end_time=time(19),
                          status="CONFIRMED", total_amount=Decimal("100"), qr_token="r" * 32)
        db.add(booking)
        db.commit()
        booking_id = booking.id
    released: list[int] = []
    monkeypatch.setattr("app.routes.integrations.release_slot", lambda *_: released.append(1))
    response = client.post(f"/api/v1/bookings/{booking_id}/cancel", headers={"Authorization": f"Bearer {_token()}"})
    assert response.status_code == 409
    assert "no recorded confirmation time" in response.json()["detail"]
    assert released == []
    with app.state.test_session() as db:
        persisted = db.get(Booking, booking_id)
        assert persisted.status == "CONFIRMED"
        assert persisted.qr_token == "r" * 32


def test_confirmed_cancellation_does_not_release_newer_booking_reservation(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    with app.state.test_session() as db:
        booking = Booking(
            user_id=1, time_slot_id=911, court_id=4, venue_id=2, owner_id=22,
            slot_date=date.today(), start_time=time(18), end_time=time(19),
            status="CONFIRMED", total_amount=Decimal("100"), qr_token="s" * 32,
            confirmed_at=datetime.now(timezone.utc),
        )
        db.add(booking)
        db.commit()
        booking_id = booking.id

    reservation = {"booking_id": 9004}
    def release(slot_id: int, owner_booking_id: int):
        if reservation["booking_id"] != owner_booking_id:
            raise HTTPException(status_code=409, detail="Slot belongs to another booking")
        reservation["booking_id"] = None
        return {"status": "AVAILABLE"}
    monkeypatch.setattr("app.routes.integrations.release_slot", release)

    response = client.post(
        f"/api/v1/bookings/{booking_id}/cancel",
        headers={"Authorization": f"Bearer {_token()}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert response.json()["qr_token"] is None
    assert reservation["booking_id"] == 9004


def test_admin_booking_and_checkin_endpoints(client: TestClient) -> None:
    checked_at = datetime.now(timezone.utc)
    with app.state.test_session() as db:
        booking = Booking(
            user_id=5,
            time_slot_id=8,
            court_id=4,
            venue_id=2,
            owner_id=22,
            slot_date=date(2026, 10, 29),
            start_time=time(18, 0),
            end_time=time(19, 0),
            status="CHECKED_IN",
            total_amount=Decimal("180.00"),
            checked_in_by=22,
            checked_in_at=checked_at,
            created_at=datetime.now(timezone.utc),
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        booking_id = booking.id

    headers = {"Authorization": f"Bearer {_token(1, 'ADMIN')}"}
    listed = client.get("/api/v1/admin/bookings?status=CHECKED_IN&page=1&page_size=25", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == booking_id
    assert "qr_token" not in listed.json()["items"][0]

    checkins = client.get("/api/v1/admin/checkins?page=1&page_size=25", headers=headers)
    assert checkins.status_code == 200
    assert checkins.json()["items"][0]["checked_in_by"] == 22

    summary = client.get("/api/v1/admin/bookings/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["bookings"]["checked_in"] == 1

    detail = client.get(f"/api/v1/admin/bookings/{booking_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "CHECKED_IN"


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
    assert first["confirmed_at"]
    assert second["confirmed_at"] == first["confirmed_at"]
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
    released: list[tuple[int, int]] = []
    monkeypatch.setattr("app.routes.integrations.release_slot", lambda slot_id, booking_id: released.append((slot_id, booking_id)) or {"status": "AVAILABLE"})
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
    repeated_completion = client.post(
        f"/api/v1/internal/bookings/{created['id']}/complete",
        json={"owner_id": 22},
        headers=internal_headers,
    )

    assert wrong_owner.status_code == 404
    assert checked_in.status_code == 200
    assert checked_in.json()["status"] == "CHECKED_IN"
    assert checked_in.json()["court_id"] == 4
    assert checked_in.json()["venue_id"] == 2
    assert checked_in.json()["slot_date"] is not None
    assert checked_in.json()["start_time"] is not None
    assert checked_in.json()["end_time"] is not None
    assert repeated_check_in.status_code == 409
    assert completed.status_code == 200
    assert completed.json()["status"] == "COMPLETED"
    assert repeated_completion.status_code == 200
    assert repeated_completion.json() == completed.json()
    assert released == [(8, created["id"]), (8, created["id"])]


def test_completion_commit_failure_is_retryable(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    with app.state.test_session() as db:
        booking = Booking(
            user_id=1, time_slot_id=31, court_id=4, venue_id=2, owner_id=22,
            slot_date=date.today(), start_time=time(18), end_time=time(19),
            status="CHECKED_IN", total_amount=Decimal("100"),
        )
        db.add(booking)
        db.commit()
        booking_id = booking.id

    slot_owner: dict[str, int | None] = {"booking_id": booking_id}
    def release(slot_id: int, owner_booking_id: int):
        if slot_owner["booking_id"] not in (None, owner_booking_id):
            raise HTTPException(status_code=409, detail="Slot belongs to another booking")
        slot_owner["booking_id"] = None
        return {"status": "AVAILABLE"}
    def hold_by_booking_b():
        if slot_owner["booking_id"] is not None:
            raise HTTPException(status_code=409, detail="Slot unavailable")
        slot_owner["booking_id"] = 9002
    monkeypatch.setattr("app.routes.integrations.release_slot", release)

    original_commit = Session.commit
    fail_once = {"enabled": True}
    def commit_then_fail(session):
        if fail_once["enabled"] and any(isinstance(obj, Booking) and obj.status == "COMPLETED" for obj in session.dirty):
            fail_once["enabled"] = False
            raise SQLAlchemyError("injected commit failure")
        return original_commit(session)
    monkeypatch.setattr(Session, "commit", commit_then_fail)

    headers = {"X-Internal-Token": "test-internal-token"}
    path = f"/api/v1/internal/bookings/{booking_id}/complete"
    first = client.post(path, json={"owner_id": 22}, headers=headers)
    assert first.status_code == 503
    with app.state.test_session() as db:
        assert db.get(Booking, booking_id).status == "CHECKED_IN"
    with pytest.raises(HTTPException) as held:
        hold_by_booking_b()
    assert held.value.status_code == 409
    assert slot_owner["booking_id"] == booking_id
    second = client.post(path, json={"owner_id": 22}, headers=headers)
    assert second.status_code == 200
    assert second.json()["status"] == "COMPLETED"
    hold_by_booking_b()
    assert slot_owner["booking_id"] == 9002
    retry_after_rebooking = client.post(path, json={"owner_id": 22}, headers=headers)
    assert retry_after_rebooking.status_code == 200
    assert retry_after_rebooking.json()["booking_id"] == booking_id
    assert retry_after_rebooking.json()["status"] == "COMPLETED"
    assert slot_owner["booking_id"] == 9002


def test_completion_release_failure_retries_after_status_is_durable(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    with app.state.test_session() as db:
        booking = Booking(
            user_id=1, time_slot_id=32, court_id=4, venue_id=2, owner_id=22,
            slot_date=date.today(), start_time=time(18), end_time=time(19),
            status="CHECKED_IN", total_amount=Decimal("100"),
        )
        db.add(booking)
        db.commit()
        booking_id = booking.id

    attempts: list[tuple[int, int]] = []
    def release(slot_id: int, owner_booking_id: int):
        attempts.append((slot_id, owner_booking_id))
        if len(attempts) == 1:
            raise HTTPException(status_code=503, detail="Court unavailable")
        return {"status": "AVAILABLE"}
    monkeypatch.setattr("app.routes.integrations.release_slot", release)

    headers = {"X-Internal-Token": "test-internal-token"}
    path = f"/api/v1/internal/bookings/{booking_id}/complete"
    first = client.post(path, json={"owner_id": 22}, headers=headers)
    with app.state.test_session() as db:
        assert db.get(Booking, booking_id).status == "COMPLETED"
    assert first.status_code == 503
    second = client.post(path, json={"owner_id": 22}, headers=headers)
    assert second.status_code == 200
    assert second.json()["status"] == "COMPLETED"
    assert attempts == [(32, booking_id), (32, booking_id)]


def test_completed_booking_retry_never_releases_newer_booking(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    with app.state.test_session() as db:
        booking = Booking(
            user_id=1, time_slot_id=33, court_id=4, venue_id=2, owner_id=22,
            slot_date=date.today(), start_time=time(18), end_time=time(19),
            status="CHECKED_IN", total_amount=Decimal("100"),
        )
        db.add(booking)
        db.commit()
        booking_id = booking.id

    slot_owner: dict[str, int | None] = {"booking_id": booking_id}
    def release(slot_id: int, owner_booking_id: int):
        if slot_owner["booking_id"] not in (None, owner_booking_id):
            raise HTTPException(status_code=409, detail="Slot belongs to another booking")
        slot_owner["booking_id"] = None
        return {"status": "AVAILABLE"}
    monkeypatch.setattr("app.routes.integrations.release_slot", release)

    headers = {"X-Internal-Token": "test-internal-token"}
    path = f"/api/v1/internal/bookings/{booking_id}/complete"
    response = client.post(path, json={"owner_id": 22}, headers=headers)
    assert response.status_code == 200
    assert slot_owner["booking_id"] is None

    # Booking B acquires the slot after A's release. A stale retry cannot clear B.
    slot_owner["booking_id"] = 9002
    retry = client.post(path, json={"owner_id": 22}, headers=headers)
    assert retry.status_code == 200
    assert retry.json()["booking_id"] == booking_id
    assert retry.json()["status"] == "COMPLETED"
    assert retry.json()["completed_at"]
    assert slot_owner["booking_id"] == 9002
    with app.state.test_session() as db:
        assert db.get(Booking, booking_id).status == "COMPLETED"


def test_expiration_only_releases_expired_bookings_and_keeps_retryable_failures(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    released: list[tuple[int, int]] = []
    with app.state.test_session() as db:
        expired = Booking(
            user_id=1, time_slot_id=21, court_id=4, venue_id=2, owner_id=22,
            slot_date=date(2026, 10, 29), start_time=time(18), end_time=time(19),
            status="PENDING", total_amount=Decimal("100"),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        active = Booking(
            user_id=1, time_slot_id=22, court_id=4, venue_id=2, owner_id=22,
            slot_date=date(2026, 10, 29), start_time=time(19), end_time=time(20),
            status="PENDING", total_amount=Decimal("100"),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        no_expiry = Booking(
            user_id=1, time_slot_id=23, court_id=4, venue_id=2, owner_id=22,
            slot_date=date(2026, 10, 29), start_time=time(20), end_time=time(21),
            status="PENDING", total_amount=Decimal("100"), expires_at=None,
        )
        db.add_all([expired, active, no_expiry])
        db.commit()
        expired_id, active_id, no_expiry_id = expired.id, active.id, no_expiry.id

    def release(slot_id: int, booking_id: int):
        released.append((slot_id, booking_id))
        if slot_id == 21:
            raise HTTPException(status_code=503, detail="Court unavailable")
        return {"status": "AVAILABLE"}

    monkeypatch.setattr("app.routes.integrations.release_slot", release)
    response = client.post("/api/v1/internal/bookings/expire", headers={"X-Internal-Token": "test-internal-token"})
    assert response.status_code == 200
    assert response.json() == {"expired": 1, "released": 0}
    with app.state.test_session() as db:
        assert db.get(Booking, expired_id).status == "EXPIRED"
        assert db.get(Booking, active_id).status == "PENDING"
        assert db.get(Booking, no_expiry_id).status == "PENDING"
    monkeypatch.setattr("app.routes.integrations.release_slot", lambda slot_id, booking_id: released.append((slot_id, booking_id)) or {})
    response = client.post("/api/v1/internal/bookings/expire", headers={"X-Internal-Token": "test-internal-token"})
    assert response.status_code == 200
    assert response.json() == {"expired": 0, "released": 1}
    with app.state.test_session() as db:
        assert db.get(Booking, expired_id).status == "EXPIRED"
        assert db.get(Booking, active_id).status == "PENDING"
        assert db.get(Booking, no_expiry_id).status == "PENDING"


def test_expiration_commit_failure_keeps_booking_retryable_and_continues_batch(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    released: list[tuple[int, int]] = []
    with app.state.test_session() as db:
        rows = [Booking(
            user_id=1, time_slot_id=slot_id, court_id=4, venue_id=2, owner_id=22,
            slot_date=date.today(), start_time=time(hour), end_time=time(hour + 1),
            status="PENDING", total_amount=Decimal("100"),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        ) for slot_id, hour in ((41, 18), (42, 19))]
        db.add_all(rows)
        db.commit()
        ids = [row.id for row in rows]

    monkeypatch.setattr("app.routes.integrations.release_slot", lambda slot_id, booking_id: released.append((slot_id, booking_id)) or {"status": "AVAILABLE"})
    original_commit = Session.commit
    failed_ids: set[int] = set()
    def commit_one_failure(session):
        if any(isinstance(obj, Booking) and obj.id == ids[0] and obj.status == "EXPIRED" for obj in session.dirty) and ids[0] not in failed_ids:
            failed_ids.add(ids[0])
            raise SQLAlchemyError("injected commit failure")
        return original_commit(session)
    monkeypatch.setattr(Session, "commit", commit_one_failure)

    headers = {"X-Internal-Token": "test-internal-token"}
    response = client.post("/api/v1/internal/bookings/expire", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"expired": 1, "released": 1}
    with app.state.test_session() as db:
        assert db.get(Booking, ids[0]).status == "PENDING"
        assert db.get(Booking, ids[1]).status == "EXPIRED"

    response = client.post("/api/v1/internal/bookings/expire", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"expired": 1, "released": 1}
    with app.state.test_session() as db:
        assert db.get(Booking, ids[0]).status == "EXPIRED"
    assert (41, ids[0]) in released and released.count((41, ids[0])) == 1


def test_expire_if_needed_persists_terminal_state_before_release_and_retries(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    with app.state.test_session() as db:
        booking = Booking(
            user_id=1, time_slot_id=51, court_id=4, venue_id=2, owner_id=22,
            slot_date=date.today(), start_time=time(18), end_time=time(19),
            status="PENDING", total_amount=Decimal("100"),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=2),
        )
        db.add(booking)
        db.commit()
        booking_id = booking.id

    attempts: list[tuple[int, int]] = []
    def release(slot_id: int, owner_booking_id: int):
        attempts.append((slot_id, owner_booking_id))
        if len(attempts) == 1:
            raise HTTPException(status_code=503, detail="Court unavailable")
        return {"status": "AVAILABLE"}
    monkeypatch.setattr("app.routes.integrations.release_slot", release)
    headers = {"Authorization": f"Bearer {_token()}"}
    first = client.get(f"/api/v1/bookings/{booking_id}", headers=headers)
    assert first.status_code == 503
    with app.state.test_session() as db:
        assert db.get(Booking, booking_id).status == "EXPIRED"
    second = client.get(f"/api/v1/bookings/{booking_id}", headers=headers)
    assert second.status_code == 200
    assert second.json()["status"] == "EXPIRED"
    assert attempts == [(51, booking_id), (51, booking_id)]


def test_expiration_cleanup_marker_retry_does_not_release_new_booking(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    with app.state.test_session() as db:
        booking = Booking(
            user_id=1, time_slot_id=52, court_id=4, venue_id=2, owner_id=22,
            slot_date=date.today(), start_time=time(18), end_time=time(19),
            status="PENDING", total_amount=Decimal("100"),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=2),
        )
        db.add(booking)
        db.commit()
        booking_id = booking.id

    slot_owner: dict[str, int | None] = {"booking_id": booking_id}
    def release(slot_id: int, owner_booking_id: int):
        if slot_owner["booking_id"] not in (None, owner_booking_id):
            raise HTTPException(status_code=409, detail="Slot belongs to another booking")
        slot_owner["booking_id"] = None
        return {"status": "AVAILABLE"}
    monkeypatch.setattr("app.routes.integrations.release_slot", release)

    original_commit = Session.commit
    fail_marker_once = {"enabled": True}
    def fail_cleanup_marker(session):
        if fail_marker_once["enabled"] and any(
            isinstance(obj, Booking) and obj.id == booking_id
            and obj.status == "EXPIRED" and obj.expires_at is None
            for obj in session.dirty
        ):
            fail_marker_once["enabled"] = False
            raise SQLAlchemyError("injected cleanup marker failure")
        return original_commit(session)
    monkeypatch.setattr(Session, "commit", fail_cleanup_marker)

    headers = {"X-Internal-Token": "test-internal-token"}
    first = client.post("/api/v1/internal/bookings/expire", headers=headers)
    assert first.status_code == 200
    assert first.json() == {"expired": 1, "released": 0}
    assert slot_owner["booking_id"] is None
    with app.state.test_session() as db:
        pending_cleanup = db.get(Booking, booking_id)
        assert pending_cleanup.status == "EXPIRED"
        assert pending_cleanup.expires_at is not None

    # Another customer acquires the slot after the successful release but before
    # Booking Service persists its cleanup marker.
    slot_owner["booking_id"] = 9003
    second = client.post("/api/v1/internal/bookings/expire", headers=headers)
    assert second.status_code == 200
    assert second.json() == {"expired": 0, "released": 0}
    assert slot_owner["booking_id"] == 9003
    with app.state.test_session() as db:
        finished = db.get(Booking, booking_id)
        assert finished.status == "EXPIRED"
        assert finished.expires_at is None


def test_court_integration_maps_unavailable_and_timeout_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    class FailedClient:
        def __init__(self, error):
            self.error = error

        def __call__(self, *args, **kwargs):
            raise self.error

    monkeypatch.setenv("INTERNAL_SERVICE_TOKEN", "test-internal-token")
    monkeypatch.setattr(integrations.httpx, "request", FailedClient(httpx.ConnectError("down")))
    with pytest.raises(HTTPException) as unavailable:
        integrations.release_slot(4, 12)
    assert unavailable.value.status_code == 503

    monkeypatch.setattr(integrations.httpx, "request", FailedClient(httpx.TimeoutException("slow")))
    with pytest.raises(HTTPException) as timeout:
        integrations.release_slot(4, 12)
    assert timeout.value.status_code == 504

    class InvalidJsonResponse:
        status_code = 200
        def json(self):
            raise ValueError("not json")
    monkeypatch.setattr(integrations.httpx, "request", lambda *args, **kwargs: InvalidJsonResponse())
    with pytest.raises(HTTPException) as invalid_json:
        integrations.release_slot(4, 12)
    assert invalid_json.value.status_code == 503

    class InvalidShapeResponse:
        status_code = 200
        def json(self):
            return ["not", "an object"]
    monkeypatch.setattr(integrations.httpx, "request", lambda *args, **kwargs: InvalidShapeResponse())
    with pytest.raises(HTTPException) as invalid_shape:
        integrations.release_slot(4, 12)
    assert invalid_shape.value.status_code == 503


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
    assert expired_booking.json()["qr_token"] is None


def test_owner_booking_list_scope_filters_and_projection(client: TestClient) -> None:
    with app.state.test_session() as db:
        own = Booking(
            user_id=1, time_slot_id=10, court_id=4, venue_id=12, owner_id=22,
            slot_date=date(2026, 10, 29), start_time=time(18, 0), end_time=time(19, 0),
            status="CONFIRMED", total_amount=Decimal("180.00"), qr_token="q" * 32,
        )
        foreign = Booking(
            user_id=2, time_slot_id=11, court_id=5, venue_id=12, owner_id=23,
            slot_date=date(2026, 10, 29), start_time=time(19, 0), end_time=time(20, 0),
            status="CONFIRMED", total_amount=Decimal("200.00"), qr_token="r" * 32,
        )
        db.add_all([own, foreign])
        db.commit()
        own_id = own.id

    response = client.get(
        "/api/v1/owner/bookings?venue_id=12&date=2026-10-29&status=CONFIRMED",
        headers={"Authorization": f"Bearer {_token(22, 'OWNER')}"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == own_id
    assert "qr_token" not in response.json()[0]


def test_owner_booking_detail_role_and_scope(client: TestClient) -> None:
    with app.state.test_session() as db:
        own = Booking(
            user_id=1, time_slot_id=10, court_id=4, venue_id=12, owner_id=22,
            slot_date=date(2026, 10, 29), start_time=time(18, 0), end_time=time(19, 0),
            status="CONFIRMED", total_amount=Decimal("180.00"), qr_token="q" * 32,
        )
        foreign = Booking(
            user_id=2, time_slot_id=11, court_id=5, venue_id=13, owner_id=23,
            slot_date=date(2026, 10, 29), start_time=time(19, 0), end_time=time(20, 0),
            status="CONFIRMED", total_amount=Decimal("200.00"), qr_token="r" * 32,
        )
        db.add_all([own, foreign])
        db.commit()
        own_id, foreign_id = own.id, foreign.id

    owner_headers = {"Authorization": f"Bearer {_token(22, 'OWNER')}"}
    detail = client.get(f"/api/v1/owner/bookings/{own_id}", headers=owner_headers)
    foreign_detail = client.get(f"/api/v1/owner/bookings/{foreign_id}", headers=owner_headers)

    assert detail.status_code == 200
    assert "qr_token" not in detail.json()
    assert foreign_detail.status_code == 404
    assert client.get("/api/v1/owner/bookings", headers={}).status_code == 401
    assert client.get(
        "/api/v1/owner/bookings",
        headers={"Authorization": f"Bearer {_token(22, 'USER')}"},
    ).status_code == 403


def test_owner_booking_filters_reject_invalid_values(client: TestClient) -> None:
    headers = {"Authorization": f"Bearer {_token(22, 'OWNER')}"}
    assert client.get("/api/v1/owner/bookings?status=UNKNOWN", headers=headers).status_code == 422
    assert client.get("/api/v1/owner/bookings?date=not-a-date", headers=headers).status_code == 422
    assert client.get("/api/v1/owner/bookings?venue_id=0", headers=headers).status_code == 422


def test_public_owner_completion_reuses_state_rules(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    released: list[tuple[int, int]] = []
    monkeypatch.setattr("app.routes.integrations.release_slot", lambda slot_id, booking_id: released.append((slot_id, booking_id)) or {"status": "AVAILABLE"})
    with app.state.test_session() as db:
        own = Booking(
            user_id=1, time_slot_id=10, court_id=4, venue_id=12, owner_id=22,
            slot_date=date(2026, 10, 29), start_time=time(18, 0), end_time=time(19, 0),
            status="CHECKED_IN", total_amount=Decimal("180.00"),
        )
        foreign = Booking(
            user_id=2, time_slot_id=11, court_id=5, venue_id=13, owner_id=23,
            slot_date=date(2026, 10, 29), start_time=time(19, 0), end_time=time(20, 0),
            status="CHECKED_IN", total_amount=Decimal("200.00"),
        )
        db.add_all([own, foreign])
        db.commit()
        own_id, foreign_id = own.id, foreign.id

    headers = {"Authorization": f"Bearer {_token(22, 'OWNER')}"}
    completed = client.post(f"/api/v1/owner/bookings/{own_id}/complete", headers=headers)
    repeated = client.post(f"/api/v1/owner/bookings/{own_id}/complete", headers=headers)
    other_owner = client.post(f"/api/v1/owner/bookings/{foreign_id}/complete", headers=headers)

    assert completed.status_code == 200
    assert completed.json()["status"] == "COMPLETED"
    assert completed.json()["completed_at"]
    assert repeated.status_code == 200
    assert repeated.json() == completed.json()
    assert other_owner.status_code == 404
    assert released == [(10, own_id), (10, own_id)]


def test_owner_gets_do_not_expire_or_release_bookings(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    released: list[tuple[int, int]] = []
    monkeypatch.setattr(
        "app.routes.integrations.release_slot",
        lambda slot_id, booking_id: released.append((slot_id, booking_id)) or {},
    )
    with app.state.test_session() as db:
        booking = Booking(
            user_id=1, time_slot_id=10, court_id=4, venue_id=12, owner_id=22,
            slot_date=date(2026, 10, 29), start_time=time(18, 0), end_time=time(19, 0),
            status="PENDING", total_amount=Decimal("180.00"),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        db.add(booking)
        db.commit()
        booking_id = booking.id

    headers = {"Authorization": f"Bearer {_token(22, 'OWNER')}"}
    listed = client.get("/api/v1/owner/bookings?status=PENDING", headers=headers)
    detailed = client.get(f"/api/v1/owner/bookings/{booking_id}", headers=headers)

    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["status"] == "PENDING"
    assert detailed.status_code == 200
    assert detailed.json()["status"] == "PENDING"
    assert released == []
    with app.state.test_session() as db:
        assert db.get(Booking, booking_id).status == "PENDING"


def test_public_owner_completion_rejects_other_invalid_state(client: TestClient) -> None:
    with app.state.test_session() as db:
        booking = Booking(
            user_id=1, time_slot_id=10, court_id=4, venue_id=12, owner_id=22,
            slot_date=date(2026, 10, 29), start_time=time(18, 0), end_time=time(19, 0),
            status="CONFIRMED", total_amount=Decimal("180.00"),
        )
        db.add(booking)
        db.commit()
        booking_id = booking.id

    response = client.post(
        f"/api/v1/owner/bookings/{booking_id}/complete",
        headers={"Authorization": f"Bearer {_token(22, 'OWNER')}"},
    )

    assert response.status_code == 409


def test_owner_auth_rejects_expired_admin_and_missing_jwt(client: TestClient) -> None:
    expired = jwt.encode(
        {
            "sub": "22",
            "role": "OWNER",
            "iat": datetime.now(timezone.utc) - timedelta(minutes=20),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=10),
        },
        SECRET,
        algorithm="HS256",
    )

    assert client.get(
        "/api/v1/owner/bookings",
        headers={"Authorization": f"Bearer {expired}"},
    ).status_code == 401
    assert client.get(
        "/api/v1/owner/bookings",
        headers={"Authorization": f"Bearer {_token(22, 'ADMIN')}"},
    ).status_code == 403
    assert client.get("/api/v1/owner/bookings/{booking_id}").status_code == 401


def test_owner_venue_filter_outside_scope_returns_empty(client: TestClient) -> None:
    with app.state.test_session() as db:
        db.add(Booking(
            user_id=1, time_slot_id=10, court_id=4, venue_id=12, owner_id=22,
            slot_date=date(2026, 10, 29), start_time=time(18, 0), end_time=time(19, 0),
            status="CONFIRMED", total_amount=Decimal("180.00"),
        ))
        db.commit()

    response = client.get(
        "/api/v1/owner/bookings?venue_id=999",
        headers={"Authorization": f"Bearer {_token(22, 'OWNER')}"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_owner_completion_missing_booking_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/v1/owner/bookings/999999/complete",
        headers={"Authorization": f"Bearer {_token(22, 'OWNER')}"},
    )

    assert response.status_code == 404


def test_multi_slot_quote_is_read_only_and_calculates_combined_authoritative_total(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.routes.integrations.get_slot_quote", lambda ids: {"slots": [
        {"time_slot_id": 15, "price_per_hour": "120000", "slot_date": "2026-12-01", "start_time": "08:00:00", "end_time": "09:00:00", "court_id": 4, "venue_id": 2, "owner_id": 22},
        {"time_slot_id": 16, "price_per_hour": "120000", "slot_date": "2026-12-01", "start_time": "09:00:00", "end_time": "10:00:00", "court_id": 4, "venue_id": 2, "owner_id": 22},
    ]})
    response = client.get("/api/v1/booking-quotes/15,16", headers={"Authorization": f"Bearer {_token()}"})
    assert response.status_code == 200
    quote = response.json()
    assert quote["time_slot_ids"] == [15, 16]
    assert quote["start_time"] == "08:00:00" and quote["end_time"] == "10:00:00"
    assert quote["duration_minutes"] == 120
    assert Decimal(quote["total_amount"]) == Decimal("240000.00")
    with app.state.test_session() as db:
        assert db.query(Booking).count() == 0
        assert db.query(BookingTimeSlot).count() == 0


def test_multi_slot_quote_rejects_gaps_and_duplicate_ids(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    data = {"slots": [
        {"time_slot_id": 15, "price_per_hour": "100", "slot_date": "2026-12-01", "start_time": "08:00:00", "end_time": "09:00:00", "court_id": 4, "venue_id": 2, "owner_id": 22},
        {"time_slot_id": 16, "price_per_hour": "100", "slot_date": "2026-12-01", "start_time": "10:00:00", "end_time": "11:00:00", "court_id": 4, "venue_id": 2, "owner_id": 22},
    ]}
    monkeypatch.setattr("app.routes.integrations.get_slot_quote", lambda ids: data)
    headers = {"Authorization": f"Bearer {_token()}"}
    assert client.get("/api/v1/booking-quotes/15,16", headers=headers).status_code == 409
    data["slots"][1]["start_time"] = "09:00:00"
    data["slots"][1]["end_time"] = "10:00:00"
    data["slots"][1]["court_id"] = 5
    assert client.get("/api/v1/booking-quotes/15,16", headers=headers).status_code == 409
    data["slots"][1]["court_id"] = 4
    data["slots"][1]["slot_date"] = "2026-12-02"
    assert client.get("/api/v1/booking-quotes/15,16", headers=headers).status_code == 409
    assert client.get("/api/v1/booking-quotes/15,15", headers=headers).status_code == 422


def test_multi_slot_confirmation_confirms_the_associated_set_once(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    confirmed_slot_sets = []
    monkeypatch.setattr("app.routes.integrations.confirm_slot", lambda ids, booking_id: confirmed_slot_sets.append((ids, booking_id)) or {"status": "BOOKED"})
    with app.state.test_session() as db:
        booking = Booking(user_id=1, time_slot_id=15, court_id=4, venue_id=2, owner_id=22,
                          slot_date=date(2026, 12, 1), start_time=time(8), end_time=time(10),
                          status="PENDING", total_amount=Decimal("200"),
                          expires_at=datetime.now(timezone.utc) + timedelta(minutes=10))
        booking.slot_links = [BookingTimeSlot(time_slot_id=15, position=0), BookingTimeSlot(time_slot_id=16, position=1)]
        db.add(booking)
        db.commit()
        booking_id = booking.id
    headers = {"X-Internal-Token": "test-internal-token"}
    first = client.post(f"/api/v1/internal/bookings/{booking_id}/confirm", headers=headers)
    second = client.post(f"/api/v1/internal/bookings/{booking_id}/confirm", headers=headers)
    assert first.status_code == second.status_code == 200
    assert first.json()["qr_token"] == second.json()["qr_token"]
    assert first.json()["confirmed_at"] == second.json()["confirmed_at"]
    assert confirmed_slot_sets == [([15, 16], booking_id)]


def test_duplicate_slot_selection_is_rejected_before_booking_creation(client: TestClient) -> None:
    response = client.post("/api/v1/bookings", json={"time_slot_ids": [15, 15]}, headers={"Authorization": f"Bearer {_token()}"})
    assert response.status_code == 422
    with app.state.test_session() as db:
        assert db.query(Booking).count() == 0


def test_multi_slot_payment_failure_releases_only_that_bookings_slot_set(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    releases = []
    monkeypatch.setattr("app.routes.integrations.release_slot", lambda ids, booking_id: releases.append((ids, booking_id)) or {})
    with app.state.test_session() as db:
        booking = Booking(user_id=1, time_slot_id=31, court_id=4, venue_id=2, owner_id=22,
                          slot_date=date(2026, 12, 1), start_time=time(8), end_time=time(10),
                          status="PENDING", total_amount=Decimal("200"),
                          expires_at=datetime.now(timezone.utc) + timedelta(minutes=10))
        booking.slot_links = [BookingTimeSlot(time_slot_id=31, position=0), BookingTimeSlot(time_slot_id=32, position=1)]
        db.add(booking)
        db.commit()
        booking_id = booking.id
    response = client.post(f"/api/v1/internal/bookings/{booking_id}/fail", headers={"X-Internal-Token": "test-internal-token"})
    assert response.status_code == 200
    assert response.json()["status"] == "FAILED"
    assert releases == [([31, 32], booking_id)]


@pytest.mark.parametrize("flow", ["cancel", "expire"])
def test_multi_slot_cancellation_and_expiration_release_the_associated_set(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, flow: str
) -> None:
    releases: list[tuple[list[int], int]] = []
    monkeypatch.setattr(
        "app.routes.integrations.release_slot",
        lambda ids, booking_id: releases.append((ids, booking_id)) or {"status": "AVAILABLE"},
    )
    with app.state.test_session() as db:
        booking = Booking(
            user_id=1,
            time_slot_id=41,
            court_id=4,
            venue_id=2,
            owner_id=22,
            slot_date=date(2026, 12, 1),
            start_time=time(8),
            end_time=time(10),
            status="PENDING",
            total_amount=Decimal("200"),
            expires_at=(datetime.now(timezone.utc) + timedelta(minutes=10)
                        if flow == "cancel" else datetime.now(timezone.utc) - timedelta(minutes=1)),
        )
        booking.slot_links = [
            BookingTimeSlot(time_slot_id=41, position=0),
            BookingTimeSlot(time_slot_id=42, position=1),
        ]
        db.add(booking)
        db.commit()
        booking_id = booking.id

    if flow == "cancel":
        response = client.post(
            f"/api/v1/bookings/{booking_id}/cancel",
            headers={"Authorization": f"Bearer {_token()}"},
        )
    else:
        response = client.post(
            "/api/v1/internal/bookings/expire",
            headers={"X-Internal-Token": "test-internal-token"},
        )

    assert response.status_code == 200
    assert releases == [([41, 42], booking_id)]
    with app.state.test_session() as db:
        persisted = db.get(Booking, booking_id)
        assert persisted is not None
        assert persisted.status == ("CANCELLED" if flow == "cancel" else "EXPIRED")


def test_payment_context_reports_current_status_and_only_confirmed_qr(client: TestClient) -> None:
    with app.state.test_session() as db:
        confirmed = Booking(
            user_id=1, time_slot_id=51, court_id=4, venue_id=2, owner_id=22,
            slot_date=date(2026, 12, 1), start_time=time(8), end_time=time(9),
            status="CONFIRMED", total_amount=Decimal("100"), qr_token="c" * 32,
            confirmed_at=datetime.now(timezone.utc),
        )
        cancelled = Booking(
            user_id=1, time_slot_id=52, court_id=4, venue_id=2, owner_id=22,
            slot_date=date(2026, 12, 1), start_time=time(9), end_time=time(10),
            status="CANCELLED", total_amount=Decimal("100"), qr_token=None,
        )
        db.add_all([confirmed, cancelled])
        db.commit()
        confirmed_id, cancelled_id = confirmed.id, cancelled.id

    headers = {"X-Internal-Token": "test-internal-token"}
    confirmed_context = client.get(
        f"/api/v1/internal/bookings/{confirmed_id}/payment-context", headers=headers
    )
    cancelled_context = client.get(
        f"/api/v1/internal/bookings/{cancelled_id}/payment-context", headers=headers
    )

    assert confirmed_context.status_code == cancelled_context.status_code == 200
    assert confirmed_context.json()["status"] == "CONFIRMED"
    assert confirmed_context.json()["qr_token"] == "c" * 32
    assert cancelled_context.json()["status"] == "CANCELLED"
    assert cancelled_context.json()["qr_token"] is None


def test_multi_slot_booking_creates_one_pending_booking_and_associations(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.routes.integrations.hold_slot", lambda ids, booking_id: {
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        "slots": [
            {"time_slot_id": 15, "price_per_hour": "120000", "slot_date": "2026-12-01", "start_time": "08:00:00", "end_time": "09:00:00", "court_id": 4, "venue_id": 2, "owner_id": 22},
            {"time_slot_id": 16, "price_per_hour": "120000", "slot_date": "2026-12-01", "start_time": "09:00:00", "end_time": "10:00:00", "court_id": 4, "venue_id": 2, "owner_id": 22},
        ]
    })
    response = client.post("/api/v1/bookings", json={"time_slot_ids": [15, 16]}, headers={"Authorization": f"Bearer {_token()}"})
    assert response.status_code == 201, response.text
    booking = response.json()
    assert booking["status"] == "PENDING"
    assert booking["time_slot_id"] == 15 and booking["time_slot_ids"] == [15, 16]
    assert Decimal(booking["total_amount"]) == Decimal("240000.00")
    assert booking["start_time"] == "08:00:00" and booking["end_time"] == "10:00:00"
    with app.state.test_session() as db:
        assert db.query(Booking).count() == 1
        assert db.query(BookingTimeSlot).count() == 2


def test_customer_booking_history_returns_statuses_and_hides_nonconfirmed_qr(client: TestClient) -> None:
    with app.state.test_session() as db:
        db.add_all([
            Booking(user_id=1, time_slot_id=81, court_id=4, venue_id=2, owner_id=22, slot_date=date(2026, 12, 1), start_time=time(8), end_time=time(9), status="CHECKED_IN", total_amount=Decimal("100"), qr_token="a" * 32),
            Booking(user_id=1, time_slot_id=82, court_id=4, venue_id=2, owner_id=22, slot_date=date(2026, 12, 1), start_time=time(9), end_time=time(10), status="COMPLETED", total_amount=Decimal("100")),
        ])
        db.commit()
    response = client.get("/api/v1/bookings", headers={"Authorization": f"Bearer {_token()}"})
    assert response.status_code == 200
    assert {row["status"] for row in response.json()} == {"CHECKED_IN", "COMPLETED"}
    assert all(row["qr_token"] is None for row in response.json())

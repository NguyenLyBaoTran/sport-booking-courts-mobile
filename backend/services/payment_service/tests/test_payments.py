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
        json={"booking_id": 5, "mock_result": "SUCCESS", "payment_method": "ZALOPAY"},
        headers=headers,
    )
    second = client.post(
        "/api/v1/payments/process",
        json={"booking_id": 5, "mock_result": "SUCCESS", "payment_method": "ZALOPAY"},
        headers=headers,
    )

    assert first.status_code == 200
    assert first.json()["status"] == "PAID"
    assert first.json()["provider"] == "ZALOPAY"
    assert first.json()["booking_status"] == "CONFIRMED"
    assert first.json()["qr_token"] == "opaque-qr"
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["qr_token"] == first.json()["qr_token"]
    assert first.json()["paid_at"] is not None
    assert second.json()["paid_at"] == first.json()["paid_at"]
    assert second.json()["provider"] == "ZALOPAY"
    assert confirmations == [5]


def test_payment_method_must_be_supported(client: TestClient) -> None:
    response = client.post(
        "/api/v1/payments/process",
        json={"booking_id": 5, "payment_method": "UNSUPPORTED_PROVIDER"},
        headers={"Authorization": f"Bearer {_token()}"},
    )
    assert response.status_code == 422


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
        json={"booking_id": 5, "mock_result": "SUCCESS", "payment_method": "VNPAY"},
        headers=headers,
    )
    second = client.post(
        "/api/v1/payments/process",
        json={"booking_id": 5, "mock_result": "SUCCESS", "payment_method": "VNPAY"},
        headers=headers,
    )

    assert first.status_code == 503
    assert second.status_code == 200
    assert second.json()["status"] == "PAID"
    with client.app.state.test_session() as db:
        payments = db.query(Payment).filter(Payment.booking_id == 5).all()
        assert len(payments) == 1
        assert payments[0].idempotency_key == "same-booking-retry-key"
        assert payments[0].provider == "VNPAY"


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


def test_owner_cannot_use_customer_payment_process_or_history(client: TestClient) -> None:
    headers = {"Authorization": f"Bearer {_token(role='OWNER')}"}
    history = client.get("/api/v1/payments", headers=headers)
    process = client.post("/api/v1/payments/process", json={"booking_id": 5}, headers=headers)
    assert history.status_code == 403
    assert process.status_code == 403


def _seed_report_payments(client: TestClient) -> None:
    with client.app.state.test_session() as db:
        db.add_all([
            Payment(
                booking_id=101, successful_booking_id=101, user_id=1,
                provider="MOCK", status="PAID", amount=Decimal("100.00"),
                idempotency_key="report-paid-a", transaction_code="TX-101",
                created_at=datetime(2026, 3, 10, 8, tzinfo=timezone.utc),
                paid_at=datetime(2026, 3, 10, 8, 5, tzinfo=timezone.utc),
            ),
            Payment(
                booking_id=201, successful_booking_id=201, user_id=2,
                provider="MOCK", status="PAID", amount=Decimal("900.00"),
                idempotency_key="report-paid-b", transaction_code="TX-201",
                created_at=datetime(2026, 3, 10, 9, tzinfo=timezone.utc),
                paid_at=datetime(2026, 3, 10, 9, 5, tzinfo=timezone.utc),
            ),
            Payment(
                booking_id=102, user_id=1, provider="MOCK", status="PENDING",
                amount=Decimal("70.00"), idempotency_key="report-pending",
                created_at=datetime(2026, 3, 10, 10, tzinfo=timezone.utc),
            ),
            Payment(
                booking_id=103, user_id=1, provider="MOCK", status="FAILED",
                amount=Decimal("80.00"), idempotency_key="report-failed",
                created_at=datetime(2026, 3, 10, 11, tzinfo=timezone.utc),
            ),
            Payment(
                booking_id=104, successful_booking_id=104, user_id=1,
                provider="MOCK", status="PAID", amount=Decimal("25.00"),
                idempotency_key="report-legacy-paid", transaction_code="TX-104",
                created_at=datetime(2025, 1, 1, tzinfo=timezone.utc), paid_at=None,
            ),
        ])
        db.commit()


def _report_context(booking_ids: list[int]) -> dict:
    ownership = {
        101: {"owner_id": 10, "venue_id": 5, "court_id": 50, "status": "CANCELLED"},
        102: {"owner_id": 10, "venue_id": 5, "court_id": 50, "status": "PENDING"},
        103: {"owner_id": 10, "venue_id": 5, "court_id": 50, "status": "FAILED"},
        104: {"owner_id": 10, "venue_id": 5, "court_id": 50, "status": "CANCELLED"},
        201: {"owner_id": 20, "venue_id": 6, "court_id": 60, "status": "CONFIRMED"},
    }
    return {"bookings": [
        {"booking_id": booking_id, **ownership[booking_id]}
        for booking_id in booking_ids if booking_id in ownership
    ]}


def test_owner_report_is_scoped_and_counts_paid_cancelled_and_legacy_rows(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_report_payments(client)
    batches: list[list[int]] = []

    def lookup(booking_ids: list[int]) -> dict:
        batches.append(booking_ids)
        return _report_context(booking_ids)

    monkeypatch.setattr("app.routes.integrations.get_payment_report_context", lookup)
    response = client.get(
        "/api/v1/payments/report?owner_id=20&group_by=month&page_size=10",
        headers={"Authorization": f"Bearer {_token(user_id=10, role='OWNER')}"},
    )

    assert response.status_code == 200, response.text
    report = response.json()
    assert report["summary"] == {
        "total_revenue": "125.00",
        "successful_payments": 2,
        "pending_payments": 1,
        "failed_payments": 1,
        "total_transactions": 4,
        "undated_successful_payments": 1,
        "undated_successful_amount": "25.00",
    }
    assert report["revenue_series"] == [{
        "bucket": "2026-03", "revenue": "100.00", "successful_payments": 1,
    }]
    assert report["transactions"]["total"] == 4
    assert len(report["transactions"]["items"]) == 4
    assert all(item["booking_id"] != 201 for item in report["transactions"]["items"])
    cancelled_paid = next(item for item in report["transactions"]["items"] if item["booking_id"] == 101)
    assert cancelled_paid["booking_status"] == "CANCELLED"
    assert cancelled_paid["status"] == "PAID"
    assert len(batches) == 1


def test_date_filter_uses_paid_at_for_revenue_and_never_created_at_for_legacy_paid(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_report_payments(client)
    monkeypatch.setattr("app.routes.integrations.get_payment_report_context", _report_context)
    response = client.get(
        "/api/v1/payments/report?date_from=2026-03-10&date_to=2026-03-10&group_by=day",
        headers={"Authorization": f"Bearer {_token(user_id=10, role='OWNER')}"},
    )

    assert response.status_code == 200, response.text
    report = response.json()
    assert report["summary"]["total_revenue"] == "100.00"
    assert report["summary"]["successful_payments"] == 1
    assert report["summary"]["pending_payments"] == 1
    assert report["summary"]["failed_payments"] == 1
    assert report["summary"]["undated_successful_payments"] == 1
    assert report["revenue_series"] == [{
        "bucket": "2026-03-10", "revenue": "100.00", "successful_payments": 1,
    }]
    assert all(item["booking_id"] != 104 for item in report["transactions"]["items"])


def test_report_timezone_filters_whole_vietnam_calendar_day_and_returns_provider(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_report_payments(client)
    with client.app.state.test_session() as db:
        db.add_all([
            Payment(
                booking_id=106, successful_booking_id=106, user_id=1,
                provider="BANK_TRANSFER", status="PAID", amount=Decimal("10.00"),
                idempotency_key="report-vn-start", transaction_code="TX-106",
                created_at=datetime(2026, 3, 9, 16, 50, tzinfo=timezone.utc),
                paid_at=datetime(2026, 3, 9, 17, 0, tzinfo=timezone.utc),
            ),
            Payment(
                booking_id=107, successful_booking_id=107, user_id=1,
                provider="WALLET", status="PAID", amount=Decimal("20.00"),
                idempotency_key="report-vn-end", transaction_code="TX-107",
                created_at=datetime(2026, 3, 10, 16, 40, tzinfo=timezone.utc),
                paid_at=datetime(2026, 3, 10, 16, 59, 59, tzinfo=timezone.utc),
            ),
            Payment(
                booking_id=108, successful_booking_id=108, user_id=1,
                provider="WALLET", status="PAID", amount=Decimal("30.00"),
                idempotency_key="report-vn-next-day", transaction_code="TX-108",
                created_at=datetime(2026, 3, 10, 16, 50, tzinfo=timezone.utc),
                paid_at=datetime(2026, 3, 10, 17, 0, tzinfo=timezone.utc),
            ),
        ])
        db.commit()
    ownership = _report_context
    def context_with_new_bookings(booking_ids: list[int]) -> dict:
        response = ownership(booking_ids)
        response["bookings"].extend(
            {"booking_id": booking_id, "owner_id": 10, "venue_id": 5, "court_id": 50, "status": "CONFIRMED"}
            for booking_id in booking_ids if booking_id in {106, 107, 108}
        )
        return response
    monkeypatch.setattr("app.routes.integrations.get_payment_report_context", context_with_new_bookings)

    response = client.get(
        "/api/v1/payments/report?date_from=2026-03-10&date_to=2026-03-10&timezone=Asia%2FHo_Chi_Minh",
        headers={"Authorization": f"Bearer {_token(user_id=10, role='OWNER')}"},
    )

    assert response.status_code == 200, response.text
    report = response.json()
    assert report["timezone"] == "Asia/Ho_Chi_Minh"
    assert report["summary"]["total_revenue"] == "130.00"
    assert report["revenue_series"] == [{
        "bucket": "2026-03-10", "revenue": "130.00", "successful_payments": 3,
    }]
    providers = {item["booking_id"]: item["provider"] for item in report["transactions"]["items"]}
    assert providers[106] == "BANK_TRANSFER"
    assert providers[107] == "WALLET"
    assert 108 not in providers


def test_report_rejects_unknown_timezone_and_defaults_to_utc(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_report_payments(client)
    monkeypatch.setattr("app.routes.integrations.get_payment_report_context", _report_context)
    headers = {"Authorization": f"Bearer {_token(role='ADMIN')}"}

    invalid = client.get("/api/v1/payments/report?timezone=Not%2FAZone", headers=headers)
    default = client.get("/api/v1/payments/report", headers=headers)

    assert invalid.status_code == 422
    assert default.status_code == 200
    assert default.json()["timezone"] == "UTC"


def test_admin_report_sees_system_data_and_user_role_is_forbidden(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_report_payments(client)
    lookup_calls: list[list[int]] = []
    monkeypatch.setattr(
        "app.routes.integrations.get_payment_report_context",
        lambda ids: lookup_calls.append(ids) or _report_context(ids),
    )
    user = client.get(
        "/api/v1/payments/report",
        headers={"Authorization": f"Bearer {_token(role='USER')}"},
    )
    admin = client.get(
        "/api/v1/payments/report?page=1&page_size=10&sort=asc",
        headers={"Authorization": f"Bearer {_token(role='ADMIN')}"},
    )

    assert user.status_code == 403
    assert admin.status_code == 200
    assert admin.json()["summary"]["total_revenue"] == "1025.00"
    assert admin.json()["summary"]["successful_payments"] == 3
    assert admin.json()["summary"]["pending_payments"] == 1
    assert admin.json()["summary"]["failed_payments"] == 1
    assert admin.json()["summary"]["total_transactions"] == 5
    assert len(admin.json()["transactions"]["items"]) == 5
    assert lookup_calls == []


def test_report_rejects_invalid_date_order_and_supports_pagination(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_report_payments(client)
    monkeypatch.setattr("app.routes.integrations.get_payment_report_context", _report_context)
    headers = {"Authorization": f"Bearer {_token(role='ADMIN')}"}
    invalid = client.get(
        "/api/v1/payments/report?date_from=2026-03-11&date_to=2026-03-10",
        headers=headers,
    )
    page = client.get(
        "/api/v1/payments/report?page=2&page_size=2&sort=asc",
        headers=headers,
    )
    assert invalid.status_code == 422
    assert page.status_code == 200
    assert page.json()["transactions"]["total"] == 5
    assert page.json()["transactions"]["page"] == 2
    assert len(page.json()["transactions"]["items"]) == 2

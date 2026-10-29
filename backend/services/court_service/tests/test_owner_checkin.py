import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from jose import jwt

from app.main import app


TEST_SECRET = "court-service-checkin-test-secret-with-32-chars"
INTERNAL_TOKEN = "server-side-internal-test-token"
CHECK_IN_PATH = "/api/v1/owner/checkins"
QR_TOKEN = "q" * 48


class FakeBookingClient:
    captured: dict | None = None
    status_code = 200
    result = {"booking_id": 73, "status": "CHECKED_IN", "checked_in_at": "2026-11-01T03:00:00Z"}
    error: Exception | None = None

    def __init__(self, timeout):
        type(self).captured = {"timeout": timeout}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, *, headers, json):
        type(self).captured.update({"url": url, "headers": headers, "json": json})
        if type(self).error is not None:
            raise type(self).error
        return httpx.Response(type(self).status_code, json=type(self).result)


class OwnerCheckInAdapterTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": TEST_SECRET,
                "JWT_ALGORITHM": "HS256",
                "BOOKING_SERVICE_URL": "http://booking.test:8003/",
                "INTERNAL_SERVICE_TOKEN": INTERNAL_TOKEN,
            },
        )
        self.environment.start()
        FakeBookingClient.captured = None
        FakeBookingClient.status_code = 200
        FakeBookingClient.result = {
            "booking_id": 73,
            "status": "CHECKED_IN",
            "checked_in_at": "2026-11-01T03:00:00Z",
        }
        FakeBookingClient.error = None
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.environment.stop()

    def _token(self, role="OWNER", owner_id=37, secret=TEST_SECRET):
        now = datetime.now(timezone.utc)
        return jwt.encode(
            {
                "sub": str(owner_id),
                "role": role,
                "iat": now,
                "exp": now + timedelta(minutes=10),
            },
            secret,
            algorithm="HS256",
        )

    def _post(self, payload=None, token=None, headers=None):
        request_headers = dict(headers or {})
        if token:
            request_headers["Authorization"] = f"Bearer {token}"
        with patch("app.booking_integration.httpx.AsyncClient", FakeBookingClient):
            return self.client.post(CHECK_IN_PATH, json=payload, headers=request_headers)

    def test_owner_jwt_forwards_check_in_and_returns_booking_response(self):
        response = self._post({"qr_token": QR_TOKEN}, self._token())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), FakeBookingClient.result)
        assert FakeBookingClient.captured is not None
        self.assertEqual(
            FakeBookingClient.captured["url"],
            "http://booking.test:8003/api/v1/internal/bookings/check-in",
        )
        self.assertEqual(FakeBookingClient.captured["timeout"], 5.0)
        self.assertEqual(
            FakeBookingClient.captured["json"],
            {"owner_id": 37, "qr_token": QR_TOKEN},
        )

    def test_missing_jwt_returns_401_without_upstream_call(self):
        response = self._post({"qr_token": QR_TOKEN})
        self.assertEqual(response.status_code, 401)
        self.assertIsNone(FakeBookingClient.captured)

    def test_invalid_jwt_returns_401_without_upstream_call(self):
        response = self._post({"qr_token": QR_TOKEN}, self._token(secret="another-secret-with-at-least-32-characters"))
        self.assertEqual(response.status_code, 401)
        self.assertIsNone(FakeBookingClient.captured)

    def test_user_role_returns_403_without_upstream_call(self):
        response = self._post({"qr_token": QR_TOKEN}, self._token(role="USER"))
        self.assertEqual(response.status_code, 403)
        self.assertIsNone(FakeBookingClient.captured)

    def test_owner_id_is_derived_from_jwt_and_client_internal_header_is_ignored(self):
        response = self._post(
            {"qr_token": QR_TOKEN},
            self._token(owner_id=57),
            headers={"X-Internal-Token": "attacker-provided-token"},
        )

        self.assertEqual(response.status_code, 200)
        assert FakeBookingClient.captured is not None
        self.assertEqual(FakeBookingClient.captured["json"]["owner_id"], 57)
        self.assertEqual(
            FakeBookingClient.captured["headers"]["X-Internal-Token"],
            INTERNAL_TOKEN,
        )

    def test_empty_or_blank_qr_token_returns_422(self):
        for token in ("", "   "):
            with self.subTest(token=repr(token)):
                response = self._post({"qr_token": token}, self._token())
                self.assertEqual(response.status_code, 422)
        self.assertIsNone(FakeBookingClient.captured)

    def test_browser_cannot_supply_owner_id_in_request_body(self):
        response = self._post(
            {"qr_token": QR_TOKEN, "owner_id": 999},
            self._token(owner_id=57),
        )

        self.assertEqual(response.status_code, 422)
        self.assertIsNone(FakeBookingClient.captured)

    def test_invalid_qr_keeps_booking_not_found_status(self):
        FakeBookingClient.status_code = 404
        FakeBookingClient.result = {"detail": "Booking not found for this owner"}

        response = self._post({"qr_token": QR_TOKEN}, self._token())

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Booking not found for this owner"})

    def test_already_checked_in_keeps_conflict_status(self):
        FakeBookingClient.status_code = 409
        FakeBookingClient.result = {"detail": "Booking is not eligible for check-in"}

        response = self._post({"qr_token": QR_TOKEN}, self._token())

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json(), {"detail": "Booking is not eligible for check-in"})

    def test_booking_connection_error_returns_503_without_secret(self):
        FakeBookingClient.error = httpx.ConnectError("connection refused")

        response = self._post({"qr_token": QR_TOKEN}, self._token())

        self.assertEqual(response.status_code, 503)
        self.assertNotIn(INTERNAL_TOKEN, response.text)

    def test_booking_timeout_returns_504_without_secret(self):
        FakeBookingClient.error = httpx.TimeoutException("request timed out")

        response = self._post({"qr_token": QR_TOKEN}, self._token())

        self.assertEqual(response.status_code, 504)
        self.assertNotIn(INTERNAL_TOKEN, response.text)

    def test_client_internal_token_is_not_used_when_server_token_missing(self):
        os.environ.pop("INTERNAL_SERVICE_TOKEN", None)

        response = self._post(
            {"qr_token": QR_TOKEN},
            self._token(),
            headers={"X-Internal-Token": "client-token-must-not-be-used"},
        )

        self.assertEqual(response.status_code, 503)
        self.assertIsNone(FakeBookingClient.captured)


if __name__ == "__main__":
    unittest.main()

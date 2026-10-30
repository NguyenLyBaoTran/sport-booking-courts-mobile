import os
from typing import Any
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

import main


class FakeUpstreamClient:
    captured_request: dict[str, Any] | None = None
    response_status = 200
    response_body = b"[]"

    def __init__(self, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def request(self, **kwargs):
        type(self).captured_request = kwargs
        return httpx.Response(
            status_code=type(self).response_status,
            headers={"content-type": "application/json"},
            content=type(self).response_body,
        )


class UnavailableUpstreamClient(FakeUpstreamClient):
    async def request(self, **kwargs):
        raise httpx.ConnectError("upstream unavailable")


class GatewayTests(unittest.TestCase):
    def setUp(self):
        FakeUpstreamClient.captured_request = None
        FakeUpstreamClient.response_status = 200
        FakeUpstreamClient.response_body = b"[]"
        self.client = TestClient(main.app)

    def tearDown(self):
        self.client.close()

    def test_gateway_health(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"service": "gateway", "status": "ok"})

    def test_unavailable_upstream_returns_generic_503(self):
        with patch.object(main.httpx, "AsyncClient", UnavailableUpstreamClient):
            response = self.client.get("/api/v1/sports")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Service unavailable"})

    def test_cors_preflight_allows_supported_methods(self):
        for method in ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
            with self.subTest(method=method):
                response = self.client.options(
                    "/api/v1/auth/login",
                    headers={
                        "Origin": "http://localhost:8080",
                        "Access-Control-Request-Method": method,
                        "Access-Control-Request-Headers": "authorization,content-type,idempotency-key",
                    },
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.headers["access-control-allow-origin"],
                    "http://localhost:8080",
                )
                self.assertIn(method, response.headers["access-control-allow-methods"])
                self.assertIn("authorization", response.headers["access-control-allow-headers"].lower())
                self.assertIn("idempotency-key", response.headers["access-control-allow-headers"].lower())

    def test_configured_origin_is_allowed_without_wildcard(self):
        with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": "http://localhost:3000"}):
            self.assertIn("http://localhost:3000", main.get_allowed_origins())
        with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": "*"}):
            with self.assertRaises(ValueError):
                main.get_allowed_origins()

    def test_gateway_forwards_authorization_and_keeps_get_route(self):
        with patch.object(main.httpx, "AsyncClient", FakeUpstreamClient):
            response = self.client.get(
                "/api/v1/users/me",
                headers={"Authorization": "Bearer test-only-placeholder"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        captured_request = FakeUpstreamClient.captured_request
        self.assertIsNotNone(captured_request)
        assert captured_request is not None
        headers = captured_request.get("headers")
        assert isinstance(headers, dict)
        self.assertEqual(
            headers["authorization"],
            "Bearer test-only-placeholder",
        )

    def test_gateway_forwards_idempotency_key_to_payment_service(self):
        with patch.object(main.httpx, "AsyncClient", FakeUpstreamClient):
            response = self.client.post(
                "/api/v1/payments/process",
                json={"booking_id": 42, "mock_result": "SUCCESS"},
                headers={"Idempotency-Key": "payment-attempt-42"},
            )

        self.assertEqual(response.status_code, 200)
        captured_request = FakeUpstreamClient.captured_request
        self.assertIsNotNone(captured_request)
        assert captured_request is not None
        self.assertEqual(
            captured_request["url"],
            "http://127.0.0.1:8004/api/v1/payments/process",
        )
        headers = captured_request.get("headers")
        assert isinstance(headers, dict)
        self.assertEqual(headers["idempotency-key"], "payment-attempt-42")

    def test_payment_route_works_without_idempotency_key(self):
        with patch.object(main.httpx, "AsyncClient", FakeUpstreamClient):
            response = self.client.post(
                "/api/v1/payments/process",
                json={"booking_id": 42, "mock_result": "SUCCESS"},
            )

        self.assertEqual(response.status_code, 200)
        captured_request = FakeUpstreamClient.captured_request
        self.assertIsNotNone(captured_request)
        assert captured_request is not None
        headers = captured_request.get("headers")
        assert isinstance(headers, dict)
        self.assertNotIn("idempotency-key", headers)

    def test_gateway_does_not_forward_client_internal_token(self):
        with patch.object(main.httpx, "AsyncClient", FakeUpstreamClient):
            response = self.client.post(
                "/api/v1/payments/process",
                json={"booking_id": 42, "mock_result": "SUCCESS"},
                headers={
                    "Idempotency-Key": "payment-attempt-42",
                    "X-Internal-Token": "must-not-reach-payment-service",
                },
            )

        self.assertEqual(response.status_code, 200)
        captured_request = FakeUpstreamClient.captured_request
        self.assertIsNotNone(captured_request)
        assert captured_request is not None
        headers = captured_request.get("headers")
        assert isinstance(headers, dict)
        self.assertEqual(headers["idempotency-key"], "payment-attempt-42")
        self.assertNotIn("x-internal-token", headers)

    def test_existing_booking_and_payment_routes_keep_their_destinations(self):
        with patch.object(main.httpx, "AsyncClient", FakeUpstreamClient):
            booking = self.client.get("/api/v1/bookings")
        self.assertEqual(booking.status_code, 200)
        assert FakeUpstreamClient.captured_request is not None
        self.assertEqual(
            FakeUpstreamClient.captured_request["url"],
            "http://127.0.0.1:8003/api/v1/bookings",
        )

        FakeUpstreamClient.captured_request = None
        with patch.object(main.httpx, "AsyncClient", FakeUpstreamClient):
            payment = self.client.get("/api/v1/payments")
        self.assertEqual(payment.status_code, 200)
        assert FakeUpstreamClient.captured_request is not None
        self.assertEqual(
            FakeUpstreamClient.captured_request["url"],
            "http://127.0.0.1:8004/api/v1/payments",
        )

    def test_gateway_routes_time_slots_and_does_not_expose_internal_contract(self):
        with patch.object(main.httpx, "AsyncClient", FakeUpstreamClient):
            response = self.client.get("/api/v1/time-slots?court_id=12")
        self.assertEqual(response.status_code, 200)
        captured_request = FakeUpstreamClient.captured_request
        self.assertIsNotNone(captured_request)
        assert captured_request is not None
        self.assertEqual(captured_request["url"], "http://127.0.0.1:8002/api/v1/time-slots?court_id=12")

        FakeUpstreamClient.captured_request = None
        hidden = self.client.post("/api/v1/internal/slots/12/hold?booking_id=44")
        self.assertEqual(hidden.status_code, 404)
        self.assertIsNone(FakeUpstreamClient.captured_request)

    def test_owner_booking_list_routes_to_booking_with_query_and_authorization(self):
        with patch.object(main.httpx, "AsyncClient", FakeUpstreamClient):
            response = self.client.get(
                "/api/v1/owner/bookings?venue_id=12&date=2026-10-29&status=CONFIRMED",
                headers={"Authorization": "Bearer owner-token"},
            )

        self.assertEqual(response.status_code, 200)
        assert FakeUpstreamClient.captured_request is not None
        captured = FakeUpstreamClient.captured_request
        self.assertEqual(captured["method"], "GET")
        self.assertEqual(
            captured["url"],
            "http://127.0.0.1:8003/api/v1/owner/bookings?venue_id=12&date=2026-10-29&status=CONFIRMED",
        )
        self.assertEqual(captured["headers"]["authorization"], "Bearer owner-token")

    def test_owner_booking_detail_routes_to_booking_service(self):
        with patch.object(main.httpx, "AsyncClient", FakeUpstreamClient):
            response = self.client.get(
                "/api/v1/owner/bookings/42",
                headers={"Authorization": "Bearer owner-token"},
            )

        self.assertEqual(response.status_code, 200)
        assert FakeUpstreamClient.captured_request is not None
        self.assertEqual(FakeUpstreamClient.captured_request["method"], "GET")
        self.assertEqual(
            FakeUpstreamClient.captured_request["url"],
            "http://127.0.0.1:8003/api/v1/owner/bookings/42",
        )

    def test_owner_booking_complete_routes_to_booking_service(self):
        with patch.object(main.httpx, "AsyncClient", FakeUpstreamClient):
            response = self.client.post(
                "/api/v1/owner/bookings/42/complete",
                headers={"Authorization": "Bearer owner-token"},
            )

        self.assertEqual(response.status_code, 200)
        assert FakeUpstreamClient.captured_request is not None
        self.assertEqual(FakeUpstreamClient.captured_request["method"], "POST")
        self.assertEqual(
            FakeUpstreamClient.captured_request["url"],
            "http://127.0.0.1:8003/api/v1/owner/bookings/42/complete",
        )
        self.assertEqual(FakeUpstreamClient.captured_request["content"], b"")

    def test_owner_checkin_routes_to_court_and_forwards_body_and_authorization(self):
        body = {"qr_token": "opaque-qr-token"}
        with patch.object(main.httpx, "AsyncClient", FakeUpstreamClient):
            response = self.client.post(
                "/api/v1/owner/checkins",
                json=body,
                headers={
                    "Authorization": "Bearer owner-token",
                    "X-Internal-Token": "client-must-not-forward",
                },
            )

        self.assertEqual(response.status_code, 200)
        assert FakeUpstreamClient.captured_request is not None
        captured = FakeUpstreamClient.captured_request
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["url"], "http://127.0.0.1:8002/api/v1/owner/checkins")
        self.assertEqual(captured["content"], b'{"qr_token":"opaque-qr-token"}')
        self.assertEqual(captured["headers"]["authorization"], "Bearer owner-token")
        self.assertNotIn("x-internal-token", captured["headers"])

    def test_owner_routes_preserve_upstream_authorization_and_conflict_statuses(self):
        for status_code in (401, 403, 404, 409):
            with self.subTest(status_code=status_code):
                FakeUpstreamClient.response_status = status_code
                FakeUpstreamClient.response_body = b'{"detail":"upstream response"}'
                with patch.object(main.httpx, "AsyncClient", FakeUpstreamClient):
                    response = self.client.post(
                        "/api/v1/owner/checkins",
                        json={"qr_token": "opaque-qr-token"},
                        headers={"Authorization": "Bearer owner-token"},
                    )

                self.assertEqual(response.status_code, status_code)
                self.assertEqual(response.content, b'{"detail":"upstream response"}')

    def test_internal_booking_and_court_paths_are_not_public(self):
        for path in (
            "/api/v1/internal/slots/12/hold?booking_id=44",
            "/api/v1/internal/bookings/check-in",
        ):
            with self.subTest(path=path):
                FakeUpstreamClient.captured_request = None
                response = self.client.post(path)
                self.assertEqual(response.status_code, 404)
                self.assertIsNone(FakeUpstreamClient.captured_request)

    def test_admin_catalogue_summary_routes_to_court_and_forwards_authorization(self):
        with patch.object(main.httpx, "AsyncClient", FakeUpstreamClient):
            response = self.client.get(
                "/api/v1/admin/catalogue/summary",
                headers={"Authorization": "Bearer admin-token"},
            )

        self.assertEqual(response.status_code, 200)
        assert FakeUpstreamClient.captured_request is not None
        self.assertEqual(
            FakeUpstreamClient.captured_request["url"],
            "http://127.0.0.1:8002/api/v1/admin/catalogue/summary",
        )
        self.assertEqual(
            FakeUpstreamClient.captured_request["headers"]["authorization"],
            "Bearer admin-token",
        )

    def test_admin_prefixes_route_only_to_their_owning_services(self):
        cases = (
            ("/api/v1/admin/users?page=2", "http://127.0.0.1:8001/api/v1/admin/users?page=2"),
            ("/api/v1/admin/bookings/42", "http://127.0.0.1:8003/api/v1/admin/bookings/42"),
            ("/api/v1/admin/checkins?status=CHECKED_IN", "http://127.0.0.1:8003/api/v1/admin/checkins?status=CHECKED_IN"),
        )
        for path, expected_url in cases:
            with self.subTest(path=path):
                FakeUpstreamClient.captured_request = None
                with patch.object(main.httpx, "AsyncClient", FakeUpstreamClient):
                    response = self.client.get(path, headers={"Authorization": "Bearer admin-token"})
                self.assertEqual(response.status_code, 200)
                assert FakeUpstreamClient.captured_request is not None
                self.assertEqual(FakeUpstreamClient.captured_request["url"], expected_url)
                self.assertEqual(FakeUpstreamClient.captured_request["headers"]["authorization"], "Bearer admin-token")


if __name__ == "__main__":
    unittest.main()

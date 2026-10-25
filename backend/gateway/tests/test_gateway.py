import os
from typing import Any
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

import main


class FakeUpstreamClient:
    captured_request: dict[str, Any] | None = None

    def __init__(self, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def request(self, **kwargs):
        type(self).captured_request = kwargs
        return httpx.Response(
            status_code=200,
            headers={"content-type": "application/json"},
            content=b"[]",
        )


class UnavailableUpstreamClient(FakeUpstreamClient):
    async def request(self, **kwargs):
        raise httpx.ConnectError("upstream unavailable")


class GatewayTests(unittest.TestCase):
    def setUp(self):
        FakeUpstreamClient.captured_request = None
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
                        "Access-Control-Request-Headers": "authorization,content-type",
                    },
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.headers["access-control-allow-origin"],
                    "http://localhost:8080",
                )
                self.assertIn(method, response.headers["access-control-allow-methods"])
                self.assertIn("authorization", response.headers["access-control-allow-headers"].lower())

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


if __name__ == "__main__":
    unittest.main()

import os

import httpx
from fastapi import HTTPException


def _request(method: str, path: str) -> dict:
    base_url = os.getenv("BOOKING_SERVICE_URL", "http://127.0.0.1:8003").rstrip("/")
    token = os.getenv("INTERNAL_SERVICE_TOKEN", "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Internal service token is not configured")
    try:
        response = httpx.request(
            method,
            f"{base_url}{path}",
            headers={"X-Internal-Token": token},
            timeout=5.0,
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Booking service timed out") from None
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Booking service is unavailable") from None
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Booking not found")
    if response.status_code == 409:
        raise HTTPException(status_code=409, detail="Booking is not payable")
    if response.status_code >= 400:
        raise HTTPException(status_code=503, detail="Booking service rejected the request")
    return response.json()


def get_payment_context(booking_id: int) -> dict:
    return _request("GET", f"/api/v1/internal/bookings/{booking_id}/payment-context")


def confirm_booking(booking_id: int) -> dict:
    return _request("POST", f"/api/v1/internal/bookings/{booking_id}/confirm")

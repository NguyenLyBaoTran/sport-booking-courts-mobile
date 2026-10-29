import os

import httpx
from fastapi import HTTPException


BOOKING_CHECK_IN_PATH = "/api/v1/internal/bookings/check-in"
BOOKING_REQUEST_TIMEOUT_SECONDS = 5.0


async def check_in_booking(owner_id: int, qr_token: str) -> dict:
    base_url = os.getenv("BOOKING_SERVICE_URL", "http://127.0.0.1:8003").rstrip("/")
    internal_token = os.getenv("INTERNAL_SERVICE_TOKEN", "").strip()
    if not internal_token:
        raise HTTPException(status_code=503, detail="Booking service integration is not configured")

    try:
        async with httpx.AsyncClient(timeout=BOOKING_REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{base_url}{BOOKING_CHECK_IN_PATH}",
                headers={"X-Internal-Token": internal_token},
                json={"owner_id": owner_id, "qr_token": qr_token},
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Booking service timed out") from None
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Booking service is unavailable") from None

    if response.status_code == 200:
        try:
            result = response.json()
        except ValueError:
            raise HTTPException(status_code=503, detail="Booking service returned an invalid response") from None
        if not isinstance(result, dict):
            raise HTTPException(status_code=503, detail="Booking service returned an invalid response")
        return result
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Booking not found for this owner")
    if response.status_code == 409:
        raise HTTPException(status_code=409, detail="Booking is not eligible for check-in")
    if response.status_code == 422:
        raise HTTPException(status_code=422, detail="QR check-in request is invalid")
    raise HTTPException(status_code=503, detail="Booking service rejected the check-in request")

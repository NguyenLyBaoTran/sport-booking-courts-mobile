import os

import httpx
from fastapi import HTTPException


def _request(method: str, path: str, **kwargs) -> dict:
    base_url = os.getenv("COURT_SERVICE_URL", "http://127.0.0.1:8002").rstrip("/")
    token = os.getenv("INTERNAL_SERVICE_TOKEN", "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Internal service token is not configured")
    try:
        response = httpx.request(
            method,
            f"{base_url}{path}",
            headers={"X-Internal-Token": token},
            timeout=5.0,
            **kwargs,
        )
        if response.status_code >= 400:
            if response.status_code == 409:
                raise HTTPException(status_code=409, detail="Time slot is unavailable")
            raise HTTPException(status_code=503, detail="Court service rejected the request")
        return response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Court service timed out") from None
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Court service is unavailable") from None


def hold_slot(slot_id: int, booking_id: int) -> dict:
    return _request(
        "POST",
        f"/api/v1/internal/slots/{slot_id}/hold",
        params={"booking_id": booking_id},
    )


def confirm_slot(slot_id: int, booking_id: int) -> dict:
    return _request(
        "POST",
        f"/api/v1/internal/slots/{slot_id}/confirm",
        params={"booking_id": booking_id},
    )


def release_slot(slot_id: int, booking_id: int) -> dict:
    return _request(
        "POST",
        f"/api/v1/internal/slots/{slot_id}/release",
        params={"booking_id": booking_id},
    )

import secrets
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import integrations
from app.auth import Principal, current_principal, require_customer, require_internal_token
from app.database import get_db
from app.models import Booking
from app.schemas import (
    BookingCheckIn,
    BookingCompletion,
    BookingCreate,
    BookingResponse,
    PaymentContext,
)

router = APIRouter()


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _expire_if_needed(booking: Booking, db: Session) -> None:
    if (
        booking.status == "PENDING"
        and booking.expires_at is not None
        and _as_utc(booking.expires_at) <= datetime.now(timezone.utc)
    ):
        integrations.release_slot(booking.time_slot_id, booking.id)
        booking.status = "EXPIRED"
        db.commit()


def _owned_booking(db: Session, booking_id: int, principal: Principal) -> Booking:
    booking = db.get(Booking, booking_id)
    if booking is None or booking.user_id != principal.user_id:
        raise HTTPException(status_code=404, detail="Booking not found")
    _expire_if_needed(booking, db)
    return booking


@router.post(
    "/bookings",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["bookings"],
)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(current_principal),
):
    require_customer(principal)

    booking = Booking(
        user_id=principal.user_id,
        time_slot_id=payload.time_slot_id,
        status="PENDING",
        total_amount=Decimal("0.00"),
        expires_at=None,
    )
    db.add(booking)
    db.flush()
    try:
        hold = integrations.hold_slot(payload.time_slot_id, booking.id)
        price = Decimal(str(hold["price_per_hour"]))
        slot_date = date.fromisoformat(hold["slot_date"])
        start_time = time.fromisoformat(hold["start_time"])
        end_time = time.fromisoformat(hold["end_time"])
        starts = datetime.combine(slot_date, start_time)
        ends = datetime.combine(slot_date, end_time)
        duration_hours = Decimal(str((ends - starts).total_seconds())) / Decimal("3600")
        expires_at = datetime.fromisoformat(hold["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        court_id = int(hold["court_id"])
        venue_id = int(hold["venue_id"])
        owner_id = int(hold["owner_id"])
        if (
            price <= 0
            or duration_hours <= 0
            or court_id <= 0
            or venue_id <= 0
            or owner_id <= 0
            or expires_at <= datetime.now(timezone.utc)
        ):
            raise ValueError("Court service returned an invalid slot price or duration")
        booking.total_amount = (price * duration_hours).quantize(Decimal("0.01"))
        booking.expires_at = expires_at
        booking.court_id = court_id
        booking.venue_id = venue_id
        booking.owner_id = owner_id
        booking.slot_date = slot_date
        booking.start_time = start_time
        booking.end_time = end_time
        db.commit()
    except (KeyError, InvalidOperation, TypeError, ValueError):
        db.rollback()
        integrations.release_slot(payload.time_slot_id, booking.id)
        raise HTTPException(status_code=502, detail="Court service returned invalid slot data") from None
    except (HTTPException, SQLAlchemyError):
        db.rollback()
        integrations.release_slot(payload.time_slot_id, booking.id)
        raise
    db.refresh(booking)
    return booking


@router.get("/bookings", response_model=list[BookingResponse], tags=["bookings"])
def list_bookings(
    db: Session = Depends(get_db),
    principal: Principal = Depends(current_principal),
):
    require_customer(principal)
    bookings = list(
        db.scalars(
            select(Booking)
            .where(Booking.user_id == principal.user_id)
            .order_by(Booking.created_at.desc())
        )
    )
    for booking in bookings:
        _expire_if_needed(booking, db)
    return bookings


@router.get("/bookings/{booking_id}", response_model=BookingResponse, tags=["bookings"])
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(current_principal),
):
    require_customer(principal)
    return _owned_booking(db, booking_id, principal)


@router.post("/bookings/{booking_id}/cancel", response_model=BookingResponse, tags=["bookings"])
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(current_principal),
):
    require_customer(principal)
    booking = _owned_booking(db, booking_id, principal)
    if booking.status != "PENDING":
        raise HTTPException(status_code=409, detail="Only pending bookings can be cancelled")
    integrations.release_slot(booking.time_slot_id, booking.id)
    booking.status = "CANCELLED"
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/internal/bookings/{booking_id}/payment-context", tags=["internal"])
def payment_context(
    booking_id: int,
    x_internal_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    require_internal_token(x_internal_token)
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    _expire_if_needed(booking, db)
    if booking.status == "PENDING" and booking.expires_at is None:
        raise HTTPException(status_code=409, detail="Booking has no active slot hold")
    if booking.status not in {"PENDING", "CONFIRMED"}:
        raise HTTPException(status_code=409, detail="Booking is not payable")
    return PaymentContext(
        booking_id=booking.id,
        user_id=booking.user_id,
        status=booking.status,
        total_amount=booking.total_amount,
        expires_at=booking.expires_at,
    )


@router.post("/internal/bookings/{booking_id}/confirm", tags=["internal"])
def confirm_booking(
    booking_id: int,
    x_internal_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    require_internal_token(x_internal_token)
    booking = db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update())
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    _expire_if_needed(booking, db)
    if booking.status == "CONFIRMED":
        return {"booking_id": booking.id, "status": booking.status, "qr_token": booking.qr_token}
    if booking.status != "PENDING":
        raise HTTPException(status_code=409, detail="Booking cannot be confirmed")
    integrations.confirm_slot(booking.time_slot_id, booking.id)
    booking.status = "CONFIRMED"
    booking.expires_at = None
    booking.qr_token = secrets.token_urlsafe(32)
    db.commit()
    return {"booking_id": booking.id, "status": booking.status, "qr_token": booking.qr_token}


@router.post("/internal/bookings/check-in", tags=["internal"])
def check_in_booking(
    payload: BookingCheckIn,
    x_internal_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    require_internal_token(x_internal_token)
    booking = db.scalar(
        select(Booking).where(Booking.qr_token == payload.qr_token).with_for_update()
    )
    if booking is None or booking.owner_id != payload.owner_id:
        raise HTTPException(status_code=404, detail="Booking not found for this owner")
    if booking.status != "CONFIRMED":
        raise HTTPException(status_code=409, detail="Booking is not eligible for check-in")
    booking.status = "CHECKED_IN"
    booking.checked_in_by = payload.owner_id
    booking.checked_in_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "booking_id": booking.id,
        "status": booking.status,
        "checked_in_at": booking.checked_in_at,
    }


@router.post("/internal/bookings/{booking_id}/complete", tags=["internal"])
def complete_booking(
    booking_id: int,
    payload: BookingCompletion,
    x_internal_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    require_internal_token(x_internal_token)
    booking = db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update())
    if booking is None or booking.owner_id != payload.owner_id:
        raise HTTPException(status_code=404, detail="Booking not found for this owner")
    if booking.status != "CHECKED_IN":
        raise HTTPException(status_code=409, detail="Only checked-in bookings can be completed")
    booking.status = "COMPLETED"
    booking.completed_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "booking_id": booking.id,
        "status": booking.status,
        "completed_at": booking.completed_at,
    }


@router.post("/internal/bookings/expire", tags=["internal"])
def expire_bookings(
    x_internal_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    require_internal_token(x_internal_token)
    pending = list(
        db.scalars(
            select(Booking).where(
                Booking.status == "PENDING",
                Booking.expires_at <= datetime.now(timezone.utc),
            )
        )
    )
    for booking in pending:
        integrations.release_slot(booking.time_slot_id, booking.id)
        booking.status = "EXPIRED"
        db.commit()
    return {"expired": len(pending), "released": len(pending)}
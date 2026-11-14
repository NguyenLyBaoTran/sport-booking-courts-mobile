from __future__ import annotations

import secrets
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Literal, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import integrations
from app.auth import Principal, current_principal, require_customer, require_internal_token, require_owner
from app.database import get_db
from app.models import Booking, BookingTimeSlot
from app.schemas import (
    BookingCheckIn,
    BookingCompletion,
    BookingCreate,
    BookingResponse,
    OwnerBookingCompletionResponse,
    OwnerBookingResponse,
    PaymentContext,
    AdminBookingResponse,
    AdminBookingListResponse,
    BookingSummaryResponse,
)

router = APIRouter()
BUSINESS_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _booking_slot_ids(booking: Booking) -> list[int]:
    return booking.time_slot_ids


def _integration_slot_argument(slot_ids: list[int]) -> int | list[int]:
    return slot_ids[0] if len(slot_ids) == 1 else slot_ids


def _finish_expiration_release(booking: Booking, db: Session) -> bool:
    """Release a terminal booking's slot; expires_at marks unfinished cleanup."""
    released = False
    try:
        integrations.release_slot(_integration_slot_argument(_booking_slot_ids(booking)), booking.id)
        released = True
    except HTTPException as error:
        if error.status_code != 409:
            raise
        # Court confirms this booking no longer owns a releasable reservation.
        # Keep any newer reservation untouched and mark cleanup resolved locally.
    booking.expires_at = None
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Could not persist expiration cleanup; retry expiration") from None
    return released


def _expire_if_needed(booking: Booking, db: Session) -> None:
    if booking.status == "PENDING" and booking.expires_at is not None and _as_utc(booking.expires_at) <= datetime.now(timezone.utc):
        booking.status = "EXPIRED"
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise HTTPException(status_code=503, detail="Could not persist booking expiration; retry expiration") from None
    if booking.status in {"EXPIRED", "FAILED", "CANCELLED"} and booking.expires_at is not None:
        # expires_at is the durable marker for retrying terminal cleanup.
        _finish_expiration_release(booking, db)


def _owned_booking(db: Session, booking_id: int, principal: Principal) -> Booking:
    booking = db.get(Booking, booking_id)
    if booking is None or booking.user_id != principal.user_id:
        raise HTTPException(status_code=404, detail="Booking not found")
    _expire_if_needed(booking, db)
    return booking


def _normalize_slot_quote(slot_ids: list[int], response: dict) -> dict:
    try:
        raw_slots = response.get("slots")
        if not raw_slots and len(slot_ids) == 1:
            raw_slots = [{**response, "time_slot_id": slot_ids[0]}]
        if not isinstance(raw_slots, list) or len(raw_slots) != len(slot_ids):
            raise ValueError
        by_id = {}
        for raw in raw_slots:
            slot_id = int(raw["time_slot_id"])
            price = Decimal(str(raw["price_per_hour"]))
            slot_date = date.fromisoformat(raw["slot_date"])
            start_time = time.fromisoformat(raw["start_time"])
            end_time = time.fromisoformat(raw["end_time"])
            court_id, venue_id, owner_id = int(raw["court_id"]), int(raw["venue_id"]), int(raw["owner_id"])
            duration = Decimal(str((datetime.combine(slot_date, end_time) - datetime.combine(slot_date, start_time)).total_seconds())) / Decimal("3600")
            if (slot_id not in slot_ids or price <= 0 or duration <= 0
                    or min(court_id, venue_id, owner_id) <= 0):
                raise ValueError
            by_id[slot_id] = {"time_slot_id": slot_id, "court_id": court_id, "venue_id": venue_id,
                              "owner_id": owner_id, "slot_date": slot_date, "start_time": start_time,
                              "end_time": end_time, "price_per_hour": price,
                              "total_amount": (price * duration).quantize(Decimal("0.01")),
                              "duration_minutes": int(duration * 60)}
        if set(by_id) != set(slot_ids):
            raise ValueError
        ordered = [by_id[value] for value in slot_ids]
        first = ordered[0]
        for prev, current in zip(ordered, ordered[1:]):
            if (current["court_id"] != first["court_id"] or current["slot_date"] != first["slot_date"]
                    or prev["end_time"] != current["start_time"]):
                raise HTTPException(status_code=409, detail="Selected time slots must be consecutive on the same court and date")
        total = sum((entry["total_amount"] for entry in ordered), Decimal("0.00")).quantize(Decimal("0.01"))
        return {"time_slot_id": first["time_slot_id"], "time_slot_ids": slot_ids,
                "court_id": first["court_id"], "venue_id": first["venue_id"], "owner_id": first["owner_id"],
                "slot_date": first["slot_date"], "start_time": first["start_time"],
                "end_time": ordered[-1]["end_time"], "duration_minutes": sum(x["duration_minutes"] for x in ordered),
                "total_amount": total, "slots": ordered}
    except HTTPException:
        raise
    except (KeyError, InvalidOperation, TypeError, ValueError):
        raise HTTPException(status_code=502, detail="Court service returned invalid slot data") from None


def _booking_quote(slot_ids: list[int]) -> dict:
    return _normalize_slot_quote(slot_ids, integrations.get_slot_quote(_integration_slot_argument(slot_ids)))


def _can_cancel(booking: Booking) -> bool:
    if booking.status == "PENDING":
        return booking.expires_at is not None and _as_utc(booking.expires_at) > datetime.now(timezone.utc)
    return (booking.status == "CONFIRMED" and booking.confirmed_at is not None
            and datetime.now(timezone.utc) <= _as_utc(booking.confirmed_at) + timedelta(minutes=30))


def _is_upcoming(booking: Booking) -> bool:
    if booking.status != "CONFIRMED" or booking.slot_date is None or booking.start_time is None:
        return False
    return datetime.combine(booking.slot_date, booking.start_time, tzinfo=BUSINESS_TIMEZONE) > datetime.now(BUSINESS_TIMEZONE)


def _complete_booking(db: Session, booking_id: int, owner_id: int) -> dict:
    booking = db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update())
    if booking is None or booking.owner_id != owner_id:
        raise HTTPException(status_code=404, detail="Booking not found for this owner")
    if booking.status == "COMPLETED":
        # Completion is already durable; retry the booking-scoped release.
        try:
            integrations.release_slot(_integration_slot_argument(_booking_slot_ids(booking)), booking.id)
        except HTTPException as error:
            if error.status_code != 409:
                raise
            # Court confirms this booking no longer owns the slot. Preserve any
            # newer reservation and return the already-durable completion.
        return {
            "booking_id": booking.id,
            "status": booking.status,
            "completed_at": booking.completed_at,
        }
    if booking.status != "CHECKED_IN":
        raise HTTPException(status_code=409, detail="Only checked-in bookings can be completed")
    booking.status = "COMPLETED"
    booking.completed_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Could not persist booking completion; retry completion") from None
    # Persist first so a Court outage cannot leave a reusable slot attached to a
    # CHECKED_IN booking. A repeated completion retries release.
    integrations.release_slot(_integration_slot_argument(_booking_slot_ids(booking)), booking.id)
    return {
        "booking_id": booking.id,
        "status": booking.status,
        "completed_at": booking.completed_at,
    }


def require_admin(principal: Principal) -> None:
    if principal.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")


def _paginate_admin_bookings(
    db: Session,
    query,
    page: int,
    page_size: int,
    order_by_checked_in: bool = False,
) -> AdminBookingListResponse:
    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(status_code=422, detail="Invalid pagination")
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    if order_by_checked_in:
        ordered = query.order_by(Booking.checked_in_at.desc(), Booking.id.desc())
    else:
        ordered = query.order_by(Booking.created_at.desc(), Booking.id.desc())
    items = list(
        db.scalars(ordered.offset((page - 1) * page_size).limit(page_size))
    )
    return AdminBookingListResponse(
        items=[AdminBookingResponse.model_validate(item) for item in items],
        total=int(total),
        page=page,
        page_size=page_size,
    )


@router.get("/admin/bookings/summary", response_model=BookingSummaryResponse, tags=["admin"])
def admin_booking_summary(
    db: Session = Depends(get_db),
    principal: Principal = Depends(current_principal),
) -> BookingSummaryResponse:
    require_admin(principal)
    total = db.scalar(select(func.count(Booking.id))) or 0
    checked_in = db.scalar(
        select(func.count(Booking.id)).where(Booking.status == "CHECKED_IN")
    ) or 0
    completed = db.scalar(
        select(func.count(Booking.id)).where(Booking.status == "COMPLETED")
    ) or 0
    return BookingSummaryResponse(
        bookings={
            "total": int(total),
            "checked_in": int(checked_in),
            "completed": int(completed),
        }
    )


@router.get("/admin/bookings", response_model=AdminBookingListResponse, tags=["admin"])
def admin_list_bookings(
    page: int = 1,
    page_size: int = 25,
    booking_id: Optional[int] = Query(default=None, gt=0),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    venue_id: Optional[int] = Query(default=None, gt=0),
    court_id: Optional[int] = Query(default=None, gt=0),
    owner_id: Optional[int] = Query(default=None, gt=0),
    user_id: Optional[int] = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    principal: Principal = Depends(current_principal),
) -> AdminBookingListResponse:
    require_admin(principal)
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must be before date_to")
    query = select(Booking)
    if booking_id is not None:
        query = query.where(Booking.id == booking_id)
    if status_filter is not None:
        query = query.where(Booking.status == status_filter)
    if date_from is not None:
        query = query.where(Booking.slot_date >= date_from)
    if date_to is not None:
        query = query.where(Booking.slot_date <= date_to)
    if venue_id is not None:
        query = query.where(Booking.venue_id == venue_id)
    if court_id is not None:
        query = query.where(Booking.court_id == court_id)
    if owner_id is not None:
        query = query.where(Booking.owner_id == owner_id)
    if user_id is not None:
        query = query.where(Booking.user_id == user_id)
    return _paginate_admin_bookings(db, query, page, page_size)


@router.get("/admin/bookings/{booking_id}", response_model=AdminBookingResponse, tags=["admin"])
def admin_get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(current_principal),
) -> Booking:
    require_admin(principal)
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.get("/admin/checkins", response_model=AdminBookingListResponse, tags=["admin"])
def admin_list_checkins(
    page: int = 1,
    page_size: int = 25,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    venue_id: Optional[int] = Query(default=None, gt=0),
    court_id: Optional[int] = Query(default=None, gt=0),
    checked_in_by: Optional[int] = Query(default=None, gt=0),
    booking_id: Optional[int] = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    principal: Principal = Depends(current_principal),
) -> AdminBookingListResponse:
    require_admin(principal)
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must be before date_to")
    query = select(Booking).where(Booking.checked_in_at.is_not(None))
    if date_from is not None:
        query = query.where(
            Booking.checked_in_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        )
    if date_to is not None:
        query = query.where(
            Booking.checked_in_at < datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
        )
    if venue_id is not None:
        query = query.where(Booking.venue_id == venue_id)
    if court_id is not None:
        query = query.where(Booking.court_id == court_id)
    if checked_in_by is not None:
        query = query.where(Booking.checked_in_by == checked_in_by)
    if booking_id is not None:
        query = query.where(Booking.id == booking_id)
    return _paginate_admin_bookings(db, query, page, page_size, order_by_checked_in=True)


@router.get("/owner/bookings", response_model=list[OwnerBookingResponse], tags=["owner"])
def list_owner_bookings(
    venue_id: Optional[int] = Query(default=None, gt=0),
    slot_date: Optional[date] = Query(default=None, alias="date"),
    booking_status: Optional[Literal["PENDING", "CONFIRMED", "CHECKED_IN", "COMPLETED", "CANCELLED", "FAILED", "EXPIRED"]] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(current_principal),
):
    require_owner(principal)
    query = select(Booking).where(Booking.owner_id == principal.user_id)
    if venue_id is not None:
        query = query.where(Booking.venue_id == venue_id)
    if slot_date is not None:
        query = query.where(Booking.slot_date == slot_date)
    bookings = list(db.scalars(query.order_by(Booking.created_at.desc())))
    if booking_status is not None:
        return [booking for booking in bookings if booking.status == booking_status]
    return bookings


@router.get("/owner/bookings/{booking_id}", response_model=OwnerBookingResponse, tags=["owner"])
def get_owner_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(current_principal),
):
    require_owner(principal)
    booking = db.get(Booking, booking_id)
    if booking is None or booking.owner_id != principal.user_id:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.post("/owner/bookings/{booking_id}/complete", response_model=OwnerBookingCompletionResponse, tags=["owner"])
def complete_owner_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(current_principal),
):
    require_owner(principal)
    return _complete_booking(db, booking_id, principal.user_id)


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

    try:
        slot_ids = payload.selected_slot_ids()
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    booking = Booking(
        user_id=principal.user_id,
        time_slot_id=slot_ids[0],
        status="PENDING",
        total_amount=Decimal("0.00"),
        expires_at=None,
    )
    db.add(booking)
    db.flush()
    booking.slot_links = [BookingTimeSlot(time_slot_id=slot_id, position=index) for index, slot_id in enumerate(slot_ids)]
    try:
        hold = integrations.hold_slot(_integration_slot_argument(slot_ids), booking.id)
        quote = _normalize_slot_quote(slot_ids, hold)
        expires_at = datetime.fromisoformat(hold["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if (
            quote["total_amount"] <= 0 or expires_at <= datetime.now(timezone.utc)
        ):
            raise ValueError("Court service returned an invalid slot price or duration")
        booking.total_amount = quote["total_amount"]
        booking.expires_at = expires_at
        booking.court_id = quote["court_id"]
        booking.venue_id = quote["venue_id"]
        booking.owner_id = quote["owner_id"]
        booking.slot_date = quote["slot_date"]
        booking.start_time = quote["start_time"]
        booking.end_time = quote["end_time"]
        db.commit()
    except (KeyError, InvalidOperation, TypeError, ValueError):
        db.rollback()
        try:
            integrations.release_slot(_integration_slot_argument(slot_ids), booking.id)
        except HTTPException:
            raise HTTPException(status_code=503, detail="Could not release slot after invalid Court response; retry cleanup") from None
        raise HTTPException(status_code=502, detail="Court service returned invalid slot data") from None
    except (HTTPException, SQLAlchemyError) as error:
        db.rollback()
        # The Court hold may have succeeded before the local booking commit failed.
        # Release is idempotent and booking-scoped, so retrying this cleanup is safe.
        try:
            integrations.release_slot(_integration_slot_argument(slot_ids), booking.id)
        except HTTPException:
            if isinstance(error, HTTPException):
                if error.status_code >= 500:
                    raise HTTPException(status_code=503, detail="Could not release slot after booking failure; retry cleanup") from None
                raise error
            raise HTTPException(status_code=503, detail="Could not release slot after booking failure") from None
        raise
    db.refresh(booking)
    return booking


@router.get("/booking-quotes/{slot_ids}", tags=["bookings"])
def get_booking_quote(
    slot_ids: str,
    principal: Principal = Depends(current_principal),
):
    require_customer(principal)
    try:
        ids = [int(value) for value in slot_ids.split(",")]
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid time slot IDs") from None
    if not ids or len(ids) > 24 or any(value <= 0 for value in ids) or len(set(ids)) != len(ids):
        raise HTTPException(status_code=422, detail="Time slot IDs must be unique positive IDs (up to 24)")
    return _booking_quote(ids)


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
    responses = []
    for booking in bookings:
        response = BookingResponse.model_validate(booking).model_copy(
            update={"can_cancel": _can_cancel(booking), "is_upcoming": _is_upcoming(booking)}
        )
        if booking.status != "CONFIRMED":
            response = response.model_copy(update={"qr_token": None})
        responses.append(response)
    return responses


@router.get("/bookings/{booking_id}", response_model=BookingResponse, tags=["bookings"])
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(current_principal),
):
    require_customer(principal)
    booking = _owned_booking(db, booking_id, principal)
    response = BookingResponse.model_validate(booking)
    response = response.model_copy(update={"can_cancel": _can_cancel(booking), "is_upcoming": _is_upcoming(booking)})
    if booking.status != "CONFIRMED":
        response = response.model_copy(update={"qr_token": None})
    return response


@router.post("/bookings/{booking_id}/cancel", response_model=BookingResponse, tags=["bookings"])
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(current_principal),
):
    require_customer(principal)
    booking = _owned_booking(db, booking_id, principal)
    if booking.status == "CONFIRMED":
        if booking.confirmed_at is None:
            raise HTTPException(status_code=409, detail="This legacy confirmed booking has no recorded confirmation time and cannot be cancelled")
        confirmed_at = _as_utc(booking.confirmed_at)
        if datetime.now(timezone.utc) > confirmed_at + timedelta(minutes=30):
            raise HTTPException(status_code=409, detail="The 30-minute cancellation period has expired")
    elif booking.status != "PENDING":
        raise HTTPException(status_code=409, detail="Only pending or recently confirmed bookings can be cancelled")
    booking.status = "CANCELLED"
    booking.qr_token = None
    if booking.expires_at is None:
        booking.expires_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Could not persist booking cancellation") from None
    _finish_expiration_release(booking, db)
    db.refresh(booking)
    return booking


@router.post("/internal/bookings/{booking_id}/fail", tags=["internal"])
def fail_booking(
    booking_id: int,
    x_internal_token: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    require_internal_token(x_internal_token)
    booking = db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update())
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status == "FAILED":
        if booking.expires_at is not None:
            _finish_expiration_release(booking, db)
        return {"booking_id": booking.id, "status": booking.status}
    if booking.status != "PENDING":
        raise HTTPException(status_code=409, detail="Booking cannot be failed")
    booking.status = "FAILED"
    if booking.expires_at is None:
        booking.expires_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Could not persist booking failure") from None
    _finish_expiration_release(booking, db)
    return {"booking_id": booking.id, "status": booking.status}


@router.get("/internal/bookings/{booking_id}/payment-context", tags=["internal"])
def payment_context(
    booking_id: int,
    x_internal_token: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    require_internal_token(x_internal_token)
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    _expire_if_needed(booking, db)
    if booking.status == "PENDING" and booking.expires_at is None:
        raise HTTPException(status_code=409, detail="Booking has no active slot hold")
    return PaymentContext(
        booking_id=booking.id,
        user_id=booking.user_id,
        status=booking.status,
        total_amount=booking.total_amount,
        expires_at=booking.expires_at,
        qr_token=booking.qr_token if booking.status == "CONFIRMED" else None,
    )


@router.post("/internal/bookings/{booking_id}/confirm", tags=["internal"])
def confirm_booking(
    booking_id: int,
    x_internal_token: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    require_internal_token(x_internal_token)
    booking = db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update())
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    _expire_if_needed(booking, db)
    if booking.status == "CONFIRMED":
        return {
            "booking_id": booking.id,
            "status": booking.status,
            "qr_token": booking.qr_token,
            "confirmed_at": booking.confirmed_at,
        }
    if booking.status != "PENDING":
        raise HTTPException(status_code=409, detail="Booking cannot be confirmed")
    integrations.confirm_slot(_integration_slot_argument(_booking_slot_ids(booking)), booking.id)
    booking.status = "CONFIRMED"
    booking.confirmed_at = datetime.now(timezone.utc)
    booking.expires_at = None
    booking.qr_token = secrets.token_urlsafe(32)
    db.commit()
    return {"booking_id": booking.id, "status": booking.status, "qr_token": booking.qr_token,
            "confirmed_at": booking.confirmed_at}


@router.post("/internal/bookings/check-in", tags=["internal"])
def check_in_booking(
    payload: BookingCheckIn,
    x_internal_token: Optional[str] = Header(default=None),
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
        "user_id": booking.user_id,
        "venue_id": booking.venue_id,
        "court_id": booking.court_id,
        "slot_date": booking.slot_date,
        "start_time": booking.start_time,
        "end_time": booking.end_time,
        "total_amount": booking.total_amount,
    }


@router.post("/internal/bookings/{booking_id}/complete", tags=["internal"])
def complete_booking(
    booking_id: int,
    payload: BookingCompletion,
    x_internal_token: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    require_internal_token(x_internal_token)
    return _complete_booking(db, booking_id, payload.owner_id)


@router.post("/internal/bookings/expire", tags=["internal"])
def expire_bookings(
    x_internal_token: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    require_internal_token(x_internal_token)
    now = datetime.now(timezone.utc)
    candidates = list(db.scalars(
        select(Booking).where(
            (
                (Booking.status == "PENDING")
                & Booking.expires_at.is_not(None)
                & (Booking.expires_at <= now)
            )
            | ((Booking.status.in_(["EXPIRED", "FAILED", "CANCELLED"])) & Booking.expires_at.is_not(None))
        ).with_for_update()
    ))
    expired = 0
    released = 0
    for booking in candidates:
        if booking.status == "PENDING":
            booking.status = "EXPIRED"
            try:
                db.commit()
            except SQLAlchemyError:
                db.rollback()
                continue
            expired += 1
        try:
            was_released = _finish_expiration_release(booking, db)
        except HTTPException:
            db.rollback()
            # EXPIRED remains durable and is retried by this job. A 409 protects
            # any newer booking currently holding/booked on the slot.
            continue
        if was_released:
            released += 1
    return {"expired": expired, "released": released}

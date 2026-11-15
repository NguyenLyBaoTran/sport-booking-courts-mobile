import secrets
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import integrations
from app.auth import Principal, current_principal, require_customer
from app.database import get_db
from app.models import Payment
from app.schemas import (
    PaymentProcess,
    PaymentProcessResponse,
    PaymentReport,
    PaymentReportPage,
    PaymentReportResponse,
    PaymentReportSummary,
    PaymentResponse,
    RevenuePoint,
)

router = APIRouter()
CENT = Decimal("0.01")


def _response(payment: Payment, booking: dict | None = None):
    return PaymentProcessResponse(
        id=payment.id,
        booking_id=payment.booking_id,
        status=payment.status,
        amount=payment.amount,
        transaction_code=payment.transaction_code,
        created_at=payment.created_at,
        paid_at=payment.paid_at,
        booking_status=booking.get("status") if booking else None,
        qr_token=booking.get("qr_token") if booking else payment.qr_token,
    )


@router.post(
    "/payments/process",
    response_model=PaymentProcessResponse,
    tags=["payments"],
)
def process_payment(
    payload: PaymentProcess,
    db: Session = Depends(get_db),
    principal: Principal = Depends(current_principal),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    require_customer(principal)
    if idempotency_key is not None and not 1 <= len(idempotency_key) <= 100:
        raise HTTPException(status_code=422, detail="Idempotency-Key must be 1-100 characters")

    paid = db.scalar(
        select(Payment).where(Payment.successful_booking_id == payload.booking_id)
    )
    if paid is not None:
        if paid.user_id != principal.user_id:
            raise HTTPException(status_code=404, detail="Booking not found")
        context = integrations.get_payment_context(payload.booking_id)
        if int(context["user_id"]) != principal.user_id:
            raise HTTPException(status_code=404, detail="Booking not found")
        return _response(paid, {
            "status": context["status"],
            "qr_token": context.get("qr_token") if context["status"] == "CONFIRMED" else None,
        })

    context = integrations.get_payment_context(payload.booking_id)
    if int(context["user_id"]) != principal.user_id:
        raise HTTPException(status_code=404, detail="Booking not found")
    if context["status"] not in {"PENDING", "CONFIRMED"}:
        raise HTTPException(status_code=409, detail="Booking is not payable")

    key = idempotency_key or secrets.token_urlsafe(24)
    attempt = db.scalar(select(Payment).where(Payment.idempotency_key == key))
    if attempt is not None:
        if attempt.booking_id != payload.booking_id or attempt.user_id != principal.user_id:
            raise HTTPException(status_code=409, detail="Idempotency-Key already used")
        if attempt.status == "FAILED":
            return _response(attempt)
    else:
        attempt = Payment(
            booking_id=payload.booking_id,
            user_id=principal.user_id,
            provider="MOCK",
            status="PENDING",
            amount=context["total_amount"],
            idempotency_key=key,
        )
        db.add(attempt)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            attempt = db.scalar(select(Payment).where(Payment.idempotency_key == key))
            if attempt is None:
                raise HTTPException(status_code=409, detail="Payment request conflict") from None
    if attempt.booking_id != payload.booking_id or attempt.user_id != principal.user_id:
        raise HTTPException(status_code=409, detail="Idempotency-Key already used")

    if payload.mock_result == "FAILED":
        integrations.fail_booking(payload.booking_id)
        attempt.status = "FAILED"
        db.commit()
        db.refresh(attempt)
        return _response(attempt)

    booking = integrations.confirm_booking(payload.booking_id)
    if booking.get("status") != "CONFIRMED" or not booking.get("qr_token"):
        raise HTTPException(status_code=502, detail="Booking service returned an invalid confirmation")
    attempt.status = "PAID"
    attempt.successful_booking_id = payload.booking_id
    if attempt.paid_at is None:
        attempt.paid_at = datetime.now(timezone.utc)
    attempt.qr_token = booking["qr_token"]
    attempt.transaction_code = f"MOCK-{secrets.token_hex(12)}"
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        paid = db.scalar(
            select(Payment).where(Payment.successful_booking_id == payload.booking_id)
        )
        if paid is None:
            raise HTTPException(status_code=409, detail="Payment confirmation conflict") from None
        return _response(paid, booking)
    db.refresh(attempt)
    return _response(attempt, booking)


@router.get("/payments", response_model=list[PaymentResponse], tags=["payments"])
def list_payments(
    db: Session = Depends(get_db),
    principal: Principal = Depends(current_principal),
):
    require_customer(principal)
    return list(
        db.scalars(
            select(Payment)
            .where(Payment.user_id == principal.user_id)
            .order_by(Payment.created_at.desc())
        )
    )


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _inside_range(
    value: datetime | None,
    date_from: date | None,
    date_to: date | None,
    report_timezone: ZoneInfo,
) -> bool:
    if value is None:
        return date_from is None and date_to is None
    day = _as_utc(value).astimezone(report_timezone).date()
    return (date_from is None or day >= date_from) and (date_to is None or day <= date_to)


def _payment_report_context(booking_ids: list[int]) -> dict[int, dict]:
    contexts: dict[int, dict] = {}
    for start in range(0, len(booking_ids), 500):
        batch = booking_ids[start : start + 500]
        response = integrations.get_payment_report_context(batch)
        try:
            items = response["bookings"]
            for item in items:
                booking_id = int(item["booking_id"])
                if booking_id not in batch or booking_id in contexts:
                    raise ValueError
                contexts[booking_id] = item
        except (KeyError, TypeError, ValueError):
            raise HTTPException(status_code=502, detail="Booking service returned invalid reporting data") from None
    return contexts


@router.get("/payments/report", response_model=PaymentReport, tags=["payment-reporting"])
def payment_report(
    date_from: date | None = None,
    date_to: date | None = None,
    timezone_name: str = Query(default="UTC", alias="timezone"),
    group_by: Literal["day", "month"] = "day",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: Literal["asc", "desc"] = "desc",
    db: Session = Depends(get_db),
    principal: Principal = Depends(current_principal),
) -> PaymentReport:
    if principal.role not in {"OWNER", "ADMIN"}:
        raise HTTPException(status_code=403, detail="Owner or Admin account required")
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must be on or before date_to")
    try:
        report_timezone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(status_code=422, detail="timezone must be a valid IANA time zone") from None

    all_payments = list(db.scalars(select(Payment)))
    booking_contexts: dict[int, dict] = {}
    if principal.role == "OWNER":
        booking_contexts = _payment_report_context(sorted({payment.booking_id for payment in all_payments})) if all_payments else {}
        all_payments = [
            payment for payment in all_payments
            if booking_contexts.get(payment.booking_id, {}).get("owner_id") == principal.user_id
        ]

    undated_paid = [payment for payment in all_payments if payment.status == "PAID" and payment.paid_at is None]
    filtered: list[Payment] = []
    for payment in all_payments:
        effective_date = payment.paid_at if payment.status == "PAID" else payment.created_at
        if _inside_range(effective_date, date_from, date_to, report_timezone):
            filtered.append(payment)

    paid = [payment for payment in filtered if payment.status == "PAID"]
    pending = [payment for payment in filtered if payment.status == "PENDING"]
    failed = [payment for payment in filtered if payment.status == "FAILED"]
    total_revenue = sum((payment.amount for payment in paid), Decimal("0.00"))
    total_revenue = total_revenue.quantize(CENT)

    buckets: dict[str, list] = defaultdict(lambda: [Decimal("0.00"), 0])
    for payment in paid:
        payment_date = _as_utc(payment.paid_at)
        if payment_date is None:
            continue
        bucket = payment_date.astimezone(report_timezone).strftime("%Y-%m" if group_by == "month" else "%Y-%m-%d")
        buckets[bucket][0] += payment.amount
        buckets[bucket][1] += 1
    revenue_series = [
        RevenuePoint(bucket=bucket, revenue=values[0].quantize(CENT), successful_payments=values[1])
        for bucket, values in sorted(buckets.items())
    ]

    def payment_timestamp(payment: Payment) -> datetime | None:
        return _as_utc(payment.paid_at if payment.status == "PAID" else payment.created_at)

    dated_transactions = [item for item in filtered if payment_timestamp(item) is not None]
    undated_transactions = [item for item in filtered if payment_timestamp(item) is None]
    dated_transactions.sort(key=lambda item: (payment_timestamp(item), item.id), reverse=sort == "desc")
    undated_transactions.sort(key=lambda item: item.id, reverse=sort == "desc")
    filtered = dated_transactions + undated_transactions
    total = len(filtered)
    page_items = filtered[(page - 1) * page_size : page * page_size]
    report_items = []
    for payment in page_items:
        booking = booking_contexts.get(payment.booking_id, {})
        report_items.append(PaymentReportResponse(
            payment_id=payment.id,
            booking_id=payment.booking_id,
            provider=payment.provider,
            booking_status=booking.get("status"),
            venue_id=booking.get("venue_id"),
            court_id=booking.get("court_id"),
            status=payment.status,
            amount=payment.amount,
            transaction_code=payment.transaction_code,
            payment_date=payment.paid_at if payment.status == "PAID" else payment.created_at,
            created_at=payment.created_at,
        ))

    return PaymentReport(
        date_from=date_from,
        date_to=date_to,
        timezone=timezone_name,
        group_by=group_by,
        sort=sort,
        summary=PaymentReportSummary(
            total_revenue=total_revenue,
            successful_payments=len(paid),
            pending_payments=len(pending),
            failed_payments=len(failed),
            total_transactions=total,
            undated_successful_payments=len(undated_paid),
            undated_successful_amount=sum((payment.amount for payment in undated_paid), Decimal("0.00")).quantize(CENT),
        ),
        revenue_series=revenue_series,
        transactions=PaymentReportPage(items=report_items, total=total, page=page, page_size=page_size),
    )


@router.get("/payments/{payment_id}", response_model=PaymentResponse, tags=["payments"])
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(current_principal),
):
    require_customer(principal)
    payment = db.get(Payment, payment_id)
    if payment is None or payment.user_id != principal.user_id:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment

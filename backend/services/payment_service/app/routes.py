import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import integrations
from app.auth import Principal, current_principal
from app.database import get_db
from app.models import Payment
from app.schemas import PaymentProcess, PaymentProcessResponse, PaymentResponse

router = APIRouter()


def _response(payment: Payment, booking: dict | None = None):
    return PaymentProcessResponse(
        id=payment.id,
        booking_id=payment.booking_id,
        status=payment.status,
        amount=payment.amount,
        transaction_code=payment.transaction_code,
        created_at=payment.created_at,
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
    if idempotency_key is not None and not 1 <= len(idempotency_key) <= 100:
        raise HTTPException(status_code=422, detail="Idempotency-Key must be 1-100 characters")

    paid = db.scalar(
        select(Payment).where(Payment.successful_booking_id == payload.booking_id)
    )
    if paid is not None:
        if paid.user_id != principal.user_id:
            raise HTTPException(status_code=404, detail="Booking not found")
        return _response(paid, {"status": "CONFIRMED"})

    context = integrations.get_payment_context(payload.booking_id)
    if int(context["user_id"]) != principal.user_id:
        raise HTTPException(status_code=404, detail="Booking not found")

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
        attempt.status = "FAILED"
        db.commit()
        db.refresh(attempt)
        return _response(attempt)

    booking = integrations.confirm_booking(payload.booking_id)
    if booking.get("status") != "CONFIRMED" or not booking.get("qr_token"):
        raise HTTPException(status_code=502, detail="Booking service returned an invalid confirmation")
    attempt.status = "PAID"
    attempt.successful_booking_id = payload.booking_id
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
    return list(
        db.scalars(
            select(Payment)
            .where(Payment.user_id == principal.user_id)
            .order_by(Payment.created_at.desc())
        )
    )


@router.get("/payments/{payment_id}", response_model=PaymentResponse, tags=["payments"])
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(current_principal),
):
    payment = db.get(Payment, payment_id)
    if payment is None or payment.user_id != principal.user_id:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment
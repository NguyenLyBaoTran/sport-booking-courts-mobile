from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class BookingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    time_slot_id: int = Field(gt=0)


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    time_slot_id: int
    court_id: int
    venue_id: int
    slot_date: date
    start_time: time
    end_time: time
    status: str
    total_amount: Decimal
    expires_at: datetime | None
    qr_token: str | None
    created_at: datetime


class PaymentContext(BaseModel):
    booking_id: int
    user_id: int
    status: str
    total_amount: Decimal
    expires_at: datetime | None


class BookingCheckIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_id: int = Field(gt=0)
    qr_token: str = Field(min_length=32, max_length=128)


class BookingCompletion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_id: int = Field(gt=0)
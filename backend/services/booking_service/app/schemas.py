from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BookingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    time_slot_id: int | None = Field(default=None, gt=0)
    time_slot_ids: list[int] | None = Field(default=None, min_length=1, max_length=24)

    @model_validator(mode="after")
    def require_one_slot_selection_shape(self):
        if self.time_slot_id is not None and self.time_slot_ids is not None:
            raise ValueError("Provide time_slot_id or time_slot_ids, not both")
        if self.time_slot_id is None and self.time_slot_ids is None:
            raise ValueError("A time slot selection is required")
        if self.time_slot_ids is not None and len(set(self.time_slot_ids)) != len(self.time_slot_ids):
            raise ValueError("time_slot_ids must contain unique slot IDs")
        return self

    def selected_slot_ids(self) -> list[int]:
        values = self.time_slot_ids if self.time_slot_ids is not None else ([self.time_slot_id] if self.time_slot_id else [])
        if not values or any(value <= 0 for value in values) or len(set(values)) != len(values):
            raise ValueError("time_slot_ids must contain unique positive slot IDs")
        return values


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    time_slot_id: int
    time_slot_ids: list[int] = Field(default_factory=list)
    court_id: int
    venue_id: int
    slot_date: date
    start_time: time
    end_time: time
    status: str
    total_amount: Decimal
    expires_at: Optional[datetime]
    confirmed_at: Optional[datetime]
    qr_token: Optional[str]
    can_cancel: bool = False
    is_upcoming: bool = False
    created_at: datetime


class OwnerBookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    time_slot_id: int
    time_slot_ids: list[int] = Field(default_factory=list)
    court_id: int
    venue_id: int
    slot_date: date
    start_time: time
    end_time: time
    status: str
    total_amount: Decimal
    expires_at: Optional[datetime]
    confirmed_at: Optional[datetime]
    checked_in_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime


class OwnerBookingCompletionResponse(BaseModel):
    booking_id: int
    status: str
    completed_at: datetime


class PaymentContext(BaseModel):
    booking_id: int
    user_id: int
    status: str
    total_amount: Decimal
    expires_at: Optional[datetime]
    qr_token: Optional[str] = None


class BookingCheckIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_id: int = Field(gt=0)
    qr_token: str = Field(min_length=32, max_length=128)


class BookingCompletion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_id: int = Field(gt=0)


class AdminBookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    time_slot_id: int
    time_slot_ids: list[int] = Field(default_factory=list)
    court_id: Optional[int]
    venue_id: Optional[int]
    owner_id: Optional[int]
    slot_date: Optional[date]
    start_time: Optional[time]
    end_time: Optional[time]
    status: str
    total_amount: Decimal
    expires_at: Optional[datetime]
    confirmed_at: Optional[datetime]
    checked_in_by: Optional[int]
    checked_in_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime


class AdminBookingListResponse(BaseModel):
    items: list[AdminBookingResponse]
    total: int
    page: int
    page_size: int


class BookingSummaryResponse(BaseModel):
    bookings: dict[str, int]

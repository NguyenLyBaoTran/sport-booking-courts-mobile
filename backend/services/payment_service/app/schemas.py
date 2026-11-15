from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_serializer


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class MockResult(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class PaymentProcess(BaseModel):
    model_config = ConfigDict(extra="forbid")

    booking_id: int = Field(gt=0)
    mock_result: MockResult = MockResult.SUCCESS


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_id: int
    status: str
    amount: Decimal
    transaction_code: str | None
    created_at: datetime
    paid_at: datetime | None = None

    @field_serializer("created_at", "paid_at")
    def serialize_utc_timestamps(self, value: datetime | None) -> datetime | None:
        return _as_utc(value)


class PaymentProcessResponse(PaymentResponse):
    booking_status: str | None = None
    qr_token: str | None = None


class PaymentReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment_id: int
    booking_id: int
    provider: str
    booking_status: str | None = None
    venue_id: int | None = None
    court_id: int | None = None
    status: str
    amount: Decimal
    transaction_code: str | None
    payment_date: datetime | None
    created_at: datetime

    @field_serializer("payment_date", "created_at")
    def serialize_utc_timestamps(self, value: datetime | None) -> datetime | None:
        return _as_utc(value)


class RevenuePoint(BaseModel):
    bucket: str
    revenue: Decimal
    successful_payments: int


class PaymentReportSummary(BaseModel):
    total_revenue: Decimal
    successful_payments: int
    pending_payments: int
    failed_payments: int
    total_transactions: int
    undated_successful_payments: int
    undated_successful_amount: Decimal


class PaymentReportPage(BaseModel):
    items: list[PaymentReportResponse]
    total: int
    page: int
    page_size: int


class PaymentReport(BaseModel):
    date_from: date | None
    date_to: date | None
    timezone: str = "UTC"
    group_by: str
    sort: str
    summary: PaymentReportSummary
    revenue_series: list[RevenuePoint]
    transactions: PaymentReportPage

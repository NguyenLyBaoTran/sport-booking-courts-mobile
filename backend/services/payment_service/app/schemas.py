from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


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


class PaymentProcessResponse(PaymentResponse):
    booking_status: str | None = None
    qr_token: str | None = None
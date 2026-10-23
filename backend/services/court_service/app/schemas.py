from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SportInput(InputModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value


class SportOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None
    is_active: bool


class VenueInput(InputModel):
    owner_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=200)
    address: str = Field(min_length=1, max_length=255)
    description: str | None = None
    phone: str | None = Field(default=None, max_length=20)
    is_active: bool = True

    @field_validator("name", "address")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class VenueOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    owner_id: int
    name: str
    address: str
    description: str | None
    phone: str | None
    is_active: bool
    created_at: datetime


class CourtInput(InputModel):
    venue_id: int = Field(gt=0)
    sport_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    price_per_hour: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value


class CourtOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    venue_id: int
    sport_id: int
    name: str
    description: str | None
    price_per_hour: Decimal
    is_active: bool


class TimeSlotInput(InputModel):
    court_id: int = Field(gt=0)
    slot_date: date
    start_time: time
    end_time: time
    is_active: bool = True

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be earlier than end_time")
        return self


class TimeSlotOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    court_id: int
    slot_date: date
    start_time: time
    end_time: time
    is_active: bool

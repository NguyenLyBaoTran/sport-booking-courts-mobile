from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from app.database import Base


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    time_slot_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    court_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    venue_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    owner_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    slot_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    qr_token: Mapped[Optional[str]] = mapped_column(String(128), unique=True)
    checked_in_by: Mapped[Optional[int]] = mapped_column(Integer)
    checked_in_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
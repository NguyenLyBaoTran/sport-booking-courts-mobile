from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Sport(Base):
    __tablename__ = "sports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )

    courts: Mapped[list[Court]] = relationship(back_populates="sport")


class Venue(Base):
    __tablename__ = "venues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Logical reference to users.id in User Service; there is no cross-database FK.
    owner_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    courts: Mapped[list[Court]] = relationship(back_populates="venue")


class Court(Base):
    __tablename__ = "courts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    venue_id: Mapped[int] = mapped_column(
        ForeignKey("venues.id"), nullable=False
    )
    sport_id: Mapped[int] = mapped_column(
        ForeignKey("sports.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_per_hour: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )

    venue: Mapped[Venue] = relationship(back_populates="courts")
    sport: Mapped[Sport] = relationship(back_populates="courts")
    time_slots: Mapped[list[TimeSlot]] = relationship(back_populates="court")


class TimeSlot(Base):
    __tablename__ = "time_slots"
    __table_args__ = (
        UniqueConstraint(
            "court_id",
            "slot_date",
            "start_time",
            "end_time",
            name="uq_time_slots_court_date_start_end",
        ),
        Index("ix_time_slots_reservation_expiry", "reservation_status", "reservation_expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    court_id: Mapped[int] = mapped_column(ForeignKey("courts.id"), nullable=False)
    slot_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )
    reservation_status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="AVAILABLE", server_default="AVAILABLE"
    )
    reservation_booking_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reservation_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    court: Mapped[Court] = relationship(back_populates="time_slots")

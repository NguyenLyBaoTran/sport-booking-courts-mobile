"""Seed development/demo data for the Court Service without overwriting rows."""

import argparse
import os
import sys
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError


BACKEND_ROOT = Path(__file__).resolve().parents[1]
COURT_SERVICE_ROOT = BACKEND_ROOT / "services" / "court_service"
sys.path.insert(0, str(COURT_SERVICE_ROOT))
load_dotenv(BACKEND_ROOT / ".env")

from app.database import SessionLocal, engine  # noqa: E402
from app.models import Court, Sport, TimeSlot, Venue  # noqa: E402


SPORT_SEEDS = [
    ("Badminton", "Demo sport"),
    ("Football", "Demo sport"),
    ("Pickleball", "Demo sport"),
]

VENUE_SEEDS = [
    {
        "name": "Demo Sports Center A",
        "address": "Địa chỉ giả định, Phường 1, Quận 1, TP. Hồ Chí Minh",
        "phone": "0900000001",
    },
    {
        "name": "Demo Sports Center B",
        "address": "Địa chỉ giả định, Phường 7, Quận 3, TP. Hồ Chí Minh",
        "phone": "0900000002",
    },
]

COURT_SEEDS = [
    ("Badminton", "Badminton Court 1", "120000.00"),
    ("Football", "Football Court 1", "500000.00"),
    ("Pickleball", "Pickleball Court 1", "150000.00"),
    ("Badminton", "Badminton Court 2", "120000.00"),
    ("Football", "Football Court 2", "500000.00"),
    ("Pickleball", "Pickleball Court 2", "150000.00"),
]

SLOT_TIMES = [
    (time(8), time(9)),
    (time(9), time(10)),
    (time(17), time(18)),
    (time(18), time(19)),
    (time(19), time(20)),
]


def positive_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed Court Service development/demo data.")
    parser.add_argument(
        "--owner-id",
        type=positive_integer,
        default=os.getenv("DEMO_OWNER_ID") or None,
        help="S1-confirmed OWNER user ID (or set DEMO_OWNER_ID in backend/.env).",
    )
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        default=date.today(),
        metavar="YYYY-MM-DD",
        help="First date for the seven-day time-slot schedule (defaults to today).",
    )
    args = parser.parse_args()
    if args.owner_id is None:
        parser.error("provide an S1-confirmed --owner-id or set DEMO_OWNER_ID; no data was written")
    if engine is None:
        parser.error("COURT_DATABASE_URL is not configured; no data was written")
    if engine.url.database != "sports_court_db":
        parser.error("COURT_DATABASE_URL must target sports_court_db; no data was written")
    return args


def get_or_create_sports(db) -> tuple[dict[str, Sport], int, int]:
    sports: dict[str, Sport] = {}
    created = 0
    existing = 0
    for name, description in SPORT_SEEDS:
        sport = db.scalar(select(Sport).where(Sport.name == name))
        if sport is None:
            sport = Sport(name=name, description=description, is_active=True)
            db.add(sport)
            db.flush()
            created += 1
        else:
            if not sport.is_active:
                raise ValueError(f"Seed sport {name!r} already exists but is inactive; it was not changed.")
            existing += 1
        sports[name] = sport
    return sports, created, existing


def get_or_create_venues(db, owner_id: int) -> tuple[list[Venue], int, int]:
    venues: list[Venue] = []
    created = 0
    existing = 0
    for seed in VENUE_SEEDS:
        matches = db.scalars(select(Venue).where(Venue.name == seed["name"])).all()
        if len(matches) > 1:
            raise ValueError(f"Multiple venues named {seed['name']!r} exist; no rows were changed.")
        if matches:
            venue = matches[0]
            if venue.owner_id != owner_id or venue.address != seed["address"]:
                raise ValueError(
                    f"Venue {seed['name']!r} exists with a different owner or address; "
                    "it was not changed."
                )
            if not venue.is_active:
                raise ValueError(f"Venue {seed['name']!r} is inactive; it was not changed.")
            existing += 1
        else:
            venue = Venue(
                owner_id=owner_id,
                name=seed["name"],
                address=seed["address"],
                description="Development/demo venue; address is fictitious.",
                phone=seed["phone"],
                is_active=True,
                created_at=datetime.utcnow(),
            )
            db.add(venue)
            db.flush()
            created += 1
        venues.append(venue)
    return venues, created, existing


def get_or_create_courts(
    db, venues: list[Venue], sports: dict[str, Sport]
) -> tuple[list[Court], int, int]:
    courts: list[Court] = []
    created = 0
    existing = 0
    for venue_index, venue in enumerate(venues):
        for sport_name, name, price in COURT_SEEDS[venue_index * 3 : venue_index * 3 + 3]:
            sport = sports[sport_name]
            court = db.scalar(
                select(Court).where(
                    Court.venue_id == venue.id,
                    Court.sport_id == sport.id,
                    Court.name == name,
                )
            )
            expected_price = Decimal(price)
            if court is None:
                court = Court(
                    venue_id=venue.id,
                    sport_id=sport.id,
                    name=name,
                    description="Development/demo court.",
                    price_per_hour=expected_price,
                    is_active=True,
                )
                db.add(court)
                db.flush()
                created += 1
            else:
                if court.price_per_hour != expected_price or not court.is_active:
                    raise ValueError(
                        f"Court {name!r} differs from the seed definition; it was not changed."
                    )
                existing += 1
            courts.append(court)
    return courts, created, existing


def seed_time_slots(db, courts: list[Court], start_date: date) -> tuple[int, int]:
    created = 0
    existing = 0
    for day_offset in range(7):
        slot_date = start_date + timedelta(days=day_offset)
        for court in courts:
            for start_time, end_time in SLOT_TIMES:
                exact = db.scalar(
                    select(TimeSlot).where(
                        TimeSlot.court_id == court.id,
                        TimeSlot.slot_date == slot_date,
                        TimeSlot.start_time == start_time,
                        TimeSlot.end_time == end_time,
                    )
                )
                if exact is not None:
                    existing += 1
                    continue

                overlap = db.scalar(
                    select(TimeSlot.id).where(
                        TimeSlot.court_id == court.id,
                        TimeSlot.slot_date == slot_date,
                        TimeSlot.is_active.is_(True),
                        TimeSlot.start_time < end_time,
                        TimeSlot.end_time > start_time,
                    )
                )
                if overlap is not None:
                    raise ValueError(
                        f"An active time slot overlaps court {court.id} on {slot_date}; "
                        "the transaction was rolled back."
                    )
                db.add(
                    TimeSlot(
                        court_id=court.id,
                        slot_date=slot_date,
                        start_time=start_time,
                        end_time=end_time,
                        is_active=True,
                    )
                )
                created += 1
    db.flush()
    return created, existing


def main() -> int:
    args = parse_args()
    try:
        with SessionLocal() as db:
            with db.begin():
                sports, sports_created, sports_existing = get_or_create_sports(db)
                venues, venues_created, venues_existing = get_or_create_venues(db, args.owner_id)
                courts, courts_created, courts_existing = get_or_create_courts(db, venues, sports)
                slots_created, slots_existing = seed_time_slots(db, courts, args.start_date)
    except (SQLAlchemyError, ValueError) as error:
        if isinstance(error, SQLAlchemyError):
            print(f"Seed failed ({type(error).__name__}); no changes were committed.", file=sys.stderr)
        else:
            print(f"Seed failed: {error}", file=sys.stderr)
        return 1

    print(f"Demo Owner ID: {args.owner_id}")
    print(f"Time-slot date range: {args.start_date} through {args.start_date + timedelta(days=6)}")
    print(f"Sports: {sports_created} created, {sports_existing} reused")
    print(f"Venues: {venues_created} created, {venues_existing} reused")
    print(f"Courts: {courts_created} created, {courts_existing} reused")
    print(f"Time slots: {slots_created} created, {slots_existing} reused")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

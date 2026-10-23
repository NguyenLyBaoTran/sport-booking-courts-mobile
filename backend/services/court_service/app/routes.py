from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Court, Sport, TimeSlot, Venue
from app.schemas import (
    CourtInput,
    CourtOutput,
    SportInput,
    SportOutput,
    TimeSlotInput,
    TimeSlotOutput,
    VenueInput,
    VenueOutput,
)

router = APIRouter(prefix="/api/v1")


def require_write_access():
    """Placeholder until S1 JWT and OWNER/ADMIN authorization are integrated."""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Write API authentication integration is pending",
    )


def get_or_404(db: Session, model, object_id: int, label: str):
    item = db.get(model, object_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return item


def commit_or_conflict(db: Session, detail: str = "Conflicting data") -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=detail) from None
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database operation failed") from None


@router.get("/sports", response_model=list[SportOutput])
def list_sports(is_active: bool | None = None, db: Session = Depends(get_db)):
    query = select(Sport)
    if is_active is not None:
        query = query.where(Sport.is_active == is_active)
    return db.scalars(query.order_by(Sport.id)).all()


@router.get("/sports/{sport_id}", response_model=SportOutput)
def read_sport(sport_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Sport, sport_id, "Sport")


@router.post("/sports", response_model=SportOutput, status_code=201, dependencies=[Depends(require_write_access)])
def create_sport(data: SportInput, db: Session = Depends(get_db)):
    sport = Sport(**data.model_dump())
    db.add(sport)
    commit_or_conflict(db, "Sport name already exists")
    db.refresh(sport)
    return sport


@router.put("/sports/{sport_id}", response_model=SportOutput, dependencies=[Depends(require_write_access)])
def update_sport(sport_id: int, data: SportInput, db: Session = Depends(get_db)):
    sport = get_or_404(db, Sport, sport_id, "Sport")
    for key, value in data.model_dump().items():
        setattr(sport, key, value)
    commit_or_conflict(db, "Sport name already exists")
    db.refresh(sport)
    return sport


@router.delete("/sports/{sport_id}", status_code=204, dependencies=[Depends(require_write_access)])
def delete_sport(sport_id: int, db: Session = Depends(get_db)):
    sport = get_or_404(db, Sport, sport_id, "Sport")
    sport.is_active = False
    commit_or_conflict(db)
    return Response(status_code=204)


@router.get("/venues", response_model=list[VenueOutput])
def list_venues(
    owner_id: int | None = Query(default=None, gt=0),
    is_active: bool | None = None,
    db: Session = Depends(get_db),
):
    query = select(Venue)
    if owner_id is not None:
        query = query.where(Venue.owner_id == owner_id)
    if is_active is not None:
        query = query.where(Venue.is_active == is_active)
    return db.scalars(query.order_by(Venue.id)).all()


@router.get("/venues/{venue_id}", response_model=VenueOutput)
def read_venue(venue_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Venue, venue_id, "Venue")


@router.post("/venues", response_model=VenueOutput, status_code=201, dependencies=[Depends(require_write_access)])
def create_venue(data: VenueInput, db: Session = Depends(get_db)):
    venue = Venue(**data.model_dump(), created_at=datetime.utcnow())
    db.add(venue)
    commit_or_conflict(db)
    db.refresh(venue)
    return venue


@router.put("/venues/{venue_id}", response_model=VenueOutput, dependencies=[Depends(require_write_access)])
def update_venue(venue_id: int, data: VenueInput, db: Session = Depends(get_db)):
    venue = get_or_404(db, Venue, venue_id, "Venue")
    for key, value in data.model_dump().items():
        setattr(venue, key, value)
    commit_or_conflict(db)
    db.refresh(venue)
    return venue


@router.delete("/venues/{venue_id}", status_code=204, dependencies=[Depends(require_write_access)])
def delete_venue(venue_id: int, db: Session = Depends(get_db)):
    venue = get_or_404(db, Venue, venue_id, "Venue")
    venue.is_active = False
    commit_or_conflict(db)
    return Response(status_code=204)


@router.get("/courts", response_model=list[CourtOutput])
def list_courts(
    venue_id: int | None = Query(default=None, gt=0),
    sport_id: int | None = Query(default=None, gt=0),
    is_active: bool | None = None,
    db: Session = Depends(get_db),
):
    query = select(Court)
    if venue_id is not None:
        query = query.where(Court.venue_id == venue_id)
    if sport_id is not None:
        query = query.where(Court.sport_id == sport_id)
    if is_active is not None:
        query = query.where(Court.is_active == is_active)
    return db.scalars(query.order_by(Court.id)).all()


@router.get("/courts/{court_id}", response_model=CourtOutput)
def read_court(court_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Court, court_id, "Court")


def validate_court_references(db: Session, data: CourtInput) -> None:
    venue = db.get(Venue, data.venue_id)
    if venue is None:
        raise HTTPException(status_code=400, detail="Venue does not exist")
    if not venue.is_active:
        raise HTTPException(status_code=400, detail="Venue is inactive")
    if db.get(Sport, data.sport_id) is None:
        raise HTTPException(status_code=400, detail="Sport does not exist")


@router.post("/courts", response_model=CourtOutput, status_code=201, dependencies=[Depends(require_write_access)])
def create_court(data: CourtInput, db: Session = Depends(get_db)):
    validate_court_references(db, data)
    court = Court(**data.model_dump())
    db.add(court)
    commit_or_conflict(db)
    db.refresh(court)
    return court


@router.put("/courts/{court_id}", response_model=CourtOutput, dependencies=[Depends(require_write_access)])
def update_court(court_id: int, data: CourtInput, db: Session = Depends(get_db)):
    court = get_or_404(db, Court, court_id, "Court")
    validate_court_references(db, data)
    for key, value in data.model_dump().items():
        setattr(court, key, value)
    commit_or_conflict(db)
    db.refresh(court)
    return court


@router.delete("/courts/{court_id}", status_code=204, dependencies=[Depends(require_write_access)])
def delete_court(court_id: int, db: Session = Depends(get_db)):
    court = get_or_404(db, Court, court_id, "Court")
    court.is_active = False
    commit_or_conflict(db)
    return Response(status_code=204)


@router.get("/time-slots", response_model=list[TimeSlotOutput])
def list_time_slots(
    court_id: int | None = Query(default=None, gt=0),
    slot_date: date | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
):
    query = select(TimeSlot)
    if court_id is not None:
        query = query.where(TimeSlot.court_id == court_id)
    if slot_date is not None:
        query = query.where(TimeSlot.slot_date == slot_date)
    if is_active is not None:
        query = query.where(TimeSlot.is_active == is_active)
    return db.scalars(query.order_by(TimeSlot.slot_date, TimeSlot.start_time)).all()


@router.get("/time-slots/{slot_id}", response_model=TimeSlotOutput)
def read_time_slot(slot_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, TimeSlot, slot_id, "Time slot")


def validate_slot_court(db: Session, court_id: int) -> None:
    court = db.get(Court, court_id)
    if court is None:
        raise HTTPException(status_code=400, detail="Court does not exist")
    if not court.is_active:
        raise HTTPException(status_code=400, detail="Court is inactive")


def validate_slot_overlap(db: Session, data: TimeSlotInput, exclude_id: int | None = None) -> None:
    if not data.is_active:
        return
    query = select(TimeSlot.id).where(
        TimeSlot.court_id == data.court_id,
        TimeSlot.slot_date == data.slot_date,
        TimeSlot.is_active.is_(True),
        TimeSlot.start_time < data.end_time,
        TimeSlot.end_time > data.start_time,
    )
    if exclude_id is not None:
        query = query.where(TimeSlot.id != exclude_id)
    if db.scalar(query) is not None:
        raise HTTPException(status_code=409, detail="Time slot overlaps an active slot")


@router.post("/time-slots", response_model=TimeSlotOutput, status_code=201, dependencies=[Depends(require_write_access)])
def create_time_slot(data: TimeSlotInput, db: Session = Depends(get_db)):
    validate_slot_court(db, data.court_id)
    validate_slot_overlap(db, data)
    slot = TimeSlot(**data.model_dump())
    db.add(slot)
    commit_or_conflict(db, "Time slot conflicts with an existing slot")
    db.refresh(slot)
    return slot


@router.put("/time-slots/{slot_id}", response_model=TimeSlotOutput, dependencies=[Depends(require_write_access)])
def update_time_slot(slot_id: int, data: TimeSlotInput, db: Session = Depends(get_db)):
    slot = get_or_404(db, TimeSlot, slot_id, "Time slot")
    validate_slot_court(db, data.court_id)
    validate_slot_overlap(db, data, exclude_id=slot_id)
    for key, value in data.model_dump().items():
        setattr(slot, key, value)
    commit_or_conflict(db, "Time slot conflicts with an existing slot")
    db.refresh(slot)
    return slot


@router.delete("/time-slots/{slot_id}", status_code=204, dependencies=[Depends(require_write_access)])
def delete_time_slot(slot_id: int, db: Session = Depends(get_db)):
    slot = get_or_404(db, TimeSlot, slot_id, "Time slot")
    slot.is_active = False
    commit_or_conflict(db)
    return Response(status_code=204)

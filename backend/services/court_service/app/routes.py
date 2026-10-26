from datetime import date, datetime, timedelta, timezone
import hmac
import os
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Court, Sport, TimeSlot, Venue
from app.security import JWTConfigurationError, JWTError, Principal, decode_access_token
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
bearer_scheme = HTTPBearer(auto_error=False)
BUSINESS_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")


def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Principal:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return decode_access_token(credentials.credentials)
    except JWTConfigurationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT verification is not configured",
        ) from None
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def require_owner_or_admin(principal: Principal = Depends(get_current_principal)) -> Principal:
    if principal.role not in {"OWNER", "ADMIN"}:
        raise HTTPException(status_code=403, detail="Owner or Admin role required")
    return principal


def require_admin(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    if principal.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return principal


def require_internal_token(x_internal_token: str | None = Header(default=None)) -> None:
    configured = os.getenv("INTERNAL_SERVICE_TOKEN", "").strip()
    if not configured:
        raise HTTPException(status_code=503, detail="Internal service token is not configured")
    if not x_internal_token or not hmac.compare_digest(x_internal_token, configured):
        raise HTTPException(status_code=403, detail="Invalid internal service token")


def get_or_404(db: Session, model, object_id: int, label: str):
    item = db.get(model, object_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return item


def require_owned_venue(db: Session, venue_id: int, principal: Principal) -> Venue:
    venue = get_or_404(db, Venue, venue_id, "Venue")
    if principal.role != "ADMIN" and venue.owner_id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Venue is outside the authenticated owner's scope",
        )
    return venue


def require_owned_court(db: Session, court_id: int, principal: Principal) -> Court:
    court = get_or_404(db, Court, court_id, "Court")
    require_owned_venue(db, court.venue_id, principal)
    return court


def commit_or_conflict(db: Session, detail: str = "Conflicting data") -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=detail) from None
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database operation failed") from None


def _reservation_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _locked_slot(db: Session, slot_id: int) -> TimeSlot:
    slot = db.scalar(select(TimeSlot).where(TimeSlot.id == slot_id).with_for_update())
    if slot is None:
        raise HTTPException(status_code=404, detail="Time slot not found")
    return slot


def _lock_courts_for_schedule(db: Session, *court_ids: int) -> None:
    for court_id in sorted(set(court_ids)):
        db.scalar(select(Court.id).where(Court.id == court_id).with_for_update())


def _ensure_slot_not_reserved(slot: TimeSlot) -> None:
    if slot.reservation_status == "HELD":
        if slot.reservation_expires_at is not None and slot.reservation_expires_at <= _reservation_now():
            slot.reservation_status = "AVAILABLE"
            slot.reservation_booking_id = None
            slot.reservation_expires_at = None
            return
        raise HTTPException(status_code=409, detail="Time slot has an active booking hold")
    if slot.reservation_status == "BOOKED":
        raise HTTPException(status_code=409, detail="Time slot is booked")


@router.post("/internal/slots/{slot_id}/hold", dependencies=[Depends(require_internal_token)])
def hold_slot(slot_id: int, booking_id: int = Query(gt=0), db: Session = Depends(get_db)):
    slot = _locked_slot(db, slot_id)
    now = _reservation_now()
    if not slot.is_active:
        raise HTTPException(status_code=409, detail="Time slot is unavailable")
    if datetime.combine(slot.slot_date, slot.start_time, tzinfo=BUSINESS_TIMEZONE) <= business_now():
        raise HTTPException(status_code=409, detail="Time slot is unavailable")
    if slot.reservation_status == "BOOKED":
        raise HTTPException(status_code=409, detail="Time slot is unavailable")
    if slot.reservation_status == "HELD" and slot.reservation_expires_at and slot.reservation_expires_at > now:
        if slot.reservation_booking_id != booking_id:
            raise HTTPException(status_code=409, detail="Time slot is unavailable")
    else:
        try:
            ttl = int(os.getenv("BOOKING_HOLD_MINUTES", "10"))
        except ValueError:
            raise HTTPException(status_code=503, detail="Booking hold duration is not configured") from None
        if ttl <= 0:
            raise HTTPException(status_code=503, detail="Booking hold duration is not configured")
        slot.reservation_status = "HELD"
        slot.reservation_booking_id = booking_id
        slot.reservation_expires_at = now + timedelta(minutes=ttl)
    court = get_or_404(db, Court, slot.court_id, "Court")
    venue = get_or_404(db, Venue, court.venue_id, "Venue")
    if not court.is_active or not venue.is_active:
        raise HTTPException(status_code=409, detail="Time slot is unavailable")
    db.commit()
    expiry = slot.reservation_expires_at.replace(tzinfo=timezone.utc)
    return {
        "court_id": court.id,
        "venue_id": venue.id,
        "owner_id": venue.owner_id,
        "price_per_hour": str(court.price_per_hour),
        "slot_date": slot.slot_date.isoformat(),
        "start_time": slot.start_time.isoformat(),
        "end_time": slot.end_time.isoformat(),
        "expires_at": expiry.isoformat(),
    }


@router.post("/internal/slots/{slot_id}/confirm", dependencies=[Depends(require_internal_token)])
def confirm_slot(slot_id: int, booking_id: int = Query(gt=0), db: Session = Depends(get_db)):
    slot = _locked_slot(db, slot_id)
    if slot.reservation_status == "BOOKED" and slot.reservation_booking_id == booking_id:
        return {"status": "BOOKED"}
    if (
        slot.reservation_status != "HELD"
        or slot.reservation_booking_id != booking_id
        or slot.reservation_expires_at is None
        or slot.reservation_expires_at <= _reservation_now()
    ):
        raise HTTPException(status_code=409, detail="Booking does not hold this time slot")
    slot.reservation_status = "BOOKED"
    slot.reservation_expires_at = None
    db.commit()
    return {"status": "BOOKED"}


@router.post("/internal/slots/{slot_id}/release", dependencies=[Depends(require_internal_token)])
def release_slot(slot_id: int, booking_id: int = Query(gt=0), db: Session = Depends(get_db)):
    slot = _locked_slot(db, slot_id)
    if slot.reservation_status == "AVAILABLE":
        return {"status": "AVAILABLE"}
    if slot.reservation_status != "HELD" or slot.reservation_booking_id != booking_id:
        raise HTTPException(status_code=409, detail="Booking does not hold this time slot")
    slot.reservation_status = "AVAILABLE"
    slot.reservation_booking_id = None
    slot.reservation_expires_at = None
    db.commit()
    return {"status": "AVAILABLE"}


@router.get("/sports", response_model=list[SportOutput])
def list_sports(is_active: bool | None = None, db: Session = Depends(get_db)):
    query = select(Sport)
    if is_active is not None:
        query = query.where(Sport.is_active == is_active)
    return db.scalars(query.order_by(Sport.id)).all()


@router.get("/sports/{sport_id}", response_model=SportOutput)
def read_sport(sport_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Sport, sport_id, "Sport")


@router.post("/sports", response_model=SportOutput, status_code=201, dependencies=[Depends(require_admin)])
def create_sport(data: SportInput, db: Session = Depends(get_db)):
    sport = Sport(**data.model_dump())
    db.add(sport)
    commit_or_conflict(db, "Sport name already exists")
    db.refresh(sport)
    return sport


@router.put("/sports/{sport_id}", response_model=SportOutput, dependencies=[Depends(require_admin)])
def update_sport(sport_id: int, data: SportInput, db: Session = Depends(get_db)):
    sport = get_or_404(db, Sport, sport_id, "Sport")
    for key, value in data.model_dump().items():
        setattr(sport, key, value)
    commit_or_conflict(db, "Sport name already exists")
    db.refresh(sport)
    return sport


@router.delete("/sports/{sport_id}", status_code=204, dependencies=[Depends(require_admin)])
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


@router.post("/venues", response_model=VenueOutput, status_code=201)
def create_venue(
    data: VenueInput,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_owner_or_admin),
):
    if principal.role != "ADMIN" and data.owner_id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="owner_id must match the authenticated owner",
        )
    values = data.model_dump()
    if principal.role != "ADMIN":
        values["owner_id"] = principal.user_id
    venue = Venue(**values, created_at=datetime.now(timezone.utc).replace(tzinfo=None))
    db.add(venue)
    commit_or_conflict(db)
    db.refresh(venue)
    return venue


@router.put("/venues/{venue_id}", response_model=VenueOutput)
def update_venue(
    venue_id: int,
    data: VenueInput,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_owner_or_admin),
):
    venue = require_owned_venue(db, venue_id, principal)
    if principal.role != "ADMIN" and data.owner_id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="owner_id must match the authenticated owner",
        )
    values = data.model_dump() if principal.role == "ADMIN" else data.model_dump(exclude={"owner_id"})
    for key, value in values.items():
        setattr(venue, key, value)
    commit_or_conflict(db)
    db.refresh(venue)
    return venue


@router.delete("/venues/{venue_id}", status_code=204)
def delete_venue(
    venue_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_owner_or_admin),
):
    venue = require_owned_venue(db, venue_id, principal)
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


@router.post("/courts", response_model=CourtOutput, status_code=201)
def create_court(
    data: CourtInput,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_owner_or_admin),
):
    validate_court_references(db, data)
    require_owned_venue(db, data.venue_id, principal)
    court = Court(**data.model_dump())
    db.add(court)
    commit_or_conflict(db)
    db.refresh(court)
    return court


@router.put("/courts/{court_id}", response_model=CourtOutput)
def update_court(
    court_id: int,
    data: CourtInput,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_owner_or_admin),
):
    court = require_owned_court(db, court_id, principal)
    validate_court_references(db, data)
    require_owned_venue(db, data.venue_id, principal)
    for key, value in data.model_dump().items():
        setattr(court, key, value)
    commit_or_conflict(db)
    db.refresh(court)
    return court


@router.delete("/courts/{court_id}", status_code=204)
def delete_court(
    court_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_owner_or_admin),
):
    court = require_owned_court(db, court_id, principal)
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


def validate_slot_court(db: Session, court_id: int, principal: Principal) -> None:
    court = db.get(Court, court_id)
    if court is None:
        raise HTTPException(status_code=400, detail="Court does not exist")
    if not court.is_active:
        raise HTTPException(status_code=400, detail="Court is inactive")
    require_owned_venue(db, court.venue_id, principal)


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


def business_now() -> datetime:
    return datetime.now(BUSINESS_TIMEZONE)


def validate_slot_start_time(data: TimeSlotInput, existing: TimeSlot | None = None) -> None:
    """Require new or changed slot starts to be future Vietnam business time."""
    if existing is not None and data.slot_date == existing.slot_date and data.start_time == existing.start_time:
        return

    slot_start = datetime.combine(data.slot_date, data.start_time, tzinfo=BUSINESS_TIMEZONE)
    if slot_start <= business_now():
        raise HTTPException(
            status_code=422,
            detail="Time slot start must be in the future (Asia/Ho_Chi_Minh)",
        )


@router.post("/time-slots", response_model=TimeSlotOutput, status_code=201)
def create_time_slot(
    data: TimeSlotInput,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_owner_or_admin),
):
    _lock_courts_for_schedule(db, data.court_id)
    validate_slot_court(db, data.court_id, principal)
    validate_slot_start_time(data)
    validate_slot_overlap(db, data)
    slot = TimeSlot(**data.model_dump())
    db.add(slot)
    commit_or_conflict(db, "Time slot conflicts with an existing slot")
    db.refresh(slot)
    return slot


@router.put("/time-slots/{slot_id}", response_model=TimeSlotOutput)
def update_time_slot(
    slot_id: int,
    data: TimeSlotInput,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_owner_or_admin),
):
    slot = _locked_slot(db, slot_id)
    _ensure_slot_not_reserved(slot)
    _lock_courts_for_schedule(db, slot.court_id, data.court_id)
    require_owned_court(db, slot.court_id, principal)
    validate_slot_court(db, data.court_id, principal)
    validate_slot_start_time(data, existing=slot)
    validate_slot_overlap(db, data, exclude_id=slot_id)
    for key, value in data.model_dump().items():
        setattr(slot, key, value)
    commit_or_conflict(db, "Time slot conflicts with an existing slot")
    db.refresh(slot)
    return slot


@router.delete("/time-slots/{slot_id}", status_code=204)
def delete_time_slot(
    slot_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_owner_or_admin),
):
    slot = _locked_slot(db, slot_id)
    _ensure_slot_not_reserved(slot)
    require_owned_court(db, slot.court_id, principal)
    slot.is_active = False
    commit_or_conflict(db)
    return Response(status_code=204)

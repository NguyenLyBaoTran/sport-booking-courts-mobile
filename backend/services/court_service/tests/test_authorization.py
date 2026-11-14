import os
import unittest
from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Court, Sport, TimeSlot, Venue
from app.security import decode_access_token


TEST_SECRET = "court-service-test-secret-with-at-least-32-characters"


def make_token(role="OWNER", user_id=10, **claims):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=60),
    }
    payload.update(claims)
    return jwt.encode(payload, TEST_SECRET, algorithm="HS256")


class CourtAuthorizationTests(unittest.TestCase):
    FROZEN_BUSINESS_NOW = datetime(2026, 11, 1, 10, 0, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))

    @classmethod
    def setUpClass(cls):
        os.environ["JWT_SECRET_KEY"] = TEST_SECRET
        os.environ["JWT_ALGORITHM"] = "HS256"
        os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
        os.environ["INTERNAL_SERVICE_TOKEN"] = "court-internal-test-token"
        os.environ["BOOKING_HOLD_MINUTES"] = "10"

    def setUp(self):
        self.business_clock = patch("app.routes.business_now", return_value=self.FROZEN_BUSINESS_NOW)
        self.business_clock.start()
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self._seed_records()

        def override_get_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()
        self.business_clock.stop()

    def _seed_records(self):
        with self.Session() as db:
            sport = Sport(name="Tennis")
            venue_a = Venue(
                owner_id=10,
                name="Owner A venue",
                address="1 Example Street",
                created_at=datetime.now(),
            )
            venue_b = Venue(
                owner_id=20,
                name="Owner B venue",
                address="2 Example Street",
                created_at=datetime.now(),
            )
            db.add_all([sport, venue_a, venue_b])
            db.flush()
            court_a = Court(
                venue_id=venue_a.id,
                sport_id=sport.id,
                name="Court A",
                price_per_hour=25,
            )
            court_b = Court(
                venue_id=venue_b.id,
                sport_id=sport.id,
                name="Court B",
                price_per_hour=25,
            )
            court_a2 = Court(
                venue_id=venue_a.id,
                sport_id=sport.id,
                name="Court A2",
                price_per_hour=25,
            )
            db.add_all([court_a, court_b, court_a2])
            db.flush()
            slot_b = TimeSlot(
                court_id=court_b.id,
                slot_date=date(2026, 11, 1),
                start_time=time(9),
                end_time=time(10),
            )
            db.add(slot_b)
            db.commit()
            self.venue_a_id = venue_a.id
            self.venue_b_id = venue_b.id
            self.sport_id = sport.id
            self.court_a_id = court_a.id
            self.court_b_id = court_b.id
            self.court_a2_id = court_a2.id
            self.slot_b_id = slot_b.id

    def test_court_health(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"service": "court", "status": "ok"})

    def test_admin_catalogue_summary_is_aggregate_and_admin_only(self):
        url = "/api/v1/admin/catalogue/summary"
        self.assertEqual(self.client.get(url).status_code, 401)
        self.assertEqual(
            self.client.get(url, headers=self._headers(role="OWNER")).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(url, headers=self._headers(role="USER")).status_code,
            403,
        )

        response = self.client.get(url, headers=self._headers(role="ADMIN", user_id=3))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json(),
            {
                "sports": {"total": 1, "active": 1},
                "venues": {"total": 2, "active": 2},
                "courts": {"total": 3, "active": 3},
                "time_slots": {"total": 1, "active": 1},
            },
        )

    def _headers(self, role="OWNER", user_id=10, token=None):
        return {"Authorization": f"Bearer {token or make_token(role, user_id)}"}

    def _venue_payload(self, owner_id=10, name="New venue"):
        return {
            "owner_id": owner_id,
            "name": name,
            "address": "3 Example Street",
            "description": None,
            "phone": None,
            "is_active": True,
        }

    def test_public_get_remains_available_without_token(self):
        response = self.client.get("/api/v1/sports")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["name"], "Tennis")

    def test_missing_or_invalid_tokens_are_401(self):
        endpoint = f"/api/v1/venues/{self.venue_a_id}"
        self.assertEqual(self.client.delete(endpoint).status_code, 401)
        with self.subTest(case="wrong signature"):
            bad = jwt.encode(
                {"sub": "10", "role": "OWNER", "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
                "different-secret-key-with-32-characters",
                algorithm="HS256",
            )
            self.assertEqual(self.client.delete(endpoint, headers=self._headers(token=bad)).status_code, 401)
        with self.subTest(case="expired"):
            expired = make_token(exp=datetime.now(timezone.utc) - timedelta(seconds=1))
            self.assertEqual(self.client.delete(endpoint, headers=self._headers(token=expired)).status_code, 401)
        with self.subTest(case="missing required claims"):
            missing = jwt.encode({"sub": "10", "role": "OWNER"}, TEST_SECRET, algorithm="HS256")
            self.assertEqual(self.client.delete(endpoint, headers=self._headers(token=missing)).status_code, 401)
        with self.subTest(case="invalid role"):
            invalid_role = make_token(role="SUPERUSER")
            self.assertEqual(self.client.delete(endpoint, headers=self._headers(token=invalid_role)).status_code, 401)

    def test_valid_token_resolves_identity_and_role(self):
        principal = decode_access_token(make_token(role="OWNER", user_id=42))
        self.assertEqual(principal.user_id, 42)
        self.assertEqual(principal.role, "OWNER")

    def test_user_cannot_mutate_and_public_get_still_works(self):
        response = self.client.post(
            "/api/v1/venues",
            json=self._venue_payload(),
            headers=self._headers(role="USER"),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.get("/api/v1/venues").status_code, 200)

    def test_owner_can_create_only_for_authenticated_identity(self):
        accepted = self.client.post(
            "/api/v1/venues",
            json=self._venue_payload(owner_id=10),
            headers=self._headers(),
        )
        self.assertEqual(accepted.status_code, 201)
        self.assertEqual(accepted.json()["owner_id"], 10)

        spoofed = self.client.post(
            "/api/v1/venues",
            json=self._venue_payload(owner_id=20, name="Spoofed venue"),
            headers=self._headers(),
        )
        self.assertEqual(spoofed.status_code, 403)

    def test_owner_can_manage_venue_court_and_time_slot_in_owned_venue(self):
        venue = self.client.put(
            f"/api/v1/venues/{self.venue_a_id}",
            json=self._venue_payload(owner_id=10, name="Updated own venue"),
            headers=self._headers(),
        )
        self.assertEqual(venue.status_code, 200)
        self.assertEqual(venue.json()["owner_id"], 10)

        court_payload = {
            "venue_id": self.venue_a_id,
            "sport_id": self.sport_id,
            "name": "New own court",
            "price_per_hour": "30.00",
            "is_active": True,
        }
        court = self.client.post(
            "/api/v1/courts", json=court_payload, headers=self._headers()
        )
        self.assertEqual(court.status_code, 201)
        court_id = court.json()["id"]

        slot_payload = {
            "court_id": court_id,
            "slot_date": "2026-11-05",
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "is_active": True,
        }
        slot = self.client.post(
            "/api/v1/time-slots", json=slot_payload, headers=self._headers()
        )
        self.assertEqual(slot.status_code, 201)
        slot_id = slot.json()["id"]
        slot_payload["end_time"] = "11:30:00"
        self.assertEqual(
            self.client.put(
                f"/api/v1/time-slots/{slot_id}",
                json=slot_payload,
                headers=self._headers(),
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.delete(
                f"/api/v1/time-slots/{slot_id}", headers=self._headers()
            ).status_code,
            204,
        )

    def test_owner_cannot_update_or_delete_another_owners_venue(self):
        endpoint = f"/api/v1/venues/{self.venue_b_id}"
        updated = self.client.put(
            endpoint,
            json=self._venue_payload(owner_id=20, name="Changed"),
            headers=self._headers(),
        )
        deleted = self.client.delete(endpoint, headers=self._headers())
        self.assertEqual(updated.status_code, 403)
        self.assertEqual(deleted.status_code, 403)

    def test_admin_can_manage_catalogue_across_owner_boundaries(self):
        headers = self._headers(role="ADMIN", user_id=3)
        venue_body = self._venue_payload(owner_id=20, name="Admin venue")
        created_venue = self.client.post("/api/v1/venues", json=venue_body, headers=headers)
        self.assertEqual(created_venue.status_code, 201, created_venue.text)
        venue_id = created_venue.json()["id"]
        changed_venue = self.client.put(
            f"/api/v1/venues/{self.venue_a_id}",
            json=self._venue_payload(owner_id=20, name="Admin changed venue"),
            headers=headers,
        )
        self.assertEqual(changed_venue.status_code, 200, changed_venue.text)
        self.assertEqual(changed_venue.json()["owner_id"], 20)

        court_body = {
            "venue_id": self.venue_b_id,
            "sport_id": self.sport_id,
            "name": "Admin court",
            "price_per_hour": "40.00",
            "is_active": True,
        }
        created_court = self.client.post("/api/v1/courts", json=court_body, headers=headers)
        self.assertEqual(created_court.status_code, 201, created_court.text)
        court_id = created_court.json()["id"]
        slot_body = self._time_slot_payload(court_id, "08:00:00", "09:00:00")
        created_slot = self.client.post("/api/v1/time-slots", json=slot_body, headers=headers)
        self.assertEqual(created_slot.status_code, 201, created_slot.text)
        self.assertEqual(
            self.client.delete(f"/api/v1/time-slots/{created_slot.json()['id']}", headers=headers).status_code,
            204,
        )
        self.assertEqual(self.client.delete(f"/api/v1/courts/{court_id}", headers=headers).status_code, 204)
        self.assertEqual(self.client.delete(f"/api/v1/venues/{venue_id}", headers=headers).status_code, 204)

    def test_court_mutations_require_ownership_of_related_venue(self):
        body = {
            "venue_id": self.venue_b_id,
            "sport_id": self.sport_id,
            "name": "Foreign court",
            "price_per_hour": "20.00",
            "is_active": True,
        }
        created = self.client.post("/api/v1/courts", json=body, headers=self._headers())
        updated = self.client.put(
            f"/api/v1/courts/{self.court_b_id}", json=body, headers=self._headers()
        )
        deleted = self.client.delete(
            f"/api/v1/courts/{self.court_b_id}", headers=self._headers()
        )
        self.assertEqual(created.status_code, 403)
        self.assertEqual(updated.status_code, 403)
        self.assertEqual(deleted.status_code, 403)

    def test_time_slot_mutations_require_ownership_through_court_and_venue(self):
        body = {
            "court_id": self.court_b_id,
            "slot_date": "2026-11-02",
            "start_time": "11:00:00",
            "end_time": "12:00:00",
            "is_active": True,
        }
        created = self.client.post("/api/v1/time-slots", json=body, headers=self._headers())
        updated = self.client.put(
            f"/api/v1/time-slots/{self.slot_b_id}", json=body, headers=self._headers()
        )
        deleted = self.client.delete(
            f"/api/v1/time-slots/{self.slot_b_id}", headers=self._headers()
        )
        self.assertEqual(created.status_code, 403)
        self.assertEqual(updated.status_code, 403)
        self.assertEqual(deleted.status_code, 403)

    def _time_slot_payload(self, court_id, start_time, end_time, slot_date="2026-11-05"):
        return {
            "court_id": court_id,
            "slot_date": slot_date,
            "start_time": start_time,
            "end_time": end_time,
            "is_active": True,
        }

    def test_time_slots_accept_half_hour_boundaries(self):
        for slot_date, start, end in (
            ("2026-11-05", "08:00:00", "09:00:00"),
            ("2026-11-06", "08:30:00", "09:30:00"),
        ):
            with self.subTest(start=start, end=end):
                response = self.client.post(
                    "/api/v1/time-slots",
                    json=self._time_slot_payload(self.court_a_id, start, end, slot_date),
                    headers=self._headers(),
                )
                self.assertEqual(response.status_code, 201, response.text)

    def test_time_slots_reject_non_half_hour_boundaries(self):
        for start, end in (("08:15:00", "09:00:00"), ("08:00:00", "09:45:00")):
            with self.subTest(start=start, end=end):
                response = self.client.post(
                    "/api/v1/time-slots",
                    json=self._time_slot_payload(self.court_a_id, start, end),
                    headers=self._headers(),
                )
                self.assertEqual(response.status_code, 422, response.text)

    def test_time_slots_reject_start_equal_to_or_after_end(self):
        for start, end in (("09:00:00", "09:00:00"), ("09:30:00", "09:00:00")):
            with self.subTest(start=start, end=end):
                response = self.client.post(
                    "/api/v1/time-slots",
                    json=self._time_slot_payload(self.court_a_id, start, end),
                    headers=self._headers(),
                )
                self.assertEqual(response.status_code, 422, response.text)

    def test_overlapping_active_slots_on_same_court_are_rejected(self):
        first = self.client.post(
            "/api/v1/time-slots",
            json=self._time_slot_payload(self.court_a_id, "08:00:00", "09:00:00"),
            headers=self._headers(),
        )
        self.assertEqual(first.status_code, 201, first.text)
        overlap = self.client.post(
            "/api/v1/time-slots",
            json=self._time_slot_payload(self.court_a_id, "08:30:00", "09:30:00"),
            headers=self._headers(),
        )
        self.assertEqual(overlap.status_code, 409, overlap.text)

    def test_same_time_is_allowed_on_different_courts(self):
        for court_id in (self.court_a_id, self.court_a2_id):
            with self.subTest(court_id=court_id):
                response = self.client.post(
                    "/api/v1/time-slots",
                    json=self._time_slot_payload(court_id, "08:00:00", "09:00:00"),
                    headers=self._headers(),
                )
                self.assertEqual(response.status_code, 201, response.text)

    def test_time_slot_update_rejects_non_half_hour_boundary(self):
        created = self.client.post(
            "/api/v1/time-slots",
            json=self._time_slot_payload(self.court_a_id, "08:00:00", "09:00:00"),
            headers=self._headers(),
        )
        self.assertEqual(created.status_code, 201, created.text)
        invalid_update = self.client.put(
            f"/api/v1/time-slots/{created.json()['id']}",
            json=self._time_slot_payload(self.court_a_id, "08:15:00", "09:15:00"),
            headers=self._headers(),
        )
        self.assertEqual(invalid_update.status_code, 422, invalid_update.text)

    def test_time_slots_reject_past_and_same_day_past_starts(self):
        for slot_date, start, end in (
            ("2026-10-31", "08:00:00", "09:00:00"),
            ("2026-11-01", "09:30:00", "10:30:00"),
            ("2026-11-01", "10:00:00", "11:00:00"),
        ):
            with self.subTest(slot_date=slot_date, start=start):
                response = self.client.post(
                    "/api/v1/time-slots",
                    json=self._time_slot_payload(self.court_a_id, start, end, slot_date),
                    headers=self._headers(),
                )
                self.assertEqual(response.status_code, 422, response.text)

    def test_time_slot_future_start_is_accepted(self):
        response = self.client.post(
            "/api/v1/time-slots",
            json=self._time_slot_payload(self.court_a_id, "10:30:00", "11:30:00", "2026-11-01"),
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 201, response.text)

    def test_time_slot_update_rejects_changed_start_in_the_past(self):
        created = self.client.post(
            "/api/v1/time-slots",
            json=self._time_slot_payload(self.court_a_id, "10:30:00", "11:30:00", "2026-11-01"),
            headers=self._headers(),
        )
        self.assertEqual(created.status_code, 201, created.text)
        updated = self.client.put(
            f"/api/v1/time-slots/{created.json()['id']}",
            json=self._time_slot_payload(self.court_a_id, "09:00:00", "10:00:00", "2026-11-01"),
            headers=self._headers(),
        )
        self.assertEqual(updated.status_code, 422, updated.text)

    def test_historical_slot_can_be_updated_without_changing_its_start(self):
        with self.Session() as db:
            historic = TimeSlot(
                court_id=self.court_a_id,
                slot_date=date(2026, 10, 30),
                start_time=time(8),
                end_time=time(9),
                is_active=True,
            )
            db.add(historic)
            db.commit()
            slot_id = historic.id
        response = self.client.put(
            f"/api/v1/time-slots/{slot_id}",
            json=self._time_slot_payload(self.court_a_id, "08:00:00", "09:30:00", "2026-10-30"),
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["start_time"], "08:00:00")

    def test_time_slot_create_and_update_still_enforce_auth_and_ownership(self):
        valid = self._time_slot_payload(self.court_a_id, "08:00:00", "09:00:00")
        self.assertEqual(self.client.post("/api/v1/time-slots", json=valid).status_code, 401)
        foreign = self._time_slot_payload(self.court_b_id, "08:00:00", "09:00:00")
        self.assertEqual(
            self.client.post(
                "/api/v1/time-slots", json=foreign, headers=self._headers()
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.put(
                f"/api/v1/time-slots/{self.slot_b_id}",
                json=foreign,
                headers=self._headers(),
            ).status_code,
            403,
        )

    def test_only_admin_can_create_update_and_deactivate_sports(self):
        payload = {"name": "New sport", "description": None, "is_active": True}
        owner_response = self.client.post(
            "/api/v1/sports", json=payload, headers=self._headers()
        )
        user_response = self.client.post(
            "/api/v1/sports", json=payload, headers=self._headers(role="USER")
        )
        admin_response = self.client.post(
            "/api/v1/sports", json=payload, headers=self._headers(role="ADMIN")
        )
        self.assertEqual(owner_response.status_code, 403)
        self.assertEqual(user_response.status_code, 403)
        self.assertEqual(admin_response.status_code, 201, admin_response.text)
        sport_id = admin_response.json()["id"]
        updated = self.client.put(
            f"/api/v1/sports/{sport_id}",
            json={"name": "Updated sport", "description": "Changed", "is_active": True},
            headers=self._headers(role="ADMIN"),
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["name"], "Updated sport")
        self.assertEqual(
            self.client.delete(
                f"/api/v1/sports/{sport_id}", headers=self._headers(role="ADMIN")
            ).status_code,
            204,
        )
        self.assertFalse(self.client.get(f"/api/v1/sports/{sport_id}").json()["is_active"])

    def test_sports_writes_require_authentication_and_duplicate_name_conflicts(self):
        payload = {"name": "Tennis", "description": None, "is_active": True}
        self.assertEqual(self.client.post("/api/v1/sports", json=payload).status_code, 401)
        duplicate = self.client.post(
            "/api/v1/sports", json=payload, headers=self._headers(role="ADMIN")
        )
        self.assertEqual(duplicate.status_code, 409)

    def test_booking_hold_contract_is_idempotent_and_booking_scoped(self):
        with self.Session() as db:
            slot = TimeSlot(
                court_id=self.court_a_id,
                slot_date=date(2026, 11, 5),
                start_time=time(8),
                end_time=time(9),
            )
            db.add(slot)
            db.commit()
            slot_id = slot.id
        url = f"/api/v1/internal/slots/{slot_id}/hold?booking_id=501"
        headers = {"X-Internal-Token": "court-internal-test-token"}
        first = self.client.post(url, headers=headers)
        second = self.client.post(url, headers=headers)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(first.json()["court_id"], self.court_a_id)
        self.assertEqual(first.json()["venue_id"], self.venue_a_id)
        self.assertEqual(first.json()["owner_id"], 10)
        self.assertIn("expires_at", first.json())
        self.assertEqual(self.client.post(url.replace("501", "502"), headers=headers).status_code, 409)
        release_url = f"/api/v1/internal/slots/{slot_id}/release?booking_id=501"
        wrong_release_url = f"/api/v1/internal/slots/{slot_id}/release?booking_id=502"
        self.assertEqual(self.client.post(wrong_release_url, headers=headers).status_code, 409)
        self.assertEqual(self.client.post(release_url, headers=headers).json(), {"status": "AVAILABLE"})
        self.assertEqual(self.client.post(release_url, headers=headers).json(), {"status": "AVAILABLE"})
        first = self.client.post(url, headers=headers)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(
            self.client.post(
                f"/api/v1/internal/slots/{slot_id}/confirm?booking_id=501", headers=headers
            ).json(),
            {"status": "BOOKED"},
        )
        self.assertEqual(
            self.client.post(
                f"/api/v1/internal/slots/{slot_id}/confirm?booking_id=501", headers=headers
            ).json(),
            {"status": "BOOKED"},
        )
        self.assertEqual(self.client.post(url.replace("501", "502"), headers=headers).status_code, 409)
        self.assertEqual(self.client.post(release_url, headers=headers).status_code, 200)
        with self.Session() as db:
            released = db.get(TimeSlot, slot_id)
            self.assertEqual(released.reservation_status, "AVAILABLE")
            self.assertIsNone(released.reservation_booking_id)
            self.assertIsNone(released.reservation_expires_at)

    def test_quote_does_not_reserve_available_slot(self):
        with self.Session() as db:
            slot = TimeSlot(
                court_id=self.court_a_id,
                slot_date=date.today() + timedelta(days=10),
                start_time=time(8),
                end_time=time(9),
            )
            db.add(slot)
            db.commit()
            slot_id = slot.id
        headers = {"X-Internal-Token": "court-internal-test-token"}
        response = self.client.get(f"/api/v1/internal/slots/{slot_id}/quote", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["court_id"], self.court_a_id)
        with self.Session() as db:
            quoted = db.get(TimeSlot, slot_id)
            self.assertEqual(quoted.reservation_status, "AVAILABLE")
            self.assertIsNone(quoted.reservation_booking_id)
            self.assertIsNone(quoted.reservation_expires_at)

    def test_release_booked_slot_only_for_matching_booking(self):
        with self.Session() as db:
            slot = TimeSlot(court_id=self.court_a_id, slot_date=date(2026, 11, 5), start_time=time(8), end_time=time(9))
            db.add(slot)
            db.commit()
            slot_id = slot.id
        headers = {"X-Internal-Token": "court-internal-test-token"}
        base = f"/api/v1/internal/slots/{slot_id}"
        self.assertEqual(self.client.post(f"{base}/hold?booking_id=901", headers=headers).status_code, 200)
        self.assertEqual(self.client.post(f"{base}/confirm?booking_id=901", headers=headers).status_code, 200)
        self.assertEqual(self.client.post(f"{base}/release?booking_id=902", headers=headers).status_code, 409)
        with self.Session() as db:
            slot = db.get(TimeSlot, slot_id)
            self.assertEqual(slot.reservation_status, "BOOKED")
            self.assertEqual(slot.reservation_booking_id, 901)
        self.assertEqual(self.client.post(f"{base}/release?booking_id=901", headers=headers).status_code, 200)
        self.assertEqual(self.client.post(f"{base}/release?booking_id=901", headers=headers).status_code, 200)
        with self.Session() as db:
            slot = db.get(TimeSlot, slot_id)
            self.assertEqual(slot.reservation_status, "AVAILABLE")
            self.assertIsNone(slot.reservation_booking_id)
            self.assertIsNone(slot.reservation_expires_at)

    def test_confirm_is_idempotent_for_same_booking_and_rejects_other_booking(self):
        with self.Session() as db:
            slot = TimeSlot(court_id=self.court_a_id, slot_date=date(2026, 11, 5), start_time=time(8), end_time=time(9))
            db.add(slot)
            db.commit()
            slot_id = slot.id
        headers = {"X-Internal-Token": "court-internal-test-token"}
        root = f"/api/v1/internal/slots/{slot_id}"
        self.assertEqual(self.client.post(f"{root}/hold?booking_id=111", headers=headers).status_code, 200)
        self.assertEqual(self.client.post(f"{root}/confirm?booking_id=111", headers=headers).json(), {"status": "BOOKED"})
        with self.Session() as db:
            db.get(Court, self.court_a_id).is_active = False
            db.commit()
        self.assertEqual(self.client.post(f"{root}/confirm?booking_id=111", headers=headers).json(), {"status": "BOOKED"})
        self.assertEqual(self.client.post(f"{root}/confirm?booking_id=222", headers=headers).status_code, 409)
        with self.Session() as db:
            slot = db.get(TimeSlot, slot_id)
            self.assertEqual(slot.reservation_status, "BOOKED")
            self.assertEqual(slot.reservation_booking_id, 111)

    def test_release_available_slot_clears_only_matching_stale_reservation_fields(self):
        with self.Session() as db:
            matching = TimeSlot(court_id=self.court_a_id, slot_date=date(2026, 11, 5), start_time=time(8), end_time=time(9), reservation_status="AVAILABLE", reservation_booking_id=333, reservation_expires_at=datetime(2026, 11, 1, 0, 0))
            foreign = TimeSlot(court_id=self.court_a_id, slot_date=date(2026, 11, 5), start_time=time(9), end_time=time(10), reservation_status="AVAILABLE", reservation_booking_id=444, reservation_expires_at=datetime(2026, 11, 1, 0, 0))
            db.add_all([matching, foreign])
            db.commit()
            matching_id, foreign_id = matching.id, foreign.id
        headers = {"X-Internal-Token": "court-internal-test-token"}
        root = "/api/v1/internal/slots"
        self.assertEqual(self.client.post(f"{root}/{matching_id}/release?booking_id=333", headers=headers).json(), {"status": "AVAILABLE"})
        self.assertEqual(self.client.post(f"{root}/{foreign_id}/release?booking_id=333", headers=headers).status_code, 409)
        with self.Session() as db:
            matching = db.get(TimeSlot, matching_id)
            foreign = db.get(TimeSlot, foreign_id)
            self.assertIsNone(matching.reservation_booking_id)
            self.assertIsNone(matching.reservation_expires_at)
            self.assertEqual(foreign.reservation_booking_id, 444)
            self.assertIsNotNone(foreign.reservation_expires_at)

    def test_customer_availability_filters_reserved_past_and_inactive_parent_slots(self):
        with self.Session() as db:
            future = self.FROZEN_BUSINESS_NOW.date() + timedelta(days=1)
            slots = [
                TimeSlot(court_id=self.court_a_id, slot_date=future, start_time=time(hour), end_time=time(hour + 1), reservation_status=state, reservation_booking_id=501 if state != "AVAILABLE" else None)
                for hour, state in ((8, "AVAILABLE"), (9, "HELD"), (10, "BOOKED"))
            ]
            slots.append(TimeSlot(court_id=self.court_a_id, slot_date=self.FROZEN_BUSINESS_NOW.date() - timedelta(days=1), start_time=time(8), end_time=time(9)))
            inactive_court = Court(venue_id=self.venue_a_id, sport_id=self.sport_id, name="Inactive Court", price_per_hour=25, is_active=False)
            db.add(inactive_court)
            db.flush()
            slots.append(TimeSlot(court_id=inactive_court.id, slot_date=future, start_time=time(11), end_time=time(12)))
            inactive_venue = Venue(owner_id=10, name="Inactive Venue", address="4 Example Street", created_at=datetime.now(), is_active=False)
            db.add(inactive_venue)
            db.flush()
            inactive_venue_court = Court(venue_id=inactive_venue.id, sport_id=self.sport_id, name="Inactive Venue Court", price_per_hour=25)
            db.add(inactive_venue_court)
            db.flush()
            slots.append(TimeSlot(court_id=inactive_venue_court.id, slot_date=future, start_time=time(12), end_time=time(13)))
            db.add_all(slots)
            db.commit()
            public_ids = {slot.id for slot in slots}
            available_id = slots[0].id
        response = self.client.get(f"/api/v1/time-slots?slot_date={future.isoformat()}")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual({row["id"] for row in response.json()}, {slot.id for slot in slots[:3]})
        availability = {row["id"]: row for row in response.json()}
        self.assertTrue(availability[available_id]["is_selectable"])
        self.assertFalse(availability[slots[1].id]["is_selectable"])
        self.assertEqual(availability[slots[1].id]["reservation_status"], "HELD")
        self.assertFalse(availability[slots[2].id]["is_selectable"])
        self.assertEqual(availability[slots[2].id]["reservation_status"], "BOOKED")
        user = self.client.get(f"/api/v1/time-slots?slot_date={future.isoformat()}", headers=self._headers(role="USER"))
        self.assertEqual(user.status_code, 200, user.text)
        self.assertEqual({row["id"] for row in user.json()}, {slot.id for slot in slots[:3]})
        # Owners retain all schedule records for management, including reservations.
        owner = self.client.get(f"/api/v1/time-slots?slot_date={future.isoformat()}", headers=self._headers())
        self.assertEqual(owner.status_code, 200, owner.text)
        self.assertEqual({row["id"] for row in owner.json()}, public_ids - {slots[3].id})
        admin = self.client.get(f"/api/v1/time-slots?slot_date={future.isoformat()}", headers=self._headers(role="ADMIN", user_id=3))
        self.assertEqual(admin.status_code, 200, admin.text)
        self.assertEqual({row["id"] for row in admin.json()}, public_ids - {slots[3].id})

    def test_time_slot_availability_authorization_responses(self):
        url = "/api/v1/time-slots"
        self.assertEqual(self.client.get(url, headers=self._headers(role="SUPERUSER")).status_code, 403)
        expired = make_token(exp=datetime.now(timezone.utc) - timedelta(seconds=1))
        self.assertEqual(self.client.get(url, headers=self._headers(token=expired)).status_code, 401)
        wrong_signature = jwt.encode(
            {"sub": "10", "role": "USER", "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
            "different-secret-key-with-32-characters", algorithm="HS256",
        )
        self.assertEqual(self.client.get(url, headers=self._headers(token=wrong_signature)).status_code, 401)
        with patch.dict(os.environ, {"JWT_SECRET_KEY": ""}):
            self.assertEqual(self.client.get(url, headers=self._headers(role="USER")).status_code, 503)

    def test_customer_availability_hides_slot_already_started_vietnam_time(self):
        with self.Session() as db:
            slot = TimeSlot(court_id=self.court_a_id, slot_date=self.FROZEN_BUSINESS_NOW.date(), start_time=time(9), end_time=time(11))
            db.add(slot)
            db.commit()
        self.assertEqual(self.client.get(f"/api/v1/time-slots?slot_date={self.FROZEN_BUSINESS_NOW.date().isoformat()}").json(), [])

    def test_expired_hold_cannot_be_confirmed_and_can_be_reacquired(self):
        with self.Session() as db:
            slot = TimeSlot(
                court_id=self.court_a_id,
                slot_date=date(2026, 11, 5),
                start_time=time(8),
                end_time=time(9),
            )
            db.add(slot)
            db.commit()
            slot_id = slot.id
        headers = {"X-Internal-Token": "court-internal-test-token"}
        hold_url = f"/api/v1/internal/slots/{slot_id}/hold?booking_id=700"
        initial_utc = datetime(2026, 10, 26, 0, 0)
        expired_utc = initial_utc + timedelta(minutes=11)
        with patch("app.routes._reservation_now", side_effect=[initial_utc, expired_utc, expired_utc]):
            first = self.client.post(hold_url, headers=headers)
            self.assertEqual(first.status_code, 200, first.text)
            expired = self.client.post(
                f"/api/v1/internal/slots/{slot_id}/confirm?booking_id=700", headers=headers
            )
            replacement = self.client.post(
                f"/api/v1/internal/slots/{slot_id}/hold?booking_id=701", headers=headers
            )
        self.assertEqual(expired.status_code, 409)
        self.assertEqual(replacement.status_code, 200, replacement.text)

    def test_reserved_time_slot_cannot_be_changed_or_deactivated(self):
        slot = self.client.post(
            "/api/v1/time-slots",
            json=self._time_slot_payload(self.court_a_id, "08:00:00", "09:00:00"),
            headers=self._headers(),
        )
        self.assertEqual(slot.status_code, 201, slot.text)
        slot_id = slot.json()["id"]
        internal_headers = {"X-Internal-Token": "court-internal-test-token"}
        self.assertEqual(
            self.client.post(
                f"/api/v1/internal/slots/{slot_id}/hold?booking_id=801",
                headers=internal_headers,
            ).status_code,
            200,
        )
        owner_headers = self._headers()
        changed = self._time_slot_payload(self.court_a_id, "08:00:00", "09:30:00")
        self.assertEqual(
            self.client.put(f"/api/v1/time-slots/{slot_id}", json=changed, headers=owner_headers).status_code,
            409,
        )
        self.assertEqual(
            self.client.delete(f"/api/v1/time-slots/{slot_id}", headers=owner_headers).status_code,
            409,
        )
        confirmed = self.client.post(
            f"/api/v1/internal/slots/{slot_id}/confirm?booking_id=801",
            headers=internal_headers,
        )
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        self.assertEqual(
            self.client.put(f"/api/v1/time-slots/{slot_id}", json=changed, headers=owner_headers).status_code,
            409,
        )

    def test_internal_booking_routes_require_internal_token(self):
        response = self.client.post(
            f"/api/v1/internal/slots/{self.slot_b_id}/hold?booking_id=501"
        )
        self.assertEqual(response.status_code, 403)

    def test_batch_hold_is_atomic_and_batch_release_preserves_newer_owner(self):
        with self.Session() as db:
            first = TimeSlot(court_id=self.court_a_id, slot_date=date(2026, 11, 1), start_time=time(11), end_time=time(12))
            second = TimeSlot(court_id=self.court_a_id, slot_date=date(2026, 11, 1), start_time=time(12), end_time=time(13))
            blocked = TimeSlot(court_id=self.court_a_id, slot_date=date(2026, 11, 1), start_time=time(13), end_time=time(14), reservation_status="HELD", reservation_booking_id=999, reservation_expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5))
            db.add_all([first, second, blocked])
            db.commit()
            first_id, second_id, blocked_id = first.id, second.id, blocked.id
        headers = {"X-Internal-Token": "court-internal-test-token"}
        failed = self.client.post(f"/api/v1/internal/slots/{first_id},{blocked_id}/hold?booking_id=501", headers=headers)
        self.assertEqual(failed.status_code, 409)
        with self.Session() as db:
            self.assertEqual(db.get(TimeSlot, first_id).reservation_status, "AVAILABLE")
            self.assertEqual(db.get(TimeSlot, blocked_id).reservation_booking_id, 999)

        held = self.client.post(f"/api/v1/internal/slots/{first_id},{second_id}/hold?booking_id=501", headers=headers)
        self.assertEqual(held.status_code, 200, held.text)
        self.assertEqual(len(held.json()["slots"]), 2)
        confirmed = self.client.post(f"/api/v1/internal/slots/{first_id},{second_id}/confirm?booking_id=501", headers=headers)
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        self.assertEqual(confirmed.json()["status"], "BOOKED")
        with self.Session() as db:
            newer = db.get(TimeSlot, second_id)
            newer.reservation_status = "HELD"
            newer.reservation_booking_id = 777
            newer.reservation_expires_at = datetime(2026, 11, 1, 10, 8)
            db.commit()
        released = self.client.post(f"/api/v1/internal/slots/{first_id},{second_id}/release?booking_id=501", headers=headers)
        self.assertEqual(released.status_code, 200, released.text)
        with self.Session() as db:
            self.assertEqual(db.get(TimeSlot, first_id).reservation_status, "AVAILABLE")
            self.assertEqual(db.get(TimeSlot, second_id).reservation_status, "HELD")
            self.assertEqual(db.get(TimeSlot, second_id).reservation_booking_id, 777)


if __name__ == "__main__":
    unittest.main()

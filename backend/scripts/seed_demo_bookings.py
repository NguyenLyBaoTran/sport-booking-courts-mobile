"""Create repeatable demo bookings through the real local Gateway APIs.

This script is intentionally opt-in and loopback-only. It never connects to a
database. Booking, payment, and QR records are created by their owning services.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen


GATEWAY_URL = os.environ.get("TASK4_GATEWAY_URL", "http://127.0.0.1:8000").rstrip("/")
CONFIRMATION = "CREATE_DEMO_BOOKINGS"
DEMO_VENUES = {
    "Demo Badminton Center A",
    "Demo Football Center B",
    "Demo Tennis Center C",
    "Demo Sports Center D",
    "Demo Basketball Center E",
    "Demo Badminton Center F",
}
CUSTOMERS = [
    "customer1@example.com", "customer2@example.com", "customer3@example.com",
    "vy.524h0040@example.com", "tran.524h0130@example.com",
    "customer4@example.com", "customer5@example.com", "customer6@example.com",
    "customer7@example.com", "customer8@example.com", "customer9@example.com",
    "customer10@example.com",
]


class ApiFailure(RuntimeError):
    pass


def request_json(path: str, token: str | None = None, body: dict | None = None, headers: dict | None = None):
    request_headers = {"Accept": "application/json"}
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    if headers:
        request_headers.update(headers)
    data = None
    if body is not None:
        request_headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    request = Request(GATEWAY_URL + path, data=data, headers=request_headers, method="POST" if body is not None else "GET")
    try:
        with urlopen(request, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = ""
        try:
            detail = json.loads(error.read().decode("utf-8")).get("detail", "")
        except (ValueError, AttributeError):
            pass
        raise ApiFailure(f"API returned HTTP {error.code}: {detail or 'request failed'}") from None
    except (URLError, TimeoutError) as error:
        raise ApiFailure(f"Could not reach the local Gateway: {error.reason if isinstance(error, URLError) else 'timeout'}") from None


def slot_key(slot_ids: list[int]) -> tuple[int, ...]:
    return tuple(slot_ids)


def planned_groups(slots: list[dict], limit: int = 200) -> list[list[dict]]:
    by_court_date: dict[tuple[int, str], list[dict]] = defaultdict(list)
    for slot in slots:
        by_court_date[(int(slot["court_id"]), str(slot["slot_date"]))].append(slot)
    groups: list[list[dict]] = []
    for run_key in sorted(by_court_date):
        ordered = sorted(by_court_date[run_key], key=lambda item: str(item["start_time"]))
        runs: list[list[dict]] = []
        current: list[dict] = []
        previous_end = None
        for slot in ordered:
            if previous_end is not None and str(slot["start_time"]) != previous_end:
                if current:
                    runs.append(current)
                current = []
            current.append(slot)
            previous_end = str(slot["end_time"])
        if current:
            runs.append(current)
        for run in runs:
            index = 0
            while index < len(run) and len(groups) < limit:
                planned_count = 3 if len(groups) % 10 == 0 else (2 if len(groups) % 4 == 0 else 1)
                count = min(planned_count, len(run) - index)
                groups.append(run[index:index + count])
                index += count
            if len(groups) >= limit:
                return groups
    return groups


def exact_booking_for(group: list[dict], bookings: list[dict]):
    target = slot_key([int(slot["id"]) for slot in group])
    for booking in bookings:
        ids = booking.get("time_slot_ids") or [booking.get("time_slot_id")]
        if slot_key([int(value) for value in ids]) == target:
            return booking
    return None


def main() -> int:
    parsed = urlparse(GATEWAY_URL)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        print("Refusing non-loopback Gateway URL; this seed utility is local-development only.", file=sys.stderr)
        return 2
    if os.environ.get("TASK4_SEED_CONFIRM") != CONFIRMATION:
        print(f"Set TASK4_SEED_CONFIRM={CONFIRMATION} to create demo bookings via the local API.", file=sys.stderr)
        return 2

    password = "password123"
    tokens: dict[str, str] = {}
    try:
        # Authenticate every account before creating any records. Existing account
        # passwords are never changed; a conflict stops before booking writes.
        for email in CUSTOMERS:
            session = request_json(
                "/api/v1/auth/login",
                body={"email": email, "password": password},
            )
            user = session.get("user") or {}
            if user.get("role") != "USER" or not session.get("access_token"):
                raise ApiFailure(f"{email} is not an active customer account.")
            tokens[email] = session["access_token"]

        venues = request_json("/api/v1/venues")
        venue_ids = {int(item["id"]) for item in venues if item.get("name") in DEMO_VENUES and item.get("is_active")}
        if not venue_ids:
            raise ApiFailure("No active Task 4 demo venues found; run the catalogue seed first.")
        courts = request_json("/api/v1/courts")
        demo_court_ids = [int(item["id"]) for item in courts if int(item.get("venue_id", 0)) in venue_ids and item.get("is_active")]
        token = next(iter(tokens.values()))
        slots: list[dict] = []
        for court_id in demo_court_ids:
            query = urlencode({"court_id": court_id, "is_active": "true"})
            slots.extend(request_json(f"/api/v1/time-slots?{query}", token=token))
        slots = [item for item in slots if item.get("is_active") and item.get("slot_date")]
        groups = planned_groups(slots)
        if len(groups) < 40:
            raise ApiFailure(f"Only {len(groups)} future slot groups are available; at least 40 are required.")

        booking_lists: dict[str, list[dict]] = {
            email: request_json("/api/v1/bookings", token=customer_token)
            for email, customer_token in tokens.items()
        }
        created_bookings = 0
        already_present = 0
        paid_count = 0
        failed_count = 0
        skipped = 0
        demo_booking_ids: set[int] = set()
        for index, group in enumerate(groups):
            if created_bookings + already_present >= 40:
                break
            email = CUSTOMERS[index % len(CUSTOMERS)]
            customer_token = tokens[email]
            selected_ids = [int(item["id"]) for item in group]
            existing = exact_booking_for(group, booking_lists[email])
            if existing and existing.get("status") in {"FAILED", "CANCELLED", "EXPIRED"}:
                already_present += 1
                demo_booking_ids.add(int(existing["id"]))
                continue
            if not existing and any(item.get("reservation_status") != "AVAILABLE" for item in group):
                skipped += 1
                continue

            if existing:
                booking = existing
                already_present += 1
                demo_booking_ids.add(int(booking["id"]))
            else:
                quote_path = quote(",".join(str(value) for value in selected_ids), safe=",")
                request_json(f"/api/v1/booking-quotes/{quote_path}", token=customer_token)
                booking = request_json(
                    "/api/v1/bookings",
                    token=customer_token,
                    body={"time_slot_ids": selected_ids},
                )
                booking_lists[email].append(booking)
                created_bookings += 1
                demo_booking_ids.add(int(booking["id"]))

            if booking.get("status") not in {"PENDING", "CONFIRMED"}:
                continue
            outcome = "FAILED" if (index + 1) % 10 == 0 else "SUCCESS"
            idempotency_key = "task4-demo-" + "-".join(str(value) for value in selected_ids)
            payment = request_json(
                "/api/v1/payments/process",
                token=customer_token,
                body={"booking_id": int(booking["id"]), "mock_result": outcome},
                headers={"Idempotency-Key": idempotency_key},
            )
            if payment.get("status") == "PAID":
                paid_count += 1
            elif payment.get("status") == "FAILED":
                failed_count += 1

        verified_payment_count = 0
        for email, customer_token in tokens.items():
            payments = request_json("/api/v1/payments", token=customer_token)
            verified_payment_count += sum(
                1 for item in payments if int(item.get("booking_id", 0)) in demo_booking_ids
            )

        print(json.dumps({
            "future_slot_groups": len(groups),
            "bookings_created": created_bookings,
            "existing_bookings_reused": already_present,
            "paid_payments": paid_count,
            "failed_payments": failed_count,
            "payments_verified_from_history": verified_payment_count,
            "conflicting_groups_skipped": skipped,
        }, indent=2))
        return 0
    except ApiFailure as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

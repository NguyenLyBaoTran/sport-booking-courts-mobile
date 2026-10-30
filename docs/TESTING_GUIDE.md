# Local Test Guide — Auth, Booking, Payment

Run commands from the repository root unless a command changes directory. On
macOS/Linux, use the repository virtual environment:

```bash
.venv/bin/python -m pip install -r backend/requirements.txt
```

Do not run database reset commands against a database containing data you need.
Never commit `backend/.env` or share its secrets.

## 1. Configure and initialize

Copy `backend/.env.example` to `backend/.env` if it does not already exist. Set:

- `USER_DATABASE_URL`, `BOOKING_DATABASE_URL`, `PAYMENT_DATABASE_URL` to local
  databases.
- `JWT_SECRET_KEY` to a random value of at least 32 characters.
- The same unpredictable `INTERNAL_SERVICE_TOKEN` for Booking, Payment, and Court.
- `COURT_SERVICE_URL` and `BOOKING_SERVICE_URL` to the reachable service URLs.
- `APP_ENV=development` for the local Owner/Admin account tool.

Create the databases using `backend/scripts/create_databases.sql` or your local
database tooling. Apply the User Service migration and initialize the development
Booking/Payment schemas:

```bash
cd backend/services/user_service
../../../.venv/bin/python -m alembic -c alembic.ini upgrade head

cd ../booking_service
../../../.venv/bin/python -m app.init_db

cd ../payment_service
../../../.venv/bin/python -m app.init_db
```

The Booking/Payment initializer uses `create_all` for local development; it is not
a production migration strategy. Create a test customer via the register API. To
create an Owner/Admin, run `python -m app.create_test_account` from the User Service
directory; its password prompt is hidden, and it prints the new user ID. Run it
once with role `OWNER` and again with role `ADMIN` if both accounts are needed.
The password is chosen by the developer and cannot be recovered from the database;
keep test credentials in a password manager or another private, untracked location.

## 2. Run automated tests

These tests use isolated in-memory SQLite databases. Booking/Payment tests mock
their upstream service calls; they do not require MySQL or a running Court Service.

```bash
cd backend/services/user_service
../../../.venv/bin/python -m pytest -q

cd ../booking_service
../../../.venv/bin/python -m pytest -q

cd ../payment_service
../../../.venv/bin/python -m pytest -q
```

Expected at the time this guide was written: User `7 passed`, Booking `7 passed`,
Payment `4 passed`.

## 3. Start the services

Start Court Service first; its slot APIs must implement the internal contract in
[`API_CONTRACT.md`](./API_CONTRACT.md). Then use separate terminals:

```bash
cd backend/services/user_service
../../../.venv/bin/python -m uvicorn app.main:app --reload --port 8001
```

```bash
cd backend/services/booking_service
../../../.venv/bin/python -m uvicorn app.main:app --reload --port 8003
```

```bash
cd backend/services/payment_service
../../../.venv/bin/python -m uvicorn app.main:app --reload --port 8004
```

```bash
cd backend/gateway
../../.venv/bin/python -m uvicorn main:app --reload --port 8000
```

Check `/health` and `/health/db` on ports `8001`, `8003`, and `8004`, plus
`http://127.0.0.1:8000/health`. Database health must report connected.

## 4. Test Auth through the Gateway

Register a customer (use a unique email for each run):

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"full_name":"Test Customer","email":"customer-test@example.test","password":"test-pass-123","phone":"0900000000"}'
```

Login and copy the `access_token` from the response:

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"customer-test@example.test","password":"test-pass-123"}'
```

Use that token to read the profile:

```bash
curl -i http://127.0.0.1:8000/api/v1/users/me \
  -H 'Authorization: Bearer <CUSTOMER_ACCESS_TOKEN>'
```

Expected: register `201`, login `200`, profile `200` with role `USER`. A missing
or invalid token on `/users/me` should return `401`.

## 5. Test Booking and Payment end-to-end

This section requires a live Court Service with an active sport, venue, court and
available slot. Ask Court Service for an available `time_slot_id`; do not guess an
ID. The Court hold response must include the fields listed in `API_CONTRACT.md`.

Create a booking:

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/bookings \
  -H 'Authorization: Bearer <CUSTOMER_ACCESS_TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{"time_slot_id":<AVAILABLE_SLOT_ID>}'
```

Expected: `201`, `status: PENDING`, amount and `expires_at`; the Court Service
should show that the slot is held. Save the returned booking `id`.

Try one failed mock-payment attempt; it must not confirm the booking:

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/payments/process \
  -H 'Authorization: Bearer <CUSTOMER_ACCESS_TOKEN>' \
  -H 'Idempotency-Key: payment-failure-test-1' \
  -H 'Content-Type: application/json' \
  -d '{"booking_id":<BOOKING_ID>,"mock_result":"FAILED"}'
```

Retry with a new idempotency key and success result:

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/payments/process \
  -H 'Authorization: Bearer <CUSTOMER_ACCESS_TOKEN>' \
  -H 'Idempotency-Key: payment-success-test-1' \
  -H 'Content-Type: application/json' \
  -d '{"booking_id":<BOOKING_ID>,"mock_result":"SUCCESS"}'
```

Expected: payment `PAID`, booking `CONFIRMED`, and an opaque `qr_token`. Repeating
the same request/key must not create a second successful payment. `GET
/api/v1/bookings`, `GET /api/v1/bookings/{id}`, and `GET /api/v1/payments` should
show only the signed-in customer's records. Try reading another user's booking ID;
it should return `404`.

## 6. Test Owner check-in and completion

The Owner-facing Court API must authenticate the Owner, verify that the booking
belongs to one of their venues, then call Booking Service using the shared internal
token. Do not expose the internal token to the browser. For a local direct test,
send the configured `INTERNAL_SERVICE_TOKEN` from a trusted terminal:

```bash
curl -i -X POST http://127.0.0.1:8003/api/v1/internal/bookings/check-in \
  -H 'X-Internal-Token: <INTERNAL_SERVICE_TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{"owner_id":<OWNER_ID>,"qr_token":"<QR_TOKEN_FROM_PAYMENT>"}'
```

Expected: `CHECKED_IN`. Repeating check-in should return `409`. Complete the
checked-in booking:

```bash
curl -i -X POST http://127.0.0.1:8003/api/v1/internal/bookings/<BOOKING_ID>/complete \
  -H 'X-Internal-Token: <INTERNAL_SERVICE_TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{"owner_id":<OWNER_ID>}'
```

Expected: `COMPLETED`. This direct call only tests Booking's state transition; the
real integration test must go through Court's Owner-authenticated endpoint.

## Owner/Admin manual demo checklist

Use the local demo accounts and database setup in [Backend README](../backend/README.md#local-demo-setup). Record actual outcomes during the demo; do not pre-mark a manual test as passed.

| ID | Role | Action | Expected result | Actual result | Status |
|---|---|---|---|---|---|
| A1 | ADMIN | Login and open dashboard | ADMIN workspace; available catalogue counts come from API | | |
| A2 | ADMIN | Create, edit, deactivate a test Sport | Changes appear after successful API responses | | |
| A3 | ADMIN | Create/edit/deactivate a test Venue and Court | System-wide changes persist and remain visible | | |
| A4 | ADMIN | Create/edit/deactivate future Time Slots | Validation rejects invalid or overlapping slots | | |
| A5 | ADMIN | Open Users/Owners | Management API is unavailable until S1 provides it | | PENDING S1 |
| A6 | ADMIN | Open Bookings/Check-ins | Management API is unavailable until S1 provides it | | PENDING S1 |
| O1 | OWNER | Login and open dashboard | OWNER workspace shows only owned catalogue data | | |
| O2 | OWNER | Create/edit/deactivate own Venue, Court, and Time Slot | Changes persist through API | | |
| O3 | OWNER | Open Bookings, filters, and booking detail | Only own venue bookings appear; `qr_token` is hidden | | |
| O4 | OWNER | Check in a valid Customer QR, then scan it again | First request checks in; duplicate returns `409` | | |
| O5 | OWNER | Complete a checked-in booking and reload | Status remains `COMPLETED` after reload | | |
| O6 | OWNER | Try a resource owned by the other demo Owner | Backend denies access without exposing the record | | |
| C1 | CUSTOMER | Login and browse Sports/Venues/Courts/Time Slots | Public catalogue loads | | |
| C2 | CUSTOMER | Create a booking and complete mock payment through API | Booking is `PENDING`, then `CONFIRMED`; QR comes from Booking API | | |
| C3 | CUSTOMER | Open booking history and QR in Android | Booking/history/QR UI is not implemented in current Android client | | PENDING S1 |
| X1 | ADMIN/OWNER | Logout, then reopen a protected page | Session clears and protected page requires login | | |

## 7. Expiry and common failures

The automated Booking tests cover expiry and slot release. In a live setup, the
trusted scheduler should call the internal
`POST /api/v1/internal/bookings/expire` endpoint with `X-Internal-Token`. An expired
booking should release its held slot through Court Service.

- `401`: access token missing or invalid.
- `403`: wrong role or invalid internal token.
- `404`: booking does not exist or belongs to another user/Owner.
- `409`: slot unavailable, expired/unpayable booking, duplicate check-in, invalid
  status transition, or idempotency conflict.
- `503`/`504`: database or dependent service unavailable/timed out.

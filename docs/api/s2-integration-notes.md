# S2 Integration Notes

> Historical pre-integration audit. Its branch and blocker statements below describe the review snapshot, not the current `develop` branch. S1/S2 integration was merged by PR #6; use the current [Owner Booking & QR contract](owner-booking-qr-contract.md), [Court Service contract](court-service-api-contract.md), and [Management Web guide](../../management-web/README.md) for integrated behavior and setup.

## Reviewed branch and contracts

- Working branch: `feature/s2-court-service`.
- S1 was inspected read-only from `origin/feature/s1-w1-auth-usecase`; `docs/API_CONTRACT.md` is the source for Auth, Booking, Payment, and Booking–Court internal paths. No S1 file was edited.
- Auth issues HS256 JWTs with `sub` (numeric ID serialized as a string), `role`, `iat`, and `exp`. Court verifies those claims locally using the same `JWT_SECRET_KEY` and `JWT_ALGORITHM=HS256`.
- S1 uses `USER_DATABASE_URL`, `COURT_DATABASE_URL`, `BOOKING_DATABASE_URL`, and `PAYMENT_DATABASE_URL`, and service URLs on ports 8001–8004. Gateway defaults to 8000 and forwards Auth, Court, Booking, and Payment public prefixes. The inspected S1 Gateway snapshot omits `/api/v1/time-slots`; the current S2 Gateway already routes it to Court and has a regression test, so retain that route when integrating. `/api/v1/internal` is deliberately not routed by Gateway.
- S1 Booking calls Court directly using `POST /api/v1/internal/slots/{slot_id}/hold|confirm|release`, query `booking_id`, and `X-Internal-Token`. Court now implements these exact route shapes and response fields. The configured `INTERNAL_SERVICE_TOKEN` and `BOOKING_HOLD_MINUTES` must match in Booking and Court.

## Authorization and Management Web

- ADMIN can create, update, and soft-deactivate Sports. ADMIN also has system-wide Venue, Court, and Time Slot write access through Court Service. OWNER Venue, Court, and Time Slot mutations remain limited to Venues owned by the authenticated `sub`; Venue creation requires matching `owner_id`, and OWNER updates cannot transfer ownership. USER cannot mutate Court resources.
- Management Web exposes ADMIN Sports, Venue, and Court catalogue CRUD. Owner-facing CRUD remains scoped to the authenticated Owner. Admin Time Slot mutations are available through the Court API, but no Admin schedule screen is wired in this Web iteration.
- Login and token forwarding follow the S1 `/auth/login` and `/users/me` contracts. The access token stays in browser `sessionStorage`; the JWT secret never reaches the frontend.
- Booking and Payment remain owned by S1. This checkout does not contain the inspected Auth, Booking, or Payment implementation until the normal integration workflow brings those changes into the working branch.

## Database migration and safe test data

Court reservations add `reservation_status`, `reservation_booking_id`, and `reservation_expires_at` to `time_slots`. The schema change is in `backend/migrations/20261026_add_time_slot_reservations.sql`. It has not been applied. Hold/confirm/release and reserved slot edits lock the slot row; schedule create/update locks the affected Court rows during overlap checks. Do not run the migration against an existing database without explicit approval; use a disposable Court DB for live integration checks.

The following is an instruction template only; it was not executed. It creates records through the actual APIs. Supply a real ADMIN token and an OWNER token provisioned by S1, and point services to disposable databases. Do not substitute guessed IDs or assign privileged roles through this flow.

```powershell
$gateway = 'http://127.0.0.1:8000'
$court = 'http://127.0.0.1:8002'
$adminHeaders = @{ Authorization = 'Bearer <ADMIN_TOKEN>' }
$ownerHeaders = @{ Authorization = 'Bearer <OWNER_TOKEN>' }

# Create Sport through the ADMIN-only API.
$sport = Invoke-RestMethod -Method Post -Uri "$gateway/api/v1/sports" -Headers $adminHeaders `
  -ContentType 'application/json' -Body (@{ name = 'S2 Integration Badminton'; description = 'Disposable integration record'; is_active = $true } | ConvertTo-Json)

# Resolve the real Owner ID from the signed-in S1 profile, then create related records.
$owner = Invoke-RestMethod -Method Get -Uri "$gateway/api/v1/users/me" -Headers $ownerHeaders
$venue = Invoke-RestMethod -Method Post -Uri "$gateway/api/v1/venues" -Headers $ownerHeaders `
  -ContentType 'application/json' -Body (@{ owner_id = $owner.id; name = 'S2 Integration Venue'; address = '1 Test Street'; is_active = $true } | ConvertTo-Json)
$courtRecord = Invoke-RestMethod -Method Post -Uri "$gateway/api/v1/courts" -Headers $ownerHeaders `
  -ContentType 'application/json' -Body (@{ venue_id = $venue.id; sport_id = $sport.id; name = 'S2 Integration Court'; price_per_hour = '25.00'; is_active = $true } | ConvertTo-Json)

# Use a date/time safely in the future in Asia/Ho_Chi_Minh, on a 30-minute boundary.
$slotDate = (Get-Date).AddDays(3).ToString('yyyy-MM-dd')
$slot = Invoke-RestMethod -Method Post -Uri "$gateway/api/v1/time-slots" -Headers $ownerHeaders `
  -ContentType 'application/json' -Body (@{ court_id = $courtRecord.id; slot_date = $slotDate; start_time = '08:00:00'; end_time = '09:00:00'; is_active = $true } | ConvertTo-Json)

# Booking–Court check: call Court directly with the shared internal token, then release this test hold.
$internalHeaders = @{ 'X-Internal-Token' = '<SHARED_INTERNAL_SERVICE_TOKEN>' }
$hold = Invoke-RestMethod -Method Post -Uri "$court/api/v1/internal/slots/$($slot.id)/hold?booking_id=900001" -Headers $internalHeaders
Invoke-RestMethod -Method Post -Uri "$court/api/v1/internal/slots/$($slot.id)/release?booking_id=900001" -Headers $internalHeaders
```

After verifying the test, soft-deactivate the Time Slot, Court, Venue, and Sport using their `DELETE /api/v1/{time-slots|courts|venues|sports}/{id}` APIs with the matching Owner or Admin token. Prefer dropping the disposable databases after the run. Never use the sample booking ID against a shared environment.

## Verification state and blockers (at the time of this audit)

- Court authorization and reservation behavior are covered with isolated SQLite test databases; these tests do not write to the configured MySQL databases.
- The S1 API contract expects these paths and payloads; its inspected Booking code calls Court directly, so the Gateway does not need to proxy internal reservation paths.
- At the time of this pre-integration audit, end-to-end Auth/Booking/Payment integration had not yet been run; S1 source had not yet been merged, and no live service stack or database migration had been used.
- The audit's planned prerequisites were a shared JWT secret in User and Court, a matching internal token and hold TTL in Booking and Court, applying the Court migration only to a disposable DB, and using provisioned OWNER/ADMIN credentials. Treat this as historical planning; use the current backend and Management Web guides for setup.

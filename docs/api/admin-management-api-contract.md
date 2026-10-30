# Admin Management API Contract

**S2/S1 Admin management contract — Court catalogue summary implemented in S2; Admin User and Booking APIs remain proposed and pending S1 implementation.**

This contract is based on the integrated source schemas currently present. It does not claim that the proposed Admin User or Booking APIs exist. Existing public catalogue GET behavior and existing Owner/Customer routes remain unchanged.

## 1. Ownership and service boundaries

| Data | Owner | API work |
|---|---|---|
| Users and account status | User Service (S1) | Admin list/detail/status endpoints proposed below |
| Bookings and check-in history | Booking Service (S1) | Admin read-only list/detail/history endpoints proposed below |
| Sports, venues, courts, slots | Court Service (S2) | Existing CRUD; Admin catalogue summary endpoint proposed for dashboard |
| Gateway routes | Gateway (S2) | Explicit prefixes to the owning service; no internal route exposure |
| Admin UI | Management Web (S2) | API Mode consumes only the APIs listed here; Demo data remains isolated |

All new Admin endpoints require a valid Bearer JWT with `role=ADMIN`. The service owning the data enforces authorization; Gateway routing and frontend visibility are not authorization controls.

## 2. Pagination and common errors

Proposed list endpoints use `page` (1-based, default `1`) and `page_size` (default `25`, maximum `100`) and return records ordered by newest creation time then descending ID, unless a history-specific timestamp is stated. Date ranges are inclusive calendar dates in `Asia/Ho_Chi_Minh`. They return:

```json
{"items": [], "total": 0, "page": 1, "page_size": 25}
```

This is a new convention for these Admin endpoints; S1 must confirm it before implementation. Invalid query values return `422`. Missing/invalid JWT returns `401`; valid non-Admin JWT returns `403`. Resource IDs not found return `404`. Status transition conflicts return `409`. Responses must not include password hashes, QR tokens, internal tokens, or other credentials.

## 3. User Service — proposed Admin APIs (S1)

### `GET /api/v1/admin/users`

ADMIN only. Query: `page`, `page_size`, optional `q` (name/email substring), `role` (`USER|OWNER|ADMIN`), and `is_active` (`true|false`). Search/filter over the existing User fields. Response uses a paginated projection of `id`, `full_name`, `email`, `phone`, `role`, `is_active`, `created_at`; never `password_hash`.

Example item:

```json
{"id": 17, "full_name": "Nguyen Van A", "email": "owner@example.test", "phone": null, "role": "OWNER", "is_active": true, "created_at": "2026-10-30T08:00:00Z"}
```

### `GET /api/v1/admin/users/{id}`

ADMIN only. Returns the same safe User projection, or `404`.

### `PATCH /api/v1/admin/users/{id}/status`

ADMIN only. Request:

```json
{"is_active": false}
```

Response: updated safe User projection. The existing `users.is_active` column supports this operation; no schema migration is needed. Return `404` for a missing user and `409` if the request would deactivate the acting Admin or the last active Admin. Those safeguards need a transaction/locking strategy to avoid concurrent requests disabling all Admins.

```json
{"id": 17, "full_name": "Nguyen Van A", "email": "owner@example.test", "phone": null, "role": "OWNER", "is_active": false, "created_at": "2026-10-30T08:00:00Z"}
```

**JWT behavior requiring S1 decision:** User Service checks `is_active` at login and `/users/me`, but Court, Booking, and Payment currently validate signed JWT claims without checking the User row. Deactivation therefore does not immediately revoke an already issued JWT at those services; it remains usable there until expiry. Before claiming account suspension is immediate, S1 must add a revocation/introspection mechanism or explicitly accept and document the token-expiry window. Do not add a new role-changing or Owner-creation API in this scope.

## 4. Booking Service — proposed read-only Admin APIs (S1)

All responses use a safe Admin booking projection based on existing Booking fields: `id`, `user_id`, `time_slot_id`, `court_id`, `venue_id`, `owner_id`, `slot_date`, `start_time`, `end_time`, `status`, `total_amount`, `expires_at`, `checked_in_by`, `checked_in_at`, `completed_at`, `created_at`. Never include `qr_token`.

### `GET /api/v1/admin/bookings`

ADMIN only. Query: pagination plus optional `booking_id`, `status`, `date_from`, `date_to`, `venue_id`, `court_id`, `owner_id`, `user_id`. These filters map to existing Booking columns. Response is paginated and ordered newest first.

Example item:

```json
{"id": 42, "user_id": 8, "owner_id": 12, "time_slot_id": 91, "venue_id": 4, "court_id": 7, "slot_date": "2026-10-29", "start_time": "18:00:00", "end_time": "19:00:00", "status": "CHECKED_IN", "total_amount": "180.00", "expires_at": null, "checked_in_by": 12, "checked_in_at": "2026-10-29T11:00:00Z", "completed_at": null, "created_at": "2026-10-28T10:15:00Z"}
```

### `GET /api/v1/admin/bookings/{id}`

ADMIN only. Returns one safe booking projection or `404`. Read-only; Admin cannot check in, complete, cancel, or otherwise transition booking state through these APIs.

### `GET /api/v1/admin/checkins`

ADMIN only. Read-only history derived from Booking rows with non-null `checked_in_at`; no new Check-in table or synthetic Check-in ID. Query: pagination plus optional `date_from`, `date_to` (applied to `checked_in_at` in `Asia/Ho_Chi_Minh`), `venue_id`, `court_id`, `checked_in_by`, and `booking_id`. Each item is a booking projection containing at least booking ID, venue/court IDs, `checked_in_by`, and `checked_in_at`. No QR token. Results are ordered by `checked_in_at` descending, then booking ID descending.

Example item is the same safe Booking projection above; the booking `id` is the history row identifier, and `checked_in_by` is the existing Owner user ID. There is no generated Check-in ID.

Customer-facing `/api/v1/bookings` and Owner `/api/v1/owner/bookings` behavior is unchanged.

## 5. Court Service — Admin catalogue summary (S2, implemented)

### `GET /api/v1/admin/catalogue/summary`

ADMIN only; read-only aggregate counts from Court Service's own database. No query parameters. Response:

```json
{
  "sports": {"total": 8, "active": 7},
  "venues": {"total": 12, "active": 10},
  "courts": {"total": 35, "active": 32},
  "time_slots": {"total": 240, "active": 220}
}
```

Values are illustrative. Counts must be computed with database aggregates, not by downloading the unpaginated public catalogue. No schema change or migration is needed. Return `401`/`403` for auth failures and a safe `503` if the database is unavailable.

## 6. Dashboard contract and availability

The Dashboard must not ask Gateway to read another service's database. The UI may call separate summaries owned by each service:

| Proposed endpoint | Owner | Measures |
|---|---|---|
| `GET /api/v1/admin/users/summary` | User Service / S1 | Total Users, Owners, active and inactive accounts |
| `GET /api/v1/admin/catalogue/summary` | Court Service / S2 — implemented | Sports, Venues, Courts, Time Slots; total and active |
| `GET /api/v1/admin/bookings/summary` | Booking Service / S1 | Total bookings, checked-in and completed |

Proposed response shapes (no date-window query in the first version):

```json
{"users": {"total": 120, "active": 116, "inactive": 4}, "owners": {"total": 18, "active": 16, "inactive": 2}}
```

```json
{"bookings": {"total": 320, "checked_in": 12, "completed": 250}}
```

The User and Booking summary routes and schemas are proposals, not implemented. S1 must confirm exact count definitions and error behavior. The Court catalogue summary is implemented and covered by Court authorization/count tests. Until User and Booking summaries are available, API Mode displays those cards as unavailable; it must not derive global totals by fetching every row or substitute Demo metrics. No revenue summary is proposed because the current Payment schema and endpoints do not define an Admin reporting contract.

## 7. Gateway routing (S2)

Add only these explicit prefix mappings after approval/implementation by the owning service:

| Prefix | Upstream |
|---|---|
| `/api/v1/admin/users` | User Service |
| `/api/v1/admin/bookings` | Booking Service |
| `/api/v1/admin/checkins` | Booking Service |
| `/api/v1/admin/catalogue` | Court Service |

The existing Gateway forwards `Authorization` and preserves upstream status/body. It must continue returning `404` for `/api/v1/internal/...`; do not add a catch-all Admin or internal route. Add summary endpoints under the listed prefixes, avoiding overlapping service ownership.

## 8. S1/S2 responsibilities and implementation sequence

| Work | Owner | Dependency / tests |
|---|---|---|
| User Admin list/detail/status, authorization, safe response, self/last-Admin safeguards and JWT revocation decision | S1 | User model already has `is_active`; add User Service tests for role, filters, pagination, status conflicts, and password-hash exclusion |
| Booking Admin list/detail/check-in history, read-only authorization and safe projections | S1 | Booking already stores check-in fields; add Booking tests for role, filters, pagination, ownership-independent global view, and QR exclusion |
| Catalogue summary | S2 — implemented | Court DB only; SQLite in-memory tests for ADMIN/OWNER/USER and counts |
| Explicit Gateway route mappings | S2 | Mock-upstream tests for destinations, query/header/status passthrough and internal 404 |
| Admin Users/Bookings/Check-ins API Mode screens and client | S2 | Consume this contract; mocked frontend tests; show API errors without Demo fallback |
| Dashboard summary integration | S2 | Court summary can be integrated first; User/Booking cards remain unavailable until S1 endpoints exist |

S1 can implement User and Booking APIs in parallel after confirming the shared pagination and response rules. S2 can implement the Court summary, Gateway mappings, and frontend structure in parallel. End-to-end Admin screens depend on S1 endpoints being merged/integrated and contract-compatible.

## 9. RBAC baseline and known gaps

- Court Service already enforces Admin-only Sports writes and Owner/Admin Venue/Court/Time Slot writes; Owner writes are scoped through owned venues. Existing catalogue GET routes remain public by design and are unchanged here.
- Booking Service enforces Customer-owned booking APIs and Owner ownership for Owner booking/check-in/completion flows. It has no Admin read APIs yet.
- User Service has no Admin routes or Admin role dependency yet. The `is_active` field exists, but account administration does not.
- Frontend route guards are usability controls only; every new endpoint must enforce ADMIN in its owning backend service.
- CUSTOMER must receive `403` on all new Admin endpoints. OWNER must receive `403`; no Owner data access is granted by the new Admin contract.

## 10. Open items before S1 implementation

1. Confirm the shared pagination envelope and maximum page size.
2. Confirm whether account deactivation may remain effective only for new login/`/users/me` until JWT expiry, or implement immediate revocation across services.
3. Confirm the last-active-Admin safeguard and concurrency handling.
4. Confirm Booking filter names/date semantics and whether the check-in query's `owner_id` filter is named `checked_in_by` instead.
5. Confirm exact summary metric definitions and whether summaries need time-window filters.
6. Confirm all Admin API response schemas and error details before S1 begins implementation.

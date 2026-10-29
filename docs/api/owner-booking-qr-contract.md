# Owner Booking & QR Check-in API Contract

**Approved Design Contract — Pending Implementation**

This document records the approved shared design for Owner booking reads, completion, and QR check-in. The new public endpoints below are proposals approved for implementation; they are **not implemented or verified as available** in the inspected source. Existing Booking internal endpoints remain unchanged.

## 1. Overview

The Booking Service (S1) owns booking data and all booking state transitions. It will provide Owner-scoped list/detail and completion APIs. The Court Service (S2) will provide a thin QR check-in adapter: validate the Owner JWT, derive `owner_id` from JWT `sub`, then call Booking Service's existing internal check-in API server-side.

The verified Booking model stores `owner_id`, `venue_id`, `court_id`, `time_slot_id`, `slot_date`, `start_time`, `end_time`, `status`, `total_amount`, `expires_at`, `qr_token`, `checked_in_at`, `completed_at`, and `created_at`. Existing `BookingResponse` includes `qr_token`, so Owner endpoints must use an Owner-specific response schema that omits it. Existing `BookingCheckIn` accepts `owner_id` and `qr_token`; the adapter supplies `owner_id`, never the browser.

The approved design decisions are:

- Booking ownership is checked using `booking.owner_id` in Booking Service.
- `owner_id` is the authenticated user ID from JWT `sub`; it is distinct from `venue_id`.
- Owner list filters: `venue_id`, `date`, and `status`; pagination is out of scope for the first version.
- Missing and other-owner bookings return `404`.
- Duplicate check-in and repeated completion return `409`.
- Owner responses never contain `qr_token`.
- Gateway routes Owner bookings to Booking Service and QR check-in to Court Service.
- `JWT_SECRET_KEY` is shared consistently by the services that verify the access token.
- Internal API paths and `X-Internal-Token` remain backend-only.

## 2. API Endpoints

All paths below are relative to the API Gateway base `/api/v1`.

| Method and path | Owner | Authentication | State effect |
|---|---|---|---|
| `GET /owner/bookings` | S1 Booking | JWT `OWNER` | None |
| `GET /owner/bookings/{booking_id}` | S1 Booking | JWT `OWNER` | None |
| `POST /owner/bookings/{booking_id}/complete` | S1 Booking | JWT `OWNER` | `CHECKED_IN` → `COMPLETED` |
| `POST /owner/checkins` | S2 Court adapter | JWT `OWNER` | Delegates `CONFIRMED` → `CHECKED_IN` to S1 internal API |

These paths do not conflict with existing S1 `/bookings/{booking_id}` routes or `/internal/bookings/...` routes. They are new design endpoints and remain pending implementation.

### 2.1 Owner booking list

`GET /api/v1/owner/bookings`

Optional query parameters:

| Name | Type | Rule |
|---|---|---|
| `venue_id` | positive integer | Must be a venue associated with the authenticated Owner; otherwise return an empty list or `404` according to implementation consistency. Recommended: empty list. |
| `date` | `YYYY-MM-DD` | Matches `Booking.slot_date`. |
| `status` | string | One of `PENDING`, `CONFIRMED`, `CHECKED_IN`, `COMPLETED`, `CANCELLED`, `EXPIRED`. |

List results are always scoped by `booking.owner_id == int(JWT.sub)`. Query filters narrow this scope and cannot widen it. No pagination in the first version.

### 2.2 Owner booking detail

`GET /api/v1/owner/bookings/{booking_id}`

Return the booking only if `booking.owner_id == int(JWT.sub)`. Return `404` both when absent and when owned by another Owner.

### 2.3 Complete booking

`POST /api/v1/owner/bookings/{booking_id}/complete`

No request body. Booking Service derives the Owner ID from JWT, checks `booking.owner_id`, locks/updates the booking using the existing completion business rules, and commits `CHECKED_IN` → `COMPLETED`. A booking in any other state, including an already `COMPLETED` booking, returns `409`.

The existing internal completion endpoint remains available only to trusted services; the public endpoint must reuse its business logic rather than duplicate or weaken it.

### 2.4 QR check-in adapter

`POST /api/v1/owner/checkins`

Request body contains only `qr_token`. Browser-supplied `owner_id`, `venue_id`, or booking data is not accepted. The adapter verifies the JWT role is `OWNER`, parses `sub` as `owner_id`, and sends the following request to the existing S1 internal endpoint:

`POST /api/v1/internal/bookings/check-in`

Header `X-Internal-Token` is added by Court Service from server-side configuration. The adapter does not implement booking lookup, ownership decisions, row locking, or state mutation; S1 remains authoritative for those operations.

## 3. Request/Response Examples

### 3.1 List bookings

```http
GET /api/v1/owner/bookings?venue_id=12&date=2026-10-29&status=CONFIRMED
Authorization: Bearer <OWNER_ACCESS_TOKEN>
```

Response `200` — array of Owner booking projections. These fields are already present in the Booking model/schema, except `qr_token` is intentionally excluded:

```json
[
  {
    "id": 42,
    "user_id": 8,
    "time_slot_id": 91,
    "court_id": 4,
    "venue_id": 12,
    "slot_date": "2026-10-29",
    "start_time": "18:00:00",
    "end_time": "19:00:00",
    "status": "CONFIRMED",
    "total_amount": "180.00",
    "expires_at": null,
    "created_at": "2026-10-28T10:15:00Z"
  }
]
```

The Booking ORM model also has `owner_id`, but it is not included in the example because the authenticated Owner already defines the scope. `checked_in_at` and `completed_at` exist on the model but are not in `BookingResponse`; adding them to the Owner response is optional and **TO CONFIRM**. Customer name/contact and court/venue display names are not available on the current Booking schema and are out of this minimum contract.

### 3.2 Booking detail

```http
GET /api/v1/owner/bookings/42
Authorization: Bearer <OWNER_ACCESS_TOKEN>
```

Response `200` uses the same Owner projection as the list. It must omit `qr_token` even though the existing general `BookingResponse` includes it.

### 3.3 Complete booking

```http
POST /api/v1/owner/bookings/42/complete
Authorization: Bearer <OWNER_ACCESS_TOKEN>
```

Response `200` matches the existing internal completion result:

```json
{
  "booking_id": 42,
  "status": "COMPLETED",
  "completed_at": "2026-10-29T12:00:00Z"
}
```

### 3.4 Check in QR token

Browser request:

```http
POST /api/v1/owner/checkins
Authorization: Bearer <OWNER_ACCESS_TOKEN>
Content-Type: application/json
```

```json
{
  "qr_token": "<opaque-token>"
}
```

Court Service server-to-server request to S1 (never made by browser):

```http
POST /api/v1/internal/bookings/check-in
X-Internal-Token: <server-side secret>
Content-Type: application/json
```

```json
{
  "owner_id": 12,
  "qr_token": "<opaque-token>"
}
```

Response `200` is the existing S1 internal response forwarded by the adapter:

```json
{
  "booking_id": 42,
  "status": "CHECKED_IN",
  "checked_in_at": "2026-10-29T11:00:00Z"
}
```

## 4. Authentication & Authorization

- Public Owner endpoints require `Authorization: Bearer <JWT>`.
- JWT uses HS256 and the shared `JWT_SECRET_KEY`; `sub` is the numeric user ID serialized as a string, and `role` must equal `OWNER`.
- Each service verifies the JWT locally with the same secret. Missing/invalid/expired JWT returns `401`; a valid non-Owner role returns `403`.
- S1 list/detail/completion compare `booking.owner_id` with the authenticated `sub`. They do not trust a request body or query parameter as authorization evidence.
- S2 QR adapter extracts `owner_id` from the validated JWT `sub`. It does not accept `owner_id` from browser input.
- `venue_id` identifies a venue and is only a list filter; it is not the Owner ID. S1 applies both the Owner scope and requested venue filter.
- The internal token is configured only on backend services and sent from S2 to S1 in `X-Internal-Token`. It must not be returned, logged in user-visible output, stored in browser storage, or forwarded from browser input.

## 5. Booking State Rules

The current project status vocabulary is `PENDING`, `CONFIRMED`, `CHECKED_IN`, `COMPLETED`, `CANCELLED`, and `EXPIRED`.

| Operation | Required current status | Result | Failure |
|---|---|---|---|
| Owner list/detail | Any existing status | No state change | Non-owned/missing detail is `404` |
| Check-in | `CONFIRMED` | `CHECKED_IN`, with `checked_in_by` set to JWT `sub` and `checked_in_at` set | Invalid/missing/wrong-owner token `404`; other state or duplicate `409` |
| Complete | `CHECKED_IN` | `COMPLETED`, with `completed_at` set | Missing/other-owner booking `404`; other state or repeat `409` |

S1 currently uses `SELECT ... FOR UPDATE` in the internal check-in and completion handlers. Check-in is committed once; subsequent scans return `409`. Public completion should reuse the same transition/locking behavior. No additional Booking status or time-window rule is introduced by this contract.

## 6. Gateway Routing

The current Gateway maps `/api/v1/bookings` to Booking Service and has a generic proxy that forwards `authorization`, `content-type`, and `accept`. It does not currently have `/api/v1/owner` routing. The following explicit routes are part of the approved design:

| Path | Destination |
|---|---|
| `/api/v1/owner/bookings` and `/api/v1/owner/bookings/...` | S1 Booking Service |
| `/api/v1/owner/checkins` | S2 Court Service adapter |

Implement explicit path matching or longest-prefix matching so `/api/v1/owner/bookings` and `/api/v1/owner/checkins` route to their distinct services. Do not add a broad `/api/v1/owner` mapping that can capture existing S2 Owner Venue/Court/Time Slot routes. Preserve current `/api/v1/bookings` routing. Keep `/api/v1/internal/...` unavailable through Gateway.

Gateway forwards `Authorization`, `Content-Type`, and `Accept` to the selected upstream. The browser never sends `X-Internal-Token`; Court Service adds it only for the internal Booking call.

## 7. S1/S2 Responsibilities

| Task | Owner | Files to change | Dependency | Tests |
|---|---|---|---|---|
| Implement Owner booking list with `venue_id`, `date`, `status` filters and Owner-only projection | S1 | `backend/services/booking_service/app/routes.py`, `schemas.py`, `docs/API_CONTRACT.md` | Approved response and filter contract | JWT/role checks; Owner scope; filter combinations; QR token omitted |
| Implement Owner booking detail | S1 | Booking `routes.py`, `schemas.py`, `docs/API_CONTRACT.md` | Owner projection | Own booking `200`; missing/other-owner `404`; non-Owner denied |
| Implement public Owner completion by reusing existing transition logic | S1 | Booking `routes.py` and shared transition helper if needed; tests; `docs/API_CONTRACT.md` | `CHECKED_IN` transition and `booking.owner_id` | success; invalid state `409`; repeated completion `409`; foreign Owner `404`; concurrency/row lock behavior |
| Implement QR check-in adapter in Court Service | S2 | `backend/services/court_service/app/routes.py` or a dedicated router, server-side integration/config module, Court tests | S1 internal check-in remains unchanged; shared JWT secret; internal token; Booking URL | derives Owner ID from JWT; rejects browser `owner_id`; forwards correct internal request; maps errors; secret never returned |
| Route the two Owner API families through Gateway | S2 | `backend/gateway/main.py`, `backend/gateway/tests/test_gateway.py` | Booking and Court upstream URLs | bookings → S1; checkins → S2; headers forwarded; internal route hidden; existing Owner Court paths unaffected |
| Connect Owner Bookings and QR screen in API Mode | S2 | `management-web/assets/js/app.js`; `api.js` only if helper extension is needed; Management Web tests | S1/S2 endpoints reachable through Gateway | list/detail/filter/complete; scanner/manual token check-in; loading/errors/success; no internal token or `owner_id`; Demo Mode retained |
| Cross-service integration verification | S1 + S2 | Integration documentation/tests as agreed | Both services and Gateway configured with shared JWT secret and internal token | list → detail → check-in → complete; isolation; duplicate scan; invalid state; Gateway routing |

### Implementation checklist — S1

- [ ] Add Owner-only routes without changing existing USER booking routes or internal route paths.
- [ ] Add an Owner response schema that excludes `qr_token`.
- [ ] Scope list/detail/completion by `booking.owner_id == JWT.sub`.
- [ ] Implement approved list filters and reject invalid `status`/date input with `422`.
- [ ] Reuse locking and transition logic for completion; retain `409` for repeat completion.
- [ ] Update `docs/API_CONTRACT.md` and add route/authorization/state tests.

### Implementation checklist — S2

- [ ] Add the Court Service adapter route `POST /api/v1/owner/checkins` using existing JWT validation.
- [ ] Derive `owner_id` from JWT `sub`; accept only `qr_token` from browser.
- [ ] Call existing S1 internal check-in with server-side `X-Internal-Token`; do not duplicate Booking state logic.
- [ ] Add explicit Gateway mappings for Owner bookings → S1 and checkins → S2; preserve existing Owner Court routes and hide `/internal`.
- [ ] Connect Management Web API Mode while keeping Demo Mode unchanged; never expose internal token.
- [ ] Add adapter, Gateway, and Management Web tests for authorization, forwarding, errors, and success.

## 8. Integration Test Cases

1. Missing/invalid/expired JWT → `401`; valid `USER` or `ADMIN` JWT on Owner-only APIs → `403`.
2. Owner A list returns only rows with `booking.owner_id == A`; `venue_id`, `date`, and `status` filters narrow those results.
3. Owner A detail or complete for Owner B's booking → `404`; no state change.
4. Owner list/detail JSON never contains `qr_token`.
5. Confirmed booking's valid QR, checked in by its Owner → `200`, `CHECKED_IN`, and timestamp.
6. Missing/invalid/wrong-owner QR → `404`, with no booking details disclosed.
7. Duplicate or concurrent check-in → at most one success; duplicate returns `409`.
8. Check-in on `PENDING`, `CANCELLED`, `EXPIRED`, `CHECKED_IN`, or `COMPLETED` → `409`.
9. Complete `CHECKED_IN` booking → `COMPLETED`; complete again or from another state → `409`.
10. Booking upstream unavailable/timeout → adapter returns `503`/`504`; internal token is not exposed.
11. Gateway sends `/owner/bookings...` to S1 and `/owner/checkins` to S2, forwards allowed public headers, and does not expose `/internal`.
12. Existing S2 Owner Venue/Court/Time Slot routes continue to reach Court Service after route mapping changes.
13. Management Web API Mode sends only the agreed public requests; Demo Mode remains local and unchanged.

## 9. Open Questions / TO CONFIRM

The following implementation details do not change the approved security or routing decisions:

1. **Booking URL configuration for Court adapter:** use the existing `BOOKING_SERVICE_URL` setting or introduce a Court-specific URL setting. No new service is required; prefer reusing the existing setting if deployment environments share it.
2. **List `venue_id` outside Owner scope:** approved isolation rule is clear; recommended behavior is an empty result. Confirm whether the implementation should instead return `404`.
3. **Optional timestamps:** `checked_in_at` and `completed_at` exist in the model but not in current `BookingResponse`. Confirm whether Owner list/detail should include them; completion response already includes `completed_at` in the existing internal result.
4. **Upstream error detail mapping:** preserve `404` and `409` semantics from internal S1 API while returning a stable public error message; exact wording can follow existing FastAPI `detail` convention.

Until the implementation and integration tests are complete, all four public Owner endpoints in this document remain **Pending Implementation**.

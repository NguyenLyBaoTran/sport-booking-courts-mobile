# Court Service API Contract

Status: reflects the implementation in `backend/services/court_service/app` on 2026-10-23. This is a description of implemented routes plus clearly marked future integration points; it does not promise unimplemented APIs.

## 1. Overview

- Direct service base URL: `http://localhost:8002`
- API Gateway base URL: `http://localhost:8000`
- API prefix: `/api/v1`
- Content type: JSON (`application/json`); date values use `YYYY-MM-DD`, time values use `HH:MM:SS`, and timestamps use ISO 8601. `price_per_hour` is a decimal with two places and is serialized as a JSON string, for example `"25.00"`.
- Current access: all GET routes are public. POST, PUT, and DELETE routes have a write-access dependency that currently returns `503` until S1 authentication and authorization are integrated. Do not use request `owner_id` as evidence of ownership.
- Gateway forwards the Court Service path, query string, request body, `Authorization` header, and upstream status. The same API paths work directly and through the Gateway.

Every response schema contains the fields shown below; list routes return arrays of these objects. `description` and `phone` may be `null` where applicable.

## 2. Routes

### Sports

| Method and URL | Function | Query/body | Response | Status and access |
|---|---|---|---|---|
| `GET /api/v1/sports` | List sports | Optional `is_active: boolean` | `200`, `Sport[]` | Public |
| `GET /api/v1/sports/{sport_id}` | Get one sport | Positive integer path ID | `200`, `Sport` | Public; `404` if absent |
| `POST /api/v1/sports` | Create sport | `SportInput` | Intended `201`, `Sport` | Currently `503`; intended OWNER/ADMIN |
| `PUT /api/v1/sports/{sport_id}` | Replace editable sport fields | `SportInput` | Intended `200`, `Sport` | Currently `503`; intended OWNER/ADMIN; `404` if absent after auth integration |
| `DELETE /api/v1/sports/{sport_id}` | Soft-deactivate (`is_active=false`) | No body | Intended `204`, no body | Currently `503`; intended OWNER/ADMIN, exact policy pending S1 |

`SportInput`: `name` (required, trimmed, 1–100 characters), `description` (optional nullable string), `is_active` (optional boolean, defaults to `true`). `name` is unique; a duplicate produces `409` when the write path is enabled.

### Venues

| Method and URL | Function | Query/body | Response | Status and access |
|---|---|---|---|---|
| `GET /api/v1/venues` | List venues | Optional `owner_id` (positive integer), `is_active` (boolean) | `200`, `Venue[]` | Public; `owner_id` is only a filter, not an authorization check |
| `GET /api/v1/venues/{venue_id}` | Get one venue | Positive integer path ID | `200`, `Venue` | Public; `404` if absent |
| `POST /api/v1/venues` | Create venue | `VenueInput` | Intended `201`, `Venue` | Currently `503`; intended OWNER/ADMIN |
| `PUT /api/v1/venues/{venue_id}` | Replace editable venue fields | `VenueInput` | Intended `200`, `Venue` | Currently `503`; intended owner or ADMIN; `404` if absent after auth integration |
| `DELETE /api/v1/venues/{venue_id}` | Soft-deactivate (`is_active=false`) | No body | Intended `204`, no body | Currently `503`; intended owner or ADMIN |

`VenueInput`: `owner_id` (required positive integer), `name` (required, trimmed, 1–200 characters), `address` (required, trimmed, 1–255 characters), optional nullable `description` and `phone` (maximum 20 characters), and optional `is_active` (defaults to `true`). The current Court Service does not verify that `owner_id` belongs to a real User Service account; that check depends on authenticated identity and the S1 contract.

### Courts

| Method and URL | Function | Query/body | Response | Status and access |
|---|---|---|---|---|
| `GET /api/v1/courts` | List courts | Optional positive `venue_id`, positive `sport_id`, `is_active` | `200`, `Court[]` | Public |
| `GET /api/v1/courts/{court_id}` | Get one court | Positive integer path ID | `200`, `Court` | Public; `404` if absent |
| `POST /api/v1/courts` | Create court | `CourtInput` | Intended `201`, `Court` | Currently `503`; intended OWNER/ADMIN |
| `PUT /api/v1/courts/{court_id}` | Replace editable court fields | `CourtInput` | Intended `200`, `Court` | Currently `503`; intended owner or ADMIN |
| `DELETE /api/v1/courts/{court_id}` | Soft-deactivate (`is_active=false`) | No body | Intended `204`, no body | Currently `503`; intended owner or ADMIN |

`CourtInput`: positive `venue_id` and `sport_id`, `name` (required, trimmed, 1–100 characters), optional nullable `description`, `price_per_hour` (decimal greater than zero, at most 12 digits and 2 decimal places), and optional `is_active` (defaults to `true`). Create/update checks that the Venue exists and is active and that the Sport exists. The API currently does not reject an inactive Sport.

### Time Slots

| Method and URL | Function | Query/body | Response | Status and access |
|---|---|---|---|---|
| `GET /api/v1/time-slots` | List time slots | Optional positive `court_id`, `slot_date`, `is_active` | `200`, `TimeSlot[]` | Public |
| `GET /api/v1/time-slots/{slot_id}` | Get one time slot | Positive integer path ID | `200`, `TimeSlot` | Public; `404` if absent |
| `POST /api/v1/time-slots` | Create time slot | `TimeSlotInput` | Intended `201`, `TimeSlot` | Currently `503`; intended OWNER/ADMIN |
| `PUT /api/v1/time-slots/{slot_id}` | Replace editable time-slot fields | `TimeSlotInput` | Intended `200`, `TimeSlot` | Currently `503`; intended owner or ADMIN |
| `DELETE /api/v1/time-slots/{slot_id}` | Soft-deactivate (`is_active=false`) | No body | Intended `204`, no body | Currently `503`; intended owner or ADMIN |

`TimeSlotInput`: positive `court_id`, required `slot_date`, `start_time`, `end_time`, optional `is_active` (defaults to `true`). `start_time` must be earlier than `end_time`; the Court must exist and be active. Active slots may not overlap on the same court and date; an update excludes the slot being changed. Inactive slots are excluded from overlap checks. The database also has an exact-range unique constraint. The overlap pre-check is not atomic, so simultaneous requests can race; this API does not claim to prevent that race. No booking state is read or changed by this service.

## 3. JSON examples

Examples use illustrative IDs only. They match the current Pydantic schemas.

### Sport

Request to `POST /api/v1/sports`:

```json
{
  "name": "Badminton",
  "description": "Indoor court sport",
  "is_active": true
}
```

Response shape after the write route is enabled (`201`):

```json
{
  "id": 1,
  "name": "Badminton",
  "description": "Indoor court sport",
  "is_active": true
}
```

### Venue

Request to `POST /api/v1/venues`:

```json
{
  "owner_id": 7,
  "name": "Central Sports Hall",
  "address": "10 Example Street",
  "description": null,
  "phone": "0900000000",
  "is_active": true
}
```

Response shape after the write route is enabled (`201`):

```json
{
  "id": 1,
  "owner_id": 7,
  "name": "Central Sports Hall",
  "address": "10 Example Street",
  "description": null,
  "phone": "0900000000",
  "is_active": true,
  "created_at": "2026-10-23T10:30:00"
}
```

### Court

Request to `POST /api/v1/courts`:

```json
{
  "venue_id": 1,
  "sport_id": 1,
  "name": "Court A",
  "description": "Indoor court",
  "price_per_hour": "25.00",
  "is_active": true
}
```

Response shape after the write route is enabled (`201`):

```json
{
  "id": 1,
  "venue_id": 1,
  "sport_id": 1,
  "name": "Court A",
  "description": "Indoor court",
  "price_per_hour": "25.00",
  "is_active": true
}
```

### Time Slot

Request to `POST /api/v1/time-slots`:

```json
{
  "court_id": 1,
  "slot_date": "2026-10-24",
  "start_time": "08:00:00",
  "end_time": "09:00:00",
  "is_active": true
}
```

Response shape after the write route is enabled (`201`):

```json
{
  "id": 1,
  "court_id": 1,
  "slot_date": "2026-10-24",
  "start_time": "08:00:00",
  "end_time": "09:00:00",
  "is_active": true
}
```

## 4. Error behavior

| Status | Meaning | Implementation status |
|---|---|---|
| `400 Bad Request` | Court references a missing/inactive Venue or missing Sport; Time Slot references a missing/inactive Court | Implemented in write handlers, but currently behind the write-access dependency |
| `401 Unauthorized` | Missing, invalid, or expired Bearer token | Expected after JWT integration; not currently returned by Court Service |
| `403 Forbidden` | Authenticated role is insufficient or Owner does not own the Venue | Expected after authorization integration; not currently returned by Court Service |
| `404 Not Found` | Requested resource ID does not exist | Implemented on GET detail; write handlers also check existence after access is granted |
| `409 Conflict` | Duplicate Sport name, overlapping active Time Slot, or database uniqueness conflict | Implemented in write handlers, but currently behind the write-access dependency |
| `422 Unprocessable Entity` | Invalid path/query/body, extra body fields, blank required text, invalid price, or invalid time range | Implemented by FastAPI/Pydantic; may be returned before the write-access dependency for malformed requests |
| `503 Service Unavailable` | Write authentication integration is pending | Current response for valid POST/PUT/DELETE requests |
| `503 Service Unavailable` / `504 Gateway Timeout` | Gateway cannot reach a service or the upstream request times out | Implemented by Gateway, not by Court Service |

Error JSON follows FastAPI's `{"detail": "..."}` shape, except the normal Pydantic `422` validation response. Database credentials and JWT material are not returned.

## 5. Integration contract with S1

### Authentication and authorization questions to confirm

Court Service currently does not decode or trust JWT claims. Before enabling writes, S1 and S2 need to agree on:

1. Signing algorithm and verification method: shared secret or public-key/JWKS distribution; issuer and audience validation requirements.
2. Required claims, including the authenticated user ID claim and role claim.
3. Token expiry and clock-skew policy, and whether refresh is only handled by User Service.
4. Bearer token transport (`Authorization: Bearer <token>`); the Gateway already forwards this header.
5. Exact role names and permissions for USER, OWNER, and ADMIN, including which read routes need authentication.
6. Error behavior for missing, invalid, expired, or insufficient-role tokens (`401` versus `403`).
7. How Court Service can validate the Owner-to-Venue relationship. `venues.owner_id` is a logical User Service ID; Court DB has no cross-database user foreign key.
8. Whether Gateway performs authentication, services validate tokens independently, or both. Do not authorize from unverified token contents.

No secret or token is embedded in this contract. Write routes remain closed until this contract is decided and implemented.

The inspected User Service currently exposes only `/health` and `/health/db`; the planned `POST /auth/register`, `POST /auth/login`, and `GET /users/me` are not implemented. S1 needs to provide its token issuance contract and a verification mechanism before Court writes can be enabled.

### Booking Service data and availability

The existing GET APIs provide these fields:

- `GET /api/v1/time-slots?court_id={id}&slot_date=YYYY-MM-DD` returns `id`, `court_id`, `slot_date`, `start_time`, `end_time`, `is_active`.
- `GET /api/v1/courts/{court_id}` returns `venue_id`, `sport_id`, `name`, `price_per_hour`, `is_active` and `description`.
- `GET /api/v1/venues/{venue_id}` and `GET /api/v1/sports/{sport_id}` provide the corresponding venue and sport fields.

Booking can obtain the basic slot and price data with multiple GET calls, but there is no single joined availability response. These reads do not reserve a slot. The current `is_active` flag is not a booking/hold state.

**Important V5 gap:** Project Plan V5 requires Court Service to own an atomic, idempotent slot hold, confirmation, and release flow with a 10-minute TTL. No such fields, table, or endpoint exists in the current models, schema, routes, or MySQL Court DB. The planned `GET /courts/{id}/slots` and internal hold/confirm/release APIs are also absent. Booking Service currently contains only health endpoints. S1 and S2 must agree on the reservation data model, idempotency key (`booking_request_id`), TTL, and internal authorization before implementing that later step. This contract does not create or promise those routes.

### Owner/Admin Management Web needs

| Use case | Exists in Court Service now | Other service / future work |
|---|---|---|
| Read venues and courts | Public GET list/detail routes; venue list can filter by `owner_id`, courts by `venue_id`/`sport_id` | Owner-scoped authorization and write access await JWT integration |
| Manage venues, courts, and schedule | POST/PUT/DELETE handlers exist but return `503` today; slot list/detail is readable | Enable with S1 JWT/OWNER/ADMIN and owner-scope checks; no Management Web work in this step |
| View bookings and complete booking | Not a Court Service responsibility or route | Booking Service (S1); currently not implemented in the inspected service |
| QR check-in | Not a Court Service responsibility or route | Booking Service API owned by S1; currently not implemented in the inspected service |
| Dashboard booking/revenue aggregates | Not provided by Court Service | Requires Booking/Payment API or an agreed dashboard aggregation contract from S1 |

Project Plan V5 also lists planned route shapes such as `/venues/{id}/courts`, `/courts/{id}/slots`, `/owner/venues`, `/owner/courts`, and `/owner/slots`; they are not currently implemented. The implemented public Court routes remain under `/api/v1` as documented above.

V5 lists these S1-owned shapes, which are also planned rather than implemented in the inspected services: `POST /bookings`, `GET /bookings`, `GET /bookings/{id}`, `POST /bookings/{id}/cancel`, `GET /owner/bookings`, `POST /owner/bookings/{id}/complete`, and `POST /owner/checkins`. User and Booking services currently expose only health endpoints. V5 proposes internal contracts including `POST /internal/slots/{id}/hold`, `POST /internal/holds/{hold_id}/confirm`, `POST /internal/holds/{hold_id}/release`, `GET /internal/slots/{id}`, and an ownership lookup such as `GET /internal/venues/{id}/ownership`; none are present in Court Service. These are proposals requiring team agreement, not current endpoints.

## 6. Consistency check

- SQLAlchemy models, Pydantic response schemas, and the four Court DB tables agree on names and fields: `sports`, `venues`, `courts`, `time_slots`.
- Court DB has the local physical relationships `courts.venue_id -> venues.id`, `courts.sport_id -> sports.id`, and `time_slots.court_id -> courts.id`; the unique time-slot range index is present.
- `venues.owner_id` and Booking's `time_slot_id` are logical cross-service references; they are not physical foreign keys in Court DB.
- `docs/diagrams/court-service-erd.dbml` describes the same four Court tables and internal relationships. The overall ERD contains the nine logical business tables, including `checkins` in Booking ownership; it is a conceptual ERD and does not change the database-per-service foreign-key rule.
- Two wire-format details differ from Project Plan V5 §6.1: V5 states time as `HH:mm`, while the current API schema emits `HH:MM:SS`; V5 states money as integer VND, while `price_per_hour` is `DECIMAL(12,2)` and emits a decimal string. Confirm the shared format with S1 and the clients before cross-service integration; this step does not change the existing schema or API.
- No discrepancy requiring changes to the database, Project Plan, or diagrams was found in this step. The missing reservation/hold API is a documented implementation gap against V5, not an ERD inconsistency to resolve here.

## 7. Running and checking

From the `backend` directory:

```powershell
cd services/court_service
python -m uvicorn app.main:app --reload --port 8002
```

Court Service Swagger UI: `http://localhost:8002/docs`. Start Gateway separately from `backend/gateway` with `python -m uvicorn main:app --reload --port 8000`; then use the same API paths through `http://localhost:8000`.

Read-only examples:

```text
GET http://localhost:8002/api/v1/sports
GET http://localhost:8000/api/v1/venues?owner_id=1&is_active=true
GET http://localhost:8000/api/v1/courts?venue_id=1&sport_id=1
GET http://localhost:8000/api/v1/time-slots?court_id=1&slot_date=2026-10-24
```

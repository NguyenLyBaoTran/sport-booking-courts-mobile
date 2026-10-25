# Court Service API Contract

Status: reflects the implementation in `backend/services/court_service/app` on 2026-10-25. This is a description of implemented routes plus clearly marked future integration points; it does not promise unimplemented APIs.

## 1. Overview

- Direct service base URL: `http://localhost:8002`
- API Gateway base URL: `http://localhost:8000`
- API prefix: `/api/v1`
- Content type: JSON (`application/json`); date values use `YYYY-MM-DD`, time values use `HH:MM:SS`, and timestamps use ISO 8601. `price_per_hour` is a decimal with two places and is serialized as a JSON string, for example `"25.00"`.
- Current access: all GET routes are public. Venue, Court, and Time Slot mutations require a valid OWNER JWT and enforce ownership through the related Venue; Sports writes remain closed with `503` for ADMIN while the Sports policy is pending. Do not use request `owner_id` as evidence of ownership.
- Gateway forwards the Court Service path, query string, request body, `Authorization` header, and upstream status. The same API paths work directly and through the Gateway.

Every response schema contains the fields shown below; list routes return arrays of these objects. `description` and `phone` may be `null` where applicable.

## 2. Routes

### Sports

| Method and URL | Function | Query/body | Response | Status and access |
|---|---|---|---|---|
| `GET /api/v1/sports` | List sports | Optional `is_active: boolean` | `200`, `Sport[]` | Public |
| `GET /api/v1/sports/{sport_id}` | Get one sport | Positive integer path ID | `200`, `Sport` | Public; `404` if absent |
| `POST /api/v1/sports` | Create sport | `SportInput` | Intended `201`, `Sport` | Currently `503`; ADMIN-only policy pending confirmation |
| `PUT /api/v1/sports/{sport_id}` | Replace editable sport fields | `SportInput` | Intended `200`, `Sport` | Currently `503`; ADMIN-only policy pending confirmation |
| `DELETE /api/v1/sports/{sport_id}` | Soft-deactivate (`is_active=false`) | No body | Intended `204`, no body | Currently `503`; ADMIN-only policy pending confirmation |

`SportInput`: `name` (required, trimmed, 1–100 characters), `description` (optional nullable string), `is_active` (optional boolean, defaults to `true`). `name` is unique; a duplicate produces `409` when the write path is enabled.

### Venues

| Method and URL | Function | Query/body | Response | Status and access |
|---|---|---|---|---|
| `GET /api/v1/venues` | List venues | Optional `owner_id` (positive integer), `is_active` (boolean) | `200`, `Venue[]` | Public; `owner_id` is only a filter, not an authorization check |
| `GET /api/v1/venues/{venue_id}` | Get one venue | Positive integer path ID | `200`, `Venue` | Public; `404` if absent |
| `POST /api/v1/venues` | Create venue | `VenueInput` | `201`, `Venue` | OWNER with matching authenticated `owner_id`; ADMIN policy pending |
| `PUT /api/v1/venues/{venue_id}` | Replace editable venue fields | `VenueInput` | `200`, `Venue` | Owning OWNER only; ADMIN policy pending |
| `DELETE /api/v1/venues/{venue_id}` | Soft-deactivate (`is_active=false`) | No body | `204`, no body | Owning OWNER only; ADMIN policy pending |

`VenueInput`: `owner_id` (required positive integer matching the authenticated OWNER's `sub`), `name` (required, trimmed, 1–200 characters), `address` (required, trimmed, 1–255 characters), optional nullable `description` and `phone` (maximum 20 characters), and optional `is_active` (defaults to `true`). Court Service derives authority from the verified token, rejects a mismatched body `owner_id`, and preserves the stored owner on update.

### Courts

| Method and URL | Function | Query/body | Response | Status and access |
|---|---|---|---|---|
| `GET /api/v1/courts` | List courts | Optional positive `venue_id`, positive `sport_id`, `is_active` | `200`, `Court[]` | Public |
| `GET /api/v1/courts/{court_id}` | Get one court | Positive integer path ID | `200`, `Court` | Public; `404` if absent |
| `POST /api/v1/courts` | Create court | `CourtInput` | `201`, `Court` | OWNER of the related Venue; ADMIN policy pending |
| `PUT /api/v1/courts/{court_id}` | Replace editable court fields | `CourtInput` | `200`, `Court` | OWNER of both current and target Venue; ADMIN policy pending |
| `DELETE /api/v1/courts/{court_id}` | Soft-deactivate (`is_active=false`) | No body | `204`, no body | OWNER of the related Venue; ADMIN policy pending |

`CourtInput`: positive `venue_id` and `sport_id`, `name` (required, trimmed, 1–100 characters), optional nullable `description`, `price_per_hour` (decimal greater than zero, at most 12 digits and 2 decimal places), and optional `is_active` (defaults to `true`). Create/update checks that the Venue exists and is active and that the Sport exists. The API currently does not reject an inactive Sport.

### Time Slots

| Method and URL | Function | Query/body | Response | Status and access |
|---|---|---|---|---|
| `GET /api/v1/time-slots` | List time slots | Optional positive `court_id`, `slot_date`, `is_active` | `200`, `TimeSlot[]` | Public |
| `GET /api/v1/time-slots/{slot_id}` | Get one time slot | Positive integer path ID | `200`, `TimeSlot` | Public; `404` if absent |
| `POST /api/v1/time-slots` | Create time slot | `TimeSlotInput` | `201`, `TimeSlot` | OWNER of the related Court's Venue; ADMIN policy pending |
| `PUT /api/v1/time-slots/{slot_id}` | Replace editable time-slot fields | `TimeSlotInput` | `200`, `TimeSlot` | OWNER of current and target Court Venues; ADMIN policy pending |
| `DELETE /api/v1/time-slots/{slot_id}` | Soft-deactivate (`is_active=false`) | No body | `204`, no body | OWNER of the related Court's Venue; ADMIN policy pending |

`TimeSlotInput`: positive `court_id`, required `slot_date`, `start_time`, `end_time`, optional `is_active` (defaults to `true`). Both times must be on a 30-minute boundary (`:00` or `:30`, with zero seconds), and `start_time` must be earlier than `end_time`; otherwise FastAPI returns `422`. The Court must exist and be active. Active slots may not overlap on the same court and date; an update excludes the slot being changed. Inactive slots are excluded from overlap checks. The database also has an exact-range unique constraint. The overlap pre-check is not atomic, so simultaneous requests can race; this API does not claim to prevent that race. No opening hours are imposed because Venue opening-hour configuration is not part of this API. No booking state is read or changed by this service.

This validation applies to new and updated requests; it does not modify existing database rows. The SQL `TIME` column has no 30-minute check constraint, so old rows may contain other minute values. Existing MySQL data was not queried or changed as part of this validation update.

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

Time Slot create and update requests must use start/end times on 30-minute boundaries and `start_time < end_time`. Overlap applies only to active slots on the same Court and date. A new slot must start in the future in the business timezone `Asia/Ho_Chi_Minh`. On update, this future check applies only when `slot_date` or `start_time` changes; edits to other fields on historical slots remain allowed. Historical slots remain readable and filterable. These checks do not add opening-hour rules or change the database's separate `DATE` and timezone-naive `TIME` columns.

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
| `400 Bad Request` | Court references a missing/inactive Venue or missing Sport; Time Slot references a missing/inactive Court | Implemented in write handlers after authorization |
| `401 Unauthorized` | Missing, invalid, expired, or malformed required-claim Bearer token | Implemented by Court JWT verification |
| `403 Forbidden` | Valid token has insufficient role or OWNER does not own the related Venue | Implemented for USER and cross-owner mutations; ADMIN policy remains disabled |
| `404 Not Found` | Requested resource ID does not exist | Implemented on GET detail; write handlers also check existence after access is granted |
| `409 Conflict` | Duplicate Sport name, overlapping active Time Slot, or database uniqueness conflict | Implemented in write handlers after authorization |
| `422 Unprocessable Entity` | Invalid path/query/body, extra body fields, blank required text, invalid price/range, time not on a 30-minute boundary, or new/changed start time not in the future | Implemented by FastAPI/Pydantic and Court Service write validation; malformed requests may be rejected before authorization |
| `503 Service Unavailable` | JWT verification configuration is missing/invalid, or Sports write policy is pending | Implemented; Sports write stays closed pending policy confirmation |
| `503 Service Unavailable` / `504 Gateway Timeout` | Gateway cannot reach a service or the upstream request times out | Implemented by Gateway, not by Court Service |

Error JSON follows FastAPI's `{"detail": "..."}` shape, except the normal Pydantic `422` validation response. Database credentials and JWT material are not returned.

## 5. Integration contract with S1

### Authentication and authorization

User Service on `feature/s1-w1-auth-usecase` issues HS256 access tokens with string `sub`, `role`, `iat`, and `exp`; expiration defaults to 60 minutes. Court Service verifies the signature independently using `python-jose`, requires `sub`, `iat`, and `exp`, validates the numeric user ID and one of `USER`, `OWNER`, or `ADMIN`, and does not import User Service code. Configure the same secret in the ignored local `backend/.env` for both services. Never put a real secret in this contract or Git.

- Missing, malformed, invalid-signature, expired, or invalid-claim tokens return `401`.
- A valid token with a role not allowed by an endpoint returns `403`.
- Public GET catalogue routes remain public. The `owner_id` query is a public filter, not an access-control check.
- USER cannot mutate Court data. OWNER may create a Venue only for their own `sub`; updates preserve the stored owner. Court and Time Slot writes check ownership through their related Venue. Cross-owner mutations return `403`.
- ADMIN authorization for Venue/Court/Time Slot operations remains disabled pending policy confirmation. Sports mutations remain closed with `503` while the proposed ADMIN-only rule is pending confirmation; USER and OWNER receive `403`.
- Gateway forwards the Authorization header. CORS uses exact configured origins, allows the required API methods and headers, and rejects wildcard origins.

`venues.owner_id` is a logical User Service ID; Court DB intentionally has no cross-database User foreign key. The policy for public reads, ADMIN permissions, Sports management, token issuer/audience, key rotation, and role-change/revocation behavior still needs team confirmation. No secret or token is embedded in this contract.

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
| Read venues and courts | Public GET list/detail routes; venue list can filter by `owner_id`, courts by `venue_id`/`sport_id` | Reads are public; `owner_id` is not authorization |
| Manage own venues, courts, and schedule | OWNER writes require valid JWT and ownership through related Venue; USER and cross-owner writes are denied | ADMIN permissions remain pending; Management Web login and token forwarding are implemented against the inspected S1 contract but remain unverified end-to-end until Auth is integrated and a valid local account is available |
| View bookings and complete booking | Not a Court Service responsibility or route | Booking Service (S1); currently not implemented in the inspected service |
| QR check-in | Not a Court Service responsibility or route | Booking Service API owned by S1; currently not implemented in the inspected service |
| Dashboard booking/revenue aggregates | Not provided by Court Service | Requires Booking/Payment API or an agreed dashboard aggregation contract from S1 |

Project Plan V5 also lists planned route shapes such as `/venues/{id}/courts`, `/courts/{id}/slots`, `/owner/venues`, `/owner/courts`, and `/owner/slots`; they are not currently implemented. The implemented public Court routes remain under `/api/v1` as documented above.

V5 lists these S1-owned shapes, which are also planned rather than implemented in the inspected services: `POST /bookings`, `GET /bookings`, `GET /bookings/{id}`, `POST /bookings/{id}/cancel`, `GET /owner/bookings`, `POST /owner/bookings/{id}/complete`, and `POST /owner/checkins`. On the current S2 branch the User Service exposes health endpoints only; the separately inspected S1 branch adds the Auth routes documented above, which are not present in this checkout until integration. Booking Service currently exposes health endpoints only. V5 proposes internal contracts including `POST /internal/slots/{id}/hold`, `POST /internal/holds/{hold_id}/confirm`, `POST /internal/holds/{hold_id}/release`, `GET /internal/slots/{id}`, and an ownership lookup such as `GET /internal/venues/{id}/ownership`; none are present in Court Service. These are proposals requiring team agreement, not current endpoints.

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

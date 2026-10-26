# Court Service API Contract

Status: reflects the implementation in `backend/services/court_service/app` on 2026-10-26. This is a description of implemented routes plus clearly marked future integration points; it does not promise unimplemented APIs.

## 1. Overview

- Direct service base URL: `http://localhost:8002`
- API Gateway base URL: `http://localhost:8000`
- API prefix: `/api/v1`
- Content type: JSON (`application/json`); date values use `YYYY-MM-DD`, time values use `HH:MM:SS`, and timestamps use ISO 8601. `price_per_hour` is a decimal with two places and is serialized as a JSON string, for example `"25.00"`.
- Current access: all GET routes are public. Venue, Court, and Time Slot mutations require OWNER access scoped to the related Venue or ADMIN access system-wide. Sports mutations require an ADMIN JWT. Do not use request `owner_id` as evidence of OWNER authority.
- Gateway forwards public Court paths, query strings, request bodies, the `Authorization` header, and upstream status. Public routes work directly and through the Gateway; internal reservation routes are direct service-to-service only and are intentionally not proxied.

Every response schema contains the fields shown below; list routes return arrays of these objects. `description` and `phone` may be `null` where applicable.

## 2. Routes

### Sports

| Method and URL | Function | Query/body | Response | Status and access |
|---|---|---|---|---|
| `GET /api/v1/sports` | List sports | Optional `is_active: boolean` | `200`, `Sport[]` | Public |
| `GET /api/v1/sports/{sport_id}` | Get one sport | Positive integer path ID | `200`, `Sport` | Public; `404` if absent |
| `POST /api/v1/sports` | Create sport | `SportInput` | `201`, `Sport` | ADMIN only; USER/OWNER receive `403` |
| `PUT /api/v1/sports/{sport_id}` | Replace editable sport fields | `SportInput` | `200`, `Sport` | ADMIN only; USER/OWNER receive `403` |
| `DELETE /api/v1/sports/{sport_id}` | Soft-deactivate (`is_active=false`) | No body | `204`, no body | ADMIN only; USER/OWNER receive `403` |

`SportInput`: `name` (required, trimmed, 1–100 characters), `description` (optional nullable string), `is_active` (optional boolean, defaults to `true`). `name` is unique; a duplicate produces `409` when the write path is enabled.

### Venues

| Method and URL | Function | Query/body | Response | Status and access |
|---|---|---|---|---|
| `GET /api/v1/venues` | List venues | Optional `owner_id` (positive integer), `is_active` (boolean) | `200`, `Venue[]` | Public; `owner_id` is only a filter, not an authorization check |
| `GET /api/v1/venues/{venue_id}` | Get one venue | Positive integer path ID | `200`, `Venue` | Public; `404` if absent |
| `POST /api/v1/venues` | Create venue | `VenueInput` | `201`, `Venue` | OWNER with matching authenticated `owner_id`, or ADMIN |
| `PUT /api/v1/venues/{venue_id}` | Replace editable venue fields | `VenueInput` | `200`, `Venue` | Owning OWNER or ADMIN |
| `DELETE /api/v1/venues/{venue_id}` | Soft-deactivate (`is_active=false`) | No body | `204`, no body | Owning OWNER or ADMIN |

`VenueInput`: `owner_id` (required positive integer; for OWNER it must match the authenticated `sub`), `name` (required, trimmed, 1–200 characters), `address` (required, trimmed, 1–255 characters), optional nullable `description` and `phone` (maximum 20 characters), and optional `is_active` (defaults to `true`). Court Service derives OWNER authority from the verified token, rejects mismatched OWNER `owner_id`, and preserves the stored owner on OWNER update. ADMIN may manage any venue and set its owner ID.

### Courts

| Method and URL | Function | Query/body | Response | Status and access |
|---|---|---|---|---|
| `GET /api/v1/courts` | List courts | Optional positive `venue_id`, positive `sport_id`, `is_active` | `200`, `Court[]` | Public |
| `GET /api/v1/courts/{court_id}` | Get one court | Positive integer path ID | `200`, `Court` | Public; `404` if absent |
| `POST /api/v1/courts` | Create court | `CourtInput` | `201`, `Court` | OWNER of related Venue or ADMIN |
| `PUT /api/v1/courts/{court_id}` | Replace editable court fields | `CourtInput` | `200`, `Court` | OWNER of both current and target Venue or ADMIN |
| `DELETE /api/v1/courts/{court_id}` | Soft-deactivate (`is_active=false`) | No body | `204`, no body | OWNER of related Venue or ADMIN |

`CourtInput`: positive `venue_id` and `sport_id`, `name` (required, trimmed, 1–100 characters), optional nullable `description`, `price_per_hour` (decimal greater than zero, at most 12 digits and 2 decimal places), and optional `is_active` (defaults to `true`). Create/update checks that the Venue exists and is active and that the Sport exists. The API currently does not reject an inactive Sport.

### Time Slots

| Method and URL | Function | Query/body | Response | Status and access |
|---|---|---|---|---|
| `GET /api/v1/time-slots` | List time slots | Optional positive `court_id`, `slot_date`, `is_active` | `200`, `TimeSlot[]` | Public |
| `GET /api/v1/time-slots/{slot_id}` | Get one time slot | Positive integer path ID | `200`, `TimeSlot` | Public; `404` if absent |
| `POST /api/v1/time-slots` | Create time slot | `TimeSlotInput` | `201`, `TimeSlot` | OWNER of related Court's Venue or ADMIN |
| `PUT /api/v1/time-slots/{slot_id}` | Replace editable time-slot fields | `TimeSlotInput` | `200`, `TimeSlot` | OWNER of current and target Court Venues or ADMIN |
| `DELETE /api/v1/time-slots/{slot_id}` | Soft-deactivate (`is_active=false`) | No body | `204`, no body | OWNER of related Court's Venue or ADMIN |

`TimeSlotInput`: positive `court_id`, required `slot_date`, `start_time`, `end_time`, optional `is_active` (defaults to `true`). Both times must be on a 30-minute boundary (`:00` or `:30`, with zero seconds), and `start_time` must be earlier than `end_time`; otherwise FastAPI returns `422`. The Court must exist and be active. Active slots may not overlap on the same court and date; an update excludes the slot being changed. Inactive slots are excluded from overlap checks. Writes lock the affected Court rows before checking overlaps, serializing cooperating create/update requests on MySQL. The database also has an exact-range unique constraint. No opening hours are imposed because Venue opening-hour configuration is not part of this API. Slots with an active hold or booking cannot be edited or deactivated; expired holds can be reclaimed.

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
      "slot_date": "2026-10-29",
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
  "slot_date": "2026-10-29",
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
| `403 Forbidden` | Valid token has insufficient role or OWNER does not own the related Venue | Implemented for USER, OWNER cross-owner writes, and non-ADMIN Sports writes |
| `404 Not Found` | Requested resource ID does not exist | Implemented on GET detail; write handlers also check existence after access is granted |
| `409 Conflict` | Duplicate Sport name, overlapping active Time Slot, reserved slot mutation, unavailable reservation, invalid reservation transition, or database uniqueness conflict | Implemented in write handlers after authorization |
| `422 Unprocessable Entity` | Invalid path/query/body, extra body fields, blank required text, invalid price/range, time not on a 30-minute boundary, or new/changed start time not in the future | Implemented by FastAPI/Pydantic and Court Service write validation; malformed requests may be rejected before authorization |
| `503 Service Unavailable` | JWT verification or internal service token configuration is missing/invalid | Implemented |
| `503 Service Unavailable` / `504 Gateway Timeout` | Gateway cannot reach a service or the upstream request times out | Implemented by Gateway, not by Court Service |

Error JSON follows FastAPI's `{"detail": "..."}` shape, except the normal Pydantic `422` validation response. Database credentials and JWT material are not returned.

## 5. Integration contract with S1

### Authentication and authorization

User Service on `feature/s1-w1-auth-usecase` issues HS256 access tokens with string `sub`, `role`, `iat`, and `exp`; expiration defaults to 60 minutes. Court Service verifies the signature independently using `python-jose`, requires `sub`, `iat`, and `exp`, validates the numeric user ID and one of `USER`, `OWNER`, or `ADMIN`, and does not import User Service code. Configure the same secret in the ignored local `backend/.env` for both services. Never put a real secret in this contract or Git.

- Missing, malformed, invalid-signature, expired, or invalid-claim tokens return `401`.
- A valid token with a role not allowed by an endpoint returns `403`.
- Public GET catalogue routes remain public. The `owner_id` query is a public filter, not an access-control check.
- USER cannot mutate Court data. OWNER may create a Venue only for their own `sub`; updates preserve the stored owner. Court and Time Slot writes check ownership through their related Venue. Cross-owner mutations return `403`.
- ADMIN may manage Sports and all Venues, Courts, and Time Slots system-wide. Only ADMIN may mutate Sports.
- Gateway forwards the Authorization header. CORS uses exact configured origins, allows the required API methods and headers, and rejects wildcard origins.

`venues.owner_id` is a logical User Service ID; Court DB intentionally has no cross-database User foreign key. Token issuer/audience, key rotation, and role-change/revocation behavior are not specified by the inspected S1 contract. No secret or token is embedded in this contract.

### Booking Service data, availability, and internal reservations

The existing GET APIs provide these fields:

- `GET /api/v1/time-slots?court_id={id}&slot_date=YYYY-MM-DD` returns `id`, `court_id`, `slot_date`, `start_time`, `end_time`, `is_active`.
- `GET /api/v1/courts/{court_id}` returns `venue_id`, `sport_id`, `name`, `price_per_hour`, `is_active` and `description`.
- `GET /api/v1/venues/{venue_id}` and `GET /api/v1/sports/{sport_id}` provide the corresponding venue and sport fields.

Booking can obtain the basic slot and price data with multiple GET calls, but there is no single joined availability response. These reads do not reserve a slot. The current `is_active` flag is not a booking/hold state.

Court Service implements the S1 internal contract with `POST /api/v1/internal/slots/{slot_id}/hold|confirm|release`, `booking_id` query parameter, and `X-Internal-Token`. These endpoints are service-to-service only; the Gateway does not expose `/api/v1/internal`. Hold returns the slot, court, venue, owner and hourly price fields required by Booking, with an ISO 8601 UTC `expires_at`. Repeating hold/confirm/release for the same booking is idempotent. A competing booking, wrong booking ID, expired hold confirmation, or booked-slot release returns `409`. The hold duration defaults to 10 minutes and is configured with `BOOKING_HOLD_MINUTES`; Court and Booking must share the same `INTERNAL_SERVICE_TOKEN` and hold duration. `time_slots.is_active` remains catalogue state, separate from reservation state.

The reservation state is stored on `time_slots` using `reservation_status`, `reservation_booking_id`, and `reservation_expires_at`. Existing databases require the SQL migration in `backend/migrations/20261026_add_time_slot_reservations.sql`; it has not been run. Hold, confirm, release and slot edits lock the slot row; schedule create/update also locks the affected Court rows to serialize overlap checks on MySQL. SQLite tests verify state behavior but do not establish production concurrency behavior. There is no joined availability API; no endpoint is invented for one.

### Owner/Admin Management Web needs

| Use case | Exists in Court Service now | Other service / future work |
|---|---|---|
| Read venues and courts | Public GET list/detail routes; venue list can filter by `owner_id`, courts by `venue_id`/`sport_id` | Reads are public; `owner_id` is not authorization |
| Manage venues, courts, and schedule | OWNER writes require valid JWT and ownership through related Venue; ADMIN has system-wide API access | Management Web provides OWNER CRUD and ADMIN Sports/Venue/Court CRUD; Admin Time Slot screen is not wired in this iteration. Auth remains unverified end-to-end until S1 is integrated and valid local credentials are available |
| View bookings and complete booking | Not a Court Service responsibility or route | Implemented on inspected S1 branch; unavailable in this checkout pending integration |
| QR check-in | Not a Court Service responsibility or route | Implemented on inspected S1 branch; unavailable in this checkout pending integration |
| Dashboard booking/revenue aggregates | Not provided by Court Service | Requires Booking/Payment API or an agreed dashboard aggregation contract from S1 |

Project Plan V5 also lists planned route shapes such as `/venues/{id}/courts`, `/courts/{id}/slots`, `/owner/venues`, `/owner/courts`, and `/owner/slots`; they are not currently implemented. The implemented public Court routes remain under `/api/v1` as documented above.

The inspected S1 branch implements Booking create/list/detail/cancel, internal payment-context/confirm/check-in/complete/expire routes, Payment APIs, and calls the Court reservation paths documented above. Those S1 source changes are not present in this checkout until integration. V5's alternate `/internal/holds/{hold_id}/...`, joined slot lookup, and venue ownership lookup shapes are not part of the inspected S1 contract and are not implemented here.

## 6. Consistency check

- SQLAlchemy models and Pydantic response schemas cover the four Court DB tables: `sports`, `venues`, `courts`, `time_slots`. Time Slots include internal reservation columns; existing databases need the supplied migration.
- Court DB has the local physical relationships `courts.venue_id -> venues.id`, `courts.sport_id -> sports.id`, and `time_slots.court_id -> courts.id`; the unique time-slot range index is present.
- `venues.owner_id` and Booking's `time_slot_id` are logical cross-service references; they are not physical foreign keys in Court DB.
- `docs/diagrams/court-service-erd.dbml` describes the same four Court tables and internal relationships. The overall ERD contains the nine logical business tables, including `checkins` in Booking ownership; it is a conceptual ERD and does not change the database-per-service foreign-key rule.
- Two wire-format details differ from Project Plan V5 §6.1: V5 states time as `HH:mm`, while the current API schema emits `HH:MM:SS`; V5 states money as integer VND, while `price_per_hour` is `DECIMAL(12,2)` and emits a decimal string. Confirm the shared format with S1 and the clients before cross-service integration; this step does not change the existing schema or API.
- The S1 Booking–Court endpoint shapes now match the implemented Court reservation API. The Court database needs the supplied migration before those routes can run against an existing database; no database was altered.

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
GET http://localhost:8000/api/v1/time-slots?court_id=1&slot_date=2026-10-29
```

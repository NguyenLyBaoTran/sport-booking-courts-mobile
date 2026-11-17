# OWNER & ADMIN REQUIREMENTS

**Project:** Sports Court Booking System  
**Document owner:** Student 2  
**Iteration:** 1 – Requirements & Foundation  
**Status:** Draft v1 – review with Student 1 before implementation  
**Merge target:** `docs/SYSTEM_REQUIREMENTS.md` (after both members review)

> **Purpose:** Describe the Court Owner/Staff and Admin requirements, workflows, permissions, and business rules. This is a requirements document, not an implementation report. The team must confirm any open decisions before creating database migrations or final API contracts.

## 1. Scope and actors

The system allows customers to find and book sports courts using the Android app. Court Owners manage venues, courts, time slots, bookings, and QR check-ins through the management web. Admins supervise system-wide data and operations through the same management web, using role-based access.

| Actor | Description | Interface |
|---|---|---|
| Customer (`USER`) | Searches courts, makes bookings, pays using mock payment, shows booking QR, and reviews completed bookings | Android app (Student 1) |
| Court Owner/Staff (`OWNER`) | Manages assigned venues/courts/schedules and checks customers in | Management Web (Student 2) |
| Administrator (`ADMIN`) | Manages and monitors system-wide data | Management Web (Student 2) |

**Scope of Student 2:** Owner/Admin web, public sports/venue/court/slot catalog API, owner venue/court/slot management, QR check-in, admin management, and database/architecture foundation.

**Shared dependencies:** Student 1 owns Authentication, User, Booking, Payment, and Review logic. Student 2 calls those shared APIs or services rather than creating a second implementation.

## 2. Permissions (role-based access)

| Function | USER | OWNER | ADMIN |
|---|:---:|:---:|:---:|
| Sign in | ✓ | ✓ | ✓ |
| Search sports, venues, courts, available slots | ✓ | ✓ | ✓ |
| Create and pay for own booking | ✓ | — | — |
| View own booking and QR | ✓ | — | — |
| Manage owned venues/courts/time slots | — | ✓ | —* |
| View bookings for owned venues | — | ✓ | ✓ (all) |
| Scan QR and check in customers at owned venues | — | ✓ | — |
| Mark checked-in booking as completed | — | ✓ | —* |
| View reviews of owned venues | — | ✓ | ✓ (all) |
| Manage users and owner accounts | — | — | ✓ |
| Manage sports categories | — | — | ✓ |
| Manage/oversee venues, courts, bookings, payments, reviews system-wide | — | — | ✓ |

`*` Admin may use separate moderation/override functions if explicitly approved. Admin does **not** automatically act as the venue's Owner in normal Owner workflows.

**Mandatory authorization rules:** Every protected request requires a valid JWT and correct role. An OWNER must only access records belonging to their venues, verified on the backend; hiding buttons in the web UI is insufficient.

## 3. Owner functional requirements

| ID | Requirement | Expected behavior / acceptance criterion | Priority |
|---|---|---|---|
| OWN-01 | Sign in | Owner signs in through the shared Auth API and accesses only Owner pages. | Must |
| OWN-02 | Dashboard | Display basic counts for owned venues, courts, and bookings; no other owner's data. | Must |
| OWN-03 | Venue management | Create, view, edit owned venues with required fields and validation. | Must |
| OWN-04 | Court management | Create, view, edit courts under owned venues; select a valid sport and manage court availability. | Must |
| OWN-05 | Time-slot management | Create/view/update availability and price for court time slots; reject invalid/overlapping slots according to agreed slot model. | Must |
| OWN-06 | Booking management | View and filter bookings for owned venues, including booking/customer summary, date/time, and status. | Must |
| OWN-07 | QR check-in | Scan a confirmed booking QR, send its token to the backend, and display success/failure with a clear reason. | Must |
| OWN-08 | Complete booking | Mark a valid checked-in booking as `COMPLETED` through the shared Booking logic. | Must |
| OWN-09 | Review viewing | Read customer reviews associated with owned venues, without editing customer ratings. | Should |
| OWN-10 | Payment status viewing | View payment status for owned bookings; cannot directly change payment status. | Should |

**Venue minimum data (proposed):** name, address/location, description, contact information, status. **Court minimum data (proposed):** venue, sport, name/number, description, active status. **Slot minimum data (proposed):** court, date/start/end time, price, availability. Confirm field names and time-slot representation in `DB_SCHEMA.md` and `API_CONTRACT.md`.

### 3.1 Owner workflow: create and publish bookable slots

1. Owner signs in.
2. Owner creates or selects a venue that belongs to their account.
3. Owner creates a court under that venue and assigns its sport.
4. Owner creates time slots and sets price/availability.
5. Backend validates ownership, time range, overlap, and price.
6. Available slots become visible to customers through the public Catalog/Schedule APIs.
7. A customer can book a slot through Student 1's Booking API; Owner sees the resulting booking.

### 3.2 Owner workflow: manage bookings

1. Owner opens the Booking Management page.
2. System shows only bookings linked to the Owner's venues.
3. Owner filters or opens a booking to inspect its status and payment summary.
4. Owner may check in an eligible booking using QR and later complete it using the shared Booking API.
5. Owner cannot arbitrarily mark unpaid/cancelled bookings as completed.

## 4. Admin functional requirements

| ID | Requirement | Expected behavior / acceptance criterion | Priority |
|---|---|---|---|
| ADM-01 | Sign in | Admin signs in using shared Auth API and is restricted to Admin pages. | Must |
| ADM-02 | Dashboard | Display system-wide counts for users, owners, venues, courts, and bookings. | Must |
| ADM-03 | User/Owner management | View/search accounts and update permitted account status/role according to agreed rules; never expose passwords. | Must |
| ADM-04 | Sports management | Create/view/edit/disable sports categories; prevent destructive changes that invalidate existing courts. | Must |
| ADM-05 | Venue/Court management | View/search and moderate venues/courts across owners, with authorization and validation. | Must |
| ADM-06 | Booking monitoring | View/search bookings and their states across the system. | Must |
| ADM-07 | Payment monitoring | View mock-payment attempts/status; do not directly mark a payment as successful. | Must |
| ADM-08 | Review management | View and moderate inappropriate reviews based on defined moderation rules. | Must |

**Scope control:** Keep Admin management simple: searchable tables, detail views, and only the necessary edit/status actions. Analytics, exports, audit dashboard, and advanced approval workflows are outside the mandatory Iteration 1 scope.

## 5. QR check-in workflow

**Precondition:** A Customer has a booking in `CONFIRMED` state after a successful mock payment. Android displays a QR representing a random, opaque booking token (not personal data or a predictable booking ID).

1. Customer opens the booking QR in the Android app.
2. Owner opens the QR Scanner on the management web and grants camera permission.
3. Web reads the QR token and calls `POST /api/v1/owner/checkins` with the token.
4. Backend authenticates the Owner, resolves the token, and checks that the booking belongs to one of the Owner's venues.
5. Backend verifies booking status is `CONFIRMED`, that the QR token is valid, and that no check-in already exists. Time-window validation, if adopted, must be agreed by both students.
6. On success, backend records exactly one check-in and changes the booking to `CHECKED_IN` atomically.
7. Web shows a success message with a limited booking summary. On failure, web shows a clear error (invalid QR, wrong venue, cancelled/unpaid booking, duplicate scan, etc.).
8. After the session, Owner marks the booking `COMPLETED` via Student 1's Booking API. Customer may then submit one review.

**Important:** QR generation/display is owned by Student 1. QR scanning and check-in endpoint are owned by Student 2. The token field and Booking state transition must be agreed in the shared API contract. Never trust QR text or venue IDs supplied by the browser without server-side validation.

## 6. Business rules

| ID | Rule |
|---|---|
| BR-01 | A venue belongs to exactly one Owner account in the initial model. |
| BR-02 | An Owner may manage multiple venues; a venue may contain multiple courts. |
| BR-03 | A court belongs to exactly one venue and has a defined sport. |
| BR-04 | A time slot belongs to one court; start time must precede end time and price must not be negative. |
| BR-05 | A court cannot have overlapping bookable time slots; unavailable/disabled slots must not be offered for new bookings. |
| BR-06 | A slot cannot have two simultaneously active bookings. Student 1's Booking logic must enforce this under concurrent requests. |
| BR-07 | An Owner may only view/change venues, courts, slots, and bookings related to their own venues. |
| BR-08 | A booking may be checked in only when its status is `CONFIRMED` and the QR token is valid. |
| BR-09 | Each booking can be checked in at most once. Duplicate or concurrent scans must not create duplicate check-in records. |
| BR-10 | Successful check-in changes status `CONFIRMED → CHECKED_IN`; completion changes `CHECKED_IN → COMPLETED`. |
| BR-11 | `CANCELLED`, `EXPIRED`, and unpaid bookings cannot be checked in. |
| BR-12 | Owner cannot manually change payment outcomes; payment is managed by the shared Payment module. |
| BR-13 | Admin access is system-wide only for authorized Admin endpoints; admin changes must not bypass business validation. |
| BR-14 | Records referenced by bookings/payments should be deactivated rather than deleted if deletion would break history. |
| BR-15 | Booking, payment, and check-in operations must use backend validation and database constraints/transactions where needed. |

### 6.1 Shared status vocabulary

**Booking:** `PENDING`, `CONFIRMED`, `CHECKED_IN`, `COMPLETED`, `CANCELLED`, `EXPIRED`.  
**Payment:** `PENDING`, `PAID`, `FAILED`, `CANCELLED`.  
**Payment provider:** `MOCK` (mandatory); `VNPAY` sandbox is optional and outside Iteration 1.

Do not add extra statuses or alternate spellings without updating both backend and frontend contracts.

## 7. Student 2 interfaces and dependencies

| Interface / data | Provider (owner) | Consumer | Contract to agree |
|---|---|---|---|
| Auth / JWT / `users` | Student 1 | Owner/Admin Web and all protected Student 2 endpoints | Login response, token header, role values, user ID |
| Public sports/venues/courts/slots API | Student 2 | Student 1 Android | IDs, filters, pagination, slot availability/price |
| Venue/court/slot management | Student 2 | Owner Web | CRUD request/response, validation errors |
| Booking creation/status/owner booking listing | Student 1 | Owner Web and Student 2 check-in | Booking ID, venue/court/slot relation, status, Owner listing |
| Mock payment | Student 1 | Owner/Admin status views | Payment states and safe summary fields |
| Booking QR token display | Student 1 | Student 2 QR scanner/check-in | Opaque token format and lifecycle |
| Check-in endpoint / `checkins` | Student 2 | Owner Web, shared Booking state logic | QR token, ownership checks, atomic state change |
| Complete booking endpoint | Student 1 | Owner Web | Allowed transition `CHECKED_IN → COMPLETED` |
| Reviews | Student 1 | Owner/Admin Web | Review fields and moderation rules |

### 7.1 Proposed Student 2 API inventory

- Public: `GET /api/v1/sports`, `GET /api/v1/venues`, `GET /api/v1/venues/{id}`, `GET /api/v1/venues/{id}/courts`, `GET /api/v1/courts/{id}/slots`.
- Owner: CRUD under `/api/v1/owner/venues`, `/api/v1/owner/courts`, `/api/v1/owner/slots`; `POST /api/v1/owner/checkins`.
- Admin: dashboard and management endpoints under `/api/v1/admin/...`, finalized in `API_CONTRACT.md`.

**Note:** Owner booking list and completion endpoints belong to Student 1 even though Owner Web consumes them. This avoids duplicated Booking logic.

## 8. Non-functional requirements

- **Security:** JWT role checks; Owner resource ownership checks; no passwords or secrets in frontend responses; environment variables for secrets.
- **Reliability:** Check-in must handle duplicate requests safely; Booking/Payment/Check-in state changes must be consistent.
- **Usability:** Owner/Admin pages must be clear, responsive, and show validation/error messages.
- **Maintainability:** One FastAPI backend with separated router/service/model modules; one shared database schema; Alembic migrations reviewed before merging.
- **Testing:** Include successful and failed paths, especially cross-owner access, invalid QR, repeated QR, and unauthorized Admin endpoints.

## 9. Iteration 1 deliverables (Student 2)

- [ ] Review this document with Student 1; merge agreed requirements into `docs/SYSTEM_REQUIREMENTS.md`.
- [ ] Draw `docs/diagrams/database_erd.dbml` (all nine core tables, including Student 1-owned tables) and export an image.
- [ ] Draw `docs/diagrams/system_architecture.drawio` and export an image.
- [ ] Initialize shared FastAPI application and MySQL connection.
- [ ] Set up Alembic and verify a migration can be applied to a local development database.
- [ ] Create basic seed data and Owner/Admin Web folder structure.
- [ ] Draft Chapter 2 Owner/Admin requirements for the report using actual agreed design.

## 10. Decisions to confirm with Student 1

1. **Time-slot design:** fixed stored slots versus generated schedule; date/time timezone and how overlapping intervals are checked.
2. **QR token storage:** where the opaque token lives, how it is generated, and whether it expires or rotates.
3. **Check-in transaction boundary:** which shared service owns the atomic update of Booking state and insertion of Check-in record.
4. **Owner accounts:** whether `OWNER` accounts are created by Admin or by registration with approval.
5. **Admin actions:** allowed disable/edit operations and how historical records remain valid.
6. **Venue/court required fields:** final names, validation rules, and how sports are assigned.
7. **Owner booking listing and completion:** exact routes and JSON responses from Student 1.

> **Ready for ERD v1 when:** Both students approve the core entity relationships, status vocabulary, slot representation, and QR/check-in ownership boundary.

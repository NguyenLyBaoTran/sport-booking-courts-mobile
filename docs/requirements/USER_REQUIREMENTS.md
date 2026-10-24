
# USER REQUIREMENTS

**Project:** Sports Court Booking System  
**Document owner:** Student 1  
**Iteration:** 1 – Requirements & Foundation  
**Status:** Draft v1 – review with Student 2 before implementation  
**Merge target:** `docs/SYSTEM_REQUIREMENTS.md`

> **Purpose:** Describe Customer requirements, booking and payment workflows, QR code usage, reviews, permissions, and acceptance criteria. This document defines system requirements and does not claim that the features have already been implemented.

## 1. Scope and actors

The Sports Court Booking System allows customers to find sports courts, view available time slots, create bookings, make mock payments, display booking QR codes, and review completed bookings.

Venue Owners manage their venues, courts, and schedules. Administrators manage system-wide data and operations according to their permissions.

| Actor | Description | Interface |
|---|---|---|
| Customer (`USER`) | Searches for courts, books time slots, pays, displays QR codes, and submits reviews | Android application |
| Venue Owner (`OWNER`) | Manages owned venues, courts, schedules, and customer check-ins | Management Web |
| Administrator (`ADMIN`) | Manages and monitors system-wide data | Management Web |

**Scope of Student 1:** Customer requirements, Booking, Payment, Review, Authentication requirements, System Use Case Diagram, Booking Activity Diagram, and Android User Foundation.

**Shared dependencies:** Student 2 provides the backend and database foundation. Both students must agree on the database schema, API endpoints, JSON formats, booking statuses, and payment statuses before integrating their modules.

## 2. Customer permissions

| Function | USER | OWNER | ADMIN |
|---|:---:|:---:|:---:|
| Register a customer account | ✓ | — | — |
| Sign in | ✓ | ✓ | ✓ |
| View personal profile | ✓ | — | — |
| Browse sports, venues, and courts | ✓ | ✓ | ✓ |
| View available time slots | ✓ | ✓ | ✓ |
| Create a booking | ✓ | — | — |
| View own bookings and booking history | ✓ | — | — |
| Cancel an eligible booking | ✓ | — | — |
| Make mock payments for own bookings | ✓ | — | — |
| Display booking QR code | ✓ | — | — |
| Submit a review for a completed booking | ✓ | — | — |
| Manage owned venues and courts | — | ✓ | — |
| Check in customers | — | ✓ | — |
| Manage system data | — | — | ✓ |

**Mandatory authorization rules:** Every protected request must validate the access token and the user's permissions. Customers must not access another customer's private booking or payment information. Hiding interface elements alone is not sufficient to enforce authorization.

## 3. User functional requirements

| ID | Requirement | Expected behavior / acceptance criterion | Priority |
|---|---|---|---|
| USR-01 | Register | A customer can create an account with valid required information. Duplicate email addresses are rejected. | Must |
| USR-02 | Sign in | A registered customer can sign in using valid credentials and receive an access token. | Must |
| USR-03 | Authentication validation | Invalid credentials are rejected without revealing sensitive account information. | Must |
| USR-04 | View profile | An authenticated customer can retrieve their own account information. | Must |
| USR-05 | Role-based access | The system distinguishes USER, OWNER, and ADMIN roles and restricts unauthorized operations. | Must |
| USR-06 | Secure credentials | Passwords are stored as secure hashes and are never returned in API responses. | Must |
| USR-07 | Sign out | The application clears its locally stored access token when the customer signs out. | Should |

## 4. Booking functional requirements

| ID | Requirement | Expected behavior / acceptance criterion | Priority |
|---|---|---|---|
| BKG-01 | Browse courts | Customers can browse available sports, venues, and courts. | Must |
| BKG-02 | View availability | Customers can select a date and view available time slots and prices. | Must |
| BKG-03 | Create booking | The system creates a booking for an available time slot and assigns it to the authenticated customer. | Must |
| BKG-04 | Prevent double booking | Concurrent requests for the same slot cannot create multiple valid reservations. | Must |
| BKG-05 | Pending reservation | A new booking enters PENDING and holds its slot for 10 minutes. | Must |
| BKG-06 | Booking expiration | An unpaid pending booking becomes EXPIRED after the hold period, and its slot is released. | Must |
| BKG-07 | Booking history | Customers can view their own bookings and their current statuses. | Must |
| BKG-08 | Booking details | Customers can view the details of their own bookings, including court, date, time, and payment status. | Must |
| BKG-09 | Cancel booking | Customers can cancel bookings that are eligible for cancellation under the agreed policy. | Must |
| BKG-10 | Booking status transition | The system validates every status transition and rejects invalid transitions. | Must |
| BKG-11 | Booking confirmation | A booking becomes CONFIRMED only after successful payment confirmation and validation of the reservation. | Must |

### 4.1 Booking status lifecycle

The system supports the following booking statuses:

- `PENDING`: The booking is awaiting successful payment confirmation.
- `CONFIRMED`: The booking has been successfully confirmed.
- `CHECKED_IN`: The customer has completed a valid QR check-in.
- `COMPLETED`: The booking session has finished.
- `CANCELLED`: The booking has been cancelled according to the applicable policy.
- `EXPIRED`: The pending reservation has expired.

The normal lifecycle is:

`PENDING → CONFIRMED → CHECKED_IN → COMPLETED`

`CANCELLED` and `EXPIRED` are alternative terminal states where applicable.

## 5. Payment functional requirements

| ID | Requirement | Expected behavior / acceptance criterion | Priority |
|---|---|---|---|
| PAY-01 | Mock payment | The system provides a mock payment mechanism without processing real money. | Must |
| PAY-02 | Payment success | A successful mock payment can lead to booking confirmation after the Booking logic validates the reservation. | Must |
| PAY-03 | Payment failure | A failed payment is recorded and does not confirm the booking. | Must |
| PAY-04 | Retry payment | Customers can retry after a failed payment while the booking remains eligible. | Must |
| PAY-05 | Prevent duplicate payment | Repeated or concurrent requests cannot produce multiple successful payments for the same booking. | Must |
| PAY-06 | Payment history | Customers can view payment information associated with their own bookings. | Must |
| PAY-07 | Payment consistency | A payment result alone must not cause the client to assume that the booking is confirmed. | Must |
| PAY-08 | Error recovery | The system handles service failures and reconciliation without reporting a false booking confirmation. | Must |

### 5.1 Payment status vocabulary

Payment records use the following proposed statuses:

- `PENDING`: The payment attempt has not reached a final result.
- `PAID`: The payment has been successfully recorded.
- `FAILED`: The payment attempt failed.
- `CANCELLED`: The payment operation was cancelled where applicable.

The mock provider returns a result of `SUCCESS` or `FAILED`. `SUCCESS` is the provider result; `PAID` is the recorded payment status. These terms must not be used interchangeably.

## 6. QR code and check-in requirements

| ID | Requirement | Expected behavior / acceptance criterion | Priority |
|---|---|---|---|
| QR-01 | Generate QR token | The system generates a unique, unpredictable token after the booking is confirmed. | Must |
| QR-02 | Display QR code | The Android application displays the QR code associated with the confirmed booking. | Must |
| QR-03 | Validate QR token | The backend verifies the token and the booking's eligibility before check-in. | Must |
| QR-04 | Verify Owner permission | Only an authorized Owner of the relevant venue can check in the booking. | Must |
| QR-05 | Prevent duplicate check-in | A booking can be checked in only once, including under concurrent scan requests. | Must |
| QR-06 | Update booking status | A successful check-in changes the booking from CONFIRMED to CHECKED_IN. | Must |
| QR-07 | Complete booking | An authorized Owner can complete a valid checked-in booking. | Must |
| QR-08 | Reject invalid scans | Invalid tokens, unpaid bookings, cancelled bookings, and repeated scans are rejected. | Must |

The QR token must not expose a predictable booking ID or sensitive customer information. The Owner Web submits the scanned token to the backend; it must not change the booking status directly.

## 7. Review functional requirements

| ID | Requirement | Expected behavior / acceptance criterion | Priority |
|---|---|---|---|
| REV-01 | Submit review | A customer can review a booking after it reaches COMPLETED. | Must |
| REV-02 | Verify ownership | Only the customer who owns the booking can submit its review. | Must |
| REV-03 | Prevent duplicate reviews | A booking can have at most one review. | Must |
| REV-04 | Validate review data | The backend validates the rating and required review fields. | Must |
| REV-05 | View reviews | Authorized users can retrieve reviews according to their permissions. | Should |

## 8. Non-functional requirements

- **NFR-01 – Security:** Protected APIs validate JWT authentication and authorization.
- **NFR-02 – Data integrity:** Booking and payment state changes must follow the defined business rules.
- **NFR-03 – Concurrency:** Concurrent reservation and payment requests must not create duplicate successful operations.
- **NFR-04 – Reliability:** Failed requests must not silently leave incorrect booking states.
- **NFR-05 – Usability:** The Android application provides clear validation messages and operation results.
- **NFR-06 – Maintainability:** API contracts, models, diagrams, and tests must remain consistent.
- **NFR-07 – Compatibility:** The customer application uses Java, XML layouts, Retrofit, and Gson.
- **NFR-08 – Configuration:** Secrets and database credentials must be stored in environment configuration rather than committed source code.

## 9. Dependencies and open decisions

The following items must be agreed upon with Student 2 before dependent implementation:

1. The final database fields and relationships for users, bookings, payments, and reviews.
2. The exact public API endpoints and JSON request/response formats.
3. The storage and expiration mechanism for pending slot reservations.
4. The ownership boundary for slot reservation and booking confirmation.
5. The QR token format, storage, and lifecycle.
6. The rules for cancellation and payment reconciliation.
7. The final payment status vocabulary and HTTP error responses.

## 10. Iteration 1 deliverables — Student 1

- [ ] Complete User, Booking, Payment, QR, and Review requirements.
- [ ] Complete `docs/BUSINESS_RULES.md`.
- [ ] Create `docs/diagrams/system_usecase.puml` and export PNG.
- [ ] Create `docs/diagrams/booking_activity.puml` and export PNG.
- [ ] Review the requirements and API contract with Student 2.
- [ ] Update the document when the team approves changes.

These requirements describe the planned behavior. A feature is considered implemented only after its code and tests have been verified.

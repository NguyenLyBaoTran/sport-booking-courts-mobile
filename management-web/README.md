# Owner/Admin Management Web

## Project overview

This repository contains an Android client, an Owner/Admin management website, and a Python backend. The backend keeps the original modular monolith in `backend/app/` and adds an API Gateway with separate User, Court, Booking, and Payment services. Each microservice has its own MySQL database on the shared MySQL server.

| Area | Main technology | Current role |
| --- | --- | --- |
| Android client | Java, XML | Mobile application |
| Management Web | HTML, CSS, JavaScript | Owner/Admin screens; static site |
| Backend | Python, FastAPI, Uvicorn | Gateway and four microservices |
| Data | SQLAlchemy, PyMySQL, MySQL | Separate database per service |

Useful locations: `management-web/` contains this website; `backend/app/` is the retained legacy backend; `backend/gateway/` contains the Gateway; `backend/services/` contains the microservices; `docs/api/` contains the Court Service API contract; and `docs/diagrams/` contains architecture and ERD sources.

This project uses static HTML, CSS, and JavaScript with Bootstrap 5.3.3 and Bootstrap Icons 1.11.3 vendored under `assets/vendor/`, so page styles, Bootstrap components, and icons work without Internet access. Their MIT license files are kept beside the assets. The pinned `html5-qrcode` 2.3.8 scanner library is also vendored with its Apache-2.0 license. No CDN or Node build is required at runtime.

## Current implementation status

Court Service provides its catalogue API and the Management Web reads it through the Gateway. The web has a real Auth login flow prepared for the S1 User Service contract and authenticated Owner writes for Venues, Courts, and Time Slots. These paths require the S1 Auth branch to be integrated, a shared local JWT configuration, and a real OWNER account. Booking and QR check-in remain Demo Mode previews because their APIs are not implemented in the inspected S1 branch. User/Auth and Payment integration readiness is summarized in [S2 Integration Notes](../docs/api/s2-integration-notes.md). The old backend remains in place. See `backend/README.md` for backend setup and endpoint details.

## Run locally

Start Court Service and API Gateway in separate terminals from the repository root:

```powershell
cd backend/services/court_service
python -m uvicorn app.main:app --reload --port 8002
```

```powershell
cd backend/gateway
python -m uvicorn main:app --reload --port 8000
```

In another terminal, serve the Management Web:

```powershell
cd management-web
python -m http.server 8080
```

Open `http://localhost:8080`. **Sign in** sends credentials to `/api/v1/auth/login` through the Gateway, then validates the returned profile with `/api/v1/users/me`. Use the separate **Demo Owner** or **Demo Admin** buttons for fictional workspaces; those buttons do not create or authenticate an account.

## API Mode and Gateway offline

Start Court Service and the Gateway using the commands above before opening API Mode. The UI keeps API Mode selected if the Gateway is offline; it does not substitute mock catalogue data. The Dashboard, registry, and schedule show **Cannot connect to API Gateway** with a manual Retry button. Check the two service terminals, confirm ports `8002` and `8000`, then press Retry. Requests are not retried continuously.

Camera access works only on a secure context: `http://localhost`, `http://127.0.0.1`, or HTTPS. Browser extensions can inject their own scripts and console messages; `onboarding.js` is not part of this repository. The frontend includes `favicon.svg` to avoid a missing favicon request.

## Login modes

The Login screen starts in **Demo Mode**, where a user selects the Court Owner or Admin workspace. Email and password are not checked; this mode stores only the selected demo role and never issues or stores a JWT. **API Mode** hides the workspace selector, sends credentials to `POST /api/v1/auth/login` through the Gateway, then verifies the profile with `GET /api/v1/users/me`. Only OWNER and ADMIN roles enter a management workspace; USER is rejected. API failures stay in API Mode and show an error. Sign out clears the access token and in-memory profile; protected routes redirect to Login if revisited through browser history. Local asset URLs carry a version query so the current Login UI does not reuse stale app or stylesheet files.

## Gateway configuration

The frontend calls the Gateway only. Set the single base URL in `assets/js/config.js` (`http://localhost:8000` by default). The Gateway allows browser requests from `http://localhost:8080` and `http://127.0.0.1:8080` for local development.

## Court Service screens

The Owner and Admin dashboards, Venue & Court registry, and Time Slot pages read live Sports, Venue, Court, and Time Slot data through the Gateway. Registry has independent venue and court search boxes; sport, status, and venue filters remain available. Search filters the loaded data in the browser and does not issue requests while typing. Owner API Mode loads only the authenticated Owner?s venue/court/time-slot catalogue; Admin Time Slots loads the system-wide catalogue. Search and filters apply to loaded records in the browser. Detail buttons fetch the selected resource. API loading, empty, and error states are shown with retry controls.

To populate a local demo, follow the Court Service seed instructions in [`backend/README.md`](../backend/README.md#court-service-developmentdemo-seed-step-5). The seed requires an Owner ID confirmed with S1; without one the database should remain unseeded and these screens show empty states.

Displayed slot status reflects only `is_active`; it does not indicate whether a slot is booked or available. Prices are formatted from the API decimal string for display and are not used for payment calculations.

## Owner CRUD

On the Owner Dashboard, Venue & Court, and Schedule screens, use the data mode selector:

- **API Mode** is the default after a real login. It reads the Sports, Venue, Court, and Time Slot APIs through the Gateway. Authenticated OWNER accounts can create/update/deactivate their own Venues, Courts, and Time Slots. ADMIN accounts can manage Sports, Venues, Courts, and Time Slots system-wide. Requests carry the session access token in `Authorization: Bearer`; the browser never receives `JWT_SECRET_KEY`. OWNER venue payloads take `owner_id` from `/users/me`; ADMIN supplies the target owner ID. Only ADMIN can mutate Sports, which Court creation requires.
- **Demo Mode** uses a separate sample dataset kept only in JavaScript memory. Add, edit, and delete (soft deactivation) work for sports, venues, courts, and time slots, with local validation including duplicate sport names and duplicate/overlapping slots. These actions never call the Gateway. Reloading the page restores the starter data. Demo venues have no real Owner ID.

Court forms require an existing venue and sport, and a positive price with up to two decimal places. Time Slot forms use the shared read-only calendar picker, ask for Venue before Court, require times on 30-minute boundaries, require start time before end time, and reject new or changed start times in the past using Vietnam business time (`Asia/Ho_Chi_Minh`). Existing historical slots can still be viewed and filtered; edits that leave their date and start time unchanged are allowed. Court Service remains authoritative for ownership, past-time, and overlap validation. API errors show permission, conflict, validation, and service-unavailable feedback.

The older backend-owned seed data remains separate from browser Demo Mode. To seed MySQL, follow the Court Service instructions in [`backend/README.md`](../backend/README.md#court-service-developmentdemo-seed-step-5); it requires an Owner ID confirmed with S1.

## Owner Booking Management (Step 7)

Open the Owner **Bookings** screen from the sidebar. In API Mode, the page calls the approved `GET /api/v1/owner/bookings` endpoint through the Gateway with the session Bearer token. Venue, date, and status filters are sent to Booking Service; text search filters the loaded response locally. List and detail views use only contract fields, show IDs where related display names are not part of the schema, and never render `qr_token`. Detail uses `GET /api/v1/owner/bookings/{booking_id}`. **Complete Booking** appears only for `CHECKED_IN`, asks for confirmation, and calls `POST /api/v1/owner/bookings/{booking_id}/complete`; the UI refreshes list and detail after success or a `409`. Loading, empty, filter-empty, and safe API error states are shown without falling back to mock rows.

Switch the shared Owner data mode selector to **Demo Mode** to view six fictional bookings covering `PENDING`, `CONFIRMED`, `CHECKED_IN`, `COMPLETED`, `CANCELLED`, and `EXPIRED`. The list is sorted newest first and supports Booking ID/customer search, booking date and status filters. Typing updates only the table rows, so the search field keeps focus and caret position. Booking details group customer and court information, show payment/check-in status only when provided, and offer **Complete Booking** only for `CHECKED_IN`. Confirm the action to change that record to `COMPLETED` in browser memory. Reload restores the original sample dataset.

Demo booking data is local UI-only mock data. It does not use MySQL, call Booking Service, or alter Court Service data. Demo booking data remains independent of the authenticated account; no Booking endpoint is called while Demo Mode is selected.

The UI follows [the approved Owner Booking & QR contract](../docs/api/owner-booking-qr-contract.md). The inspected S1 source does not yet implement the public Owner list/detail/completion routes, so API Mode will show the upstream error until those S1 endpoints are integrated and available. No live end-to-end integration is claimed.

## Owner QR Scanner & Demo Check-in (Step 8)

Serve this static site on `http://localhost:8080` or HTTPS. Open **QR Check-in** from the Owner sidebar, select **Demo Mode**, then press **Start Camera**. Camera permission is requested only after this button is pressed. Allow camera access in Chrome site settings and hold a test QR in the 4:3 preview; press **Stop Camera** to stop the stream. The scanner chooses a labeled integrated/web camera when possible, then falls back to the first available device. Leaving the screen, hiding the tab, changing mode, or closing/reloading the page also stops the scanner. The page requires an available webcam and serves `html5-qrcode` from the local `assets/vendor/` directory; if that local file is missing it reports the load error instead of claiming a scan succeeded.

For a camera-free demo, use the manual token field. The displayed test tokens are labeled Demo Only:

- `demo-qr-confirmed-3106`: valid `CONFIRMED` booking, succeeds and changes the shared Step 7 mock booking to `CHECKED_IN`.
- `demo-qr-checked-in-3105`: already checked in.
- `demo-qr-completed-3103`: completed booking.
- `demo-qr-cancelled-3102`: cancelled booking.
- `demo-qr-expired-3101`: expired booking.
- `demo-qr-other-owner-3199`: belongs to a different demo Owner and is denied.
- `demo-qr-invalid`: invalid token.

A successful check-in displays the booking ID, court, date and time. The corresponding booking state is shared with Owner Bookings while the page stays loaded. Reload resets mock data. This local simulation is not an authorization mechanism and has no effect on MySQL or Court Service.

If the preview does not start, verify camera permission, close other apps using the webcam, and confirm the page uses localhost or HTTPS. Permission denial, missing or busy camera, and local library load failures appear in the scanner result area. Start/stop and page navigation wait for camera cleanup; the QR preview stays mounted while a scan is active. If cleanup itself fails, use **Stop Camera** to retry before leaving the page.

In API Mode, the same camera and a manual token field send `POST /api/v1/owner/checkins` through the Gateway with the session Bearer token. The browser sends only `qr_token`; it never sends `owner_id` or `X-Internal-Token`, and the token is not rendered or logged. Check-in status remains server-owned: the page reports the response and marks Owner Bookings data stale so it reloads when next opened. API errors are translated to safe messages. The browser does not fall back to Demo tokens or records. Camera access requires localhost or HTTPS, permission, and the locally served `html5-qrcode` asset. The UI and route are contract-wired, but live integration still depends on S1's Booking internal check-in being reachable through the configured services; this task does not claim an end-to-end backend run.

## Demo screens

Owner Bookings and QR Check-in support API Mode and retain separate Demo Mode samples. Revenue and the Admin People directory remain pending their service/UI integration. Authenticated Profile shows the User Service account read-only; Demo Profile remains fictional. No sample data is used as a fallback when an API request fails.

## Admin Demo Mode

Choose **Demo Admin** on the login screen to open the Admin demo area. A real ADMIN account is routed to the Admin workspace after Auth login. The Dashboard account and booking cards, Users & Owners counters, and Admin Bookings counters are calculated from the fictional rows in `assets/js/data.js`; booking value is summed from those sample bookings. Users & Owners supports text, role, and status filters plus read-only account details. Admin Bookings and Check-ins support text and status filters. In Demo Mode the Venue & Court registry and Time Slots page use the in-memory Court Demo catalogue. In API Mode, authenticated ADMIN accounts can manage Sports, Venues, Courts, and Time Slots through Court Service.

Admin Demo data is browser-only, fictional, and resets on reload. It does not authenticate an administrator, call User/Booking/Payment services, or persist changes. Payments and Reviews have no connected service or Admin page in this iteration, so the interface does not invent records or totals for them. Owner CRUD and Owner QR Demo behavior remain on their existing screens and use their own demo data.

## Registry, Schedule, and filter behavior

The Owner and Admin **Venue & Court** pages use Sports, Venues, and Courts tabs with one search/filter area at a time. Owner CRUD controls are available in Demo Mode and for authenticated OWNER accounts in API Mode; authenticated ADMIN accounts can manage the full registry through its Sports, Venues, and Courts tabs. Admin **Time Slots** provides list, filters, detail, add, edit, and soft-deactivate actions through the Court Service API. Switching tabs keeps the in-memory Demo catalogue. Date selection uses the same lightweight, read-only calendar picker in Owner and Admin Time Slots, the Owner Booking Demo date filter, and Add/Edit Time Slot. It has direct month and year selectors, Monday-first day buttons, and displays `dd/MM/yyyy`; selected values remain canonical `yyyy-MM-dd` without timezone conversion. Past dates remain available for viewing/filtering. Schedule search also recognizes `dd/MM/yyyy`, `dd/MM`, and `yyyy-MM-dd`. Schedule **Reset filters** clears search, date, venue, court, and status filters without changing data. In Demo Mode, **Refresh** asks for confirmation and restores only the original Time Slot list; confirming also clears filters so the restored rows are visible. Venue, Court, Sport, Booking, and QR Demo data are preserved. In API Mode, **Refresh** reloads Time Slots with GET requests only and prevents duplicate refreshes. Add/Edit Time Slot asks for Venue first and filters Court choices to that Venue. `is_active` reflects the slot catalogue record only, not booking availability. Court Service rejects edits/deactivation of slots with active HOLD/BOOKED reservations using `409`; API Mode displays the conflict and leaves reservation state authoritative in Court Service. Admin Bookings and Check-ins currently have no date filter; their search/status filters apply immediately and include a reset control. The Users & Owners demo table displays IDs already present in its sample data; unavailable IDs are labeled rather than generated.

In Owner QR Check-in Demo Mode, checking a manual token or scanning a QR displays the result without stopping an active camera stream. Start and Stop reflect the camera lifecycle; Stop, leaving the page, or changing mode releases the scanner before cleanup of its preview.


## Authenticated integration setup

1. Start the User Service (port 8001), Court Service (8002), and Gateway (8000). The User Service routes must implement the verified S1 contract: `POST /api/v1/auth/login` with JSON email/password and `GET /api/v1/users/me` with Bearer authentication.
2. Configure the same strong `JWT_SECRET_KEY` and `JWT_ALGORITHM=HS256` in the User Service and Court Service local environment. Do not put the secret in this static frontend. The browser stores the access token in `sessionStorage`, clears it on logout/401, and reads the current role/profile from `/users/me`.
3. Log in with a real account. The inspected S1 branch registration creates USER accounts only; it does not supply a seeded OWNER or ADMIN account. Do not change a role or seed an account by bypassing Auth.
4. OWNER can write Venue/Court/Time Slot resources via the existing Court Service contract; ADMIN can manage Sports, Venue, Court, and Time Slot resources. Demo Mode remains local and does not call the API.

This frontend integration is contract-based; end-to-end login, Owner Booking operations, and QR check-in have not been verified with real services in the current local environment. Booking list/detail/completion public endpoints, User directory, Payment, and Revenue APIs remain unimplemented in the inspected S1 branch. QR check-in calls the S2 adapter, which depends on the existing S1 internal check-in API.

## Automated tests

Run the Management Web utility, API client, and login tests from the repository root with:

```powershell
node --test management-web/tests/*.test.js
```

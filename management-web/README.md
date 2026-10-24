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

This project uses static HTML, CSS, and JavaScript with the existing Bootstrap CDN assets. Local CSS fallbacks keep the core layout, forms, alerts, buttons, and tables usable when the CDN is unavailable; Bootstrap icons and the QR scanner library still load from their CDNs. No Node build or frontend package installation is required.

## Current implementation status

Court Service provides its catalogue API and the Management Web reads it through the Gateway. Owner CRUD, bookings, and QR check-in work only as clearly labeled browser Demo Mode previews; authenticated write and Booking APIs are not connected. User and Payment services currently provide foundation/health endpoints. The old backend remains in place. See `backend/README.md` for backend setup and endpoint details.

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

Open `http://localhost:8080`. The login screen is still a UI demo; choosing Owner or Administrator does not authenticate a user.

## API Mode and Gateway offline

Start Court Service and the Gateway using the commands above before opening API Mode. The UI keeps API Mode selected if the Gateway is offline; it does not substitute mock catalogue data. The Dashboard, registry, and schedule show **Cannot connect to API Gateway** with a manual Retry button. Check the two service terminals, confirm ports `8002` and `8000`, then press Retry. Requests are not retried continuously.

Camera access works only on a secure context: `http://localhost`, `http://127.0.0.1`, or HTTPS. Browser extensions can inject their own scripts and console messages; `onboarding.js` is not part of this repository. The frontend includes `favicon.svg` to avoid a missing favicon request.

## Gateway configuration

The frontend calls the Gateway only. Set the single base URL in `assets/js/config.js` (`http://localhost:8000` by default). The Gateway allows browser requests from `http://localhost:8080` and `http://127.0.0.1:8080` for local development.

## Court Service screens

The Owner and Admin dashboards, Venue & Court registry, and Schedule read live Sports, Venue, Court, and Time Slot data through the Gateway. Registry has independent venue and court search boxes; sport, status, and venue filters remain available. Search filters the loaded data in the browser and does not issue requests while typing. Schedule date and court filters are sent as API query parameters. Detail buttons fetch the selected resource. API loading, empty, and error states are shown with retry controls.

To populate a local demo, follow the Court Service seed instructions in [`backend/README.md`](../backend/README.md#court-service-developmentdemo-seed-step-5). The seed requires an Owner ID confirmed with S1; without one the database should remain unseeded and these screens show empty states.

Displayed slot status reflects only `is_active`; it does not indicate whether a slot is booked or available. Prices are formatted from the API decimal string for display and are not used for payment calculations.

## Owner CRUD preview

On the Owner Dashboard, Venue & Court, and Schedule screens, use the data mode selector:

- **API Mode** is the default. It reads the live Sports, Venue, Court, and Time Slot APIs with GET requests. Add/Edit forms show the API Contract fields and validation constraints for preparation. Save and Delete are disabled until S1 supplies the JWT and authorization contract. No token is fabricated and no write request is sent. Venue forms show `owner_id` only when the API provides it; creating a venue requires an Owner ID supplied by a future authenticated session.
- **Demo Mode** uses a separate sample dataset kept only in JavaScript memory. Add, edit, and delete (soft deactivation) work for sports, venues, courts, and time slots, with local validation including duplicate sport names and duplicate/overlapping slots. These actions never call the Gateway. Reloading the page restores the starter data. Demo venues have no real Owner ID.

Court forms require an existing Demo venue and sport, and a positive price with up to two decimal places. Time Slot forms require an existing Demo court, a date, and a start time before the end time. API Mode write controls stay disabled; conflict responses such as HTTP 409 cannot be exercised until authenticated writes are integrated.

The older backend-owned seed data remains separate from browser Demo Mode. To seed MySQL, follow the Court Service instructions in [`backend/README.md`](../backend/README.md#court-service-developmentdemo-seed-step-5); it requires an Owner ID confirmed with S1.

## Owner Booking Management (Step 7)

Open the Owner **Bookings** screen from the sidebar. In API Mode, the page displays that the Booking API contract and JWT integration are pending and shows no live or sample booking records. The frontend does not call a guessed Booking endpoint.

Switch the shared Owner data mode selector to **Demo Mode** to view six fictional bookings covering `PENDING`, `CONFIRMED`, `CHECKED_IN`, `COMPLETED`, `CANCELLED`, and `EXPIRED`. The list is sorted newest first and supports Booking ID/customer search, booking date and status filters. Typing updates only the table rows, so the search field keeps focus and caret position. Booking details group customer and court information, show payment/check-in status only when provided, and offer **Complete Booking** only for `CHECKED_IN`. Confirm the action to change that record to `COMPLETED` in browser memory. Reload restores the original sample dataset.

Demo booking data is local UI-only mock data. It does not use MySQL, call Booking Service, or alter Court Service data. The login and Owner role are still a frontend demo and do not scope bookings to a real account.

Waiting for S1: the agreed Owner booking list/detail response shapes, route paths, pagination/filter contract, JWT/Owner authorization, payment and check-in field definitions, and the completion API behavior. The V5 route names are planning proposals and are not treated as an active API contract here. Completion in API Mode remains unavailable until S1 provides the contract and authenticated integration.

## Owner QR Scanner & Demo Check-in (Step 8)

Serve this static site on `http://localhost:8080` or HTTPS. Open **QR Check-in** from the Owner sidebar, select **Demo Mode**, then press **Start Camera**. Camera permission is requested only after this button is pressed. Allow camera access in Chrome site settings and hold a test QR in the 4:3 preview; press **Stop Camera** to stop the stream. The scanner chooses a labeled integrated/web camera when possible, then falls back to the first available device. Leaving the screen, hiding the tab, changing mode, or closing/reloading the page also stops the scanner. The page requires an available webcam and network access to load `html5-qrcode` from its CDN; if the CDN is blocked it reports that error instead of claiming a scan succeeded.

For a camera-free demo, use the manual token field. The displayed test tokens are labeled Demo Only:

- `demo-qr-confirmed-3106`: valid `CONFIRMED` booking, succeeds and changes the shared Step 7 mock booking to `CHECKED_IN`.
- `demo-qr-checked-in-3105`: already checked in.
- `demo-qr-completed-3103`: completed booking.
- `demo-qr-cancelled-3102`: cancelled booking.
- `demo-qr-expired-3101`: expired booking.
- `demo-qr-other-owner-3199`: belongs to a different demo Owner and is denied.
- `demo-qr-invalid`: invalid token.

A successful check-in displays the booking ID, court, date and time. The corresponding booking state is shared with Owner Bookings while the page stays loaded. Reload resets mock data. This local simulation is not an authorization mechanism and has no effect on MySQL or Court Service.

If the preview does not start, verify camera permission, close other apps using the webcam, and confirm the page uses localhost or HTTPS. Permission denial, missing or busy camera, and CDN load failures appear in the scanner result area. Start/stop and page navigation wait for camera cleanup; the QR preview stays mounted while a scan is active. If cleanup itself fails, use **Stop Camera** to retry before leaving the page.

API Mode shows that the Booking Check-in contract and JWT are pending S1. It neither processes tokens nor sends a check-in request or changes state. V5's proposed `POST /api/v1/owner/checkins` route remains unconfirmed. S1 must provide the route/response contract, Owner JWT authorization and server-side token/status/ownership/replay checks before API integration.

## Demo screens

Bookings, QR Check-in, Revenue, People, and Profile remain sample UI because their services are not connected. These screens are labeled Demo. No sample data is used as a fallback when a Court Service request fails.

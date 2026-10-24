# Owner/Admin Management Web

This project uses static HTML, CSS, and JavaScript with the existing Bootstrap CDN assets. No Node build or frontend package installation is required.

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

## Gateway configuration

The frontend calls the Gateway only. Set the single base URL in `assets/js/config.js` (`http://localhost:8000` by default). The Gateway allows browser requests from `http://localhost:8080` and `http://127.0.0.1:8080` for local development.

## Court Service screens

The Owner and Admin dashboards, Venue & Court registry, and Schedule read live Sports, Venue, Court, and Time Slot data through the Gateway. Search and catalogue filters use the loaded data; Schedule date and court filters are sent as API query parameters. Detail buttons fetch the selected resource. API loading, empty, and error states are shown with retry controls.

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

Switch the shared Owner data mode selector to **Demo Mode** to view six fictional bookings covering `PENDING`, `CONFIRMED`, `CHECKED_IN`, `COMPLETED`, `CANCELLED`, and `EXPIRED`. The list is sorted newest first and supports Booking ID/customer search, booking date and status filters, and a detail modal with customer, venue/court, time, amount, booking status, plus payment/check-in status when present. Only a `CHECKED_IN` record offers **Complete Booking**; confirm the action to change that record to `COMPLETED` in browser memory. Reload restores the original sample dataset.

Demo booking data is local UI-only mock data. It does not use MySQL, call Booking Service, or alter Court Service data. The login and Owner role are still a frontend demo and do not scope bookings to a real account.

Waiting for S1: the agreed Owner booking list/detail response shapes, route paths, pagination/filter contract, JWT/Owner authorization, payment and check-in field definitions, and the completion API behavior. The V5 route names are planning proposals and are not treated as an active API contract here. Completion in API Mode remains unavailable until S1 provides the contract and authenticated integration.

## Demo screens

Bookings, QR Check-in, Revenue, People, and Profile remain sample UI because their services are not connected. These screens are labeled Demo. No sample data is used as a fallback when a Court Service request fails.

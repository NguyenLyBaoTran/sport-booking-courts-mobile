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

Displayed slot status reflects only `is_active`; it does not indicate whether a slot is booked or available. Prices are formatted from the API decimal string for display and are not used for payment calculations.

Add, edit, and deactivate controls do not send requests. They display a notice while Court Service write routes await S1 JWT and authorization integration.

## Demo screens

Bookings, QR Check-in, Revenue, People, and Profile remain sample UI because their services are not connected. These screens are labeled Demo. No sample data is used as a fallback when a Court Service request fails.

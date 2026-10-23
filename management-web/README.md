# Owner/Admin Management Web

Static HTML, CSS, and JavaScript prototype for the Sports Court Booking management workspace. The screens follow the Owner and Admin wireframes in the supplied FinalProject_BasicUI PDF, pages 3–4.

## Run locally

Open index.html in a browser, or start a small static server from this folder with: py -m http.server 8080

Then visit http://localhost:8080.

Select Court Owner or Administrator on the login page. This is a demo navigation only; any email and password opens the selected workspace.

## Routes

- #/login
- Owner: #/dashboard, #/venues, #/schedule, #/owner-bookings, #/qr-checkin, #/revenue, #/owner-profile
- Admin: #/admin-dashboard, #/people, #/admin-venues, #/admin-bookings, #/checkins, #/admin-profile

The screens use local sample data in assets/js/data.js. Login, account/venue actions, revenue, QR scanning, and check-in verification are not connected to authentication or backend services.

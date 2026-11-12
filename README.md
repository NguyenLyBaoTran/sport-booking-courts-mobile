# Sports Court Booking System

## 1. Project Overview

This student project contains a Management Web for venue owners and administrators, a Customer Android app, and a backend made of four FastAPI services behind an API Gateway.

The Management Web supports API sign-in and a separate Demo preview. In API Mode, Admins manage Sports, Venues, Courts, and Time Slots. Owners manage their own venues, courts, and schedules, and can use the integrated booking and QR check-in screens. Admin User, system-wide Booking, and Check-in APIs are still pending from S1. The Android app currently supports Customer registration, sign-in, and session checks; court search, bookings, and profile actions are not implemented yet.

## 2. Technology Stack

- Backend: Python, FastAPI, Uvicorn, SQLAlchemy, Alembic, PyMySQL, MySQL.
- Web: HTML, CSS, JavaScript, Bootstrap assets served locally.
- Android: Java, XML, Android Studio, Retrofit.
- Tests: pytest for backend; Node.js built-in test runner for Management Web.

## 3. Project Structure

```text
backend/          Gateway, four services, database setup, and tests
management-web/   Owner/Admin static website
android-user/     Customer Android application
docs/             API contracts and test guides
setup.bat         First-time local database setup
```

## 4. Prerequisites

- Windows with PowerShell.
- Python 3.10 or newer and MySQL running locally (for API Mode).
- Node.js (to run Management Web tests).
- Android Studio (to build the Android app).

Demo preview in the Management Web does not require MySQL or backend services.

## 5. First-Time Setup

1. Start the local MySQL service.
2. In `backend/`, create a virtual environment and install dependencies:

   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
   Copy-Item .env.example .env
   ```

3. Edit `backend/.env`. Set `APP_ENV=development`, configure the local MySQL user and password in the four service database URLs, and keep the database names `sports_user_db`, `sports_court_db`, `sports_booking_db`, and `sports_payment_db`. Set a random `JWT_SECRET_KEY` (32 or more characters) shared by User and Court, and the same random `INTERNAL_SERVICE_TOKEN` for Court and Booking. Keep secrets in `.env`; do not commit them.
4. From the repository root, run:

   ```powershell
   .\setup.bat
   ```

   Review the displayed local database targets and type `SETUP` when prompted. The script initializes service schemas and adds missing demo rows. It does not require a manual seed import and does not reset existing data.

## 6. How to Run

Start each backend command in its own PowerShell window. Run the command from the listed working directory after setup:

| Service | Working directory | Command |
| --- | --- | --- |
| User Service | `backend/services/user_service` | `..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload` |
| Court Service | `backend/services/court_service` | `..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --reload` |
| Booking Service | `backend/services/booking_service` | `..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8003 --reload` |
| Payment Service | `backend/services/payment_service` | `..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8004 --reload` |
| API Gateway | `backend/gateway` | `..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload` |

Then serve the Management Web in another window:

```powershell
cd management-web
python -m http.server 8080
```

Open <http://127.0.0.1:8080>. Login defaults to API Mode. Sign in with an Admin or Owner account. To use fictional browser-only data, choose **Demo preview** on the Login page; sign out to return and choose the other mode.

Health checks:

- Gateway: <http://127.0.0.1:8000/health>
- Service health through Gateway: `/api/v1/user/health`, `/api/v1/court/health`, `/api/v1/booking/health`, and `/api/v1/payment/health` on port 8000.
- Each service also has `/health/db` on its own port to check its MySQL connection.

### Android Customer App

Open `android-user/` in Android Studio and run the app on an emulator or device. The current app connects to the User Service for registration, login, and session validation only. Court search, My Bookings, and Profile buttons are placeholders; customer booking/payment is not yet available in this Android app.

The Android API base URL is currently set in `android-user/app/src/main/java/com/example/sportbooking/api/ApiClient.java`. For the Android Emulator, use `http://10.0.2.2:8001/`. For a physical phone, use the computer's LAN IP, keep the phone and computer on the same network, start User Service with `--host 0.0.0.0`, and allow the port through the local firewall. Do not use `localhost` from a phone.

## 7. Demo Accounts

The local seed provides these development-only accounts:

| Role | Email |
| --- | --- |
| Admin | `admin.demo@example.com` |
| Owner | `owner1.demo@example.com` |
| Owner | `owner2.demo@example.com` |
| Customer | `customer1.demo@example.com` |
| Customer | `customer2.demo@example.com` |
| Customer | `customer3.demo@example.com` |

The seed password for these accounts is `password123`. Use these accounts only with the local development databases; change or remove demo accounts before any shared deployment.

## 8. Demo Flow

1. Choose **Demo preview** at Login to explore fictional Owner/Admin screens without backend access. Demo changes stay in browser memory and do not touch MySQL.
2. For API Mode, run setup and all five backend processes, then sign in with a local demo Admin or Owner account. Admin manages the shared Sports, Venue, Court, and Time Slot catalogue; Owners see and manage their own catalogue.
3. The database seed includes users and court catalogue records, but no Booking or Payment rows. The Android Customer app does not yet provide booking. Do not expect a seeded booking or physical webcam QR flow from a fresh setup.

See [Owner Booking & QR API contract](docs/api/owner-booking-qr-contract.md), [Admin Management API contract and status](docs/api/admin-management-api-contract.md), and the [manual testing guide](docs/TESTING_GUIDE.md) for implementation details.

## 9. Troubleshooting

- **Setup stops before writing:** check `APP_ENV=development`, the four database names and local MySQL host in `backend/.env`, and that the configured account can create databases. Read the script message; do not drop or reset existing databases.
- **Database connection fails:** check MySQL is running, the username/password and port in `backend/.env`, then open each service's `/health/db` endpoint. To inspect schema names with MySQL, run `mysql -u <mysql-user> -p -e "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME IN ('sports_user_db','sports_court_db','sports_booking_db','sports_payment_db');"` and enter the password at the prompt.
- **API does not respond:** check that all four services and the Gateway are running on ports 8001–8004 and 8000. Open the Gateway and service `/health` URLs above. API docs are available at `http://127.0.0.1:8000/docs`.
- **Login fails:** confirm the account exists and is active in the local User database. User and Court must share the same `JWT_SECRET_KEY` and algorithm; Court and Booking must share `INTERNAL_SERVICE_TOKEN`.
- **Phone cannot reach the API:** use the computer's LAN IP instead of `localhost`, bind User Service to `0.0.0.0`, and check Wi-Fi and firewall settings.
- **Admin Users/Bookings/Check-ins show unavailable:** those system-wide Admin APIs are pending S1 implementation. The Web does not replace them with Demo data in API Mode.

To run tests, use `python -m pytest -q` from a service or Gateway directory and `node --test tests/*.test.js` from `management-web/`.

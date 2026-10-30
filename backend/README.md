# Backend: Sports Court Booking System

## Kiến trúc hiện tại

Backend mới có một API Gateway và bốn FastAPI microservice độc lập:

- User Service — cổng `8001`, database `sports_user_db`; Auth/Register/Login đã có.
- Court Service — cổng `8002`, database `sports_court_db`; nghiệp vụ Court/Sports do
  nhánh Court Service triển khai.
- Booking Service — cổng `8003`, database `sports_booking_db`; booking, hold
  orchestration, xác nhận nội bộ và QR token.
- Payment Service — cổng `8004`, database `sports_payment_db`; mock payment và
  payment history.
- API Gateway — cổng `8000`, nhận request từ client và chuyển tiếp theo API prefix.

Mỗi service có `/health` và `/health/db`. User Service cung cấp Register/Login/JWT
và `GET /users/me`; Booking/Payment cung cấp API nghiệp vụ cốt lõi; Court Service
cung cấp API quản lý Sports, Venues, Courts và Time Slots có xác thực. Luồng đặt chỗ
phối hợp Booking–Court và check-in Owner được mô tả trong các API contract bên dưới;
chạy riêng từng service không đồng nghĩa với đã xác minh E2E.
Gateway có `/health` và các route kiểm tra service tại
`/api/v1/{user,court,booking,payment}/health`.

`app/` và `alembic/` ở cấp `backend/` là backend Modular Monolith cũ. Chúng được
giữ lại trong giai đoạn chuyển đổi; Alembic hiện tham chiếu `app.core.config` và
`app.db.database`. Chưa có migration nghiệp vụ cho Booking/Payment; script
`python -m app.init_db` chỉ khởi tạo schema cho local development. Các file rỗng
trong Court Service vẫn là điểm mở rộng theo cấu trúc dự án.

## Công nghệ

- Python, FastAPI, Uvicorn
- SQLAlchemy, PyMySQL, MySQL
- `httpx` cho request từ Gateway đến service
- `python-dotenv` để nạp cấu hình từ `backend/.env`
- Alembic cho backend Modular Monolith cũ

## Cấu trúc backend

```text
backend/
├── app/                         # Modular Monolith cũ, giữ lại
├── alembic/                     # Migration cũ, giữ lại
│   └── versions/
├── gateway/
│   └── main.py
├── scripts/
│   └── create_databases.sql
├── services/
│   ├── user_service/app/        # main.py, database.py, models.py, schemas.py, routes.py
│   ├── court_service/app/       # main.py, database.py, models.py, schemas.py, routes.py
│   ├── booking_service/app/     # main.py, database.py, models.py, schemas.py, routes.py
│   └── payment_service/app/     # main.py, database.py, models.py, schemas.py, routes.py
├── .env.example
├── README.md
├── requirements.txt            # Runtime dependencies
└── requirements-dev.txt        # Runtime + pytest
```

## Cài đặt

Từ thư mục gốc repository, trên PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

For Court/Gateway tests, install the test tools as well:

```powershell
python -m pip install -r requirements-dev.txt
```

`requirements.txt` contains runtime packages. The development file includes it and adds test tooling. On Windows, `tzdata` supplies the IANA timezone database used by `ZoneInfo`.

Mở `backend/.env` và thay `YOUR_PASSWORD` bằng thông tin MySQL của máy. Tệp `.env`
được `.gitignore` loại trừ. Không commit thông tin đăng nhập thật. Nếu mật khẩu có
ký tự đặc biệt trong URL, hãy URL-encode các ký tự đó.

Các service và Gateway tự tìm `backend/.env` theo vị trí source code; không cần đặt
working directory cụ thể để nạp tệp này. Backend Modular Monolith cũ dùng cấu hình
Pydantic Settings với `.env` tương đối theo working directory, nên chạy backend cũ
từ thư mục `backend`.

## Tạo MySQL databases

Script tạo bốn database rỗng bằng `utf8mb4`, không tạo bảng nghiệp vụ:

```powershell
Get-Content backend/scripts/create_databases.sql | mysql -u root -p
```

Hoặc chạy lệnh MySQL từ shell hỗ trợ input redirection:

```bash
mysql -u root -p < backend/scripts/create_databases.sql
```

## Cấu hình database

`backend/.env.example` cung cấp các URL mẫu riêng:

| Biến môi trường | Service | Database |
|---|---|---|
| `USER_DATABASE_URL` | User | `sports_user_db` |
| `COURT_DATABASE_URL` | Court | `sports_court_db` |
| `BOOKING_DATABASE_URL` | Booking | `sports_booking_db` |
| `PAYMENT_DATABASE_URL` | Payment | `sports_payment_db` |

Mỗi service chỉ đọc URL của mình, tạo SQLAlchemy engine và session riêng. Khi chưa
có URL hoặc MySQL không kết nối được, `/health/db` trả HTTP 503 với thông báo chung.
`DATABASE_URL` trong file mẫu chỉ dành cho backend Modular Monolith cũ.
Database `sports_court_booking` của backend cũ không được tạo bởi script trên;
script chỉ tạo bốn database riêng của microservice.

## User Service: Authentication và JWT

Tạo một JWT secret riêng cho môi trường local rồi đặt vào `backend/.env`:

```bash
openssl rand -hex 32
```

Đặt kết quả vào `JWT_SECRET_KEY`; service chỉ chấp nhận HS256 và secret dài ít nhất
32 ký tự. Không commit `.env` hoặc secret vào Git.

Sau khi tạo `sports_user_db`, chạy migration và User Service:

```bash
cd backend/services/user_service
python -m alembic -c alembic.ini upgrade head
python -m uvicorn app.main:app --reload --port 8001
```

API public đi qua Gateway tại `http://127.0.0.1:8000`:

| Method | Path | Mô tả |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Đăng ký tài khoản USER |
| `POST` | `/api/v1/auth/login` | Đăng nhập và nhận JWT Bearer |
| `GET` | `/api/v1/users/me` | Lấy tài khoản hiện tại, cần Bearer token |

Register nhận `full_name`, `email`, `password` (8–128 ký tự) và `phone` tùy chọn.
Email được chuẩn hóa chữ thường; đăng ký công khai luôn tạo role `USER`, không nhận
role từ request. Login nhận `email` và `password`; response trả về
`access_token`, `token_type`, `expires_in` (giây) và thông tin user. JWT claims
gồm `sub` (user ID dạng chuỗi), `role`, `iat` và `exp`. Email trùng trả `409`,
thông tin đăng nhập sai hoặc token không hợp lệ trả `401`.

Chạy Auth tests (SQLite in-memory, không cần kết nối MySQL):

```bash
cd backend/services/user_service
python -m pytest -q
```

Tạo tài khoản OWNER/ADMIN dùng cho local integration test (nhập password ẩn khi
được nhắc; mật khẩu không được lưu dạng rõ trong database hoặc commit vào repo):

```bash
cd backend/services/user_service
python -m app.create_test_account
```

Lệnh chỉ chạy khi `APP_ENV=development` hoặc `test`, và in ra User ID sau khi tạo.
The demo seed resolves Owner IDs by querying the two demo Owner emails; it does not require a fixed `DEMO_OWNER_ID`. Use the login API to obtain JWTs for manual Owner/Admin tests.

### Tài khoản development cũ

Các bản local cũ có thể có tài khoản development riêng. Không dựa vào ID Owner/Admin cố định trong seed hoặc ứng dụng; dùng tài khoản E2E được quản lý trong mục [Local demo setup](#local-demo-setup) khi trình diễn.

## Booking và Payment API

Booking Service cung cấp API lịch sử/chi tiết booking cho USER, tạo booking PENDING
với slot hold 10 phút, hủy booking đang PENDING, và API nội bộ để Payment Service
xác nhận booking sau mock payment. Payment Service ghi nhận các lần mock payment,
chặn thanh toán thành công lặp lại, và chỉ cho người dùng xem payment của chính họ.
QR token opaque do Booking Service tạo sau khi xác nhận; QR check-in thuộc phạm vi
Booking Service quản lý state transition check-in/completion; Court/Owner Service
phải xác thực Owner và gọi các internal endpoint đó.

Trước khi chạy hai service, đặt `INTERNAL_SERVICE_TOKEN` thành cùng một giá trị
ngẫu nhiên riêng trong `.env`; không dùng giá trị ví dụ khi chạy thật. Cấu hình
`COURT_SERVICE_URL` và `BOOKING_SERVICE_URL` theo địa chỉ nội bộ tương ứng.
Khởi tạo bảng lần đầu cho local development:

```bash
cd backend/services/booking_service
python -m app.init_db
cd ../payment_service
python -m app.init_db
```

Chi tiết request/response và contract internal phụ thuộc Court Service nằm trong
[API contract](../docs/API_CONTRACT.md). Các service đang phát triển cần cùng thống
nhất contract này trước khi chạy end-to-end; chạy test riêng không cần MySQL hoặc
Court/Booking service đang hoạt động.

Hướng dẫn chi tiết để chạy test tự động, Auth qua Gateway và luồng tích hợp
Booking/Payment nằm trong [Local Test Guide](../docs/TESTING_GUIDE.md).

## Chạy các ứng dụng

Cài dependencies trước, sau đó mở terminal riêng cho Gateway và mỗi service.

Gateway:

```powershell
cd backend/gateway
python -m uvicorn main:app --reload --port 8000
```

Chạy từng service từ thư mục service tương ứng:

```powershell
cd backend/services/user_service
python -m uvicorn app.main:app --reload --port 8001
```

```powershell
cd backend/services/court_service
python -m uvicorn app.main:app --reload --port 8002
```

```powershell
cd backend/services/booking_service
python -m uvicorn app.main:app --reload --port 8003
```

```powershell
cd backend/services/payment_service
python -m uvicorn app.main:app --reload --port 8004
```

## URL kiểm tra

Trực tiếp tới mỗi service:

- `http://127.0.0.1:8001/health` và `/health/db`
- `http://127.0.0.1:8002/health` và `/health/db`
- `http://127.0.0.1:8003/health` và `/health/db`
- `http://127.0.0.1:8004/health` và `/health/db`

Qua Gateway:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/api/v1/user/health`
- `http://127.0.0.1:8000/api/v1/court/health`
- `http://127.0.0.1:8000/api/v1/booking/health`
- `http://127.0.0.1:8000/api/v1/payment/health`
- `http://127.0.0.1:8000/docs`

`/health/db` trả `{"database":"connected"}` chỉ khi service kết nối MySQL thành
công và thực thi được `SELECT 1`.

## Mở rộng triển khai

Public API paths của Gateway ổn định; địa chỉ từng service được cấu hình bằng
`USER_SERVICE_URL`, `COURT_SERVICE_URL`, `BOOKING_SERVICE_URL` và
`PAYMENT_SERVICE_URL`. Có thể đổi các URL này sang hostname nội bộ khi triển khai
Docker Compose sau này. Các service không import code lẫn nhau và có thể chạy độc
lập. Bước này chưa thêm Docker, Compose hay Nginx.

## Court Service REST API (Step 2)

Court Service exposes public read routes and JWT-protected writes. OWNER can manage only Venues they own and Courts/Time Slots whose related Venue belongs to them. ADMIN can manage Sports, Venues, Courts, and Time Slots across the system. Only ADMIN can mutate Sports. USER and cross-owner OWNER mutations return `403`; missing/invalid/expired tokens return `401`. OWNER Venue creation requires body `owner_id` to match the authenticated subject, and OWNER updates cannot transfer ownership. The API never authorizes an OWNER from a client-supplied ID alone.

Booking–Court internal reservation routes use `X-Internal-Token` and the S1 paths `POST /api/v1/internal/slots/{slot_id}/hold|confirm|release`. They are not exposed by Gateway. Before running these routes on an existing Court DB, apply the documented migration in `migrations/20261026_add_time_slot_reservations.sql` to a disposable database and configure the same internal token and hold duration in Booking and Court.

| Method | Endpoint | Purpose | Access now |
|---|---|---|---|
| GET | `/api/v1/sports` and `/api/v1/sports/{sport_id}` | List/filter and view sports | Public |
| POST, PUT, DELETE | `/api/v1/sports[/{sport_id}]` | Create, update, soft-deactivate sport | Closed pending ADMIN policy |
| GET | `/api/v1/venues` and `/api/v1/venues/{venue_id}` | List/filter and view venues | Public |
| POST, PUT, DELETE | `/api/v1/venues[/{venue_id}]` | Create, update, soft-deactivate venue | OWNER of the venue; ADMIN pending |
| GET | `/api/v1/courts` and `/api/v1/courts/{court_id}` | List/filter and view courts | Public |
| POST, PUT, DELETE | `/api/v1/courts[/{court_id}]` | Create, update, soft-deactivate court | OWNER of related Venue; ADMIN pending |
| GET | `/api/v1/time-slots` and `/api/v1/time-slots/{slot_id}` | List/filter and view time slots | Public |
| POST, PUT, DELETE | `/api/v1/time-slots[/{slot_id}]` | Create, update, soft-deactivate time slot | OWNER of related Court's Venue; ADMIN pending |

Example create request (after Auth integration):

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

Example response (`201 Created`):

```json
{
  "id": 12,
  "venue_id": 1,
  "sport_id": 1,
  "name": "Court A",
  "description": "Indoor court",
  "price_per_hour": "25.00",
  "is_active": true
}
```

Read routes support `is_active`; venue routes also support `owner_id`, court routes `venue_id` and `sport_id`, and time-slot routes `court_id` and `slot_date` (ISO date, for example `2026-10-23`). Query parameters can be combined. Request schemas reject extra fields such as `id` and `created_at`.

Validation returns 422 for malformed request schemas, invalid time ranges, off-boundary times, and new/changed start times that are not in the future; 400 for invalid references or inactive parent records; 404 for missing resource IDs; and 409 for duplicate sport names or overlapping time slots. Time Slot start and end times must fall on a 30-minute boundary (`:00` or `:30`, with zero seconds), and start must precede end. Future-time validation uses the business timezone `Asia/Ho_Chi_Minh` while the database continues to store a `DATE` and timezone-naive `TIME`. On update, changing only fields other than the date/start is allowed for historical rows. No fixed Venue opening hours are enforced. Existing rows are not changed by request validation; the database `TIME` columns have no 30-minute or future-time check constraint. A read-only check of the local Court DB found zero Time Slot rows, so there are no current local records to migrate; other installations may still retain older off-boundary or past slots. Deletes only set `is_active = false`. Time-slot overlap validation considers active slots on the same Court and date and excludes the slot being updated. Since there is no database constraint for arbitrary interval overlap, concurrent requests can pass the pre-check at the same time; this API does not claim to prevent that race. The existing exact-slot unique constraint can also reject re-creating an identical slot after soft deletion.

Run the service from the repository's `backend` folder:

```powershell
cd services/court_service
python -m uvicorn app.main:app --reload --port 8002
```

Open Swagger UI at `http://127.0.0.1:8002/docs`. Through the Gateway (port 8000), use the same API paths, for example `http://127.0.0.1:8000/api/v1/time-slots?court_id=1&slot_date=2026-10-23`. Gateway forwards the request body, query string, Authorization header, and upstream status code.

Court JWT verification uses `python-jose` and reads `JWT_SECRET_KEY`, `JWT_ALGORITHM`, and `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` from `backend/.env`. Set the same random secret used by User Service (at least 32 characters); the checked-in `.env.example` value is a placeholder and will not verify tokens. Generate a strong random value locally, configure the same value in User Service and Court Service, and never put it in frontend code or commit it. Gateway CORS defaults to the two localhost Management Web origins. Set `CORS_ALLOWED_ORIGINS` to a comma-separated explicit origin allowlist for other development/deployment hosts; wildcard origins are rejected.

Install `requirements-dev.txt` into the project virtual environment, then run the Gateway and Court authorization tests without MySQL from their service directories. `requirements.txt` contains runtime dependencies, including `tzdata` so `ZoneInfo("Asia/Ho_Chi_Minh")` works on Windows; `requirements-dev.txt` adds `pytest` for test workflows. The current suite uses `unittest` and can also be run by pytest:

```powershell
cd backend/gateway
python -m unittest discover -s tests -v
python -m pytest -q
```

```powershell
cd backend/services/court_service
python -m unittest discover -s tests -v
python -m pytest -q
```

Court tests use an in-memory SQLite database and a test-only JWT secret. They do not run migrations or seed MySQL. Booking Service remains responsible for bookings and does not have its status changed by Court Service time-slot operations.

## Court Service database setup

For a new `sports_court_db`, run `python -m app.init_db` from `backend/services/court_service`. For an existing schema missing the reservation columns, follow the one-time migration note in [Local demo setup](#local-demo-setup). Demo data is prepared only with [`backend/database/seed.sql`](database/seed.sql); there is no separate Court-only Python seed command.

## Local demo setup

The manual demo uses the four development databases configured in `backend/.env`. Keep that file local and verify its database names before running setup commands. Do not run this seed against `sports_*_e2e_test` databases. `backend/e2e/.env` may remain locally for isolated tests but is not used by this guide.

1. Install dependencies and configure MySQL as described above. Create the four databases with `backend/scripts/create_databases.sql`.
2. Initialize schemas from the service directories. For a new Court database `create_all` creates the current model schema. For an older existing Court schema missing reservation fields, back up first and apply `backend/migrations/20261026_add_time_slot_reservations.sql` once; do not apply it after initializing a fresh current schema.

   ```powershell
   cd backend/services/user_service
   python -m alembic -c alembic.ini upgrade head
   cd ../court_service
   python -m app.init_db
   cd ../booking_service
   python -m app.init_db
   cd ../payment_service
   python -m app.init_db
   ```
3. Open [`backend/database/seed.sql`](database/seed.sql) in MySQL Workbench. Review the read-only preflight results and run it only when the target schemas are `sports_user_db` and `sports_court_db`. The SQL inserts demo accounts and Court catalogue/schedule rows only; it does not create Booking, Payment, QR, check-in, or completion states.
4. Start the five services using the commands in the Run the applications section above. Serve Management Web from `management-web/` with `python -m http.server 8080 --bind 127.0.0.1`; open `http://127.0.0.1:8080`.

All six accounts use `password123` for local demo. The SQL stores only Argon2id hashes generated and verified with the existing User Service hasher. If a demo email already exists, the SQL leaves it untouched; verify it can log in before importing and resolve any role/status conflict manually. Do not use these credentials outside a local demo.

| Role | Email |
|---|---|
| ADMIN | `admin.demo@example.com` |
| OWNER | `owner1.demo@example.com` |
| OWNER | `owner2.demo@example.com` |
| CUSTOMER | `customer1.demo@example.com` |
| CUSTOMER | `customer2.demo@example.com` |
| CUSTOMER | `customer3.demo@example.com` |

The SQL is idempotent for exact demo names: it inserts only missing rows, never updates or deletes, resolves Owner IDs from the demo emails, and schedules 24 future one-hour slots across eight Courts. If an existing demo email/name has a conflicting role, status, or Owner, stop and resolve it manually before importing. Booking and Payment flows must be exercised through APIs. The current Android client implements authentication only; Customer booking/history/QR UI remains pending S1. Its Auth API base URL is hard-coded in `android-user/app/src/main/java/com/example/sportbooking/api/ApiClient.java`: use the emulator host `10.0.2.2:8001` or the laptop LAN IP with port `8001` when testing on a device; Android source is unchanged by this setup. Manual Owner/Admin/Customer checks are in [Local Test Guide](../docs/TESTING_GUIDE.md#owneradmin-manual-demo-checklist).

After starting Court Service and the Gateway, verify via either API base URL:

```text
GET /api/v1/sports
GET /api/v1/venues
GET /api/v1/courts
GET /api/v1/time-slots
```

Use `?owner_id=<confirmed-id>` for venues, `?venue_id=<venue-id>&sport_id=<sport-id>` for courts, and `?court_id=<court-id>&slot_date=YYYY-MM-DD` for time slots. The Management Web reads through the Gateway; its dashboards, registry, and schedule should reflect these MySQL records. Seed data does not enable API writes, bookings, payment, or QR check-in.

For a direct read-only MySQL check, connect to `sports_court_db` with your local MySQL client and run:

```sql
SELECT COUNT(*) FROM sports;
SELECT COUNT(*) FROM venues;
SELECT COUNT(*) FROM courts;
SELECT COUNT(*) FROM time_slots;
SELECT c.name, v.name AS venue, s.name AS sport, c.price_per_hour
FROM courts AS c
JOIN venues AS v ON v.id = c.venue_id
JOIN sports AS s ON s.id = c.sport_id
ORDER BY v.id, c.id;
```

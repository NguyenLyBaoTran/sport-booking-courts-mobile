# Backend: Sports Court Booking System

## Kiến trúc hiện tại

Backend mới có một API Gateway và bốn FastAPI microservice độc lập:

- User Service — cổng `8001`, database `sports_user_db`.
- Court Service — cổng `8002`, database `sports_court_db`.
- Booking Service — cổng `8003`, database `sports_booking_db`.
- Payment Service — cổng `8004`, database `sports_payment_db`.
- API Gateway — cổng `8000`, nhận request từ client và chuyển tiếp theo API prefix.

Mỗi service hiện có `/health` và `/health/db`. Court Service đã có API đọc công khai; API ghi chờ tích hợp xác thực. User, Booking và Payment Service chưa có API nghiệp vụ.
Gateway có `/health` và các route kiểm tra service tại
`/api/v1/{user,court,booking,payment}/health`.

`app/` và `alembic/` ở cấp `backend/` là backend Modular Monolith cũ. Chúng được
giữ lại trong giai đoạn chuyển đổi; Alembic hiện tham chiếu `app.core.config` và
`app.db.database`. Chưa có migration nghiệp vụ. Các file `models.py`, `schemas.py`
và `routes.py` rỗng trong từng service được giữ làm điểm mở rộng theo cấu trúc dự án.

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
└── requirements.txt
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

Court Service exposes public read routes and write routes that remain closed until S1 authentication is integrated. Every POST, PUT, and DELETE currently returns HTTP 503 with a generic pending-authentication message. Do not treat a client-supplied `owner_id` as proof of ownership. Replace the `require_write_access` dependency in `services/court_service/app/routes.py` with the agreed JWT and OWNER/ADMIN checks when the Auth contract is available.

| Method | Endpoint | Purpose | Access now |
|---|---|---|---|
| GET | `/api/v1/sports` and `/api/v1/sports/{sport_id}` | List/filter and view sports | Public |
| POST, PUT, DELETE | `/api/v1/sports[/{sport_id}]` | Create, update, soft-deactivate sport | Closed pending Auth |
| GET | `/api/v1/venues` and `/api/v1/venues/{venue_id}` | List/filter and view venues | Public |
| POST, PUT, DELETE | `/api/v1/venues[/{venue_id}]` | Create, update, soft-deactivate venue | Closed pending Auth |
| GET | `/api/v1/courts` and `/api/v1/courts/{court_id}` | List/filter and view courts | Public |
| POST, PUT, DELETE | `/api/v1/courts[/{court_id}]` | Create, update, soft-deactivate court | Closed pending Auth |
| GET | `/api/v1/time-slots` and `/api/v1/time-slots/{slot_id}` | List/filter and view time slots | Public |
| POST, PUT, DELETE | `/api/v1/time-slots[/{slot_id}]` | Create, update, soft-deactivate time slot | Closed pending Auth |

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

Validation returns 422 for malformed request schemas, 400 for invalid references or inactive parent records, 404 for missing resource IDs, and 409 for duplicate sport names or overlapping time slots. Deletes only set `is_active = false`. Time-slot overlap validation considers active slots and excludes the slot being updated. Since there is no database constraint for arbitrary interval overlap, concurrent requests can pass the pre-check at the same time; this API does not claim to prevent that race. The existing exact-slot unique constraint can also reject re-creating an identical slot after soft deletion.

Run the service from the repository's `backend` folder:

```powershell
cd services/court_service
python -m uvicorn app.main:app --reload --port 8002
```

Open Swagger UI at `http://127.0.0.1:8002/docs`. Through the Gateway (port 8000), use the same API paths, for example `http://127.0.0.1:8000/api/v1/time-slots?court_id=1&slot_date=2026-10-23`. Gateway forwards the request body, query string, Authorization header, and upstream status code.

JWT validation and OWNER/ADMIN authorization for all write routes, including checking that the authenticated Owner owns a venue, are pending the S1 Auth contract. Booking Service remains responsible for bookings and does not have its status changed by Court Service time-slot operations.

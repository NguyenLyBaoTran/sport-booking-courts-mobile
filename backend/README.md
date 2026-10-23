# Backend: Sports Court Booking System

## Kiến trúc hiện tại

Backend mới có một API Gateway và bốn FastAPI microservice độc lập:

- User Service — cổng `8001`, database `sports_user_db`.
- Court Service — cổng `8002`, database `sports_court_db`.
- Booking Service — cổng `8003`, database `sports_booking_db`.
- Payment Service — cổng `8004`, database `sports_payment_db`.
- API Gateway — cổng `8000`, nhận request từ client và chuyển tiếp theo API prefix.

Mỗi service hiện có `/health` và `/health/db`. Các API nghiệp vụ chưa được triển khai.
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

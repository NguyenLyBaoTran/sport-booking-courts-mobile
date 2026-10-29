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

Mỗi service có `/health` và `/health/db`. User Service đã có Register/Login/JWT và
`GET /users/me`. Booking/Payment có API cốt lõi nhưng luồng đặt chỗ end-to-end cần
Court Service triển khai đúng internal slot contract trong
[API contract](../docs/API_CONTRACT.md).
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
OWNER ID này có thể dùng làm `owner_id` khi seed dữ liệu Court Service. Đăng nhập
qua `/api/v1/auth/login` để lấy JWT cho web integration test.

### Tài khoản test hiện tại

Các tài khoản này đang tồn tại trong User DB local:

| Role | Email | User ID | Mật khẩu test |
|---|---|---:|---|
| OWNER | `nguyenvana@gmail.com` | `1` | `12345678` |
| ADMIN | `admin@sportbooking.com` | `3` | `12345678` |

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

# Backend — Hệ thống đặt sân thể thao

## 1. Tổng quan Backend

Backend cung cấp API cho ứng dụng Android Customer và Management Web. Bốn
microservice sở hữu database riêng; API Gateway chuyển tiếp các public API.
Các luồng giữa nhiều service đã có implementation, nhưng việc chạy từng service
riêng lẻ hoặc có unit test không tự chứng minh tích hợp E2E.

## 2. Kiến trúc hiện tại

Backend mới có một API Gateway và bốn FastAPI microservice độc lập:

- User Service — cổng `8001`, database `sports_user_db`; Auth/Register/Login đã có.
- Court Service — cổng `8002`, database `sports_court_db`; Sports, Venues, Courts,
  Time Slots và API hold/confirm/release nội bộ.
- Booking Service — cổng `8003`, database `sports_booking_db`; booking, Owner/Admin
  booking APIs, QR token và state transitions.
- Payment Service — cổng `8004`, database `sports_payment_db`; mock payment và
  payment history.
- API Gateway — cổng `8000`, nhận request từ client và chuyển tiếp theo API prefix.

Mỗi service có `/health` và `/health/db`. Gateway có `/health` cùng các route
`/api/v1/{user,court,booking,payment}/health`. User Service phát hành JWT; các
service kiểm tra token/role theo phạm vi API của mình. Booking gọi Court để giữ
slot; Payment gọi Booking để xác nhận sau mock payment. Owner check-in đi qua Court
adapter rồi tới Booking Service. Các luồng này có implementation, nhưng cần chạy
tích hợp với các cấu hình/database tương ứng để xác minh end-to-end.

Android Customer có các màn hình và API client cho catalogue, booking, payment,
profile và authentication. Management Web gọi Gateway cho Owner/Admin; QR scanner
web gọi Owner check-in API. Đây là mô tả theo code, không phải kết quả kiểm thử E2E.

Thư mục `app/` và `alembic/` ở cấp `backend/` thuộc Modular Monolith cũ; setup
microservice bên dưới không dùng chúng làm schema của bốn service.

## 3. Công nghệ

- Python, FastAPI, Uvicorn
- SQLAlchemy, PyMySQL, MySQL
- `httpx` cho request từ Gateway đến service
- `python-dotenv` để nạp cấu hình từ `backend/.env`
- Alembic cho migration User Service

## 4. Cấu trúc backend

```text
backend/
├── database/
│   └── seed.sql                 # Fixture local cho User và Court databases
├── gateway/
│   └── main.py
├── migrations/
│   └── 20261026_add_time_slot_reservations.sql
├── scripts/
│   └── setup_local.py           # Khởi tạo databases, schemas và demo seed
├── services/
│   ├── user_service/
│   ├── court_service/
│   ├── booking_service/
│   └── payment_service/
├── .env.example
├── README.md
├── requirements.txt            # Runtime dependencies
└── requirements-dev.txt        # Runtime dependencies + pytest
```

## 5. Thiết lập môi trường

Trên Windows, từ thư mục gốc repository:

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Mở `backend/.env`, cấu hình MySQL URL và thay các giá trị placeholder cho secret.
Không dùng thông tin đăng nhập thật trong tài liệu hoặc commit `.env`. Nếu mật khẩu
có ký tự đặc biệt trong URL, hãy URL-encode chúng.

Các microservice và Gateway tự tìm `backend/.env` theo vị trí source code. Chỉ dùng
`setup.bat`/`setup_local.py` với database local dành riêng cho development; script
không phải công cụ production.

## 6. Khởi tạo database và demo seed

Khởi tạo bốn database, schema và fixture demo bằng một quy trình. Script
`backend/scripts/setup_local.py` kiểm tra `APP_ENV=development`, cấu hình secret,
database URLs và địa chỉ MySQL local; các URL phải dùng đúng tên database service,
cùng MySQL host/account. Script kiểm tra schema hiện có trước khi ghi và dừng nếu
phát hiện revision không mong đợi, cột reservation bị thiếu một phần, hoặc đích
không an toàn. Chỉ tiếp tục nếu bạn chắc chắn đang dùng các database development
local đúng mục đích.

Từ repository root, chạy:

```powershell
.\setup.bat
```

Khi được hỏi, nhập `SETUP` để xác nhận. `setup.bat` yêu cầu đã tạo
`backend/.venv` và cài dependencies; nó gọi script bằng Python trong virtual
environment đó.

Nếu muốn chạy Python trực tiếp, kích hoạt `backend/.venv` trước, rồi chạy từ
repository root:

```powershell
python backend/scripts/setup_local.py
```

Sau khi xác nhận, script tạo bốn database, chạy User Service Alembic migration,
khởi tạo Court/Booking/Payment schemas, áp dụng Court reservation migration nếu
các cột đó chưa có, chạy `backend/database/seed.sql`, rồi kiểm tra các bảng và
fixture demo. Nếu không nhập đúng `SETUP`, script hủy và không ghi dữ liệu.

Seed SQL định nghĩa fixture mẫu gồm **6 tài khoản** (1 ADMIN, 2 OWNER, 3 USER),
**3 sports**, **4 venues**, **8 courts** và **24 time slots** active trong tương
lai (mỗi court có slot 09:00–10:00 trong ba ngày). Script chỉ thêm các bản ghi còn
thiếu phù hợp, không xóa hoặc cập nhật dữ liệu hiện có; xung đột fixture sẽ khiến
preflight/verification báo lỗi. Credential demo được định nghĩa trong seed script;
không sao chép password/hash vào README hoặc commit credential thật.

Seed không tạo booking, payment, QR check-in hay giao dịch hoàn tất. Các luồng đó
phải được tạo qua API tương ứng. Setup và seed dành cho local development/demo,
không phải quy trình triển khai production. `backend/scripts/create_databases.sql`
chỉ tạo database rỗng; không dùng nó thay cho quy trình setup tích hợp.

## 7. Cấu hình microservice

`backend/.env.example` cung cấp các URL mẫu riêng:

| Biến môi trường | Service | Database |
|---|---|---|
| `USER_DATABASE_URL` | User | `sports_user_db` |
| `COURT_DATABASE_URL` | Court | `sports_court_db` |
| `BOOKING_DATABASE_URL` | Booking | `sports_booking_db` |
| `PAYMENT_DATABASE_URL` | Payment | `sports_payment_db` |

Mỗi service chỉ đọc URL của mình và dùng engine/session riêng. Khi chưa có URL hoặc
database không kết nối được, `/health/db` báo database unavailable. `DATABASE_URL`
chỉ dành cho Modular Monolith cũ, không thuộc bốn database microservice.

Service URL được cấu hình bằng `USER_SERVICE_URL`, `COURT_SERVICE_URL`,
`BOOKING_SERVICE_URL`, `PAYMENT_SERVICE_URL`. Booking hold dùng
`BOOKING_HOLD_MINUTES` (mặc định 10); Court và Booking cần cấu hình thống nhất.
Booking, Court và Payment dùng cùng `INTERNAL_SERVICE_TOKEN` cho các lời gọi nội bộ
được bảo vệ. Gateway CORS dùng `CORS_ALLOWED_ORIGINS` (danh sách origin HTTP(S)
tường minh, phân cách bằng dấu phẩy); không dùng wildcard.

## 8. Authentication và Google Sign-In

User Service phát hành JWT HS256. Tạo một secret riêng cho local rồi đặt vào
`backend/.env`:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Đặt kết quả vào `JWT_SECRET_KEY`; User/Court phải dùng cùng secret và thuật toán
`JWT_ALGORITHM=HS256`. Secret phải có ít nhất 32 ký tự. Thời hạn token lấy từ
`JWT_ACCESS_TOKEN_EXPIRE_MINUTES`. Setup local chạy User Service migration.
Không commit `.env` hoặc secret vào Git.

API public đi qua Gateway tại `http://127.0.0.1:8000`:

| Method | Path | Mô tả |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Đăng ký tài khoản USER |
| `POST` | `/api/v1/auth/login` | Đăng nhập và nhận JWT Bearer |
| `POST` | `/api/v1/auth/google` | Google Sign-In cho USER |
| `POST` | `/api/v1/auth/forgot-password` | Gửi mã đặt lại mật khẩu |
| `POST` | `/api/v1/auth/reset-password` | Đặt lại bằng OTP |
| `GET/PATCH` | `/api/v1/users/me` | Xem/cập nhật profile |
| `GET` | `/api/v1/admin/users/summary`, `/api/v1/admin/users` | Admin xem summary/list |
| `GET` | `/api/v1/admin/users/{user_id}` | Admin xem chi tiết account |
| `PATCH` | `/api/v1/admin/users/{user_id}/status` | Admin đổi trạng thái account |

Register nhận `full_name`, `email`, `password` (8–128 ký tự) và `phone` tùy chọn.
Email được chuẩn hóa chữ thường; đăng ký công khai luôn tạo role `USER`, không nhận
role từ request. Login nhận `email` và `password`; response trả về
`access_token`, `token_type`, `expires_in` (giây) và thông tin user. JWT claims
gồm `sub` (user ID dạng chuỗi), `role`, `iat` và `exp`. Email trùng trả `409`,
thông tin đăng nhập sai hoặc token không hợp lệ trả `401`.

Google Sign-In dành cho role `USER` qua `POST /api/v1/auth/google` với JSON
`{"id_token":"<Google ID token>"}`. Đặt `GOOGLE_CLIENT_ID` trong `backend/.env`
thành OAuth client ID được dùng làm audience của ID token. Dependency
`google-auth[requests]` có trong `requirements.txt`. Backend xác minh token và email
đã xác minh. Tài khoản mới
được tạo với role `USER`. Nếu Gmail đã thuộc tài khoản `USER` dùng mật khẩu, backend
tự liên kết Google subject và đăng nhập vào đúng tài khoản đó. Email Workspace cũng
được tự liên kết khi email đã xác minh khớp hosted domain. Email Google khác không
tự liên kết và cần dùng đăng nhập mật khẩu.
OWNER/ADMIN không thể đăng nhập qua endpoint này.

Đặt lại mật khẩu gửi mã OTP qua SMTP. Các biến cấu hình là `SMTP_HOST`,
`SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` và `SMTP_FROM`. OTP có thời hạn
10 phút. Trong development/test, khi chưa cấu hình SMTP, code có nhánh debug OTP;
không dùng nhánh này cho production. OTP hiện được lưu trong bộ nhớ của User
Service.

Tạo tài khoản OWNER/ADMIN cho local development/test bằng lệnh sau. Chạy từ thư
mục User Service với virtual environment đã kích hoạt:

```powershell
Set-Location backend\services\user_service
python -m app.create_test_account
```

Lệnh chỉ chạy khi `APP_ENV=development` hoặc `test`, hỏi role/name/email/password
trong terminal và băm mật khẩu trước khi lưu. Không commit credential thật.

Admin User routes đã có implementation trong User Service source. Lưu ý
`docs/api/admin-management-api-contract.md` còn ghi các route này là pending, nên
tài liệu đó chưa đồng bộ với code hiện tại.

## 9. Booking và Payment

Booking Service tạo booking `PENDING` sau khi gọi Court hold; giá tính từ
`price_per_hour × thời lượng slot`. Hold mặc định 10 phút. Khách hàng có thể xem,
hủy booking PENDING hoặc xem lịch sử; booking hết hạn được release slot và chuyển
sang `EXPIRED` khi được xử lý bởi logic expiry hoặc internal endpoint
`POST /api/v1/internal/bookings/expire`. Endpoint expiry cần được gọi theo lịch nếu
cần xử lý các booking không được truy cập lại.

Sau mock payment thành công, Payment Service gọi Booking để confirm booking; Booking
xác nhận slot tại Court, chuyển trạng thái sang `CONFIRMED` và tạo QR token opaque.
Payment nhận `SUCCESS` hoặc `FAILED`; không xử lý tiền thật. `Idempotency-Key`
(1–100 ký tự) hỗ trợ retry; successful payment cho một booking không được tạo lặp.

| Method | Path | Chức năng |
|---|---|---|
| POST/GET | `/api/v1/bookings` | Tạo booking / danh sách booking của USER |
| GET | `/api/v1/bookings/{id}` | Chi tiết booking của USER |
| POST | `/api/v1/bookings/{id}/cancel` | Hủy booking PENDING |
| GET | `/api/v1/owner/bookings` | Owner list, lọc venue/date/status |
| GET | `/api/v1/owner/bookings/{id}` | Owner xem chi tiết của mình |
| POST | `/api/v1/owner/bookings/{id}/complete` | `CHECKED_IN` → `COMPLETED` |
| POST | `/api/v1/payments/process` | Mock payment |
| GET | `/api/v1/payments` và `/{id}` | Payment history của USER |
| GET | `/api/v1/admin/bookings/summary` | Admin summary bookings |
| GET | `/api/v1/admin/bookings`, `/{id}` | Admin xem booking |
| GET | `/api/v1/admin/checkins` | Admin xem check-in history |

QR check-in: Web gửi QR token tới Court `POST /api/v1/owner/checkins`; Court xác
thực Owner rồi gọi internal Booking check-in bằng server-side token. Booking Service
sở hữu kiểm tra QR/booking và state transition. Admin/Owner Booking APIs có source
implementation; các service và database cần được chạy cùng cấu hình để kiểm thử
tích hợp thực tế.

Chi tiết request/response và internal contracts: [API Contract](../docs/API_CONTRACT.md)
và [Owner Booking & QR contract](../docs/api/owner-booking-qr-contract.md). Contract
ghi rõ real cross-service E2E chưa được xác nhận.

## 10. Court Service

Court Service có public read APIs cho Sports, Venues, Courts và Time Slots. Các thao
tác ghi yêu cầu JWT: Owner chỉ quản lý venue của mình và courts/time slots thuộc
venue đó; Admin có quyền quản lý toàn hệ thống, riêng ghi Sports chỉ dành cho Admin.
Venue tạo mới của Owner phải có `owner_id` khớp JWT subject; không thể đổi owner khi
cập nhật. USER hoặc Owner khác bị từ chối; service xác thực role và ownership ở
backend.

Time Slot phải bắt đầu trước khi kết thúc, nằm trên mốc 30 phút, có ngày/giờ bắt đầu
trong tương lai và không overlap slot active khác trên cùng court/ngày. Không có
giờ mở cửa venue cố định. Xóa dữ liệu là soft-deactivate. Đây là API validation,
không phải ràng buộc DB cho mọi quy tắc thời gian.

Booking–Court internal reservation APIs dùng `X-Internal-Token`:
`POST /api/v1/internal/slots/{slot_id}/hold`, `/confirm` và `/release`; Gateway không
expose các route internal. Reservation state được lưu trong `time_slots`:
`AVAILABLE`, `HELD`, `BOOKED`, cùng booking ID và expiration time khi có hold.
Hold mặc định 10 phút (`BOOKING_HOLD_MINUTES`). Court khóa row khi thực hiện
reservation transition; điều này hỗ trợ xử lý cạnh tranh ở database, nhưng chưa
được xác minh bằng kiểm thử E2E/concurrent trên MySQL ở đây. Setup local áp dụng
migration reservation nếu cần.

| Method | Endpoint | Purpose | Access now |
|---|---|---|---|
| GET | `/api/v1/sports` and `/api/v1/sports/{sport_id}` | List/filter and view sports | Public |
| POST, PUT, DELETE | `/api/v1/sports[/{sport_id}]` | Tạo, sửa, soft-deactivate sport | ADMIN |
| GET | `/api/v1/venues` and `/api/v1/venues/{venue_id}` | List/filter and view venues | Public |
| POST, PUT, DELETE | `/api/v1/venues[/{venue_id}]` | Tạo, sửa, soft-deactivate venue | Owner của venue hoặc ADMIN |
| GET | `/api/v1/courts` and `/api/v1/courts/{court_id}` | List/filter and view courts | Public |
| POST, PUT, DELETE | `/api/v1/courts[/{court_id}]` | Tạo, sửa, soft-deactivate court | Owner venue liên quan hoặc ADMIN |
| GET | `/api/v1/time-slots` and `/api/v1/time-slots/{slot_id}` | List/filter and view time slots | Public |
| POST, PUT, DELETE | `/api/v1/time-slots[/{slot_id}]` | Tạo, sửa, soft-deactivate time slot | Owner venue liên quan hoặc ADMIN |

Ví dụ request tạo Court:

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

Read routes support `is_active`; venue routes also support `owner_id`, court routes `venue_id` and `sport_id`, and time-slot routes `court_id` and `slot_date` (ISO date). Query parameters can be combined. Request schemas reject extra fields such as `id` and `created_at`.

Validation returns `422` for invalid request/time values, `400` for invalid or inactive references, `404` for missing IDs and `409` for duplicate sport names or overlapping slots. Time uses `Asia/Ho_Chi_Minh`; the schema stores a `DATE` and timezone-naive `TIME`. Historical slots may be edited in fields unrelated to date/start. Database columns do not enforce the 30-minute or future-time rules; no fixed Venue opening hours are enforced. Overlap checks compare active slots on the same court/date and exclude the row being updated. There is no general database constraint for arbitrary interval overlaps, so API pre-validation alone is not evidence that concurrent slot creation is race-free. Exact-slot uniqueness may also prevent recreating a matching row after soft-deactivation.

Run the service from the repository's `backend` folder:

```powershell
cd services/court_service
python -m uvicorn app.main:app --reload --port 8002
```

Mở Swagger UI tại `http://127.0.0.1:8002/docs`. Gateway chuyển tiếp các Court API
theo cùng path, ví dụ `http://127.0.0.1:8000/api/v1/time-slots?court_id=1&slot_date=YYYY-MM-DD`.

Court JWT verification dùng `python-jose`, đọc `JWT_SECRET_KEY` và `JWT_ALGORITHM`.
User và Court cần cùng secret (ít nhất 32 ký tự); không đưa secret vào frontend
hoặc commit vào Git. Gateway CORS dùng `CORS_ALLOWED_ORIGINS`.

## 11. API Gateway

Gateway định tuyến public API theo path tới User (`/api/v1/auth/*`,
`/api/v1/users/*`, `/api/v1/admin/users/*`), Court (`/api/v1/sports/*`,
`/api/v1/venues/*`, `/api/v1/courts/*`, `/api/v1/time-slots/*`,
`/api/v1/owner/checkins`, `/api/v1/admin/catalogue/*`), Booking
(`/api/v1/bookings/*`, `/api/v1/owner/bookings/*`, `/api/v1/admin/bookings/*`,
`/api/v1/admin/checkins`) và Payment (`/api/v1/payments/*`). Destination URLs
được cấu hình bằng `*_SERVICE_URL` trong `.env`; Gateway dùng HTTPX, chuyển tiếp
method/path/query/body và các header được cho phép: `Authorization`,
`Content-Type`, `Accept`, `Idempotency-Key`. Header nội bộ không được browser gửi
để gọi internal endpoint; `/api/v1/internal` không được proxy công khai.

Các route health proxy riêng là `/api/v1/{user,court,booking,payment}/health`.
Timeout upstream là 10 giây: lỗi kết nối trả 503, timeout trả 504; response status
và body từ upstream được chuyển tiếp. CORS dùng `CORS_ALLOWED_ORIGINS`, mặc định
chỉ các origin Management Web trên localhost, và không cho phép wildcard. Gateway
chuyển tiếp Authorization nhưng không tự quyết định quyền nghiệp vụ; service đích
xác minh JWT/role.

## 12. Chạy các dịch vụ

Sau khi setup database và cài dependencies, mở terminal riêng cho Gateway và mỗi
service. Trong mỗi terminal, chạy từ repository root:

```powershell
Set-Location backend
.\.venv\Scripts\Activate.ps1
Set-Location gateway
python -m uvicorn main:app --reload --port 8000
```

Mỗi service còn lại chạy trong một terminal khác, thay thư mục và port tương ứng
(dùng dấu `\` trong đường dẫn PowerShell):

```powershell
Set-Location backend
.\.venv\Scripts\Activate.ps1
Set-Location services\user_service
python -m uvicorn app.main:app --reload --port 8001
```

```powershell
Set-Location backend
.\.venv\Scripts\Activate.ps1
Set-Location services\court_service
python -m uvicorn app.main:app --reload --port 8002
```

```powershell
Set-Location backend
.\.venv\Scripts\Activate.ps1
Set-Location services\booking_service
python -m uvicorn app.main:app --reload --port 8003
```

```powershell
Set-Location backend
.\.venv\Scripts\Activate.ps1
Set-Location services\payment_service
python -m uvicorn app.main:app --reload --port 8004
```

Health endpoints trực tiếp:

- User: `http://127.0.0.1:8001/health`, `http://127.0.0.1:8001/health/db`
- Court: `http://127.0.0.1:8002/health`, `http://127.0.0.1:8002/health/db`
- Booking: `http://127.0.0.1:8003/health`, `http://127.0.0.1:8003/health/db`
- Payment: `http://127.0.0.1:8004/health`, `http://127.0.0.1:8004/health/db`

Qua Gateway, kiểm tra `/health`, `/api/v1/user/health`,
`/api/v1/court/health`, `/api/v1/booking/health`, `/api/v1/payment/health` và
`/docs` tại `http://127.0.0.1:8000`. Endpoint `/health/db` chỉ báo connected khi
truy vấn database thành công.

## 13. Kiểm thử

`requirements-dev.txt` cài runtime dependencies cùng `pytest`. Sau khi kích hoạt
`backend/.venv`, chạy các lệnh trong terminal riêng của từng thư mục:

```powershell
Set-Location backend\gateway
python -m unittest discover -s tests -v
python -m pytest -q
```

```powershell
Set-Location backend\services\court_service
python -m unittest discover -s tests -v
python -m pytest -q
```

Gateway/Court tests dùng test setup riêng; Court tests dùng SQLite in-memory và JWT
test-only nên không khởi tạo hoặc seed MySQL. Có thể chạy test tương ứng của từng
service từ thư mục service. Test riêng lẻ không xác nhận cross-service E2E; hãy
kiểm thử riêng các luồng Booking → Court hold/confirm/release, Payment → Booking
confirmation và Management Web → Gateway → service với database local đã setup.
Không có test result nào được khẳng định ở đây.

## 14. Troubleshooting / Lưu ý

- Nếu setup từ chối cấu hình, kiểm tra `APP_ENV=development`, bốn URL MySQL, đúng
  tên database, cùng host/account local và secret đủ độ dài. Chỉ nhập `SETUP` sau
  khi xác nhận đúng database development.
- Nếu service báo database unavailable, kiểm tra MySQL đang chạy, service-specific
  URL có đúng database và user có quyền truy cập.
- Nếu JWT bị từ chối, xác nhận `JWT_SECRET_KEY` giống nhau giữa User và Court; không
  dùng placeholder trong `.env.example`.
- Nếu Booking giữ slot nhưng không hoàn tất, kiểm tra service URLs và
  `INTERNAL_SERVICE_TOKEN` giữa các service; hold có hạn và cần được confirm/release
  hoặc xử lý expiry.
- `docs/api/admin-management-api-contract.md` chưa đồng bộ với Admin API source hiện
  tại. Ưu tiên implementation trong service source khi đối chiếu; chưa kết luận tích
  hợp E2E chỉ dựa trên contract hoặc test từng service.
- Android Customer và Management Web có API client/UI tích hợp theo code. Cần môi
  trường với các service hoạt động để xác nhận hành vi toàn luồng; không suy ra
  thành công chỉ từ việc backend service chạy riêng.

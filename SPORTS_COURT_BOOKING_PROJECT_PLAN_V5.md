# SPORTS COURT BOOKING SYSTEM — MASTER PROJECT PLAN V5

> **Phiên bản 5 — 23/10/2026** · 2 sinh viên · Mobile là ưu tiên chính; SOA tái sử dụng Backend Microservices.  
> **Thay thế kế hoạch V4 về kiến trúc, phân công, cấu trúc thư mục và tích hợp.** Các business rules đã được hai thành viên chốt trong V4 được giữ nguyên, trừ những điều chỉnh kỹ thuật được ghi rõ dưới đây.  
> **Trạng thái:** Kế hoạch mục tiêu; không được coi các service/endpoint là đã hoàn thành cho đến khi có code và test. 

## Mục lục

1. [Mục tiêu và phạm vi](#1-mục-tiêu-và-phạm-vi)
2. [Kiến trúc và công nghệ](#2-kiến-trúc-và-công-nghệ)
3. [Phân công và file ownership](#3-phân-công-và-file-ownership)
4. [Cấu trúc repository](#4-cấu-trúc-repository)
5. [Database và quy tắc nghiệp vụ](#5-database-và-quy-tắc-nghiệp-vụ)
6. [API Contract và tích hợp](#6-api-contract-và-tích-hợp)
7. [Kế hoạch 5 iteration](#7-kế-hoạch-5-iteration)
8. [Git và kế hoạch migration từ V4](#8-git-và-kế-hoạch-migration-từ-v4)
9. [Diagram và báo cáo](#9-diagram-và-báo-cáo)
10. [Kiểm thử và nghiệm thu](#10-kiểm-thử-và-nghiệm-thu)
11. [Quyết định cần giữ thống nhất](#11-quyết-định-cần-giữ-thống-nhất)

## 1. Mục tiêu và phạm vi

### 1.1. Hai môn, một hệ thống Backend

| Hạng mục | Môn Mobile | Môn SOA |
|---|---|---|
| Customer frontend | **Android Java + XML + Retrofit**, bắt buộc, ưu tiên số 1 | Customer Web HTML/CSS/JS, triển khai sau |
| Owner/Admin frontend | Management Web HTML/CSS/JS/Bootstrap | Tái sử dụng cùng Management Web |
| Backend | **Cùng FastAPI Microservices** | **Cùng FastAPI Microservices** |
| Database | Cùng MySQL Server, database riêng theo service | Tái sử dụng |
| Báo cáo | Android, UX, nghiệp vụ, REST integration, QR | Service boundaries, service-to-service REST, database ownership, resilience |

**Không làm Customer Web SOA trong giai đoạn đầu.** Không triển khai hai backend song song. Nếu quy định nộp bài yêu cầu sản phẩm độc lập, nhóm phải xác nhận với giảng viên trước khi nộp.

### 1.2. Phạm vi Mobile phải hoàn thành

- Customer Android: đăng ký/đăng nhập, tìm sân, xem Venue/Court/Slot, tạo Booking, Mock Payment, lịch sử/chi tiết, hiển thị QR, review sau hoàn thành.
- Owner Web: đăng nhập, quản lý Venue/Court/Slot, xem Booking, **quét QR bằng webcam laptop**, check-in, complete Booking.
- Admin Web: dashboard và quản lý dữ liệu theo quyền; chỉ triển khai các chức năng đã chốt trong API Contract.
- Backend: JWT/RBAC, chống double booking, PENDING 10 phút, Mock Payment success/failure, QR token an toàn, kiểm tra Owner scope, chống check-in lặp, tests, README, report.
- **Tùy chọn sau cùng:** VNPAY Sandbox hoặc payment gateway khác; không xử lý tiền thật. Không thêm bản đồ/GPS, email, Kafka, RabbitMQ, Kubernetes hoặc chat vào phạm vi bắt buộc.

### 1.3. Ưu tiên

1. Mobile chạy được end-to-end và ổn định.
2. Backend đáp ứng ranh giới Microservices tối thiểu, có kiểm thử giao tiếp.
3. Owner/Admin Web và QR webcam hoạt động.
4. Diagram, report, test evidence chính xác.
5. Customer Web SOA, gateway thanh toán thật ở giai đoạn sau.

## 2. Kiến trúc và công nghệ

### 2.1. Công nghệ chính

| Thành phần | Công nghệ | Ghi chú |
|---|---|---|
| Android Customer | Java, XML, Retrofit, Gson, ZXing | S1 |
| Owner/Admin Web | HTML, CSS, JavaScript, Bootstrap, Fetch API, html5-qrcode | S2; webcam trên localhost hoặc HTTPS |
| Backend | FastAPI, Pydantic, SQLAlchemy, PyMySQL, Uvicorn | 4 ứng dụng FastAPI độc lập |
| API Gateway | FastAPI + HTTP client (httpx) | **Định tuyến mỏng**, không chứa business logic |
| Authentication | JWT Bearer; USER, OWNER, ADMIN | User Service phát hành; các service kiểm tra chữ ký/claims theo cấu hình chung |
| Database | Một MySQL Server, **4 logical databases** | Database-per-service; migration độc lập |
| Migrations | Alembic cho từng service | Không chạy một Alembic chung cho 4 DB |
| Testing | pytest, HTTP API tests, Swagger, Android/Web manual | Thêm timeout, service unavailable, duplicate requests |
| Payment | Mock Provider trước, gateway provider sau | Không cho client tự xác nhận thanh toán thật |

### 2.2. Service boundaries

| Service | Port local | Database | Owner | Trách nhiệm |
|---|---:|---|---|---|
| API Gateway | 8000 | Không | S2 | Chuyển tiếp API, thống nhất base URL, không truy cập DB |
| User Service | 8001 | `user_db` | S1 | Register/Login, JWT, profile, user/role management tối thiểu |
| Court Service | 8002 | `court_db` | S2 | Sports, Venues, Courts, Slots, Owner CRUD, availability |
| Booking Service | 8003 | `booking_db` | S1 | Booking lifecycle, QR token, check-in, complete, reviews |
| Payment Service | 8004 | `payment_db` | S1 | Mock Payment attempts, idempotency, optional provider adapter |

**Chỉ service sở hữu dữ liệu mới được đọc/ghi database đó.** Service khác phải gọi REST API nội bộ; không import trực tiếp model/service Python của nhau, không dùng chung SQLAlchemy Session. Không dùng FK xuyên service. `owner_id`, `user_id`, `time_slot_id`, `booking_id` là tham chiếu logic được kiểm tra qua API.

**Đơn giản hóa:** Có thể chạy cả 4 DB trong cùng một MySQL Server local. Không bắt buộc Docker, service discovery hay message broker. Gateway là một FastAPI proxy tối giản; nếu gây chậm tiến độ, có thể bắt đầu với endpoint proxy cơ bản và mở rộng sau.

### 2.3. Local URLs

| Thành phần | URL |
|---|---|
| Gateway | `http://localhost:8000` |
| User Service | `http://localhost:8001` |
| Court Service | `http://localhost:8002` |
| Booking Service | `http://localhost:8003` |
| Payment Service | `http://localhost:8004` |
| Management Web | `http://localhost:8080` (ví dụ) |
| Android Emulator gọi Gateway | `http://10.0.2.2:8000` |

Điện thoại Android thật dùng IP LAN của máy chạy Backend, không dùng `localhost`. Cấu hình Android cleartext HTTP chỉ dành cho môi trường phát triển; production phải dùng HTTPS.

## 3. Phân công và file ownership

### 3.1. Phân công chính

| Công việc | Student 1 (S1) | Student 2 (S2) |
|---|---|---|
| Frontend | **Android Customer App** | **Owner/Admin Web**, QR webcam |
| User Service | **Toàn bộ**: Auth/JWT/Users | Review contract, tích hợp Web login |
| Court Service | Review, dùng API từ Android/Booking | **Toàn bộ**: Sports/Venues/Courts/Slots |
| Booking Service | **Toàn bộ**: Booking/QR token/Check-in/Complete/Review | Định nghĩa yêu cầu check-in, test với webcam |
| Payment Service | **Toàn bộ**: Mock/Payment API/idempotency | Review tích hợp Owner/Admin |
| Gateway | Review API client behavior | **Foundation, routing, cấu hình** |
| DB foundation | Models/migrations cho 3 DB S1 | MySQL setup, Court DB, bootstrap scripts, hướng dẫn setup |
| Diagrams | System Use Case, Booking Activity/Sequence, Payment Sequence, Booking State | ERD, Microservices Architecture, QR Check-in Sequence |
| Report | User/Android/Auth/Booking/Payment/Review | Owner/Admin/Court/Gateway/Architecture/DB/QR webcam; tổng hợp |
| Testing | Android + User/Booking/Payment + concurrency | Court/Gateway/Web/QR + cross-service failures |
| Customer Web SOA | Chưa triển khai | Chưa triển khai |

### 3.2. Quy tắc sở hữu

- **S1 sở hữu Booking State và toàn bộ check-in Backend** để giữ `bookings` và `checkins` trong một transaction thuộc `booking_db`. **S2 sở hữu webcam scanner Web**, không viết API check-in độc lập ghi vào `booking_db`.
- S2 sở hữu Court Service và công bố `GET /courts/{id}/slots` cùng internal API đặt/giải phóng slot. S1 không sửa Court DB trực tiếp.
- S1 sở hữu Payment Service và cơ chế confirm Booking qua REST; S2 không tạo mock payment logic khác.
- S2 sở hữu Gateway; S1 yêu cầu thêm route bằng PR hoặc thay đổi contract đã review.
- Shared files (`docs/API_CONTRACT.md`, `docs/BUSINESS_RULES.md`, `README.md`) thay đổi tuần tự qua PR, không sửa cùng lúc.
- S1 chưa bắt đầu: chỉ bắt đầu Auth/Android sau khi foundation skeleton và contract V5 đã được merge vào `develop`; trong khi chờ có thể làm Android UI mock/diagram độc lập.

## 4. Cấu trúc repository

```text
sport-booking-courts-mobile/
├── README.md
├── .gitignore
├── SPORTS_COURT_BOOKING_PROJECT_PLAN_V5.md
├── android-user/                         # S1; Android Java/XML
├── management-web/                       # S2; giữ code V4 đã làm
├── customer-web/                         # SOA; chỉ tạo khi bắt đầu SOA Web
├── backend/
│   ├── README.md
│   ├── gateway/                         # S2
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── .env.example
│   ├── services/
│   │   ├── user_service/                 # S1
│   │   │   ├── app/
│   │   │   │   ├── main.py
│   │   │   │   ├── core/{config,database,security}.py
│   │   │   │   ├── models/
│   │   │   │   ├── schemas/
│   │   │   │   ├── routers/
│   │   │   │   └── services/
│   │   │   ├── alembic/
│   │   │   ├── tests/
│   │   │   ├── requirements.txt
│   │   │   └── .env.example
│   │   ├── court_service/                # S2; cùng cấu trúc app/alembic/tests
│   │   ├── booking_service/              # S1; cùng cấu trúc
│   │   └── payment_service/              # S1; cùng cấu trúc
│   └── scripts/                          # S2; DB setup/seed/run scripts
├── docs/
│   ├── SYSTEM_REQUIREMENTS.md
│   ├── BUSINESS_RULES.md
│   ├── API_CONTRACT.md
│   ├── DB_SCHEMA.md
│   ├── fixtures/
│   ├── diagrams/
│   │   ├── usecase/
│   │   ├── erd/
│   │   ├── architecture/
│   │   ├── activity/
│   │   ├── sequence/
│   │   └── state/
│   ├── test-cases/
│   └── screenshots/{android,web}/
└── report/
    ├── drafts/
    ├── figures/
    └── Final_Report.docx
```

**Migration rule:** Không xóa `backend/app/` cũ ngay. Tạo service skeleton mới trước; di chuyển/tái sử dụng `config.py`, `database.py`, requirements, seed và Alembic theo từng service; chỉ xóa code cũ khi tests đã pass và PR đã review. Không tạo bốn bản copy business logic của Monolith.

**Bảo mật Git:** Không commit `.env`, mật khẩu, token, `venv/`, `.venv/`, `__pycache__/`, build artifacts; chỉ commit `.env.example`. Không đặt shared secrets thật trong tài liệu.

## 5. Database và quy tắc nghiệp vụ

### 5.1. Chia 9 bảng theo database

| Database | Bảng | Người sở hữu |
|---|---|---|
| `user_db` | `users` | S1 |
| `court_db` | `sports`, `venues`, `courts`, `time_slots` | S2 |
| `booking_db` | `bookings`, `checkins`, `reviews` | S1 |
| `payment_db` | `payments` | S1 |

**ERD V4 vẫn là mô hình dữ liệu nghiệp vụ**, nhưng V5 phải cập nhật thành ERD theo 4 vùng database. Trong một DB vẫn giữ PK, FK và UNIQUE phù hợp. Các ID tham chiếu sang DB khác **không dùng DB-level FK**, thay bằng kiểm tra qua API và test consistency.

### 5.2. Quy tắc đã chốt — giữ nguyên

1. Booking thuộc một User và một Time Slot; mỗi Booking chỉ đặt một slot.
2. Một slot chỉ có tối đa một Booking đang chiếm chỗ hợp lệ. `PENDING` chưa hết hạn và `CONFIRMED/CHECKED_IN/COMPLETED` không được đặt trùng; `CANCELLED/EXPIRED` không giữ chỗ.
3. Booking `PENDING` giữ chỗ **10 phút**, hết hạn thành `EXPIRED`; kiểm tra theo giờ Backend, không tin giờ Android.
4. Booking state: `PENDING → CONFIRMED → CHECKED_IN → COMPLETED`; hỗ trợ `CANCELLED`, `EXPIRED` theo chính sách đã chốt.
5. Payment mock `SUCCESS/FAILED`; retry thất bại; không tạo hai lần thanh toán thành công. Payment attempt là dữ liệu của Payment Service.
6. QR token ngẫu nhiên, duy nhất, không chứa Booking ID dễ đoán; chỉ phát hành sau khi Booking confirmed.
7. Owner quét QR qua webcam laptop; chỉ Owner sở hữu Venue tương ứng được check-in; từ chối QR sai, chưa Confirmed, hoặc đã quét.
8. `checkins.booking_id` UNIQUE; Booking Service ghi check-in và cập nhật Booking status **trong cùng transaction của booking_db**.
9. Review chỉ khi `COMPLETED`, tối đa một Review/Booking.
10. Owner/Admin account tạo qua seed hoặc quản trị; đăng ký công khai chỉ cấp USER. Mọi service thực thi role/ownership phía Backend.

### 5.3. Double booking trong Microservices — thay đổi bắt buộc

Trong V4, Booking khóa dòng `time_slots` rồi tạo Booking trong **một MySQL transaction chung**. Cách này không còn đúng khi `time_slots` thuộc `court_db` còn `bookings` thuộc `booking_db`.

**V5 chọn Court Service làm nơi sở hữu độc quyền việc giữ slot (slot reservation).** Để không thêm bảng thứ 10 vào ERD nghiệp vụ, có thể dùng các cột trạng thái/hold trên `time_slots` hoặc một bảng kỹ thuật `slot_holds` thuộc `court_db`; phương án cuối phải được chốt trước khi code và cập nhật ERD nếu thêm bảng. Không khẳng định còn đúng 9 bảng vật lý nếu chọn bảng kỹ thuật.

Luồng tối thiểu: Booking Service gọi Court Service **atomic hold slot** bằng `booking_request_id` idempotent và TTL 10 phút → nếu giữ thành công thì tạo Booking PENDING → nếu tạo Booking thất bại thì gọi release hold (compensation). Court Service là nguồn sự thật về slot availability. Khi Payment confirmed, Booking Service yêu cầu Court Service xác nhận slot hold thành reserved; nếu hết hạn/không còn hợp lệ, không được báo Booking CONFIRMED. Các lệnh hold/confirm/release phải idempotent và được kiểm thử concurrent requests, timeout và retry. Không thực hiện distributed SQL transaction xuyên DB.

### 5.4. Payment consistency — thay đổi bắt buộc

Payment Service quản lý payment attempts, trạng thái provider và idempotency key. Mock Provider là mô phỏng, không phải cổng thanh toán thật. Khi Mock SUCCESS, Payment Service yêu cầu Booking Service confirm qua **internal REST API**; nếu Booking Service tạm thời lỗi, ghi nhận trạng thái đang đồng bộ, retry có giới hạn hoặc manual reconciliation. Không trả Booking `CONFIRMED` trước khi Booking Service thực sự xác nhận. Cần quy tắc rõ khi Booking đã `EXPIRED`: không confirm, ghi trạng thái lỗi/needs-reconciliation; không giả vờ đã hoàn tiền.

Nếu bổ sung VNPAY Sandbox, thêm provider adapter và callback verification; không thay Booking API hay tự động coi redirect của client là bằng chứng thanh toán.

## 6. API Contract và tích hợp

### 6.1. Public API qua Gateway

Giữ prefix `/api/v1`; JSON `snake_case`; ID integer; tiền integer VND; date `YYYY-MM-DD`; time `HH:mm`; timestamps ISO 8601 có timezone. JWT Bearer; mã lỗi 400/401/403/404/409/422/503 hợp lý. Swagger `/docs` tại từng service; Gateway có thể chỉ làm proxy và không cần tổng hợp OpenAPI ngay.

| Endpoint (sau `/api/v1`) | Service | Consumer |
|---|---|---|
| `POST /auth/register`, `POST /auth/login`, `GET /users/me` | User | Android, Web |
| `GET /sports`, `GET /venues`, `GET /venues/{id}` | Court | Android |
| `GET /venues/{id}/courts`, `GET /courts/{id}/slots?date=` | Court | Android |
| `GET/POST /owner/venues`, `/owner/courts`, `/owner/slots` | Court | Owner Web |
| `POST /bookings`, `GET /bookings`, `GET /bookings/{id}` | Booking | Android |
| `POST /bookings/{id}/cancel` | Booking | Android |
| `POST /bookings/{id}/payments/mock`, `GET /bookings/{id}/payments` | Payment (Gateway route) | Android |
| `GET /owner/bookings`, `POST /owner/bookings/{id}/complete` | Booking | Owner Web |
| `POST /owner/checkins` | Booking | Owner Web webcam |
| `POST /bookings/{id}/reviews` | Booking | Android |
| `GET /admin/...` | User/Court/Booking/Payment theo dữ liệu sở hữu | Admin Web |

**Admin Dashboard** cần dữ liệu tổng hợp: Gateway không tự truy cập DB; Admin Web có thể gọi nhiều endpoint theo service qua Gateway. Chưa cần xây dựng một service Admin thứ năm.

### 6.2. Internal REST API — bắt buộc chốt trước khi code

| Producer | Consumer | Hợp đồng đề xuất |
|---|---|---|
| User | Booking/Court/Payment | JWT verification theo cùng signing config; endpoint tra cứu user/role khi cần |
| Court | Booking | `POST /internal/slots/{id}/hold`, `POST /internal/holds/{hold_id}/confirm`, `POST /internal/holds/{hold_id}/release`, `GET /internal/slots/{id}` |
| Booking | Payment | `POST /internal/bookings/{id}/confirm-payment`, idempotency key, trạng thái booking |
| Booking | Court | `GET /internal/venues/{id}/ownership` hoặc endpoint kiểm tra Owner scope |
| Booking | User | Xác thực/tra cứu user ID khi cần, không đọc `user_db` trực tiếp |

**Lưu ý:** Đây là API contract **đề xuất để nhóm phê duyệt**, chưa phải endpoint đã triển khai. Internal API phải có xác thực service-to-service (ví dụ internal API key trong `.env`, chỉ dùng trong local/dev và không để lộ ở client); không coi `/internal` là bảo mật chỉ nhờ tên path. Client không được gọi internal API. Mỗi call có timeout, error handling và retry chỉ khi an toàn/idempotent.

### 6.3. QR webcam contract

1. Android nhận QR token sau `CONFIRMED` và hiển thị bằng ZXing.
2. Owner Web dùng `html5-qrcode` quét qua webcam laptop, xin quyền camera; demo trên `localhost` hoặc HTTPS.
3. Web gửi `POST /api/v1/owner/checkins` với `{"qr_token":"..."}` và JWT Owner.
4. Booking Service kiểm tra JWT, token, booking status, ownership (qua Court API), duplicate check-in; ghi `checkins` + update booking trong một transaction.
5. Web hiển thị thành công/thất bại theo response, không tự đổi Booking status.

### 6.4. Fixture và integration

- `docs/fixtures/`: auth, sports/venues/courts/slots, booking, payment, QR check-in mẫu theo contract.
- S1 dùng fixture Court khi chưa có Court API; S2 dùng fixture Auth/Booking khi chưa có User/Booking API.
- Integration **ít nhất hai lần/tuần**. Chỉ coi hoàn thành khi Android hoặc Web gọi được Gateway → service thật và dữ liệu được ghi/đọc đúng database sở hữu.

## 7. Kế hoạch 5 iteration

> Mốc tuần là thứ tự triển khai, điều chỉnh theo deadline thực tế. **Definition of Done:** code chạy, test pass, Swagger/response mẫu, PR reviewed/merged, diagram/report cập nhật tương ứng.

### ITERATION 1 — Migration foundation + Auth/Catalog skeleton

| S1 | S2 | Bàn giao chung |
|---|---|---|
| Android skeleton + Login UI; User Service register/login/JWT; Use Case, Booking Activity | **Migration V4→V5**, Gateway, 4 service skeleton, MySQL 4 DB, Court Service foundation, ERD/Architecture V5 | 5 ứng dụng FastAPI (gateway + 4 service) có health endpoint; 4 DB connect; Android gọi Gateway; Auth API + Court API tối thiểu |

**Thứ tự bắt buộc:** S2 merge migration skeleton trước; S1 có thể làm Android UI/diagram song song nhưng không triển khai Booking Service theo kiến trúc V4.

### ITERATION 2 — Catalog/Schedule + Pending Booking

| S1 | S2 | Bàn giao chung |
|---|---|---|
| Android Search/Venue/Slot; Booking Service create pending/history; Booking Sequence; concurrency tests | Court Service Sport/Venue/Court/Slot CRUD + availability/atomic hold API; Owner Web Venue/Court/Slot | Owner tạo slot → Android thấy slot → Booking PENDING; concurrent requests không đặt trùng |

### ITERATION 3 — Mock Payment + Booking History

| S1 | S2 | Bàn giao chung |
|---|---|---|
| Payment Service Mock success/failure, idempotency; Booking confirm/cancel/expiry; Android history/detail/payment; Payment Sequence, Booking State | Owner booking list/dashboard; Court hold confirm/release + timeout tests; Web tích hợp Auth | Android Mock SUCCESS → Booking CONFIRMED; Owner thấy Booking; FAILED/expired/retry đúng |

### ITERATION 4 — QR webcam + Review + Admin

| S1 | S2 | Bàn giao chung |
|---|---|---|
| QR token, Android QR display, Booking Check-in/Complete API, Review API/UI | `html5-qrcode` Owner scanner bằng webcam laptop, Admin Web, QR Sequence; cross-service authorization tests | Android QR → Owner webcam → CHECKED_IN → COMPLETED → Review; invalid/duplicate/other-owner bị chặn |

### ITERATION 5 — Stabilization, reports, SOA readiness

| S1 | S2 | Bàn giao chung |
|---|---|---|
| Android regression, screenshots, User/Booking/Payment tests, report phần S1 | Web/Gateway/Court/QR tests, clean DB setup, README, tổng hợp report | E2E demo từ database sạch, test service unavailable/timeout, source/diagram/report khớp nhau |

**Customer Web SOA chỉ làm sau khi Mobile E2E ổn định**; nếu còn thời gian, Customer Web chỉ cần tái sử dụng API hiện có. **Payment Gateway tùy chọn chỉ sau tất cả phần bắt buộc.**

## 8. Git và kế hoạch migration từ V4

### 8.1. Branch strategy

- `main`: bản demo/nộp ổn định.
- `develop`: tích hợp các PR đã chạy và review.
- `feature/s2-w1-management-web`, `feature/s2-w1-mysql`, `feature/s2-w1-db-architecture`: **branch cũ cần audit và merge phần hợp lệ trước khi migration**.
- `feature/s2-microservices-foundation`: branch mới từ `develop` đã cập nhật; S2 sở hữu.
- `feature/s1-user-auth-android`: S1 tạo sau khi foundation skeleton đã merge.
- Tiếp theo mỗi service/feature dùng branch ngắn: `feature/s2-court-catalog`, `feature/s1-booking`, `feature/s1-payment`, `feature/s2-qr-web`.

### 8.2. Quy trình an toàn cho trạng thái hiện tại

**Không chạy `git init` hoặc `git remote add` lại. Không xóa branch cũ, không force-push.**

```bash
# BƯỚC 1: Kiểm tra trên branch hiện tại, chưa đổi branch
git status -sb
git branch -vv
git log --oneline --decorate --graph --all -20
git remote -v

# BƯỚC 2: Nếu có uncommitted changes, commit trên đúng feature branch
# (hoặc git stash push -u -m "backup before microservices migration")

# BƯỚC 3: Kiểm tra diff từng branch với develop
git log --oneline develop..feature/s2-w1-management-web
git diff --stat develop...feature/s2-w1-management-web
git log --oneline develop..feature/s2-w1-mysql
git diff --stat develop...feature/s2-w1-mysql
git log --oneline develop..feature/s2-w1-db-architecture
git diff --stat develop...feature/s2-w1-db-architecture
```

**Chỉ sau khi kiểm tra:** mở PR riêng từ các feature cũ vào `develop`, merge lần lượt và kiểm thử sau mỗi PR. Nếu branch đã merge, không merge lại. Nếu các branch có conflict hoặc chứa commit không liên quan, chọn cherry-pick/PR chọn lọc sau khi review; không `git merge` mù.

```bash
# BƯỚC 4: Khi develop đã chứa toàn bộ code cần giữ
git switch develop
git pull --ff-only origin develop
git switch -c feature/s2-microservices-foundation
# Thêm V5, skeleton, migration... rồi test và tạo PR vào develop
```

### 8.3. File migration map

| V4 | V5 | Hành động |
|---|---|---|
| `management-web/` | Giữ nguyên | Bảo toàn HTML/CSS/JS; đổi API client khi endpoint sẵn sàng |
| `backend/app/main.py` | `backend/gateway/main.py` + `services/*/app/main.py` | Không copy logic monolith vào gateway; tạo app riêng |
| `backend/app/core/{config,database}.py` | `services/*/app/core/` | Tái sử dụng pattern, mỗi service DB URL riêng |
| `backend/alembic/` | `services/*/alembic/` | Migration độc lập, không áp dụng monolith migration lên 4 DB |
| `backend/seed_data.py` | `backend/scripts/` hoặc seed theo service | Seed qua DB sở hữu, không dùng cross-DB FK |
| `backend/requirements.txt` | requirements theo service hoặc shared constraints | Giữ version đang chạy nếu tương thích |
| `docs/diagrams/erd/` | Giữ file gốc, tạo phiên bản V5 | 4 vùng database; chỉnh tham chiếu logic |
| `docs/diagrams/architecture/` | `system_architecture.drawio/.png` | Vẽ Gateway, 4 services, 4 DB, 2 frontend |
| `docs/API_CONTRACT.md` | Giữ path public, thêm internal API | Cập nhật owner/JSON/errors/idempotency |
| `SPORTS_COURT_BOOKING_PROJECT_PLAN_V4.md` | `..._V5.md` | Giữ V4 làm lịch sử; V5 là tài liệu active |

### 8.4. PR acceptance checklist

- [ ] Chỉ sửa file thuộc ownership hoặc có reviewer đồng ý.
- [ ] Mô tả rõ API/schema/contract thay đổi.
- [ ] Chạy được local; có test pass và screenshot/log cần thiết.
- [ ] Không commit `.env`, secret, database dump có dữ liệu cá nhân.
- [ ] PR vào `develop`, review chéo, không force-push.
- [ ] Merge xong người còn lại `git switch develop && git pull --ff-only origin develop`.

## 9. Diagram và báo cáo

| Diagram | Owner | V5 cần thể hiện |
|---|---|---|
| System Use Case | S1 | User Android, Owner/Admin Web; chức năng đúng quyền |
| ERD / Data Ownership | S2 | 4 database, 9 bảng nghiệp vụ; nếu có bảng kỹ thuật `slot_holds` phải bổ sung; không FK xuyên DB |
| Microservices Architecture | S2 | Android + Owner/Admin Web → Gateway → 4 FastAPI services → 4 DB; REST nội bộ |
| Booking Activity | S1 | Hold slot, Pending, expiry, Mock Payment, conflict |
| Booking Sequence | S1 | Android → Gateway → Booking → Court (hold/confirm/release) → DB riêng; timeout/error branch |
| Payment Sequence | S1 | Payment Service → Booking Service, idempotency, reconciliation/error |
| Booking State | S1 | PENDING/CONFIRMED/CHECKED_IN/COMPLETED/CANCELLED/EXPIRED |
| QR Check-in Sequence | S2 | Owner Web webcam → Gateway → Booking Service → Court ownership check → Booking DB |

Lưu **source `.puml/.dbml/.drawio` + PNG/SVG**; không ghi diagram phản ánh tính năng đã hoàn thành nếu code chưa có. ERD V4 không còn là schema vật lý của V5 nếu chia DB.

**Mobile Final Report:** Chapter 1 Introduction; Chapter 2 Requirements; Chapter 3 Architecture/ERD/UML/UI; Chapter 4 Implementation; Chapter 5 Testing; Chapter 6 Conclusion/Future Work; References/Appendices. S1 viết Android/User/Booking/Payment/Review; S2 viết Court/Web/Gateway/DB/QR webcam; mỗi người giữ draft riêng, S2 tổng hợp, S1 review. **SOA Report** (sau) nhấn mạnh service boundary, REST communication, DB-per-service, failure handling; không sao chép nguyên report Mobile.

## 10. Kiểm thử và nghiệm thu

### 10.1. Test cases tối thiểu

| ID | Scenario | Expected | Owner |
|---|---|---|---|
| T01 | Register/login; role validation | JWT hợp lệ, quyền đúng | S1 |
| T02 | Owner tạo Venue/Court/Slot | Court DB đúng; Android thấy dữ liệu | S2 |
| T03 | Hai user đồng thời giữ cùng slot | Chỉ một hold hợp lệ | S1+S2 |
| T04 | Pending quá 10 phút | EXPIRED; hold được giải phóng an toàn | S1+S2 |
| T05 | Booking create thất bại sau hold | Hold được release/reconcile | S1+S2 |
| T06 | Mock SUCCESS | Payment ghi nhận; Booking CONFIRMED sau xác nhận thật | S1 |
| T07 | Mock FAILED/retry/duplicate | Không confirm trùng | S1 |
| T08 | Booking Service tạm ngắt khi Payment SUCCESS | Không báo confirmed sai; có recovery/retry | S1 |
| T09 | Android hiển thị QR Confirmed | QR token hợp lệ | S1 |
| T10 | Owner Web webcam quét QR | CHECKED_IN đúng, chỉ một lần | S2+S1 |
| T11 | Invalid/duplicate/other-owner QR | Từ chối với status đúng | S1+S2 |
| T12 | Complete rồi Review | Chỉ review COMPLETED, một review | S1 |
| T13 | User gọi Admin/Owner API | 403 | S1+S2 |
| T14 | Court Service timeout/unavailable | Booking trả lỗi có kiểm soát, không tạo booking sai | S1+S2 |
| T15 | Android E2E qua Gateway | Search→Booking→Payment→QR→Check-in→Review | Cả hai |
| T16 | Setup từ 4 DB sạch | Migration + seed + run services thành công | Cả hai |

### 10.2. Acceptance criteria

- [ ] Android Java/XML build và gọi Gateway API thật.
- [ ] Owner/Admin Web chạy trên localhost; Owner webcam quét được QR.
- [ ] Gateway + 4 service khởi động độc lập; mỗi service chỉ truy cập DB của mình.
- [ ] JWT/RBAC đúng; Owner scope được kiểm tra Backend.
- [ ] Không double booking; expiry/retry/payment/check-in lặp xử lý đúng.
- [ ] Có test cả service unavailable và timeout.
- [ ] Có `README.md`, `.env.example`, seed/migrations, demo accounts, screenshots, test evidence.
- [ ] Diagrams/report mô tả **đúng code thực tế**, không mô tả VNPAY nếu chưa tích hợp.
- [ ] `main` ổn định, `develop` tích hợp; cả hai tự giải thích được code và service communication.

## 11. Quyết định cần giữ thống nhất

1. **Mobile trước; Customer Web SOA sau.**
2. **Một Backend Microservices dùng chung** cho hai môn, không duy trì monolith song song.
3. 4 services + Gateway mỏng; không thêm service chỉ để chia việc.
4. 4 logical databases trên cùng MySQL Server; không truy cập DB của service khác.
5. S1 sở hữu Booking State/QR backend; S2 sở hữu QR webcam frontend.
6. Court Service sở hữu atomic slot hold; Booking Service điều phối booking và bù lỗi.
7. Mock Payment trước; gateway provider tùy chọn sau khi Mobile ổn định.
8. JWT/RBAC và internal service auth bắt buộc, không tin frontend.
9. Contract-first, PR review, integration hai lần mỗi tuần.
10. **Trước khi code Booking:** chốt chính xác cách lưu slot hold, confirm/release, idempotency và expiry; không dùng V4 cross-DB transaction.

---

**Việc đầu tiên sau khi nhận V5:** Audit các branch hiện tại → bảo toàn/merge code đã làm → tạo `feature/s2-microservices-foundation` từ `develop` cập nhật → chạy Gateway + 4 service skeleton + 4 DB health → PR → S1 bắt đầu Auth/Android.

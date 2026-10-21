# SPORTS COURT BOOKING SYSTEM — MASTER PROJECT PLAN

> **Tài liệu làm việc của repository** · Phiên bản 1.0 · Kế hoạch 5 tuần / 2 thành viên  
> **Đọc theo thứ tự:** §1 Phạm vi → §2 Kiến trúc → §3 Phân công → §4 Hợp đồng tích hợp → §5 Kế hoạch từng tuần → §6 Report → §7 Git → §8 Nghiệm thu.  
> **Nguồn đánh giá:** `Rubric_Assessment_Final Project.pdf` (môn Phát triển ứng dụng di động, 3 trang). Các UML/ERD là **đề xuất của nhóm**, không phải yêu cầu được rubric nêu đích danh.

## MỤC LỤC

> Các liên kết dùng ID cố định, không phụ thuộc dấu tiếng Việt hoặc cách GitHub tạo slug.

- [1. Mục tiêu, phạm vi, ưu tiên](#plan-01)
  - [1.1. Rubric — tiêu chí quyết định ưu tiên](#plan-02)
- [2. Kiến trúc và công nghệ đã chốt](#plan-03)
- [3. Phân công và quyền sở hữu (file ownership)](#plan-04)
  - [3.1. Cấu trúc repository chuẩn](#plan-05)
- [4. Hợp đồng tích hợp (Contract-First) — chốt trước khi code](#plan-06)
  - [4.1. Định nghĩa chung](#plan-07)
  - [4.2. DB schema tối thiểu và owner](#plan-08)
  - [4.3. Quy ước API](#plan-09)
  - [4.4. Cách code song song mà không chờ nhau](#plan-10)
- [5. Kế hoạch 5 iterations — nhiệm vụ, file, output, checklist](#plan-11)
  - [ITERATION 1 / WEEK 1 — Requirements, architecture, foundation](#plan-12)
  - [ITERATION 2 / WEEK 2 — Search, Venue, Court, Schedule, Pending Booking](#plan-13)
  - [ITERATION 3 / WEEK 3 — Booking history, Mock Payment, Owner booking](#plan-14)
  - [ITERATION 4 / WEEK 4 — QR Check-in, Review, Admin, polish](#plan-15)
  - [ITERATION 5 / WEEK 5 — Stabilize, report, submission](#plan-16)
- [6. Diagrams — bắt buộc theo kế hoạch nhóm, lưu ý từng hình](#plan-17)
  - [6.1. Bảng giao diagram theo từng tuần — có file, reviewer và liên kết code](#plan-18)
  - [6.2. Diagram nào nối với thành phần nào?](#plan-19)
- [6A. HƯỚNG DẪN KẾT NỐI 2 NGƯỜI (INTEGRATION PLAYBOOK)](#plan-20)
  - [A. Sơ đồ dữ liệu chạy xuyên hệ thống](#plan-21)
  - [B. 7 hợp đồng giao tiếp phải chốt trong W1](#plan-22)
  - [C. Cách dùng service chung mà không sửa file của nhau](#plan-23)
  - [D. Lịch ghép và điều kiện bàn giao](#plan-24)
  - [E. Branch cụ thể để diagram, contract và tích hợp không conflict](#plan-25)
  - [F. Checklist kết nối cho từng tuần (bổ sung checklist phần 5)](#plan-26)
- [7. Report — cấu trúc, người viết, đầu ra theo tuần](#plan-27)
  - [7.1. Cấu trúc Final Report đề xuất](#plan-28)
  - [7.2. Tiến độ Report theo tuần](#plan-29)
- [8. Git — branch, workflow và lệnh thực hiện](#plan-30)
  - [8.1. Branch chuẩn](#plan-31)
  - [8.2. Thiết lập lần đầu (một người thực hiện)](#plan-32)
  - [8.3. Mỗi người bắt đầu feature](#plan-33)
  - [8.4. Lịch phối hợp tối thiểu](#plan-34)
  - [8.5. Issue template (copy cho mỗi task)](#plan-35)
- [9. Test plan — phải có Expected + Actual + Evidence](#plan-36)
- [10. Checklist nghiệm thu cuối kỳ](#plan-37)
  - [Source & functionality](#plan-38)
  - [Diagrams & Report](#plan-39)
  - [Submission & defense](#plan-40)
- [11. Những điểm phải thống nhất trước khi mở PR đầu tiên](#plan-41)


---

<a id="plan-01"></a>

## 1. Mục tiêu, phạm vi, ưu tiên

**Đầu ra nộp:** source code chạy được + Final Report có nội dung phân tích, thiết kế, triển khai, kiểm thử và bằng chứng thực tế. **Đề tài:** ứng dụng đặt sân thể thao.

| Actor | Nền tảng | Luồng nghiệp vụ chính |
|---|---|---|
| Customer/User | Android Java + XML | Đăng ký/đăng nhập → tìm sân → xem sân → chọn lịch → đặt sân → Mock Payment → xem QR → check-in → đánh giá |
| Court Owner | Web quản lý | Đăng nhập → quản lý địa điểm/sân/lịch → xem đơn → quét QR → check-in → hoàn thành |
| Admin | Cùng Web, phân quyền | Dashboard → quản lý tài khoản, chủ sân, môn thể thao, địa điểm, sân, đơn, thanh toán, đánh giá |

**Bắt buộc:** Android User, Owner/Admin Web, FastAPI REST, MySQL, JWT/RBAC, Booking không trùng lịch, Mock Payment có success/failure, QR check-in do server xác thực, lịch sử đặt sân, Review sau khi hoàn thành, test + report. **Tùy chọn:** VNPAY Sandbox nếu toàn bộ phần bắt buộc đã ổn định; không triển khai thanh toán tiền thật/refund. Không thêm microservices, chat, bản đồ/GPS, email, analytics nâng cao.

<a id="plan-02"></a>

### 1.1. Rubric — tiêu chí quyết định ưu tiên

| Tiêu chí theo rubric | Điểm | Hành động để đáp ứng |
|---|---:|---|
| Hình thức báo cáo | 1.5 | Bố cục 0.5; mục lục/danh mục hình-bảng, nguồn/trích dẫn 0.5; chính tả 0.5 |
| Nội dung báo cáo | 1.5 | Đúng đề tài, có trọng tâm, mạch lạc, không sao chép/viết hộ, không chỉ dán ảnh |
| Ứng dụng minh họa — UI | 2.0 | Android/Web đẹp, thống nhất, dễ dùng, bố cục và màu sắc hài hòa |
| Ứng dụng minh họa — chức năng | 5.0 | Hoàn thành chức năng đã cam kết, ít lỗi, chạy ổn định, dễ thao tác |
| Vấn đáp | Có thể **trừ 20–100% tổng điểm** | Mỗi thành viên phải hiểu và giải thích được phần mình, hiểu luồng tích hợp; phân công cân bằng |

**Chú ý:** Rubric cảnh báo việc báo cáo bị phát hiện viết hộ/không thực sự tự thực hiện, sao chép, nội dung không liên quan hoặc phân công lệch có thể bị trừ điểm rất nặng. Mỗi người phải **tự code, tự viết và kiểm tra lại nội dung mình phụ trách**, dùng tài liệu này như checklist chứ không nộp nguyên kế hoạch làm báo cáo kết quả.

**Ưu tiên thời gian:** (1) chức năng và ổn định → (2) UI → (3) báo cáo đủ bằng chứng và chất lượng → (4) diagram hỗ trợ giải thích → (5) VNPAY tùy chọn. **Không** để việc vẽ UML quá nhiều làm trễ tính năng chính.

<a id="plan-03"></a>

## 2. Kiến trúc và công nghệ đã chốt

| Layer | Công nghệ | Kiểu tổ chức |
|---|---|---|
| Android User | Android Studio, Java, XML, Retrofit/Gson, ZXing | **MVVM đơn giản**: View → ViewModel → Repository → Retrofit |
| Management Web | HTML/CSS/JavaScript, Bootstrap, `fetch`, `html5-qrcode` | Page + JS Module + API Client; Owner/Admin cùng web, khác quyền |
| Backend | FastAPI, SQLAlchemy, Pydantic, Alembic, JWT | **Modular Monolith**: Router → Service → Repository/ORM → MySQL |
| Database | MySQL | **Một DB**, migration theo Alembic |
| Payment | Mock Payment; VNPAY Sandbox tùy chọn | Payment Service tách Booking Service |
| Tài liệu | Markdown, PlantUML, dbdiagram.io, draw.io, Word | Lưu **source diagram** và PNG; report tổng hợp theo chương |
| Test | pytest, Swagger/OpenAPI, kiểm thử Android/Web thủ công | Unit/API/Integration/E2E |

```
Android User (S1) ── REST/JSON ──┐
                                 ├── FastAPI (Modular Monolith) ── SQLAlchemy ── MySQL
Owner/Admin Web (S2) ─ REST/JSON ┘              │
                                               └── Mock Payment
                                                    └── VNPAY Sandbox [OPTIONAL]
```

**Không dùng Microservices**: 2 người/5 tuần không cần service discovery, nhiều DB, gateway, message broker. Android/Web không kết nối DB trực tiếp. Backend luôn kiểm tra quyền và trạng thái.

<a id="plan-04"></a>

## 3. Phân công và quyền sở hữu (file ownership)

| Hạng mục | Student 1 (S1) | Student 2 (S2) |
|---|---|---|
| Frontend | **Toàn bộ Android User App** | **Owner + Admin Web** |
| Backend chính | Auth, User, Booking, Payment, Review | Public Catalog, Venue, Court, Schedule, Check-in, Admin |
| Database models | `users`, `bookings`, `payments`, `reviews` | `sports`, `venues`, `courts`, `time_slots`, `checkins` |
| API do mình tạo | Auth, User, Booking, Payment, Review, Owner Booking list/complete | Sport, Venue, Court, Schedule, Check-in, Admin |
| Testing | Android, Auth, Booking, Payment, Review, chống double booking | Web, Venue/Court/Schedule, Check-in, Owner/Admin authorization |
| Diagram | System Use Case, Booking Activity, Booking Sequence, Payment Sequence, Booking State | ERD, System Architecture, QR Check-in Sequence |
| Report | Intro, User requirements, Android/Booking/Payment/Review, test tương ứng | Owner/Admin requirements, ERD/Architecture, Web/Schedule/Check-in/Admin, test tương ứng |
| Việc chung | Review ERD/API, test end-to-end, rà soát Report, demo/vấn đáp | Review ERD/API, test end-to-end, tổng hợp Report, demo/vấn đáp |

**Cân bằng thực tế:** S1 có nhiều Android screens và logic Booking/Payment; S2 có Web hai role, Catalog/Schedule/Admin/Check-in. Cuối mỗi tuần kiểm tra số giờ và đầu ra, nếu lệch quá nhiều thì điều chỉnh phần UI/test/report **không đổi owner file đang làm dở**.

<a id="plan-05"></a>

### 3.1. Cấu trúc repository chuẩn

```text
sports-court-booking/
├── README.md                                  [CẢ HAI, S2 merge]
├── .gitignore                                 [S2]
├── android-user/                              [S1]
│   ├── README.md
│   └── app/src/main/
│       ├── java/com/example/sportsbooking/
│       │   ├── ui/{auth,home,search,venue,booking,payment,review,profile}/
│       │   ├── data/{api,model,repository}/
│       │   └── utils/
│       └── res/{layout,drawable,values}/
├── management-web/                            [S2]
│   ├── index.html
│   ├── pages/owner/{dashboard,venues,courts,schedule,bookings,checkin}.html
│   ├── pages/admin/{dashboard,management}.html
│   ├── js/{api,common,owner,admin}/
│   └── css/
├── backend/
│   ├── requirements.txt                       [S2]
│   ├── .env.example                           [S2]
│   ├── seed_data.py                           [S2]
│   ├── alembic/versions/                      [TABLE OWNER; REVIEW BẮT BUỘC]
│   ├── app/
│   │   ├── main.py                            [S2; REVIEW BẮT BUỘC]
│   │   ├── core/
│   │   │   ├── {config,database}.py            [S2]
│   │   │   └── {security,dependencies}.py      [S1]
│   │   ├── models/
│   │   │   ├── {user,booking,payment,review}.py [S1]
│   │   │   └── {sport,venue,court,time_slot,checkin}.py [S2]
│   │   ├── schemas/
│   │   │   ├── {auth,booking,payment,review}.py [S1]
│   │   │   └── {catalog,schedule,checkin,admin}.py [S2]
│   │   ├── routers/
│   │   │   ├── {auth,users,bookings,payments,reviews}.py [S1]
│   │   │   └── {catalog,owner,schedule,checkin,admin}.py [S2]
│   │   ├── services/
│   │   │   ├── {auth,booking,payment,review}_service.py [S1]
│   │   │   └── {catalog,schedule,checkin,admin}_service.py [S2]
│   │   └── repositories/
│   │       ├── booking_repository.py          [S1]
│   │       └── schedule_repository.py         [S2]
│   └── tests/
│       ├── {test_auth,test_booking,test_payment,test_review}.py [S1]
│       └── {test_catalog,test_schedule,test_checkin,test_admin}.py [S2]
├── docs/
│   ├── SYSTEM_REQUIREMENTS.md                 [S1; S2 review]
│   ├── BUSINESS_RULES.md                      [CẢ HAI]
│   ├── API_CONTRACT.md                        [CẢ HAI; chốt Week 1]
│   ├── DB_SCHEMA.md                           [S2; S1 review]
│   ├── diagrams/
│   │   ├── usecase/system_usecase.puml        [S1]
│   │   ├── erd/database_erd.dbml              [S2]
│   │   ├── architecture/system_architecture.drawio [S2]
│   │   ├── activity/booking_activity.puml     [S1]
│   │   ├── sequence/booking_sequence.puml     [S1]
│   │   ├── sequence/payment_sequence.puml     [S1]
│   │   ├── sequence/qr_checkin_sequence.puml  [S2]
│   │   └── state/booking_state.puml           [S1]
│   ├── test-cases/{user-tests,management-tests}.md [S1/S2]
│   └── screenshots/{android,web}/             [S1/S2]
└── report/
    ├── drafts/                               [MỖI NGƯỜI FILE RIÊNG]
    ├── figures/                              [S1/S2]
    └── Final_Report.docx                     [S2 tổng hợp; S1 review]
```

**Quy tắc:** không commit `.env`, mật khẩu, API key, `venv/`, `.gradle/`, file build; chỉ commit `.env.example`. `main.py`, Alembic, `API_CONTRACT.md`, `DB_SCHEMA.md` và thay đổi schema liên module bắt buộc Pull Request review.

<a id="plan-06"></a>

## 4. Hợp đồng tích hợp (Contract-First) — chốt trước khi code

<a id="plan-07"></a>

### 4.1. Định nghĩa chung

- **Sport:** môn thể thao (badminton, football...). **Location:** khu vực tìm kiếm (ví dụ Quận 7), có thể là trường `location_text`/địa chỉ của Venue; **không bắt buộc tạo bảng `locations`**.
- **Venue:** cơ sở thể thao do Owner sở hữu. **Court:** sân con thuộc Venue. **Time Slot:** một khung ngày-giờ của Court, giá tại thời điểm đặt phải được snapshot trong Booking.
- **Booking:** đặt một Time Slot. **Payment:** một lần thử thanh toán; một Booking có thể có nhiều Payment attempts.
- **Check-in:** chỉ một lần thành công cho một Booking; QR là token ngẫu nhiên không đoán được, không dùng booking ID làm mã xác thực.
- **Review:** tối đa một Review cho một Booking đã `COMPLETED`.

<a id="plan-08"></a>

### 4.2. DB schema tối thiểu và owner

| Table (owner) | Trường cốt lõi | Ràng buộc quan trọng |
|---|---|---|
| `users` (S1) | `id, full_name, email, password_hash, role, status` | `email` UNIQUE; role USER/OWNER/ADMIN |
| `sports` (S2) | `id, name, status` | `name` UNIQUE |
| `venues` (S2) | `id, owner_id, name, address, location_text, description, status` | FK owner→users; Owner chỉ sửa Venue của mình |
| `courts` (S2) | `id, venue_id, sport_id, name, status` | FK Venue/Sport |
| `time_slots` (S2) | `id, court_id, slot_date, start_time, end_time, price, status` | UNIQUE `(court_id, slot_date, start_time, end_time)`; `start_time < end_time`; không tạo các slot chồng lấn cùng court |
| `bookings` (S1) | `id, user_id, time_slot_id, total_amount, status, expires_at, qr_token, created_at` | FK User/Slot; token UNIQUE, nullable trước khi confirmed |
| `payments` (S1) | `id, booking_id, provider, transaction_id, amount, status, paid_at, created_at` | FK Booking; transaction id UNIQUE khi có; nhiều attempts |
| `checkins` (S2) | `id, booking_id, checked_in_by, checked_in_at` | `booking_id` UNIQUE; FK Owner user |
| `reviews` (S1) | `id, booking_id, user_id, rating, comment, created_at` | `booking_id` UNIQUE; rating 1–5 |

**Quan hệ:** Owner User 1–N Venue; Venue 1–N Court; Sport 1–N Court; Court 1–N TimeSlot; TimeSlot 1–N Booking **trong lịch sử**; User 1–N Booking; Booking 1–N Payment; Booking 1–0..1 Checkin; Booking 1–0..1 Review.

**Quy tắc booking cạnh tranh:** `PENDING` chưa hết hạn và `CONFIRMED/CHECKED_IN` giữ slot; `CANCELLED/EXPIRED` không giữ. Đặt mới cần transaction với khóa trên dòng `time_slots` (`SELECT ... FOR UPDATE`) rồi kiểm tra Booking hiệu lực và insert; thanh toán phải recheck hạn và trạng thái. Đây là thiết kế logic cần test đồng thời, không chỉ check `available=true` từ Android. Nếu Booking `COMPLETED` thì slot lịch sử vẫn đã được sử dụng và không thể đặt lại cho thời điểm đã qua. S2 không được xóa/sửa slot đã có Booking hiệu lực.

**Trạng thái:** Booking `PENDING → CONFIRMED → CHECKED_IN → COMPLETED`; `PENDING → CANCELLED/EXPIRED`; `CONFIRMED → CANCELLED` **chỉ nếu nhóm có chính sách hủy đã định nghĩa**. Payment `PENDING/PAID/FAILED/CANCELLED`. Mock Success phải cập nhật Payment + Booking trong **một transaction**; retry không xác nhận hai lần. Có `expires_at` và logic hết hạn được gọi trước khi tìm slot/trước khi tạo booking; có thể bổ sung scheduled cleanup sau, không cần Celery.

<a id="plan-09"></a>

### 4.3. Quy ước API

- Base path: `/api/v1`; JSON `snake_case`; ID integer; giá trị tiền **integer VND**; ngày `YYYY-MM-DD`; giờ `HH:mm`; timestamp ISO 8601 có timezone (DB lưu UTC).
- JWT `Authorization: Bearer <token>`; login chung **do S1 viết**, cả Android và Web sử dụng; S2 không viết API login thứ hai.
- HTTP 200/201 thành công, 400 request sai, 401 chưa login, 403 không đủ quyền, 404 không tồn tại, 409 conflict, 422 validation error.
- Swagger `/docs`; với mỗi endpoint phải có request/response/error mẫu trong `docs/API_CONTRACT.md`.

| Method + endpoint | Owner | Consumer / mục đích |
|---|---|---|
| `POST /auth/register`, `POST /auth/login` | S1 | Android/Web login; register mặc định USER |
| `GET /users/me` | S1 | Android/Web profile + role |
| `GET /sports`, `GET /venues? sport_id=&location=`, `GET /venues/{id}` | S2 | Android search/catalog |
| `GET /venues/{id}/courts`, `GET /courts/{id}/slots?date=` | S2 | Android chọn Court/Slot |
| `POST /bookings`, `GET /bookings`, `GET /bookings/{id}` | S1 | Android booking/history/detail |
| `POST /bookings/{id}/cancel` | S1 | Android hủy đúng điều kiện |
| `POST /bookings/{id}/payments/mock`, `GET /bookings/{id}/payments` | S1 | Android Mock Payment/history |
| `POST /bookings/{id}/reviews` | S1 | Android review sau Completed |
| `GET /owner/bookings`, `POST /owner/bookings/{id}/complete` | S1 | Owner Web quản lý booking; kiểm tra owner scope |
| `GET/POST /owner/venues`, `PUT/DELETE /owner/venues/{id}` | S2 | Owner Web |
| `GET/POST /owner/courts`, `PUT/DELETE /owner/courts/{id}` | S2 | Owner Web |
| `GET/POST /owner/slots`, `PUT/DELETE /owner/slots/{id}` | S2 | Owner Web |
| `POST /owner/checkins` | S2 | Owner Web QR scanner |
| `GET /admin/dashboard`, `GET/PATCH /admin/users`, `GET/PATCH /admin/venues` | S2 | Admin Web |
| `GET/POST/PATCH /admin/sports`, `GET /admin/bookings`, `GET /admin/payments`, `GET/PATCH /admin/reviews` | S2 | Admin Web |

**API paths trong bảng nối sau `/api/v1`.** Nếu endpoint `GET/PATCH` chung, định nghĩa chính xác collection vs item (`/admin/users/{id}` cho PATCH) trong Contract trước Week 2. Không triển khai DELETE cứng với Venue/Court đã có lịch sử Booking: ưu tiên `status=INACTIVE`.

**Contract examples** (đồng bộ giữa S1/S2):

```json
// POST /api/v1/bookings
{"time_slot_id":15}
// 201
{"id":101,"time_slot_id":15,"total_amount":120000,"status":"PENDING","expires_at":"2026-11-01T10:10:00+07:00"}
```

```json
// POST /api/v1/bookings/101/payments/mock
{"result":"SUCCESS"}
// 200
{"payment_id":25,"booking_id":101,"provider":"MOCK","status":"PAID","booking_status":"CONFIRMED"}
```

```json
// POST /api/v1/owner/checkins
{"qr_token":"secure-random-token"}
// 200
{"booking_id":101,"status":"CHECKED_IN","message":"Check-in successful"}
```

**Chú ý:** ví dụ JSON có dòng comment chỉ để giải thích trong tài liệu, khi gửi HTTP chỉ gửi object JSON. Mock `result` chỉ dành cho môi trường demo; **không cho client tự xác nhận thanh toán trong gateway thật**. QR token phải được tạo/kiểm tra phía Backend; Android chỉ hiển thị token dưới dạng QR. Check-in S2 gọi hàm nghiệp vụ chuyển trạng thái do S1 cung cấp (hoặc shared interface đã review), không tự viết logic Booking State khác.

<a id="plan-10"></a>

### 4.4. Cách code song song mà không chờ nhau

| Interface | Người cung cấp | Người sử dụng | Dữ liệu giả lập trước khi ghép |
|---|---|---|---|
| JWT/Auth | S1 | Android S1 + Web S2 | Token demo / role fixture |
| Catalog/Slots | S2 | Android S1 | `fixtures/venues.json`, `slots.json` |
| Booking/Payment | S1 | Android S1 + Web S2 | `fixtures/bookings.json`, `payments.json` |
| QR token | S1 | Web scanner S2 | Token demo hợp lệ/sai |
| Check-in | S2 | Owner Web + Booking Detail | Check-in response fixture |

Tạo `docs/fixtures/` ở Week 1, JSON theo **đúng API Contract**. Không sửa field tùy tiện. Ghép thật ít nhất **2 lần/tuần** (giữa tuần và cuối tuần), tránh dồn integration vào Week 5.

<a id="plan-11"></a>

## 5. Kế hoạch 5 iterations — nhiệm vụ, file, output, checklist

> **Done** = code chạy + test có kết quả + file được commit + phần Report tương ứng đã viết + người kia review những interface dùng chung.

<a id="plan-12"></a>

### ITERATION 1 / WEEK 1 — Requirements, architecture, foundation

**Mục tiêu:** chốt nghiệp vụ, DB, API, diagram nền tảng; Android/Web/Backend khởi chạy; Auth tối thiểu.

| Người | Nhiệm vụ | File/output |
|---|---|---|
| S1 | Đặc tả User, Booking, Payment, Review; quy tắc nghiệp vụ | `docs/SYSTEM_REQUIREMENTS.md`, `docs/BUSINESS_RULES.md` |
| S1 | Use Case tổng + Booking Activity v1 | `system_usecase.puml/.png`, `booking_activity.puml/.png` |
| S1 | Android skeleton + MVVM + Retrofit + Auth screen | `android-user/app/.../ui/auth/`, `data/api/`, XML layouts |
| S1 | JWT/Auth API, User model, test login | `auth.py`, `auth_service.py`, `user.py`, `test_auth.py` |
| S2 | FastAPI, MySQL, SQLAlchemy, Alembic, CORS/config | `main.py`, `core/{config,database}.py`, `alembic/`, `requirements.txt` |
| S2 | ERD v1, Architecture v1, schema/data dictionary | `database_erd.dbml/.png`, `system_architecture.drawio/.png`, `DB_SCHEMA.md` |
| S2 | Models Catalog/Schedule + seed, Web skeleton/login UI | `models/{sport,venue,court,time_slot}.py`, `seed_data.py`, `management-web/` |
| Cả hai | Chốt API Contract + fixtures + repo/branch rules | `API_CONTRACT.md`, `docs/fixtures/`, README v1 |

**Report W1:** S1 viết Chapter 1 + Chapter 2 phần User/Booking/Payment + Use Case/Activity; S2 viết Chapter 2 phần Owner/Admin + Chapter 3 Architecture/ERD/Database v1. Viết bản nháp theo mục riêng, có nguồn, không chỉ chèn hình.

**Checklist W1**
- [ ] Requirements đủ 3 actor và các chức năng bắt buộc
- [ ] Booking/Payment/QR Business Rules được hai người duyệt
- [ ] Use Case, Activity, ERD v1, Architecture v1 có file gốc + PNG
- [ ] S1/S2 kiểm tra PK/FK và trạng thái Booking cùng nhau
- [ ] API Contract v1 và fixtures đã chốt
- [ ] Android build, Web mở được, FastAPI `/docs` chạy, MySQL kết nối
- [ ] Login JWT hoạt động; Web biết cách dùng chung API Auth
- [ ] Migration + seed tạo được dữ liệu mẫu
- [ ] Chapter 1–2 và Chapter 3 phần đầu đã viết
- [ ] Mỗi người giải thích được diagram mình vẽ

**Demo cuối tuần:** Login cơ bản + Swagger + DB + giao diện nền tảng.

<a id="plan-13"></a>

### ITERATION 2 / WEEK 2 — Search, Venue, Court, Schedule, Pending Booking

| Người | Nhiệm vụ | File/output |
|---|---|---|
| S1 | Home, Search, Venue Detail, Court/Slot selection (Android) | `ui/{home,search,venue,booking}/`, XML, Retrofit repositories |
| S1 | Create Pending Booking, kiểm tra slot, transaction chống trùng | `models/booking.py`, `routers/bookings.py`, `booking_service.py`, `booking_repository.py` |
| S1 | Booking Sequence + tests conflict | `booking_sequence.puml/.png`, `test_booking.py` |
| S2 | Public Sport/Venue/Court/Available Slot APIs | `routers/{catalog,schedule}.py`, `catalog_service.py`, `schedule_service.py` |
| S2 | Owner Venue/Court/Slot CRUD + Web pages | `routers/owner.py`, `pages/owner/{venues,courts,schedule}.html`, JS |
| S2 | Hoàn thiện ERD, Data Dictionary, seed | `database_erd.dbml/.png`, `DB_SCHEMA.md`, `seed_data.py` |

**Report W2:** S1 viết Chapter 3 Android UI, Booking Sequence, API Booking; S2 viết Chapter 3 ERD/Data Dictionary, Owner UI, Schedule Design. Thêm screenshots/mockups có caption.

**Checklist W2**
- [ ] User tìm Venue theo Sport và Location
- [ ] User xem Venue/Court, chọn ngày và slot còn trống
- [ ] Owner CRUD Venue/Court/Slot, có kiểm tra ownership
- [ ] Pending Booking được tạo và lưu DB
- [ ] Hai request cùng đặt một slot: tối đa một Booking hiệu lực
- [ ] Slot đã giữ không hiển thị là còn trống
- [ ] Booking Sequence có `alt` conflict + transaction
- [ ] ERD v2 và Data Dictionary khớp SQLAlchemy/Alembic
- [ ] Chapter 3 được cập nhật; API Contract theo code thật
- [ ] Android gọi được ít nhất một API Catalog/Slot thật

**Demo cuối tuần:** Owner tạo sân/lịch → Android tìm và tạo Pending Booking.

<a id="plan-14"></a>

### ITERATION 3 / WEEK 3 — Booking history, Mock Payment, Owner booking

| Người | Nhiệm vụ | File/output |
|---|---|---|
| S1 | Booking Summary, History, Detail, Cancel UI/API | `ui/booking/`, `routers/bookings.py`, `booking_service.py` |
| S1 | Payment model, Mock Success/Failed, pending expiry, idempotency | `payment.py`, `payments.py`, `payment_service.py`, `test_payment.py` |
| S1 | Payment Sequence + Booking State | `payment_sequence.puml/.png`, `booking_state.puml/.png` |
| S2 | Owner Dashboard, Booking List, Schedule UI hoàn thiện | `pages/owner/{dashboard,bookings,schedule}.html`, JS |
| S2 | Test Owner scope, Schedule conflicts, Web API integration | `test_schedule.py`, `docs/test-cases/management-tests.md` |
| Cả hai | Test Booking ↔ Schedule ↔ Payment | Test evidence, screenshots, API Contract cập nhật |

**Report W3:** S1 Chapter 4 Auth/Booking/Mock Payment + State/Payment Sequence + test cases; S2 Chapter 4 Venue/Court/Schedule/Owner Booking + quyền Owner + DB verification.

**Checklist W3**
- [ ] Booking Summary/History/Detail hoạt động
- [ ] Mock Success → Payment PAID, Booking CONFIRMED (atomic)
- [ ] Mock Failed không xác nhận Booking
- [ ] Pending quá hạn không thanh toán được, slot được giải phóng đúng
- [ ] Retry thanh toán không tạo nhiều xác nhận thành công
- [ ] Cancel đúng chính sách, không phá dữ liệu lịch sử
- [ ] Owner chỉ xem Booking thuộc Venue mình
- [ ] Payment Sequence, Booking State khớp trạng thái code
- [ ] Chapter 4 phần đã làm có code giải thích + screenshots
- [ ] Test cases có expected/actual result

**Demo cuối tuần:** Search → Booking → Mock Payment → Confirmed → Owner thấy Booking.

<a id="plan-15"></a>

### ITERATION 4 / WEEK 4 — QR Check-in, Review, Admin, polish

| Người | Nhiệm vụ | File/output |
|---|---|---|
| S1 | Tạo token QR phía Backend, hiển thị QR Android | `booking_service.py`, `ui/booking/`, ZXing |
| S1 | Review model/API/UI, Profile, Android UI polish | `review.py`, `reviews.py`, `review_service.py`, `ui/{review,profile}/` |
| S1 | Android/Booking/Payment/Review tests + ảnh | `test_review.py`, `docs/screenshots/android/` |
| S2 | Web Camera QR scanner + Check-in Service/API/DB | `pages/owner/checkin.html`, `js/owner/`, `checkin.py`, `checkin_service.py`, `models/checkin.py` |
| S2 | Owner Complete Booking, Admin Dashboard/Management | `admin.py`, `admin_service.py`, `pages/admin/` |
| S2 | QR Sequence + Check-in/Admin tests + ảnh | `qr_checkin_sequence.puml/.png`, `test_checkin.py`, `test_admin.py`, `docs/screenshots/web/` |

**Report W4:** S1 Chapter 4 Android/QR Display/Review + Chapter 5 user test cases; S2 Chapter 4 QR/Admin + QR Sequence + Chapter 5 management/security tests. Hoàn tất **bản nháp đầy đủ** Chapter 1–5.

**Checklist W4**
- [ ] Android hiển thị QR cho Booking CONFIRMED
- [ ] QR token ngẫu nhiên, Backend xác thực
- [ ] Web scanner xin quyền camera, đọc QR trong HTTPS/localhost
- [ ] Invalid QR, duplicate QR, Booking chưa Confirmed bị từ chối
- [ ] Owner không check-in Booking của Owner khác
- [ ] Check-in + cập nhật Booking trong cùng transaction
- [ ] Owner đánh dấu COMPLETED đúng điều kiện
- [ ] Review chỉ cho Booking COMPLETED, tối đa một review/booking
- [ ] Admin quản lý đủ các mục đã cam kết (có phân quyền)
- [ ] UI Android và Web thống nhất, dễ thao tác
- [ ] QR Sequence và toàn bộ diagrams cập nhật theo code
- [ ] Có screenshots và test evidence cho mọi tính năng chính
- [ ] Bản nháp Report Chapter 1–5 đầy đủ

**Demo cuối tuần:** User Booking → Mock Payment → QR → Owner Check-in → Completed → Review; Admin quản lý.

<a id="plan-16"></a>

### ITERATION 5 / WEEK 5 — Stabilize, report, submission

| Người | Nhiệm vụ | File/output |
|---|---|---|
| S1 | Android regression, Auth/Booking/Payment/Review/concurrency tests, README Android | `test_*.py`, `user-tests.md`, `android-user/README.md`, screenshots |
| S2 | Web/Backend/DB/QR/Admin tests, seed/reset, README tổng | `test_*.py`, `management-tests.md`, `README.md`, `seed_data.py` |
| S1 | Viết kết quả test User + Chapter 6 cùng S2; review nội dung report | Draft S1, review comments |
| S2 | Viết kết quả test Management + tổng hợp Report, TOC/figures/references | `report/Final_Report.docx` |
| Cả hai | Cross-test, chạy thử trên máy khác, sửa lỗi, demo/vấn đáp | Source ổn định + Report + test evidence |

**Checklist W5**
- [ ] Android build và chạy trên thiết bị/emulator
- [ ] Owner/Admin Web chạy, Backend/DB migration + seed chạy được
- [ ] Toàn bộ luồng chính chạy ổn định, ít lỗi nghiêm trọng
- [ ] UI đẹp, nhất quán, không có màn hình bỏ dở
- [ ] Test thành công/thất bại, quyền truy cập, double booking, QR lặp
- [ ] Test case có precondition, steps, expected, actual, PASS/FAIL, evidence
- [ ] Use Case/ERD/Architecture/Activity/Sequence/State khớp source code
- [ ] Chapter 1–6 + References + Appendices hoàn chỉnh
- [ ] Mục lục, danh mục hình/bảng, số trang, caption, nguồn đúng
- [ ] Đọc sửa lỗi chính tả; tránh nội dung chắp vá/chỉ toàn ảnh
- [ ] `.env.example`, README, demo accounts, hướng dẫn chạy đầy đủ
- [ ] Hai người tự trình bày phần mình và trả lời câu hỏi tích hợp
- [ ] Tag bản nộp và lưu bản source/report cuối cùng

**Chỉ khi toàn bộ checklist chính đạt:** có thể thử VNPAY Sandbox; nếu chưa hoàn thành, ghi vào **Future Work**, không ghi đã tích hợp.

<a id="plan-17"></a>

## 6. Diagrams — bắt buộc theo kế hoạch nhóm, lưu ý từng hình

| Diagram / File | Owner | Deadline | Nội dung cần có | Lỗi phải tránh |
|---|---|---|---|---|
| System Use Case `usecase/system_usecase.puml` | S1 | W1; review W4 | User/Owner/Admin, chức năng theo role, system boundary | Đưa SQL/API thành Use Case; lạm dụng include/extend; sai quyền |
| ERD `erd/database_erd.dbml` | S2 | W1 v1; W2 v2; W4 final | 9 bảng, PK/FK, cardinality, unique, nullable | ERD khác models/migrations; tách Owner thành bảng tài khoản riêng không cần thiết |
| Architecture `architecture/system_architecture.drawio` | S2 | W1; review W4 | Android/Web → FastAPI modules → MySQL; Mock; VNPAY optional | Vẽ Android truy cập DB, hoặc vẽ microservices không triển khai |
| Booking Activity `activity/booking_activity.puml` | S1 | W1; review W3 | Start/End, chọn slot, unavailable, Pending, Payment success/fail | Thiếu decision/error branch; vẽ như sequence |
| Booking Sequence `sequence/booking_sequence.puml` | S1 | W2 | User→Android→API→Service→DB; transaction, conflict | Android gọi DB; Confirmed trước Payment; không thể hiện locking |
| Payment Sequence `sequence/payment_sequence.puml` | S1 | W3 | Payment attempt, check expiry, success/fail, atomic update | Nhầm Payment `PAID` với Booking `CONFIRMED`; client tự xác minh Gateway |
| Booking State `state/booking_state.puml` | S1 | W3 | Pending, Confirmed, Checked-in, Completed, Cancelled, Expired | Cho chuyển trạng thái sai; thiếu guard điều kiện |
| QR Sequence `sequence/qr_checkin_sequence.puml` | S2 | W4 | Owner Web→scanner→API→Service→DB; token, role, duplicate, atomic | QR chứa booking ID dễ đoán; Web tự xác nhận; thiếu owner scope |

**Quy tắc hình trong Report:** xuất PNG/SVG rõ nét, giữ source `.puml/.dbml/.drawio`, có số hình/caption và đoạn giải thích **hình thể hiện gì và liên hệ với code nào**. Ghi nguồn nếu lấy/chỉnh từ nguồn khác. Các hình **không được** thay thế phần giải thích. Không thêm diagram ngoài danh sách nếu chưa hoàn thành code chính.

<a id="plan-18"></a>

### 6.1. Bảng giao diagram theo từng tuần — có file, reviewer và liên kết code

| Tuần | S1 phải nộp | S2 phải nộp | Ai review và kiểm tra kết nối |
|---|---|---|---|
| **W1** | `usecase/system_usecase.puml` + PNG; `activity/booking_activity.puml` + PNG | `erd/database_erd.dbml` + PNG (v1); `architecture/system_architecture.drawio` + PNG | **S2 review Use Case/Activity** theo quyền Owner/Admin và Schedule; **S1 review ERD/Architecture** theo Booking/Payment/Android. Cả hai chốt `API_CONTRACT.md`. |
| **W2** | `sequence/booking_sequence.puml` + PNG; cập nhật Use Case theo code | ERD v2 + `DB_SCHEMA.md` (Data Dictionary), cập nhật Architecture nếu cần | S2 xác nhận Booking Sequence dùng đúng `time_slot_id`, lock và schema; S1 xác nhận Slot API khớp UI. |
| **W3** | `sequence/payment_sequence.puml` + PNG; `state/booking_state.puml` + PNG; cập nhật Activity | Review ERD với bảng Payment, Booking; cập nhật Owner/Booking API mô tả trong Report | S2 kiểm tra Booking State phù hợp Check-in; S1 kiểm tra Payment/Booking relationship và status. |
| **W4** | Cập nhật toàn bộ hình S1 theo API/Android thực tế; xuất PNG/SVG cuối | `sequence/qr_checkin_sequence.puml` + PNG; ERD final; Architecture final | **S1 review QR Sequence** theo `booking_service` và QR token; **S2 review toàn bộ diagram S1** theo Owner/Web. |
| **W5** | Chèn hình S1 vào đúng mục Report, viết caption, giải thích, dẫn file/code | Chèn hình S2, tổng hợp danh mục hình/bảng, kiểm tra chất lượng ảnh | Cả hai đối chiếu từng diagram với code, database, test và cùng tập trình bày. |

**Đường dẫn chuẩn:** `docs/diagrams/<loại>/<tên_file>` như bảng phần 6. Mỗi diagram bắt buộc có **source chỉnh sửa được + PNG/SVG xuất ra**, ít nhất một đoạn giải thích và **liên kết đến module thực tế**. S1 không tự vẽ lại ERD của S2; S2 không tự vẽ lại Booking Sequence của S1. Mọi thay đổi liên module gửi yêu cầu cập nhật cho owner và review qua PR.

<a id="plan-19"></a>

### 6.2. Diagram nào nối với thành phần nào?

| Diagram | Nguồn sự thật phải đối chiếu | Tài liệu / module cần cập nhật cùng |
|---|---|---|
| Use Case (S1) | `SYSTEM_REQUIREMENTS.md`, role permissions | Android screens + Owner/Admin Web + API endpoints |
| ERD (S2) | SQLAlchemy models, Alembic migrations, `DB_SCHEMA.md` | Booking, Payment, Schedule, Check-in FK và constraints |
| Architecture (S2) | Cấu trúc repo, `main.py`, Android Retrofit, Web fetch | Backend modules + MySQL + Mock Payment |
| Booking Activity (S1) | Booking business rules + Payment outcomes | `booking_service.py`, `payment_service.py` |
| Booking Sequence (S1) | `POST /bookings` request/response | `booking_service.py`, `schedule_service.py`, DB transaction |
| Payment Sequence (S1) | Mock Payment contract | `payment_service.py`, `bookings`, `payments` |
| Booking State (S1) | Quy tắc trạng thái chung | Booking Service và Check-in Service của S2 |
| QR Check-in Sequence (S2) | `POST /owner/checkins`, QR token | `checkin_service.py` + Booking State của S1 |

**Không được có hai phiên bản trạng thái Booking:** S1 quản lý Booking State; S2 triển khai QR Check-in nhưng phải sử dụng giao diện nghiệp vụ chung đã chốt. **ERD chỉ có một bản chính** do S2 duy trì, S1 bắt buộc review.

---

<a id="plan-20"></a>

## 6A. HƯỚNG DẪN KẾT NỐI 2 NGƯỜI (INTEGRATION PLAYBOOK)

<a id="plan-21"></a>

### A. Sơ đồ dữ liệu chạy xuyên hệ thống

```text
[S2 Owner Web] --POST /owner/venues, /owner/courts, /owner/slots--> [S2 Catalog/Schedule API]
                                                                  |
                                                                  v
                                                           [MySQL: Venue/Court/Slot]
                                                                  |
[S1 Android] --GET /venues, /courts/{id}/slots---------------------+
     |
     +-- POST /bookings -----------------> [S1 Booking API/Service] --lock slot + insert--> [MySQL: Booking]
     |                                               |
     +-- POST /bookings/{id}/payments/mock --> [S1 Payment Service] --> [MySQL: Payment + Booking]
     |                                               |
     +-- GET /bookings/{id} <---- Confirmed + qr_token (S1) -------+
     |
     +-- Android render QR
              |
              v
[S2 Owner Web Camera] --POST /owner/checkins--> [S2 Check-in Service]
                                                        |
                                      verify token, owner, status
                                                        |
                                      [S1 Booking State contract]
                                                        |
                                             [MySQL: Checkin + Booking]
                                                        |
[S2 Owner Web] --POST /owner/bookings/{id}/complete--> [S1 Booking API]
                                                        |
[S1 Android] --POST /bookings/{id}/reviews------------> [S1 Review API]
```

**Lưu ý:** Owner/Admin Web là frontend của S2; API `GET /owner/bookings` và `POST /owner/bookings/{id}/complete` **do S1 cung cấp**. Web gọi API của S1, không tự thao tác DB. S1 có thể dùng Catalog API của S2 qua Retrofit, nhưng Backend Booking cần trực tiếp sử dụng SQLAlchemy model/DB transaction (không gọi HTTP nội bộ giữa module trong cùng monolith).

<a id="plan-22"></a>

### B. 7 hợp đồng giao tiếp phải chốt trong W1

| # | Producer → Consumer | Chốt cụ thể | Khi chưa có API thật |
|---|---|---|---|
| 1 | **S1 Auth → S2 Web** | `POST /auth/login` trả `access_token`, `token_type`, `role`; `GET /users/me` trả `id`, `role`, `full_name`; role `USER/OWNER/ADMIN` | S2 dùng mock response `docs/fixtures/auth_owner.json`, không tạo API auth riêng |
| 2 | **S2 Catalog → S1 Android** | `GET /sports`, `/venues`, `/venues/{id}`, `/venues/{id}/courts`; fields `id`, `name`, `address`, `sport_id` theo từng DTO | S1 dùng `venues.json`, `courts.json` |
| 3 | **S2 Slots → S1 Android/Booking** | `GET /courts/{id}/slots?date=YYYY-MM-DD`; `time_slot_id`, `slot_date`, `start_time`, `end_time`, `price`, `is_available` | S1 dùng `slots.json`; Booking Service kiểm tra lại DB, không tin `is_available` từ Android |
| 4 | **S1 Booking → S2 Owner Web** | `GET /owner/bookings` trả `id`, `venue_id`, `court_id`, `time_slot_id`, `status`, `total_amount`, `user` (DTO thống nhất) | S2 dùng `owner_bookings.json` |
| 5 | **S1 Payment → S2 Owner Web/Admin** | `payments` có `booking_id`, `provider`, `amount`, `status`; `PAID` dẫn tới Booking `CONFIRMED` | S2 dùng `payments.json` |
| 6 | **S1 QR → S2 Check-in** | QR chứa **opaque `qr_token`**, Check-in API nhận `{"qr_token":"..."}`; chỉ `CONFIRMED` được check-in | S2 dùng token fixture, test token sai/lặp |
| 7 | **S2 Check-in → S1 Booking State** | Check-in chuyển `CONFIRMED → CHECKED_IN`; Complete chuyển `CHECKED_IN → COMPLETED`; dùng hàm service chung do S1 công bố, hoặc cùng transaction có review | Hai người viết contract + tests cho state transitions trước khi ghép |

<a id="plan-23"></a>

### C. Cách dùng service chung mà không sửa file của nhau

- **S1 cung cấp** `booking_service.py` với các hàm nghiệp vụ được thống nhất trong `API_CONTRACT.md`/`BUSINESS_RULES.md`: `create_booking(...)`, `confirm_payment(...)`, `mark_checked_in(db, booking_id, owner_id)`, `complete_booking(db, booking_id, owner_id)` (chữ ký cụ thể chốt trong W1). `mark_checked_in` kiểm tra trạng thái và Owner scope, nhưng **không commit** nếu được gọi trong transaction do Check-in Service điều phối.
- **S2 viết** `checkin_service.py`: xác thực QR token, dùng `mark_checked_in(...)` của S1, thêm `checkins` và commit **cùng một transaction**. Nếu token sai, role sai, đã check-in: rollback.
- **S2 viết** `schedule_service.py`: kiểm tra khung giờ không chồng lấn; công bố model `TimeSlot` và hàm đọc slot; **S1 viết** `booking_service.py` khóa dòng TimeSlot trong transaction để tránh double-booking.
- **S1 tạo** `auth.py`, `security.py`, `dependencies.py`; **S2 import** `get_current_user`/`require_role` theo interface thống nhất, không tự viết JWT verifier khác.
- **S2 sở hữu** `main.py` và đăng ký routers từ PR của S1. **S1 sở hữu** `owner/bookings` endpoint dù S2 sở hữu Owner Web. Điều này tránh có hai Booking Services.

<a id="plan-24"></a>

### D. Lịch ghép và điều kiện bàn giao

| Mốc | S1 bàn giao cho S2 | S2 bàn giao cho S1 | Bài test tích hợp |
|---|---|---|---|
| **W1 cuối tuần** | Auth JWT + fixture Booking/Payment/QR + API Contract | DB migration + fixture Venue/Court/Slot + backend startup | S2 login Web bằng Auth của S1; S1 Retrofit gọi API mẫu |
| **W2 giữa/cuối tuần** | `POST /bookings`, `GET /owner/bookings` bản đầu | Public Catalog + Slot API + Owner CRUD | Owner tạo slot → Android thấy slot → tạo Pending Booking |
| **W3 giữa/cuối tuần** | Mock Payment + Booking Status + History/Detail | Owner Booking Web + Schedule hoàn thiện | Android thanh toán → Owner Web thấy `CONFIRMED` |
| **W4 giữa/cuối tuần** | QR token/Display + `mark_checked_in`/`complete_booking` contract + Review | Scanner Web + Check-in API + Admin | Android hiển thị QR → Owner quét → Checked-in → Completed → Review |
| **W5** | Android tests, screenshots, Report S1 | Web/DB/QR tests, screenshots, Report S2 | Chạy E2E trên DB mới bằng README, test lỗi và trình bày |

**Bàn giao đạt yêu cầu** khi: (1) file được commit trên branch, (2) PR review/merge vào `develop`, (3) endpoint có Swagger + JSON mẫu, (4) test thành công và thất bại, (5) cập nhật diagram/Report tương ứng. **Không gửi code qua chat rồi chép thủ công.**

<a id="plan-25"></a>

### E. Branch cụ thể để diagram, contract và tích hợp không conflict

```bash
# Tạo repo: main là nhánh ổn định, develop là nhánh tích hợp
 git switch main
 git switch -c develop
 git push -u origin develop

# S1 - tuần 1 (tạo từ develop)
 git switch develop && git pull origin develop
 git switch -c feature/s1-w1-auth-usecase

# S2 - tuần 1 (tạo từ develop)
 git switch develop && git pull origin develop
 git switch -c feature/s2-w1-db-architecture

# Cuối mỗi tuần: PR của từng người -> develop, sau khi review và test
# Tuần tiếp theo: tạo branch mới từ develop mới nhất
```

| Tuần | Branch S1 | Branch S2 | Tài liệu/diagram chủ sở hữu |
|---|---|---|---|
| W1 | `feature/s1-w1-auth-usecase` | `feature/s2-w1-db-architecture` | S1 Use Case/Activity; S2 ERD/Architecture |
| W2 | `feature/s1-w2-search-booking-seq` | `feature/s2-w2-catalog-schedule-erd` | S1 Booking Sequence; S2 ERD v2/Data Dictionary |
| W3 | `feature/s1-w3-payment-state` | `feature/s2-w3-owner-web` | S1 Payment Sequence/Booking State; S2 ERD review |
| W4 | `feature/s1-w4-qr-review` | `feature/s2-w4-checkin-admin-seq` | S1 diagram update; S2 QR Sequence/ERD final |
| W5 | `fix/s1-w5-android-report` | `fix/s2-w5-web-report` | Hai người final review + report |

**File chung** (`API_CONTRACT.md`, `BUSINESS_RULES.md`, `Final_Report.docx`) không chỉnh cùng lúc: mỗi người đề xuất thay đổi trên PR hoặc viết file nháp theo module; S2 tổng hợp Report, S1 review. Đối với diagram, owner commit source + ảnh xuất trong **cùng PR**.

<a id="plan-26"></a>

### F. Checklist kết nối cho từng tuần (bổ sung checklist phần 5)

- **W1:** [ ] S1/S2 ký duyệt DTO, status, role, endpoints, DB FK; [ ] 4 diagram nền tảng được review chéo; [ ] mock fixtures có đủ các luồng.
- **W2:** [ ] Android lấy Catalog/Slots thật từ S2; [ ] Owner Web tạo slot, Android thấy slot; [ ] S1 tạo Booking không trùng slot; [ ] Booking Sequence khớp API.
- **W3:** [ ] Android Mock Payment cập nhật DB thật; [ ] Owner Web thấy trạng thái Confirmed; [ ] Payment Sequence/Booking State khớp kết quả test.
- **W4:** [ ] Android QR → Owner Scanner → Backend Check-in → Booking State → Review; [ ] QR Sequence được S1 review; [ ] test invalid/duplicate/owner khác.
- **W5:** [ ] chạy hệ thống từ clean database; [ ] cả hai trình bày được mọi điểm giao tiếp; [ ] Report + diagram + source thống nhất.

---

<a id="plan-27"></a>

## 7. Report — cấu trúc, người viết, đầu ra theo tuần

<a id="plan-28"></a>

### 7.1. Cấu trúc Final Report đề xuất

> Rubric **không chỉ định tên chương hay template**; dùng cấu trúc này nếu giảng viên không cấp mẫu khác.

| Phần | Nội dung | Người viết |
|---|---|---|
| Trang bìa; thông tin nhóm; phân công; TOC; danh mục hình/bảng | Metadata, đóng góp thực tế, mục lục tự động | S2 tổng hợp, S1 kiểm tra |
| **Ch.1 Introduction** | Background, Problem, Objectives, Scope, Technologies | **S1** |
| **Ch.2 Requirements Analysis** | Actors, Business Processes, Functional/Non-functional Requirements, Business Rules, Use Cases | S1 User/Booking/Payment/Review; S2 Owner/Admin/Venue/Schedule/QR |
| **Ch.3 System Analysis & Design** | Architecture, ERD, Data Dictionary, Activity/Sequence/State, API Contract, UI Design | S1 Android + Booking/Payment UML; S2 DB + Architecture + QR + Web |
| **Ch.4 Implementation** | Environment, Android, Auth, Catalog, Booking, Mock Payment, QR, Owner/Admin, Review | S1 Android/Auth/Booking/Payment/Review/QR display; S2 Catalog/Schedule/Web/QR scan/Admin/DB |
| **Ch.5 Testing & Results** | Strategy, Environment, test cases, actual results, screenshots, limitations | S1 User; S2 Owner/Admin/QR; E2E cả hai |
| **Ch.6 Conclusion & Future Work** | Achievements, limitations, lessons learned, optional VNPAY | **Cả hai** |
| References; Appendices | Trích dẫn, API list, schema, test cases, installation, demo accounts | S2 tổng hợp, S1 review |

**Mẫu viết cho mỗi chức năng:** mục đích → actor/luồng → class/file liên quan → API & DB → logic chính (trích code ngắn có giải thích) → ảnh kết quả có caption → test case/kết quả. Không viết nội dung không hiểu hoặc không đúng hệ thống thực tế.

<a id="plan-29"></a>

### 7.2. Tiến độ Report theo tuần

| Tuần | S1 phải nộp bản nháp | S2 phải nộp bản nháp | Mốc chung |
|---|---|---|---|
| **W1** | Ch.1; Ch.2 User/Booking/Payment; Use Case + Activity | Ch.2 Owner/Admin; Ch.3 Architecture + ERD v1 | Report skeleton, nguồn tham khảo ban đầu |
| **W2** | Ch.3 Android UI, Booking Sequence, API Booking | Ch.3 ERD v2, Data Dictionary, Owner UI/Schedule | Ch.3 gần hoàn chỉnh |
| **W3** | Ch.4 Auth/Booking/Mock Payment; Payment Sequence/State; test case đầu tiên | Ch.4 Venue/Court/Schedule/Owner Booking; authorization tests | Ch.4 các chức năng W1–3 |
| **W4** | Ch.4 QR Display/Review; Ch.5 Android/Booking/Payment | Ch.4 QR/Admin; Ch.5 Web/QR/Admin; QR Sequence | **Bản nháp Ch.1–5 đầy đủ** |
| **W5** | Ch.5 actual results, Ch.6, review chính tả/nội dung | Ch.5 actual results, Ch.6, ghép Word + mục lục/hình/bảng/nguồn | **Final_Report.docx**, rà soát toàn bộ |

**Quản lý bản nháp:** `report/drafts/S1_01_Introduction.docx`, `S1_02_User_Requirements.docx`, `S2_02_Management_Requirements.docx`, `S1_04_Booking_Payment.docx`, `S2_04_Management_QR.docx`, ...; **không cùng lúc sửa `Final_Report.docx`**. S2 tổng hợp; S1 duyệt bản cuối. Các file `.docx` có thể gây conflict Git: mỗi người chỉ sửa file mình, ghép bằng một người.

**Rubric quality gate:** TOC/danh mục hình/bảng chính xác, số hình/caption/nguồn, trích dẫn đúng, tối đa rất ít lỗi chính tả, hành văn tự nhiên, không dùng hình thay nội dung, chỉ mô tả tính năng **đã làm thật**. Đảm bảo cả hai hiểu Report và code.

<a id="plan-30"></a>

## 8. Git — branch, workflow và lệnh thực hiện

<a id="plan-31"></a>

### 8.1. Branch chuẩn

- `main`: chỉ bản ổn định để demo/nộp.
- `develop`: nhánh tích hợp, merge các feature sau review.
- Mỗi người có branch theo tính năng **không dùng một branch dài suốt 5 tuần**.

| Tuần | Branch S1 | Branch S2 |
|---|---|---|
| W1 | `feature/s1-foundation-auth` | `feature/s2-foundation-db-web` |
| W2 | `feature/s1-android-search-booking` | `feature/s2-catalog-schedule` |
| W3 | `feature/s1-booking-payment` | `feature/s2-owner-bookings-web` |
| W4 | `feature/s1-qr-review-ui` | `feature/s2-checkin-admin` |
| W5 | `fix/s1-android-booking-tests` | `fix/s2-web-backend-tests` |
| Report | `docs/s1-report` (tách khi cần) | `docs/s2-report` (tách khi cần) |

**Lưu ý:** Nếu W2 S1 và S2 cùng sửa `API_CONTRACT.md`, dùng PR riêng theo module, merge lần lượt; người merge sau **rebase/pull** và kiểm tra diff. `main.py` chỉ S2 cập nhật `include_router`, nhưng S1 phải cung cấp router và nhờ S2 merge theo PR, không tự sửa trên branch riêng nếu dễ conflict.

<a id="plan-32"></a>

### 8.2. Thiết lập lần đầu (một người thực hiện)

```bash
git init
git branch -M main
git add .
git commit -m "chore: initialize sports court booking project"
git remote add origin <GITHUB_REPOSITORY_URL>
git push -u origin main

git switch -c develop
git push -u origin develop
```

> Nếu repository GitHub đã tạo sẵn với README, **clone repo trước**, không chạy lại `git init`/`remote add`. Tạo branch `develop` từ `main` đã có.

<a id="plan-33"></a>

### 8.3. Mỗi người bắt đầu feature

```bash
git switch develop
git pull origin develop
git switch -c feature/s1-foundation-auth  # S1; S2 thay bằng tên branch của mình
# code + test + cập nhật tài liệu phần mình
git add .
git commit -m "feat(auth): implement JWT login and register"
git push -u origin feature/s1-foundation-auth
```

Trên GitHub tạo **Pull Request: `feature/...` → `develop`**, reviewer là thành viên còn lại. PR mô tả: mục tiêu, file thay đổi, API/schema đổi gì, cách chạy, test results, screenshot nếu có. Sau review + pass test → merge → xóa feature branch đã merge. Cuối mỗi tuần merge `develop` vào `main` khi demo ổn định, tạo tag `iteration-1`, ..., `iteration-5`.

```bash
# Sau khi PR được merge, cập nhật code local
git switch develop
git pull origin develop

# Cuối tuần: chỉ khi develop ổn định
git switch main
git pull origin main
git merge --no-ff develop
git push origin main
git tag iteration-1  # thay số tuần
git push origin iteration-1
```

**Không dùng `git push --force` lên `main`/`develop`.** Không commit file cấu hình chứa secret. Migration phải chạy thử trên DB mới trước khi merge. Nếu PR gây conflict, giải quyết dựa trên **file ownership + API Contract**, không xóa code người kia tùy tiện.

<a id="plan-34"></a>

### 8.4. Lịch phối hợp tối thiểu

| Khi nào | Việc phải làm | Bằng chứng |
|---|---|---|
| Đầu tuần | Chốt task và branch cho từng người | GitHub Issues/Project board |
| Giữa tuần | Integration lần 1: pull `develop`, chạy API liên module | Test log/screenshot |
| Cuối tuần | Integration lần 2, review PR, update report, checklist | Merge PR + Report draft |
| Cuối mỗi iteration | Demo workflow của tuần, tag bản ổn định | `iteration-N` tag |

<a id="plan-35"></a>

### 8.5. Issue template (copy cho mỗi task)

```markdown
## Task
- Iteration: W__
- Owner: S1 / S2
- Branch: feature/...
- Requirement / API Contract: ...
- Files expected: ...
- Test cases: ...
- Report section: ...

## Definition of Done
- [ ] Implemented and run successfully
- [ ] API/schema matches contract
- [ ] Test passed; evidence saved
- [ ] Documentation/diagram updated
- [ ] Report section updated
- [ ] PR reviewed and merged
```

<a id="plan-36"></a>

## 9. Test plan — phải có Expected + Actual + Evidence

| ID | Kịch bản | Kết quả mong đợi | Owner |
|---|---|---|---|
| TC01 | Register hợp lệ | Tạo User | S1 |
| TC02 | Login sai mật khẩu | 401 | S1 |
| TC03 | Search Sport/Location | Danh sách đúng | S2 |
| TC04 | Đặt Slot còn trống | Booking PENDING | S1 |
| TC05 | Đặt Slot đang được giữ | 409 Conflict | S1 |
| TC06 | Mock Payment Success | PAID + CONFIRMED | S1 |
| TC07 | Mock Payment Failed | Không Confirmed | S1 |
| TC08 | Thanh toán Booking hết hạn | Bị từ chối | S1 |
| TC09 | Thanh toán Success lặp | Không xác nhận trùng | S1 |
| TC10 | Owner sửa Venue người khác | 403 | S2 |
| TC11 | Quét QR hợp lệ | CHECKED_IN | S2 |
| TC12 | Quét QR sai | Bị từ chối | S2 |
| TC13 | Quét QR lặp | Bị từ chối lần 2 | S2 |
| TC14 | Owner quét Booking Venue khác | 403 | S2 |
| TC15 | Review Booking COMPLETED | Thành công | S1 |
| TC16 | Review Booking PENDING | Bị từ chối | S1 |
| TC17 | User truy cập Admin API | 403 | S2 |
| TC18 | Hai request đặt cùng Slot đồng thời | Tối đa 1 Booking hiệu lực | S1 + S2 |
| TC19 | Xóa/Sửa slot đã có booking | Bị chặn hoặc xử lý theo rule | S2 |
| TC20 | End-to-end User→Payment→QR→Review | Toàn luồng thành công | Cả hai |

**Test case template:** `ID | Preconditions | Test Data | Steps | Expected Result | Actual Result | Pass/Fail | Evidence (ảnh/log)`; screenshot và logs đặt trong `docs/screenshots/`/`docs/test-cases/`. Không ghi PASS khi chưa chạy.

<a id="plan-37"></a>

## 10. Checklist nghiệm thu cuối kỳ

<a id="plan-38"></a>

### Source & functionality
- [ ] Android User App build, giao diện hoàn chỉnh, gọi API thật
- [ ] Owner/Admin Web chạy, phân quyền đúng
- [ ] FastAPI + MySQL + Alembic + seed chạy lại từ đầu được
- [ ] Search/Booking/Mock Payment/History/QR/Check-in/Review hoàn chỉnh
- [ ] Venue/Court/Schedule/Admin hoạt động đúng quyền
- [ ] Không double booking; payment và QR không xử lý lặp sai
- [ ] Có test thành công, lỗi, quyền truy cập, concurrency và E2E
- [ ] README, `.env.example`, demo accounts, cách chạy rõ ràng

<a id="plan-39"></a>

### Diagrams & Report
- [ ] Use Case, ERD, Architecture, Booking Activity, Booking Sequence, Payment Sequence, Booking State, QR Sequence
- [ ] Tất cả diagrams có source + hình xuất rõ, khớp code/DB/API
- [ ] Report đủ Ch.1–6, References, Appendices
- [ ] Mục lục, danh mục hình/bảng, caption, nguồn, trích dẫn chuẩn
- [ ] Code snippets ngắn, có giải thích; ảnh có nội dung giải thích
- [ ] Test Cases có Actual Results và Evidence
- [ ] Report không mô tả chức năng chưa làm; VNPAY chỉ Future Work nếu chưa tích hợp
- [ ] Mỗi người tự viết, hiểu và trình bày phần phụ trách

<a id="plan-40"></a>

### Submission & defense
- [ ] `main` chứa bản chạy ổn định, tag `iteration-5`
- [ ] Source Code + Final Report đúng định dạng yêu cầu giảng viên
- [ ] Thử setup trên máy khác / môi trường sạch
- [ ] Chuẩn bị demo: tài khoản User/Owner/Admin + sân/lịch + Booking mẫu
- [ ] S1 giải thích MVVM, Retrofit, Auth, Booking, transaction, Payment, QR Display
- [ ] S2 giải thích Web, FastAPI modules, ERD, Schedule, Check-in, Admin, RBAC
- [ ] Cả hai giải thích được end-to-end flow, API Contract và lý do chọn Modular Monolith

<a id="plan-41"></a>

## 11. Những điểm phải thống nhất trước khi mở PR đầu tiên

1. **Giá theo slot:** `time_slots.price` là giá hiện tại; `bookings.total_amount` snapshot khi đặt.
2. **Slot cố định:** mỗi Booking đặt **một** slot; không đặt nhiều giờ/đa sân trong một Booking ở phiên bản này.
3. **Chính sách hủy:** tối thiểu cho hủy Pending; nếu cho hủy Confirmed, phải ghi rõ điều kiện và xử lý Payment/slot; không triển khai refund thực.
4. **Slot quá hạn:** dùng `expires_at` và kiểm tra phía Backend khi truy vấn/đặt/thanh toán; không chỉ dựa vào đồng hồ Android.
5. **QR token:** random unique, phát hành khi Confirmed, chỉ Check-in một lần, Owner scope và Booking status được kiểm tra trong transaction.
6. **Account Owner/Admin:** tạo bằng seed hoặc admin, không cho register công khai tự chọn `OWNER`/`ADMIN`.
7. **Owner Complete Booking:** API do S1 quản lý Booking State, S2 gọi từ Web; Check-in API do S2 quản lý, dùng quy tắc Booking State đã chốt với S1.
8. **Role permissions:** cả Backend kiểm tra role + owner scope, không chỉ frontend ẩn nút.
9. **Review:** tối đa một Review/Booking, chỉ khi Completed.
10. **Optional VNPAY:** chỉ sau khi source/report chính đạt yêu cầu; không để gateway ảnh hưởng submission.

---

**Quy trình bắt đầu ngay:** Tạo GitHub repo → commit tài liệu này ở root → tạo `develop` → tạo 2 branch W1 → mở GitHub Issues theo bảng W1 → chốt `API_CONTRACT.md` và ERD v1 → code độc lập → integration giữa/cuối tuần → hoàn thành Report W1 → review/tag `iteration-1`.

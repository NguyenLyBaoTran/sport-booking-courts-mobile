# API Contract — Auth, Booking, Payment

Base URL qua API Gateway: `http://127.0.0.1:8000/api/v1`.
Thời gian trả về theo ISO 8601 UTC. Protected customer routes cần
`Authorization: Bearer <access_token>`.

## Authentication

| Method | Path | Access |
|---|---|---|
| POST | `/auth/register` | Public; luôn tạo USER |
| POST | `/auth/login` | Public |
| GET | `/users/me` | Authenticated |

Register body:

```json
{
  "full_name": "Test Customer",
  "email": "customer@example.test",
  "password": "at-least-8-characters",
  "phone": "0900000000"
}
```

Login response có `access_token`, `token_type`, `expires_in` (giây) và `user`.
JWT ký HS256, claims `sub` (user ID dạng chuỗi), `role`, `iat`, `exp`.
Đăng ký public không nhận role tùy ý. Tạo OWNER/ADMIN cho môi trường local bằng
`python -m app.create_test_account` trong `backend/services/user_service`.

## Booking

| Method | Path | Access | Purpose |
|---|---|---|---|
| POST | `/bookings` | USER | Giữ slot và tạo PENDING booking |
| GET | `/bookings` | USER | Danh sách booking của chính user |
| GET | `/bookings/{booking_id}` | USER | Chi tiết booking của chính user |
| POST | `/bookings/{booking_id}/cancel` | USER | Hủy booking PENDING |

Create body:

```json
{ "time_slot_id": 42 }
```

Response `201` gồm `id`, `user_id`, `time_slot_id`, `court_id`, `venue_id`,
`slot_date`, `start_time`, `end_time`, `status: "PENDING"`, `total_amount`,
`expires_at`, `qr_token: null`, `created_at`. Booking Service yêu
cầu Court Service hold slot trước khi commit; `expires_at` lấy từ kết quả hold để
đồng nhất thời hạn ở hai service. Court Service mặc định giữ slot 10 phút
(`BOOKING_HOLD_MINUTES`); cấu hình giá trị giống nhau ở Court/Booking environments
nếu endpoint Court cần biến này. Chỉ booking PENDING được hủy theo chính sách
Iteration 1; các trạng thái khác trả `409`.

Booking hết hạn được chuyển thành EXPIRED và slot được release khi đọc booking đã
hết hạn hoặc khi job nội bộ gọi endpoint expire. Scheduler cần gọi endpoint expire
định kỳ để cập nhật các booking không được người dùng đọc lại.

## Mock Payment

| Method | Path | Access | Purpose |
|---|---|---|---|
| POST | `/payments/process` | USER | Tạo mock payment attempt |
| GET | `/payments` | USER | Lịch sử payment của chính user |
| GET | `/payments/{payment_id}` | USER | Chi tiết payment của chính user |

Request:

```json
{ "booking_id": 42, "mock_result": "SUCCESS" }
```

`mock_result` nhận `SUCCESS` (mặc định) hoặc `FAILED`. Đây là mô phỏng, không xử lý
tiền thật. Có thể gửi `Idempotency-Key` (1–100 ký tự); khi retry sau một attempt
FAILED, dùng key mới. Response thành công có status `PAID`, `transaction_code`,
`booking_status: "CONFIRMED"` và `qr_token`. Attempt FAILED không xác nhận booking.
Booking không thuộc user hiện tại trả `404`; request không hợp lệ hoặc booking
không còn payable trả `409`.

## Internal service contract

Các endpoint dưới đây không dành cho client/browser. Chỉ service-to-service với
header `X-Internal-Token: <INTERNAL_SERVICE_TOKEN>` được chấp nhận. Tất cả service
phải cấu hình cùng một secret riêng; không commit token thật.

### Booking Service ↔ Court Service (dependency chờ Court Service)

Booking Service gọi:

| Method | Court Service path | Query | Response cần có |
|---|---|---|---|
| POST | `/api/v1/internal/slots/{slot_id}/hold` | `booking_id` | `court_id`, `venue_id`, `owner_id`, `price_per_hour`, `slot_date`, `start_time`, `end_time`, `expires_at` (ISO 8601 UTC) |
| POST | `/api/v1/internal/slots/{slot_id}/confirm` | `booking_id` | `{"status":"BOOKED"}` |
| POST | `/api/v1/internal/slots/{slot_id}/release` | `booking_id` | `{"status":"AVAILABLE"}` |

Court Service phải bảo đảm hold atomically, trả `409` nếu slot không còn sẵn sàng,
cho phép confirm chỉ đúng booking đang giữ slot chưa hết hạn, và release chỉ hold
đúng booking. Request lặp cùng `booking_id` cần idempotent. Giá booking được tính
trên `price_per_hour × thời lượng slot`.

Court Service thực hiện xác thực Owner và scan QR qua API quản lý của nó, sau đó
gọi endpoint nội bộ Booking Service dưới đây để Booking Service thực hiện state
transition. `owner_id` phải là Owner đã được Court Service xác thực; Booking
Service đối chiếu với `owner_id` đã snapshot khi giữ slot.

### Payment Service ↔ Booking Service

| Method | Booking Service path | Response |
|---|---|---|
| GET | `/api/v1/internal/bookings/{booking_id}/payment-context` | `booking_id`, `user_id`, `status`, `total_amount`, `expires_at` |
| POST | `/api/v1/internal/bookings/{booking_id}/confirm` | `booking_id`, `status`, `qr_token` |
| POST | `/api/v1/internal/bookings/check-in` | Body `owner_id`, `qr_token`; đổi CONFIRMED → CHECKED_IN một lần |
| POST | `/api/v1/internal/bookings/{booking_id}/complete` | Body `owner_id`; đổi CHECKED_IN → COMPLETED |
| POST | `/api/v1/internal/bookings/expire` | `expired`, `released` |

Confirm idempotent: booking đã CONFIRMED trả lại cùng QR token. QR là token ngẫu
nhiên, không chứa user data hoặc booking ID. Check-in status mutation và completion
thuộc Booking Service; QR scanner, xác thực Owner trước khi gọi internal API và
Management Web route thuộc Court/Owner integration.

## Error behavior

| Status | Meaning |
|---|---|
| 401 | Missing/invalid bearer token |
| 403 | Role not permitted or invalid internal service token |
| 404 | Resource absent or belongs to another customer |
| 409 | Slot unavailable, booking state invalid, or idempotency conflict |
| 422 | Request validation failed |
| 502 | Upstream service returned malformed slot data |
| 503 / 504 | Internal dependency unavailable / timed out |

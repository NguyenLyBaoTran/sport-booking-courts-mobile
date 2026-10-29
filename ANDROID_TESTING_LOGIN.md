# README – Test Sport Booking trên điện thoại Android

## 1. Kết nối điện thoại

- Điện thoại và Mac phải kết nối cùng Wi-Fi.
- Lấy IP của Mac bằng lệnh:

```bash
ipconfig getifaddr en0
```

## 2. Cấu hình API

Mở file `ApiClient.java` và cập nhật `BASE_URL` theo IP của Mac:

```java
private static final String BASE_URL = "http://192.168.28.158:8001/";
```

Thay IP ví dụ bằng IP thực tế của Mac.

## 3. Chạy Backend

Tại thư mục gốc của project, mở Terminal và chạy:

```bash
cd backend/services/user_service
../../../.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Giữ Terminal mở trong quá trình kiểm thử.

Kiểm tra kết nối bằng cách mở trình duyệt trên điện thoại:

```text
http://192.168.28.158:8001/docs
```

Nếu trang API mở được, điện thoại đã kết nối đến backend.

## 4. Chạy ứng dụng

1. Mở project Android bằng Android Studio.
2. Kết nối điện thoại với Mac qua USB và bật **USB debugging**.
3. Chọn điện thoại trong Android Studio.
4. Nhấn **Run ▶** để cài đặt và mở ứng dụng.

## 5. Kiểm thử chức năng

| Chức năng | Thao tác | Kết quả mong đợi |
|---|---|---|
| Đăng ký | Nhập thông tin tài khoản mới và nhấn Register | Đăng ký thành công |
| Đăng nhập | Nhập email và mật khẩu đúng | Chuyển đến Home |
| Đăng nhập sai | Nhập sai email hoặc mật khẩu | Hiển thị thông báo lỗi |
| Duy trì phiên | Đóng rồi mở lại ứng dụng | Vào Home nếu phiên còn hợp lệ |
| Đăng xuất | Nhấn Log out tại Home | Quay về Login |


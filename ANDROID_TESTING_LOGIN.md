# Đăng nhập Google trên app Android

Hướng dẫn này chỉ cấu hình đăng nhập Google trong **app Android**. Không cần
làm trang web đăng nhập. Google vẫn yêu cầu một loại OAuth Client tên **Web
application** để app xin ID token và backend kiểm tra token đó.

## 1. Tạo hai OAuth Client ID

Trong cùng một Google Cloud project, mở **Google Auth Platform → Clients** và
tạo/kiểm tra hai client:

1. **Web application** (trong danh sách có thể tên `Sport Courting`). Đây là ID
   app gửi cho Google khi xin ID token và backend dùng để xác minh token. Sao
   chép Client ID đầy đủ; thường kết thúc bằng
   `.apps.googleusercontent.com`. Không cần điền JavaScript origins hay redirect
   URI cho luồng app Android này.
2. **Android** (ví dụ `SportBooking`). Cấu hình này giúp Google nhận diện app
   Android theo package name và chữ ký. Nhập package `com.example.sportbooking`
   cùng SHA-1 của khóa ký.

Lấy SHA-1 của bản debug bằng terminal, từ thư mục `android-user`:

```bash
./gradlew signingReport
```

Trong kết quả, tìm variant `debug`, sao chép dòng `SHA1` và nhập vào Android
OAuth Client. Nếu sau này ký app bằng khóa khác, cần thêm SHA-1 của khóa đó.

## 2. Dán Web Client ID vào đúng hai chỗ

Lấy ID của **Web application** ở bước 1, rồi dùng chính ID đó ở cả backend và
Android. Không dán Android Client ID vào các chỗ này.

```env
# backend/.env
GOOGLE_CLIENT_ID=<Web OAuth Client ID>
```

```properties
# ~/.gradle/gradle.properties
GOOGLE_SERVER_CLIENT_ID=<Web OAuth Client ID>
```

Giữ nguyên tên biến, bỏ dấu `< >`, và dán Client ID đầy đủ. Trong Google Auth
Platform, nếu Audience đang ở trạng thái **Testing**, thêm Gmail muốn thử vào
danh sách **Test users**.

Sau khi sửa `backend/.env`, khởi động lại backend. Sau khi sửa
`~/.gradle/gradle.properties`, build/cài lại app để app nhận cấu hình mới:

```bash
cd android-user
./gradlew installDebug
```

## 3. Chọn địa chỉ backend cho emulator hoặc điện thoại

App gọi API Gateway ở cổng `8000`. Backend phải chạy với `--host 0.0.0.0` như
lệnh bên dưới để thiết bị khác trên máy có thể kết nối.

### Android Emulator

Mặc định app dùng `http://10.0.2.2:8000/`. Địa chỉ `10.0.2.2` là cách Android
Emulator truy cập máy tính đang chạy emulator; không thay bằng `localhost`.

### Điện thoại thật qua Wi-Fi

Kết nối điện thoại và máy tính vào cùng Wi-Fi. Tìm IP Wi-Fi của máy tính (trên
macOS có thể chạy `ipconfig getifaddr en0`; nếu không ra IP, thử `en1`). Ví dụ
nếu máy tính có IP `192.168.36.158`, thêm dòng sau vào
`~/.gradle/gradle.properties`:

```properties
API_BASE_URL=http://192.168.36.158:8000/
```

Thay IP ví dụ bằng IP hiện tại của máy tính. Build/cài lại app sau khi đổi URL.
Nếu IP máy tính đổi khi kết nối Wi-Fi lại, cập nhật dòng này.

### Điện thoại thật qua USB

Bật USB debugging, kết nối điện thoại rồi chạy:

```bash
adb reverse tcp:8000 tcp:8000
```

Đặt trong `~/.gradle/gradle.properties`:

```properties
API_BASE_URL=http://127.0.0.1:8000/
```

Sau đó build/cài lại app. Lệnh `adb reverse` cần chạy lại nếu rút cắm điện thoại
hoặc khởi động lại kết nối ADB.

## 4. Cài dependencies và nâng database

Từ thư mục gốc repository, kích hoạt `.venv` nếu chưa kích hoạt:

```bash
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
cd backend/services/user_service
python -m alembic -c alembic.ini upgrade head
```

## 5. Chạy backend

Mở hai terminal riêng tại thư mục gốc repository:

```bash
cd backend/services/user_service
../../../.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

```bash
cd backend/gateway
../../.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

App gọi User Service qua API Gateway ở cổng `8000`.

## 6. Thử đăng nhập

Mở app trên thiết bị/emulator, chọn đăng nhập Google và chọn tài khoản đã thêm
vào **Test users** nếu Audience đang ở Testing. App nhận Google ID token rồi gửi
token lên backend; backend xác minh token và trả phiên đăng nhập cho user.

## 7. Quên mật khẩu

Màn hình đăng nhập có **Forgot Password**. User nhập email, nhận mã OTP qua
email, rồi nhập OTP và mật khẩu mới trong app. Mã hết hạn sau 10 phút; sau khi
đổi mật khẩu thành công, đăng nhập lại bằng mật khẩu mới.

Để gửi email thật, cấu hình các biến SMTP sau trong `backend/.env`, rồi khởi
động lại User Service:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=<địa chỉ Gmail gửi mã>
SMTP_PASSWORD=<App Password của Gmail>
SMTP_FROM=<địa chỉ Gmail gửi mã>
```

Với Gmail, dùng **App Password** thay cho mật khẩu đăng nhập Gmail. Không đưa
App Password vào app Android hoặc commit lên Git. Nếu chưa cấu hình SMTP, API
sẽ báo chưa gửi được email.

## Luồng tài khoản và xử lý lỗi

- User đăng ký bằng email/mật khẩu.
- Lần đầu đăng nhập Google bằng cùng Gmail đã xác minh, backend tự liên kết
  Google subject với tài khoản `USER` hiện có và cấp JWT cho chính tài khoản đó.
- OWNER/ADMIN không dùng Google Sign-In. Email đã có tài khoản nhưng không đủ
  điều kiện tự liên kết sẽ nhận lỗi từ backend; app cần hiển thị lỗi đó.
- Nếu Google picker báo lỗi trước khi gọi backend, kiểm tra Android OAuth Client,
  package name, SHA-1 debug, Test users và Google Play Services.
- Nếu chọn được tài khoản nhưng backend trả lỗi, kiểm tra Web Client ID ở hai
  chỗ đã nêu, log User Service và thông báo lỗi trong app.

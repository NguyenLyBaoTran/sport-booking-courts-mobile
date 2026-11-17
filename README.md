# Sports Court Booking

Sports Court Booking là hệ thống đặt sân thể thao gồm ứng dụng Android cho khách hàng, trang quản trị Management Web cho chủ sân/quản trị viên và backend FastAPI chia thành các dịch vụ nhỏ. Docker Compose tạo môi trường phát triển trên máy cá nhân với MySQL, Mailpit và các ứng dụng.

## Kiến trúc tổng quan

```text
Android ───────────┐
Management Web ────┴──> API Gateway :8000 ──> User / Court / Booking / Payment
                                                  └── MySQL 8.4 (4 database riêng)
User Service ── SMTP ──> Mailpit (chỉ nhận email local)
```

Gateway là điểm vào API cho Android và Management Web. Các service sở hữu dữ liệu riêng; Booking gọi Court để giữ/xác nhận slot, Payment gọi Booking để xác nhận booking. Môi trường Compose được khai báo trong [`compose.yaml`](compose.yaml). Chi tiết kiến trúc, chức năng, API và giới hạn hiện tại nằm trong [tài liệu dự án](docs/PROJECT_DOCUMENTATION.md).

## Công nghệ và yêu cầu

| Mục đích | Cần cài |
|---|---|
| Chạy Backend bằng Docker | Git, Docker Desktop trên Windows/macOS hoặc Docker Engine và Compose v2 trên Linux; Python 3.10+ để chạy helper. |
| Phát triển/chạy Android | Android Studio, Android SDK và JDK tương thích với Gradle Wrapper trong repository. Emulator hoặc điện thoại Android để chạy app. |
| Chạy kiểm thử Backend/Web | Python 3.10+; Node.js để chạy bộ test JavaScript trong Management Web. |

Ứng dụng Android viết bằng Java/XML, dùng Retrofit và Credential Manager; backend dùng Python, FastAPI, SQLAlchemy, Alembic và MySQL 8.4; Management Web dùng HTML/CSS/JavaScript. Các phiên bản Android/JDK cụ thể cần theo Gradle Wrapper và Android Gradle Plugin đã khóa trong project.

## Clone project

```sh
git clone https://github.com/NguyenLyBaoTran/sport-booking-courts-mobile.git
cd sport-booking-courts-mobile
```

Đường dẫn trên lấy từ remote `origin` hiện tại. Nếu repository được chuyển sang nơi khác, dùng URL do nhóm cung cấp. Không đưa `.env` hoặc thông tin đăng nhập vào Git.

## Cấu hình và setup lần đầu

Docker Compose dùng file `.env` ở thư mục gốc. `.env.example` là mẫu tên biến và giá trị hướng dẫn; không chứa secret dùng thật. Có hai cách:

1. Nếu chưa có `.env`, chạy setup; helper tạo file từ `.env.example`, tạo secret local nếu an toàn và hỏi cấu hình tích hợp tùy chọn.
2. Nếu muốn tạo thủ công, sao chép mẫu rồi thay mọi giá trị `replace_with_...` bằng giá trị phù hợp trước khi chạy setup.

**Windows PowerShell**

```powershell
Copy-Item .env.example .env
```

**Linux/macOS**

```sh
cp .env.example .env
```

Nếu `.env` đã tồn tại và cấu hình hợp lệ, helper mặc định giữ nguyên file. Nếu thiếu secret bắt buộc, helper có thể điền các giá trị còn thiếu sau khi kiểm tra volume; nếu chọn cập nhật cấu hình, helper chỉ sửa các biến tích hợp/secret do setup quản lý và giữ các mục khác. Nếu volume Dev MySQL đã tồn tại mà secret bắt buộc bị thiếu, helper dừng để tránh làm lệch mật khẩu với dữ liệu. Không chia sẻ `.env`, không thay password MySQL của volume đang dùng.

### Các biến môi trường

| Biến | Bắt buộc | Mục đích / hướng dẫn |
|---|---|---|
| `MYSQL_DEV_ROOT_PASSWORD` | Có cho Compose | Password MySQL phát triển; giữ nguyên theo volume hiện có. |
| `JWT_SECRET_KEY` | Có cho Backend | Khóa ký JWT local; dùng chuỗi ngẫu nhiên riêng. |
| `INTERNAL_SERVICE_TOKEN` | Có cho các tích hợp nội bộ | Token dùng chung giữa các backend service; không đưa vào Android/Web. |
| `GATEWAY_BIND_ADDRESS` | Không | Compose dùng `127.0.0.1` nếu biến bị bỏ trống; `.env.example` của project đặt `0.0.0.0` để cho phép truy cập từ LAN. Chỉ dùng giá trị này khi cần và giới hạn mạng bằng firewall phù hợp. |
| `GATEWAY_HOST_PORT` | Không | Cổng host, mặc định `8000`; cổng container vẫn là `8000`. |
| `GOOGLE_LOGIN_ENABLED`, `GOOGLE_CLIENT_ID` | Không | Bật Google Login và cấu hình Web Client ID khi đã tạo OAuth client. Nếu không cấu hình, email/mật khẩu vẫn dùng được. |
| `GOOGLE_ANDROID_CLIENT_ID`, `GOOGLE_ANDROID_PACKAGE_NAME`, `GOOGLE_ANDROID_SHA1` | Không | Thông tin Android OAuth dùng để kiểm tra cấu hình trong quy trình setup/Google Cloud; package hiện tại là `com.example.sportbooking`. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_STARTTLS` | Không | Cấu hình máy chủ gửi OTP. Compose mặc định nối User Service tới Mailpit local. Gmail dùng `smtp.gmail.com:587`, STARTTLS và App Password. |
| `CORS_ALLOWED_ORIGINS` | Không | Danh sách origin HTTP(S) cụ thể cho trình duyệt; mặc định cho Management Web localhost. |
| `BOOKING_HOLD_MINUTES` | Không | Thời gian giữ chỗ chờ thanh toán; mặc định Compose là 10 phút. |

`SMTP_PROVIDER` được setup dùng để chọn và kiểm tra cấu hình tích hợp; User Service đọc trực tiếp `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` và `SMTP_STARTTLS`. Không có `SMTP_FROM_NAME` trong implementation hiện tại. `backend/.env.example` là mẫu riêng cho chạy backend trực tiếp trên host; không thay thế `.env.example` ở thư mục gốc.

Chạy từ thư mục gốc:

**Windows**

```powershell
.\setup.bat
```

**Linux/macOS**

```sh
chmod +x ./setup.sh   # chỉ cần nếu file chưa có quyền thực thi
./setup.sh
```

Cả hai launcher gọi chung `setup_config.py`; phần chọn Python theo hệ điều hành nằm trong launcher, còn quy trình dùng chung ở helper. Helper kiểm tra Python 3.10+, Docker/Compose, cấu hình Compose và cổng; chuẩn bị `backend/.venv`; sau đó khởi động từng giai đoạn, chờ healthcheck hữu hạn, khởi tạo schema, chạy demo seed rồi kiểm tra Gateway. Mỗi giai đoạn chờ health tối đa 720 giây; từng lệnh Compose có timeout tối đa 900 giây. Khi quá hạn, setup dừng và hướng dẫn xem trạng thái/log; thời gian tổng có thể dài hơn do nhiều giai đoạn chạy nối tiếp. Compose có thể tải/build image còn thiếu. Setup không hỏi Android IP.

## Chạy Docker Compose thủ công

Sau khi đã có `.env` hợp lệ, các lệnh sau dùng profile phát triển:

```sh
docker compose --profile dev config --quiet
docker compose --profile dev up -d
docker compose --profile dev ps
```

Lần khởi động đầy đủ cần theo dependency trong Compose: MySQL và schema init, backend services, demo seed, Gateway, rồi Management Web. `setup_config.py` chạy các giai đoạn này có kiểm tra trạng thái giữa chúng. `docker compose up -d` cũng tuân theo dependency khai báo, nhưng nếu lỗi thì xem `ps --all` và logs trước khi thử lại.

## Kiểm tra ứng dụng

- Gateway: mở <http://127.0.0.1:8000/health> (endpoint thực tế là `GET /health`). API docs: <http://127.0.0.1:8000/docs>.
- Các service qua Gateway: `/api/v1/user/health`, `/api/v1/court/health`, `/api/v1/booking/health`, `/api/v1/payment/health`.
- Management Web: <http://127.0.0.1:8080>.
- Mailpit UI: <http://127.0.0.1:8025>; email bắt ở đây không được gửi ra ngoài.

Xem trạng thái và log:

```sh
docker compose --profile dev ps --all
docker compose --profile dev logs --tail 100 gateway user-service court-service booking-service payment-service management-web
docker compose --profile dev logs --tail 100 seed
```

Seed là service chạy một lần trong startup. `Exited (0)` nghĩa là seed thành công; mã thoát khác cần được điều tra trong log. Seed tạo fixture demo theo `backend/database/seed.sql`; chi tiết về mật khẩu và tính idempotent có trong [tài liệu kỹ thuật](docs/PROJECT_DOCUMENTATION.md#4-ca-sử-dụng-và-quy-tắc-nghiệp-vụ).

### Tài khoản demo

Các tài khoản local trong seed:

| Role | Email |
|---|---|
| Admin | `admin@example.com` |
| Owner | `owner1@example.com`, `owner2@example.com`, `owner3@example.com`, `owner4@example.com` |
| Customer | `customer1@example.com` đến `customer10@example.com`, `vy.524h0040@example.com`, `tran.524h0130@example.com` |

Tài khoản **mới được seed** dùng mật khẩu `password123`. Seed không reset password hash của account đã tồn tại; nếu account cũ đã đổi mật khẩu thì dùng password hiện tại của account đó. Chỉ dùng dữ liệu đăng nhập này trên môi trường phát triển local.

## Chạy Android Customer App

Mở thư mục `android-user` bằng Android Studio, chờ Gradle Sync hoàn tất, chọn emulator hoặc thiết bị Android rồi chạy cấu hình `app`. Retrofit lấy địa chỉ từ `BuildConfig.API_BASE_URL`; mặc định và vị trí chỉnh nằm trong `android-user/app/build.gradle.kts`. Có thể override khi build bằng `-PAPI_BASE_URL=<URL>`.

- **Android Emulator:** `http://10.0.2.2:8000/`.
- **Điện thoại thật qua Wi-Fi:** `http://<LAPTOP_LAN_IP>:8000/`; thay placeholder bằng IPv4 hiện tại của laptop. Không ghi IP riêng của một máy vào tài liệu hoặc commit.

Để điện thoại truy cập laptop, root `.env` cần `GATEWAY_BIND_ADDRESS=0.0.0.0`; Compose publish host port `8000` tới container port `8000`. `0.0.0.0` là địa chỉ lắng nghe phía máy chủ, không phải URL Android. USB dùng để cài/chạy/debug; API vẫn đi qua Wi-Fi LAN trừ khi tự cấu hình ADB reverse. Setup không cấu hình Android IP.

Kiểm tra kết nối theo thứ tự:

1. Xem Gateway đang `running` và `healthy`: `docker compose --profile dev ps gateway`.
2. Trên laptop mở <http://127.0.0.1:8000/health>.
3. Lấy IPv4 của adapter Wi-Fi: chạy `ipconfig` trên Windows, `ip -4 addr` trên Linux hoặc `ipconfig getifaddr en0` trên macOS (nếu Wi-Fi dùng interface khác, kiểm tra đúng interface).
4. Trên điện thoại hoặc thiết bị khác cùng Wi-Fi mở `http://<LAPTOP_LAN_IP>:8000/health`.
5. Chỉ sau khi kiểm tra LAN thành công, đặt URL Android thành `http://<LAPTOP_LAN_IP>:8000/` rồi build/cài lại app.

Nếu localhost hoạt động nhưng LAN không, kiểm tra Gateway health, `GATEWAY_BIND_ADDRESS=0.0.0.0`, mapping host `8000` sang container `8000`, IP Wi-Fi hiện tại và router có cho phép thiết bị liên lạc trực tiếp hay không.

Windows Firewall có thể cần rule inbound TCP 8000 trên profile **Private**. Chỉ chạy lệnh dưới đây nếu đã xác định firewall đang chặn; mở PowerShell với quyền phù hợp. Lệnh không tạo lại rule cùng tên:

```powershell
$ruleName = 'Sports Court Booking Gateway TCP 8000'
if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow `
        -Protocol TCP -LocalPort 8000 -Profile Private
}
```

Xem rule bằng `Get-NetFirewallRule -DisplayName 'Sports Court Booking Gateway TCP 8000' | Format-List DisplayName, Enabled, Direction, Action, Profile`. Xóa riêng rule này khi không còn cần bằng `Remove-NetFirewallRule -DisplayName 'Sports Court Booking Gateway TCP 8000'`. Không tắt Windows Firewall.

## Google Login (tùy chọn)

Đăng nhập email/mật khẩu vẫn hoạt động khi Google Login tắt. Implementation Android dùng Google Credential Manager để lấy **ID token**, gửi token tới `POST /api/v1/auth/google`; backend xác minh token bằng Google Auth Library với `GOOGLE_CLIENT_ID` làm audience. Đây không phải luồng web redirect/callback nên không cần cấu hình redirect URI cho flow hiện tại. Tham khảo hướng dẫn chính thức của [Google về ID token Android gửi tới backend](https://developers.google.com/identity/sign-in/android/backend-auth).

1. Mở Google Cloud Console, chọn hoặc tạo project, và hoàn tất phần branding/consent screen theo hướng dẫn hiện tại của Google. Nếu ứng dụng ở trạng thái kiểm thử, thêm tài khoản Google thử vào danh sách test users.
2. Tạo **Web application OAuth Client ID** trong cùng project. Backend xác minh audience bằng Web Client ID; Android cũng yêu cầu ID này để xin ID token.
3. Tạo **Android OAuth Client ID** với package `com.example.sportbooking` và SHA-1 của chứng chỉ dùng để ký bản app. Lấy SHA-1 debug từ thư mục Android bằng `./gradlew signingReport` (Windows: `gradlew.bat signingReport`). Nếu ký bằng khóa khác, đăng ký fingerprint tương ứng.
4. Root `.env` cho Docker: đặt `GOOGLE_LOGIN_ENABLED=true`, `GOOGLE_CLIENT_ID=<WEB_CLIENT_ID>`, cùng Android Client ID/package/SHA-1 nếu setup cần kiểm tra chúng. Chạy User Service host trực tiếp thì cấu hình `backend/.env`.
5. Android local file `android-user/google-oauth.local.properties` cần `GOOGLE_SERVER_CLIENT_ID=<WEB_CLIENT_ID>` và `GOOGLE_LOGIN_ENABLED=true`. Setup helper có thể đồng bộ hai giá trị công khai này khi `.env` hợp lệ. Sau khi đổi, build/cài lại app và khởi động lại backend nếu cấu hình backend đổi.
6. Kiểm tra nút Google xuất hiện, chọn tài khoản test, rồi xác nhận đăng nhập thành công. Lỗi trước khi gọi backend thường liên quan package/SHA-1/OAuth client; lỗi xác minh backend thường liên quan flag hoặc Web Client ID.

| Thông tin | Bí mật? | Nơi dùng |
|---|---|---|
| Web Client ID | Không | Root `GOOGLE_CLIENT_ID`, Android `GOOGLE_SERVER_CLIENT_ID`. |
| Android Client ID | Không | Google Cloud Console; setup có thể dùng để xác thực cấu hình đầu vào. |
| Package name / SHA-1 | Không | Android project và Android OAuth Client registration. |
| Google Client Secret | Có; **không dùng trong implementation này** | Không đặt trong APK, repository hoặc các file cấu hình app. |
| Redirect URI | Không áp dụng cho luồng ID-token hiện tại | Không cấu hình callback web cho flow Android này. |

Mỗi người tự chạy backend cần OAuth config riêng nếu muốn bật Google Login. Nếu chưa cấu hình, tắt Google Login và dùng email/mật khẩu.

## SMTP và email (tùy chọn)

Compose mặc định dùng Mailpit: User Service gửi qua `mailpit-dev:1025`; mở `http://127.0.0.1:8025` để xem thư. Mailpit chỉ lưu thư local, không gửi ra Internet. Forgot Password tạo OTP 6 chữ số có hạn 10 phút.

Muốn gửi Gmail thật, bật xác minh 2 bước trên tài khoản, tạo App Password nếu Google cho phép tài khoản đó, rồi cấu hình trong root `.env`:

```dotenv
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=<GMAIL_ADDRESS>
SMTP_PASSWORD=<GMAIL_APP_PASSWORD>
SMTP_FROM=<GMAIL_ADDRESS>
SMTP_STARTTLS=true
```

Backend yêu cầu username/password cùng có hoặc cùng để trống. Không dùng mật khẩu đăng nhập Gmail thường. Google có thể không cung cấp App Password cho một số tài khoản/chính sách; xem [hướng dẫn App Password chính thức](https://support.google.com/mail/answer/185833?hl=vi) và [cấu hình SMTP Gmail](https://support.google.com/mail/answer/7104828?hl=vi). Khi cấu hình Gmail, chọn phương thức Gmail trong setup nếu `.env` chưa tồn tại để helper điền host/port/STARTTLS phù hợp. Khi `.env` đã tồn tại, sửa file thủ công; setup không ghi lại file.

Nếu chưa cấu hình SMTP, code hiện tại có nhánh phát triển ghi OTP vào log và trả trường `otp_debug`; đây chỉ là fallback local, không phải gửi email. Trong development/test, lỗi SMTP được ghi log và không được xem là gửi thành công. Production trả lỗi dịch vụ khi gửi thất bại. Không bật fallback hoặc dùng Mailpit làm bằng chứng gửi thư thật.

## Kiểm thử

Backend tests (từ repository root, sau khi cài dependencies):

```sh
backend/.venv/bin/python -m pytest -q backend/services/user_service/tests
backend/.venv/bin/python -m pytest -q backend/services/court_service/tests
backend/.venv/bin/python -m pytest -q backend/services/booking_service/tests
backend/.venv/bin/python -m pytest -q backend/services/payment_service/tests
backend/.venv/bin/python -m pytest -q backend/gateway/tests
backend/.venv/bin/python -m pytest -q backend/tests
backend/.venv/bin/python -m pytest -q tests/test_setup_config.py
```

Chạy riêng từng lệnh backend để tránh xung đột tên package `app` giữa các service. Trên Windows thay `backend/.venv/bin/python` bằng `backend\.venv\Scripts\python.exe`. Management Web không có `package.json`; chạy các test Node tích hợp sẵn từ thư mục `management-web`:

```sh
cd management-web
node --test tests/*.test.js
```

Android unit tests chạy từ Android Studio hoặc `gradlew test`; build instrumentation test cần emulator/device. Test tự động không thay cho kiểm tra tích hợp trên stack Docker đang chạy. Khi kiểm tra thủ công, ghi lại lệnh, môi trường và kết quả thực tế; chỉ dùng database local cô lập nếu kịch bản tạo booking hoặc thay đổi dữ liệu.

## Dừng service và dọn dữ liệu an toàn

Các lệnh dưới đây là hướng dẫn, không được chạy tự động bởi tài liệu:

- `docker compose --profile dev stop`: dừng container nhưng giữ container và dữ liệu.
- `docker compose --profile dev down`: xóa container/network của project, giữ named volumes (bao gồm dữ liệu MySQL).
- `docker compose --profile dev down -v`: xóa cả named volumes của project; thao tác này có thể xóa vĩnh viễn database development. Chỉ dùng khi chủ động muốn xóa dữ liệu và đã xác nhận đúng project/volume.

Không dùng `down -v` như cách sửa lỗi khởi động. Trước khi dọn dữ liệu, kiểm tra project và volume; sao lưu nếu dữ liệu cần giữ.

## Xử lý lỗi thường gặp

- **Python không được tìm thấy / phiên bản cũ:** cài Python 3.10+; Linux/macOS launcher thử `python3` rồi `python`.
- **Docker Engine hoặc Compose chưa sẵn sàng:** khởi động Docker Desktop/Engine và kiểm tra `docker info`, `docker compose version`.
- **Cổng đang được dùng:** xem thông báo setup; đổi host port tương ứng trong root `.env` hoặc dừng ứng dụng đang chiếm cổng.
- **Service timeout/unhealthy:** xem `docker compose --profile dev ps --all` và log của service lỗi. Không xóa database volume để bỏ qua lỗi schema/secret.
- **Seed thất bại:** chạy `docker compose --profile dev logs --tail 100 seed`; giải quyết conflict/preflight trước khi thử lại. Chỉ sau khi hiểu và sửa nguyên nhân mới chạy lại riêng seed bằng `docker compose --profile dev up -d seed`.
- **Điện thoại không gọi được API:** kiểm tra Gateway healthy, `GATEWAY_BIND_ADDRESS=0.0.0.0`, mapping `8000:8000`, LAN IPv4 hiện tại, cùng mạng có cho phép client-to-client, và firewall Private profile.
- **Google Login không hiện:** kiểm tra `GOOGLE_LOGIN_ENABLED`, Web Client ID trong Android local properties, Android package/SHA-1 trong Google Cloud và test users nếu consent đang ở chế độ thử nghiệm.
- **Google Login báo token không hợp lệ:** đảm bảo Android xin ID token bằng Web Client ID giống `GOOGLE_CLIENT_ID` của backend; không dùng Android Client ID làm audience backend.
- **Gmail SMTP authentication failed:** kiểm tra `smtp.gmail.com`, cổng `587`, `SMTP_STARTTLS=true`, username/from và App Password; xác nhận 2-Step Verification và chính sách tài khoản cho phép App Password.
- **Gradle Sync/build lỗi:** xem nguyên nhân đầu tiên trong Build Output, kiểm tra JDK/SDK theo Gradle Wrapper; không xóa global Gradle cache như bước xử lý đầu tiên.
- **Compose báo thiếu biến:** xác nhận root `.env` tồn tại và các giá trị bắt buộc đã cấu hình; không dán secret vào issue/log công khai.

## Tài liệu

Tài liệu kỹ thuật dành cho kiến trúc, yêu cầu, API, database, nghiệp vụ và giới hạn hiện tại nằm trong [PROJECT_DOCUMENTATION.md](docs/PROJECT_DOCUMENTATION.md). README này là hướng dẫn duy nhất để cài đặt và chạy dự án. Các file contract và requirements trong `docs/` là tài liệu tham chiếu, không cần mở để làm theo quy trình setup ở đây.

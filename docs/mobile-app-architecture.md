# Taranom Hamdeli mobile app architecture

## Product decision

Build one Flutter application for Android and iOS. The first usable release is
student-first, while the identity and authorization model reserves separate
roles for parents, counselors, and center administrators.

The existing Telegram bot, FastAPI web panels, SQLite database, and Railway
persistent volume remain in service. The mobile app is an additional client,
not a replacement. No existing student records are migrated or deleted.

## Current backend baseline

- FastAPI application is assembled in `app/admin.py`.
- Telegram bot runs alongside Uvicorn from `app/main.py`.
- Existing database helpers and schema live in `app/db.py` and
  `app/migrations.py`.
- SQLite database is configured by `DATABASE_PATH` and currently resides on
  the persistent Railway volume.
- Existing student identity is linked to a Telegram numeric user ID.

## Mobile client

- Flutter, with Android and iOS targets.
- RTL-first Persian interface and accessible typography.
- Local SQLite storage (Drift) for cached plans, downloaded tests, draft
  answers, daily reports, and mood check-ins.
- An outbox stores user actions with client-generated UUIDs.
- Each action is retried safely after reconnect; the server must enforce
  idempotency to prevent duplicate reports or assessment attempts.
- The app displays pending, synced, and failed items and never silently drops
  offline entries.

## Backend boundaries

The app must communicate only through versioned HTTPS endpoints under
`/api/v1/mobile`; it must never connect directly to the SQLite database.

The first foundation endpoints are:
- `GET /api/v1/mobile/health`: connectivity check.
- `GET /api/v1/mobile/capabilities`: supported roles, offline features, and
  sync contract.

No personal-data endpoint is exposed in this foundation change. Before adding
those endpoints, implement account verification through the existing Telegram
bot, short-lived access tokens, refresh-token rotation, role checks, rate
limits, and audit logging. Do not use a Telegram ID or phone number alone as
a password.

## Sync contract

Every queued operation will include:
- `operation_id`: client-generated UUID, unique across retries.
- `operation_type`: e.g. `daily_report.submit` or `assessment.answer`.
- `entity_id`: optional server-side record ID.
- `client_created_at`: timestamp with timezone.
- `payload`: validated operation data.

The server records processed operation IDs and returns the canonical server
record plus sync status. Replaying an operation ID returns the original result
instead of creating a duplicate. Conflicting edits must be returned explicitly
for reconciliation; last-write-wins must not silently overwrite counselor
plans or sensitive assessment records.

## Delivery phases

1. Backend contract and safe authentication.
2. Student Flutter shell, registration/activation, profile, and dashboard.
3. Offline plan cache, daily report, local queue, and sync.
4. Downloadable assessments and offline answer capture.
5. Parent, counselor, and admin roles and screens.
6. Notifications, security review, device testing, and store distribution.

## Privacy and safety

- Enforce ownership and role permissions server-side on every request.
- Store only the minimum local data needed for offline use.
- Encrypt sensitive local data and clear protected caches on logout where
  appropriate.
- Keep psychological assessment details behind explicit permissions.
- Use HTTPS, secure token storage, backups, and audit logs.
- Do not expose AI provider keys or database credentials in the mobile app.

## آزمون محلی نسخه ۱۴

APK امضاشدهٔ شاخهٔ `feature/mobile-app-foundation` در محیط آزمایشی از API حلقهٔ محلی استفاده می‌کند. برای اجرای آن روی تلفن دارای USB debugging یا شبیه‌ساز، از ریشهٔ مخزن اجرا کنید.

```bash
python -m venv .venv
.venv/bin/python -m pip install 'fastapi>=0.115' uvicorn
.venv/bin/python -m tools.mobile_test_api
```

در ترمینال دیگری اجرا کنید.

```bash
adb reverse tcp:8765 tcp:8765
adb install -r app-debug.apk
```

با کد چاپ‌شده در ترمینال وارد حساب ساختگی شوید. برنامهٔ مشاور را باز کنید، API را موقتاً از دسترس گوشی خارج کنید (`adb reverse --remove tcp:8765`) و یک گزارش جدید ثبت کنید. سپس مسیر `adb reverse` را برقرار کنید و منتظر تلاش خودکار بعدی بمانید یا ارسال را از صفحهٔ گزارش‌ها بزنید. وضعیت گزارش باید به «همگام‌شده» تغییر کند. پایگاه موقت سرور با پایان اجرای آن حذف می‌شود و پس از اجرای مجدد، کد ورود تازه صادر می‌شود.

«باز کردن داشبورد آفلاین» داده‌های قبلی را در همان قالب ذخیره‌سازی نسخهٔ ۱۳ نمایش می‌دهد. گزارش‌های این داشبورد پیشین در همان بخش باقی می‌مانند. گزارش‌های تازهٔ بخش حساب آزمایشی پس از تأیید شناسهٔ رویداد توسط API، همگام‌شده علامت می‌خورند.

در ساخت متصل به سامانه، ورود با تأیید حساب تلگرام دانش‌آموز انجام می‌شود و `API_BASE_URL` باید HTTPS باشد. مسیر ورود با کد فقط در سرور محلی و APK آزمایشی فعال است.

## قرارداد اتصال نسخه ۱۵

ساخت آزمایشی `0.15.0+43` به سرور محلی وصل می‌شود. تنظیمات ساخت متصل به سامانه مستلزم تعیین صریح مبدأ HTTPS در `API_BASE_URL` و حذف `APEX_LOCAL_TEST` است. این نسخه با سامانهٔ فعال اعتبارسنجی نشده است.

| مسیر زیر `/api/v1/mobile` | قرارداد |
| --- | --- |
| `POST /auth/challenge` و `POST /auth/challenge/{challenge_id}` | ایجاد چالش کوتاه‌مدت و دریافت توکن پس از تأیید حساب دانش‌آموز ثبت‌شده در ربات |
| `POST /auth/refresh` و `POST /auth/logout` | چرخش توکن تجدید و ابطال نشست با توکن‌های همان نشست |
| `GET /student/profile` | پروفایل حداقلی دانش‌آموز صاحب توکن |
| `GET /student/counselor` | `{"assignment":null,"plan":null}` برای دانش‌آموز بدون مشاور. در صورت تخصیص، `assignment` شامل `id`، `name` و `assigned_at` است. آخرین برنامهٔ همان تخصیص در `plan` با `id`، `title`، `created_at` و `schedule` بازمی‌گردد. هر بلوک به شکل `[روز، دقیقه شروع، دقیقه پایان، درس]` است. پیش از نخستین انتشار، `plan` برابر `null` است. |
| `POST /student/study-activities/sync` | گزارش‌های همان حساب، حداکثر ۵۰ فعالیت در هر درخواست. تکرار گزارش با همان شناسه و محتوا تنها یک بار ثبت می‌شود. تغییر محتوا با همان شناسه پاسخ ۴۰۹ دارد. فقط شناسه‌های تأییدشده در `accepted_event_ids` از صف خارج می‌شوند. |

پروفایل، برنامه و ارسال گزارش از توکن Bearer استفاده می‌کنند. خطای اعتبار توکن با یک تلاش برای تجدید نشست مدیریت می‌شود. تغییر تخصیص، برنامهٔ مشاور قبلی را از پاسخ جاری کنار می‌گذارد. برنامهٔ شخصی و داده‌های قبلی در داشبورد آفلاین و با کلید `apex360_offline_v1` باقی می‌مانند.

برای آزمایش، در دستور نصب نسخهٔ ۱۴، بسته‌های `python-multipart` و `itsdangerous` را هم نصب کنید. سرور محلی کد ورود دانش‌آموز و مشخصات ورود مشاور ساختگی را چاپ می‌کند. از `http://127.0.0.1:8765/counselor/login` وارد پنل مشاور شوید. در پروندهٔ دانش‌آموز آزمایشی برنامه‌ای جدید منتشر کنید، آن را در تب «برنامه مشاور» دریافت کنید و گزارش ثبت‌شده در گوشی را پس از اتصال دوباره در پرونده ببینید.

## قرارداد و نمایش نسخه ۱۶

نسخهٔ `0.16.0+44` بر پایهٔ `dd9cca1` است. مسیرهای زیر به قرارداد
`/api/v1/mobile` افزوده شده‌اند. این قرارداد با بک‌اند همین شاخه و
پایگاه موقت آزموده شده است. تأیید قرارداد و استقرار در سامانهٔ مرکزی هنوز انجام نشده‌اند.

| مسیر | درخواست و پاسخ |
| --- | --- |
| `GET /capabilities` | دو قابلیت `plan_receipts` و `report_feedback` اعلام می‌شوند. |
| `GET /student/counselor` | در آبجکت `plan`، فیلد `received_at` زمان UTC تأیید دریافت است و پیش از تأیید `null` است. |
| `POST /student/counselor/plans/{plan_id}/receipt` | بدون بدنه و با Bearer دانش‌آموز. پاسخ `{plan_id, received_at}` است. تکرار درخواست همان زمان اولیه را برمی‌گرداند. برنامهٔ حساب دیگر یا تخصیص پایان‌یافته پاسخ ۴۰۴ دارد. |
| `POST /student/study-activities/sync` | قرارداد نسخهٔ ۱۵ حفظ می‌شود. سرور هر شناسهٔ تأییدشده را فقط یک بار در پاسخ فهرست می‌کند. |
| `GET /student/study-activities/feedback` | با Bearer دانش‌آموز. پاسخ `{feedback: [{event_id, subject, message, updated_at, counselor_name}]}` شامل حداکثر ۴۵ بازخورد تخصیص فعال است. |
| `POST /counselor/student/{student_id}/feedback` | مسیر وب پنل با نشست مشاور، توکن فرم، `event_id` و `message` (حداکثر ۱۰۰۰ نویسه). نوشتن به تخصیص فعال و گزارش همان دانش‌آموز محدود می‌شود. ارسال دوباره بازخورد همان گزارش را ویرایش می‌کند. |

ثبت‌نام واقعی در ربات رسمی و تخصیص مشاور در پنل مدیر موجود انجام
می‌شود. ورود متصل به تأیید تلگرام و مبدأ HTTPS نیاز دارد. پایگاه داده
با مهاجرت افزایشی ۸ جدول تأیید دریافت و جدول بازخورد را اضافه می‌کند.
داشبورد شخصی همچنان از `apex360_offline_v1` استفاده می‌کند. صف رمزگذاری‌شدهٔ
حساب با کلید قبلی باقی می‌ماند و فقط شناسه‌های تأییدشده از صف ارسال خارج می‌شوند.

### اجرای سناریوی همایش

1. از ریشهٔ مخزن با وابستگی‌های نسخهٔ ۱۵، `python -m tools.mobile_test_api`
   را اجرا کنید. سرور فقط روی `127.0.0.1:8765` گوش می‌دهد و پایگاه دادهٔ
   موقت می‌سازد. کد راه‌اندازی، کد ورود دانش‌آموز و رمز مشاور جداگانه
   در همان ترمینال چاپ می‌شوند.
2. روی رایانه به `http://127.0.0.1:8765/demo` بروید. با کد راه‌اندازی،
   دانش‌آموز ساختگی را ثبت کنید. با همان کد، مشاور آزمایشی را تخصیص دهید.
3. گوشی را با USB debugging وصل کنید و `adb reverse tcp:8765 tcp:8765`
   را اجرا کنید. APK امضاشده را با `adb install -r app-debug.apk`
   روی نسخهٔ قبلی نصب کنید. با کد ورود دانش‌آموز آزمایشی وارد شوید.
4. از `http://127.0.0.1:8765/counselor/login` وارد پنل مشاور ساختگی
   شوید. در پرونده، برنامه‌ای با سطر نمونهٔ `شنبه | 16:00 | 16:45 | ریاضی`
   منتشر کنید. در گوشی تب «برنامه مشاور» را باز و «تأیید دریافت برنامه»
   را بزنید. پس از تازه‌سازی پرونده در مرورگر، وضعیت تأیید را ببینید.
5. برای نمایش آفلاین، `adb reverse --remove tcp:8765` را اجرا کنید
   و در گوشی گزارشی ثبت کنید. بعد از وصل‌کردن مجدد با دستور مرحلهٔ ۳،
   ارسال دستی را بزنید یا برای تلاش خودکار صبر کنید. گزارش در پنل مشاور
   یک بار نمایش داده می‌شود. برای همان گزارش بازخورد بفرستید و در تب
   «گزارش‌ها» روی «دریافت بازخورد» بزنید.
6. برای مرور داده‌های قبلی، «باز کردن داشبورد آفلاین» را انتخاب کنید.

برای حفظ سناریو در طول نمایش، سرور محلی را روشن نگه دارید. هر بار اجرای
سرور یک حساب ساختگی تازه ایجاد می‌کند و گزارش‌های محلی اجرای قبلی را
به حساب تازه ارسال نمی‌کند.

## نسخهٔ ۱۷ و نمایش ۱۸ آذر

نسخهٔ `0.17.0+45` به‌صورت پیش‌فرض برای نمایش روی API حلقهٔ محلی ساخته می‌شود.
برای ساخت متصل، گردش‌کار GitHub Actions را روی شاخهٔ
`feature/mobile-app-foundation` با ورودی `api_origin` اجرا کنید. ورودی
باید مبدأ HTTPS تأییدشدهٔ محیط آزمایشی باشد. این ساخت ورود با کد محلی
را فعال نمی‌کند. اپ پیش از درخواست تأیید تلگرام،
`GET /api/v1/mobile/capabilities` را بررسی می‌کند و به
`api_version: 1`، `student_workflow_version: 17` و قابلیت‌های تخصیص،
تأیید برنامه و بازخورد نیاز دارد.

محیط متصل باید از همین قرارداد، مهاجرت ۸، پنل مدیریت و پنل مشاور و
تأیید ورود در ربات رسمی پشتیبانی کند. مدیر از پروندهٔ دانش‌آموز
مشاور فعال را تخصیص می‌دهد. فرم تخصیص از نشست مدیر و توکن فرم
استفاده می‌کند. ثبت دوبارهٔ مشاور فعلی، برنامه و بازخورد همان تخصیص
را حفظ می‌کند. مسیرهای خصوصی پاسخ `no-store` دارند و کوکی نشست
در برنامهٔ سرور مرکزی فقط روی HTTPS ارسال می‌شود.

برای سناریوی محلی، دستورهای بخش نسخهٔ ۱۶ را اجرا کنید. در مرحلهٔ ۲
فقط ثبت‌نام ساختگی را در `/demo` انجام دهید. سپس از پیوند پرونده در
همان صفحه وارد پنل مدیر شوید و با نام کاربری و رمز آزمایشی چاپ‌شده
در ترمینال، مشاور آزمایشی را تخصیص دهید. پنل مشاور را در پنجرهٔ
خصوصی یا نمایهٔ دیگری باز کنید تا نشست مدیر و مشاور مستقل بماند.
باقی مراحل دریافت برنامه، قطع و وصل اتصال، ارسال گزارش و دریافت
بازخورد با همان دستورهای نسخهٔ ۱۶ انجام می‌شوند.

آزمون یکپارچه از پایگاه موقت، مسیر واقعی پنل مدیر و فرم مشاور، و
توابع سرور برای تأیید هویت تلگرام استفاده می‌کند. تأیید تلگرام در
آزمون از طریق فراخوانی تابع سمت سرور شبیه‌سازی می‌شود. برای اثبات
اتصال واقعی به ترنم همدلی، مبدأ HTTPS مجاز با بک‌اند نسخهٔ ۱۷ و
حساب‌های آزمایشی دانش‌آموز، مدیر و مشاور لازم است.

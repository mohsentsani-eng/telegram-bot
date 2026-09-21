# اجرای ۲۴ ساعته بات ترنم همدلی روی Railway

این نسخه برای اجرای دائمی یک پردازش Python/aiogram آماده شده است.

## متغیرهای ضروری
در Railway > Service > Variables این موارد را بسازید:

- `BOT_TOKEN` = توکن BotFather
- `GEMINI_API_KEY` = کلید Google Gemini
- `AI_ENABLED` = `true`
- `REQUIRED_CHANNEL_ID` = `@tarnoomhamdeli`
- `REQUIRED_CHANNEL_URL` = `https://t.me/tarnoomhamdeli`
- `ADMIN_USERNAME` = نام کاربری پنل
- `ADMIN_PASSWORD` = یک رمز قوی
- `ADMIN_SECRET` = یک رشته تصادفی طولانی
- `DATABASE_PATH` = `./data/taranom.db`

`PORT` را دستی تنظیم نکنید؛ Railway آن را فراهم می‌کند و برنامه از آن استفاده می‌کند.

## اجرا
1. وارد Railway شوید.
2. یک Project بسازید و `Deploy from GitHub repo` یا آپلود پروژه را انتخاب کنید.
3. این پروژه را Deploy کنید.
4. در Variables کلیدهای بالا را وارد کنید. Railway متغیرها را در زمان اجرای سرویس در اختیار برنامه می‌گذارد.
5. سرویس باید به‌صورت Long-running Service اجرا شود؛ Start Command این نسخه: `python -m app.main` است.

## نکته مهم دیتابیس
این بات از SQLite استفاده می‌کند. برای نگهداری پایدار `data/taranom.db` در محیط ابری، در Railway یک Volume روی مسیر `/app/data` متصل کنید. بدون دیسک پایدار، ممکن است فایل SQLite با بعضی redeployها/تغییرات محیط از بین برود.

## کانال
بات باید در کانال `@tarnoomhamdeli` ادمین باشد تا بتواند عضویت کاربران را بررسی کند و پیام روزانه را منتشر کند.

## امنیت
توکن Bot و کلید Gemini را داخل GitHub، ZIP عمومی یا کد قرار ندهید؛ فقط به‌عنوان Environment Variable وارد کنید.


## تنظیم پیشنهادی نهایی برای اجرای ۲۴ساعته

1. در Railway یک Service از همین ZIP/Repository بسازید.
2. در Variables این مقادیر را وارد کنید: `BOT_TOKEN`، `GEMINI_API_KEY`، `AI_ENABLED=true`، `REQUIRED_CHANNEL_ID=@tarnoomhamdeli`، `REQUIRED_CHANNEL_URL=https://t.me/tarnoomhamdeli` و `DAILY_MESSAGE_TIMEZONE=Asia/Tehran`.
3. در Service → Volumes یک Volume بسازید و آن را دقیقاً روی `/app/data` Mount کنید. این کار برای حفظ SQLite، پرونده دانش‌آموزان، وضعیت پیام روزانه و داده‌های بات بعد از Restart/Deploy ضروری است.
4. Serverless/Sleep را برای Service خاموش نگه دارید؛ بات باید همیشه روشن باشد.
5. Start Command: `python -m app.main`
6. Bot باید در کانال `@tarnoomhamdeli` دسترسی Administrator و اجازه Post Messages داشته باشد.
7. زمان پیام روزانه پیش‌فرض 09:00 به وقت تهران است. اگر بات در ساعت 09:00 خاموش بوده باشد، پس از برگشت به سرویس پیام همان روز را منتشر می‌کند و اگر ارسال با خطای تلگرام مواجه شود، هر دقیقه دوباره تلاش می‌کند.

### هزینه
برای اجرای دائمی، Railway Free فقط $1 اعتبار منابع ماهانه دارد و برای سرویس همیشه‌روشن محدود است. Hobby ماهانه $5 است و این مبلغ به مصرف منابع اختصاص می‌یابد؛ برای یک بات سبک معمولاً گزینه ساده و کم‌دردسر است. برای کاهش هزینه، مصرف CPU/RAM را پایین نگه دارید و Usage Hard Limit بگذارید.

### نکته امنیتی
`BOT_TOKEN` و `GEMINI_API_KEY` را داخل کد، ZIP عمومی یا GitHub قرار ندهید؛ فقط در Railway Variables ذخیره کنید.

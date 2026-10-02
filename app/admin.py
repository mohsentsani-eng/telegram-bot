import os
import csv
import io
import secrets
import html
import json

from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from starlette.middleware.sessions import SessionMiddleware

from . import db


app = FastAPI(title="Taranom Hamdeli Admin")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("ADMIN_SECRET", "change-me"),
)


def esc(x):
    return html.escape(str(x or ""))


def auth(req: Request):
    return bool(req.session.get("admin"))


def guard(req: Request):
    return None if auth(req) else RedirectResponse("/admin/login", status_code=303)


def page(title: str, body: str) -> HTMLResponse:
    nav = """
    <div class="nav">
      <a href="/admin">داشبورد</a>
      <a href="/admin/students">دانش‌آموزان</a>
      <a href="/admin/questions">بانک سؤال</a>
      <a href="/admin/question/new">افزودن سؤال</a>
      <a href="/admin/import">ورود CSV</a>
      <a href="/admin/csv-template">قالب CSV</a>
      <a href="/admin/requests">درخواست‌ها</a>
      <a href="/admin/daily-reports">🌙 گزارش روزانه</a>
      <a href="/admin/counselors">👨‍🏫 مشاوران</a>
      <a href="/admin/marketing">📣 آمار بازاریابی</a>
      <a href="/admin/crm">📇 CRM و پیگیری</a>
      <a href="/admin/registrations">💰 ثبت‌نام خدمات</a>
      <a href="/admin/kpi">📈 KPI تیم</a>
      <a href="/admin/access">🔐 دسترسی و تمدید</a>
    </div>
    """

    css = """
    body{font-family:Tahoma,Arial,sans-serif;max-width:1400px;margin:24px auto;
         padding:0 16px;background:#f6f7fb;color:#222;line-height:1.8}
    .nav{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px}
    .nav a,.btn{background:#fff;padding:9px 13px;border-radius:10px;
                text-decoration:none;color:#1557b0;border:1px solid #e5e7eb}
    .btn.primary,button{background:#1557b0;color:#fff;border:0;cursor:pointer}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
    .card{background:#fff;padding:18px;border-radius:14px;border:1px solid #e5e7eb}
    .n{font-size:30px;font-weight:bold}
    table{width:100%;border-collapse:collapse;background:#fff}
    th,td{padding:8px;border-bottom:1px solid #eee;text-align:right;font-size:13px;vertical-align:top}
    input,select,textarea{width:100%;box-sizing:border-box;padding:9px;margin:4px 0 10px;
                           border:1px solid #d0d5dd;border-radius:8px;font-family:inherit}
    textarea{min-height:100px}
    button{padding:10px 18px;border-radius:9px;font-family:inherit}
    .muted{color:#667085;font-size:13px}
    .ok{background:#ecfdf3;color:#027a48;padding:12px;border-radius:10px}
    .warn{background:#fffaeb;color:#b54708;padding:12px;border-radius:10px}
    .err{background:#fef3f2;color:#b42318;padding:12px;border-radius:10px}
    .code{direction:ltr;text-align:left;background:#111827;color:#e5e7eb;
          padding:12px;border-radius:10px;overflow:auto}
    .actions{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}
    """

    html_doc = f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<style>{css}</style>
</head>
<body>
{nav}
{body}
</body>
</html>"""

    # Explicitly return HTMLResponse so browsers never render the HTML source as plain text.
    return HTMLResponse(content=html_doc, media_type="text/html; charset=utf-8")


@app.get("/admin/login", response_class=HTMLResponse)
def login_page():
    return HTMLResponse(
        """<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <body style="font-family:Tahoma;max-width:420px;margin:80px auto">
        <h2>ورود مدیر ترنم همدلی</h2>
        <form method="post">
        <input name="username" placeholder="نام کاربری" required>
        <input type="password" name="password" placeholder="رمز عبور" required>
        <button style="padding:10px 18px">ورود</button>
        </form></body></html>""",
        media_type="text/html; charset=utf-8",
    )


@app.post("/admin/login")
def login(
    req: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    good_user = secrets.compare_digest(
        username, os.getenv("ADMIN_USERNAME", "admin")
    )
    good_pass = secrets.compare_digest(
        password, os.getenv("ADMIN_PASSWORD", "change-me")
    )

    if good_user and good_pass:
        req.session["admin"] = True
        return RedirectResponse("/admin", status_code=303)

    return page(
        "خطای ورود",
        "<div class='err'><h2>نام کاربری یا رمز عبور اشتباه است.</h2>"
        "<a class='btn' href='/admin/login'>بازگشت</a></div>",
    )


@app.get("/admin", response_class=HTMLResponse)
def dashboard(req: Request):
    if (g := guard(req)):
        return g

    s = db.stats()
    body = f"""
    <h1>داشبورد مدیریت ترنم همدلی</h1>
    <div class="grid">
      <div class="card">دانش‌آموزان<div class="n">{s.get('students', 0)}</div></div>
      <div class="card">سؤالات فعال<div class="n">{s.get('questions', 0)}</div></div>
      <div class="card">ارزیابی‌ها<div class="n">{s.get('assessments', 0)}</div></div>
      <div class="card">درخواست‌های جدید<div class="n">{s.get('requests', 0)}</div></div>
    </div>
    <div class="actions">
      <a class="btn" href="/admin/marketing">📣 قیف جذب و لینک‌های کمپین</a>
      <a class="btn" href="/admin/daily-reports">🌙 گزارش روزانه و پیگیری مشاور</a>
      <a class="btn" href="/admin/questions/cleanup">🧹 قرنطینه تکراری‌های بانک</a>
      <a class="btn" href="/admin/questions/report">📊 گزارش پوشش مباحث</a>
    </div>
    <p class="muted">ورود CSV فقط اضافه می‌کند و داده‌های دانش‌آموزان را حذف نمی‌کند. پاک‌سازی تکراری‌ها یک عملیات جدا و قابل مشاهده است.</p>
    """
    return page("داشبورد", body)


@app.get("/admin/marketing", response_class=HTMLResponse)
def marketing(req: Request):
    if (g := guard(req)):
        return g

    m = db.marketing_stats()
    bot_username = os.getenv("BOT_USERNAME", "").strip().lstrip("@")
    base = f"https://t.me/{bot_username}" if bot_username else "https://t.me/YOUR_BOT_USERNAME"
    sources = m.get("sources", [])
    rows = ""
    for x in sources:
        rows += (
            f"<tr><td>{esc(x['source'])}</td><td>{x['starts']}</td>"
            f"<td>{x['registrations']}</td><td>{x['quick_completed']}</td>"
            f"<td>{x['channel_joins']}</td><td>{x['counseling_requests']}</td><td>{x['instagram_clicks']}</td></tr>"
        )

    campaigns = [
        ("پوستر گروه‌ها", "group_poster"),
        ("کانال والدین", "parent_channels"),
        ("کانال دانش‌آموزی", "student_channels"),
        ("اینستاگرام", "instagram"),
        ("پوستر مرکز", "center_poster"),
        ("معرفی دوستان", "share"),
    ]
    links = "".join(
        f"<tr><td>{esc(title)}</td><td><code>{esc(base+'?start='+code)}</code></td></tr>"
        for title, code in campaigns
    )

    body = f"""
    <h1>📣 قیف جذب و بازاریابی</h1>
    <div class="grid">
      <div class="card">شروع‌ها<div class="n">{m.get('starts',0)}</div></div>
      <div class="card">ثبت‌نام کامل<div class="n">{m.get('registrations',0)}</div></div>
      <div class="card">ارزیابی سریع کامل<div class="n">{m.get('quick_completed',0)}</div></div>
      <div class="card">عضویت تأییدشده کانال<div class="n">{m.get('channel_joins',0)}</div></div>
      <div class="card">درخواست مشاوره<div class="n">{m.get('counseling_requests',0)}</div></div>
      <div class="card">بازدید از مسیر اینستاگرام<div class="n">{m.get('instagram_views',0)}</div></div>
      <div class="card">کلیک ورود به اینستاگرام<div class="n">{m.get('instagram_clicks',0)}</div></div>
      <div class="card">بازگشت به بات<div class="n">{m.get('instagram_returned',0)}</div></div>
    </div>

    <h2>لینک‌های آماده کمپین</h2>
    <p class="muted">هر لینک منبع متفاوتی ثبت می‌کند تا بعداً مشخص شود کدام کانال/پوستر کاربر بیشتری آورده است.</p>
    <table><tr><th>کمپین</th><th>لینک</th></tr>{links}</table>

    <h2>عملکرد هر منبع</h2>
    <table>
      <tr><th>منبع</th><th>شروع</th><th>ثبت‌نام</th><th>ارزیابی سریع</th><th>عضویت کانال</th><th>درخواست مشاوره</th><th>اینستاگرام</th></tr>
      {rows if rows else '<tr><td colspan="7">هنوز داده‌ای ثبت نشده است.</td></tr>'}
    </table>

    <p class="muted">
      نکته: این آمار بر اساس رویدادهای ثبت‌شده در ربات است. یک کاربر می‌تواند چند بار /start بزند؛
      بنابراین «شروع‌ها» با «افراد یکتا» یکسان نیست.
    </p>
    """
    return page("آمار بازاریابی", body)


@app.get("/admin/students", response_class=HTMLResponse)
def students(req: Request):
    if (g := guard(req)):
        return g

    rows = db.list_students()
    trs = "".join(
        f"<tr><td><a href='/admin/student/{r['id']}'>{r['id']}</a></td>"
        f"<td>{esc(r['first_name'])} {esc(r['last_name'])}</td>"
        f"<td>{esc(r['grade'])}</td><td>{esc(r['track'])}</td>"
        f"<td>{esc(r['city'])}</td><td>{esc(r['phone'])}</td>"
        f"<td>{esc(r['referral_source'])}</td></tr>"
        for r in rows
    )

    body = (
        "<h1>پرونده دانش‌آموزان</h1>"
        "<table><tr><th>ID</th><th>نام</th><th>پایه</th><th>رشته</th>"
        "<th>شهر</th><th>تلفن</th><th>منبع جذب</th></tr>"
        + trs
        + "</table>"
    )
    return page("دانش‌آموزان", body)


@app.get("/admin/student/{sid}", response_class=HTMLResponse)
def student(req: Request, sid: int):
    if (g := guard(req)):
        return g

    s = db.get_student(sid)
    if not s:
        return page("یافت نشد", "<div class='err'>دانش‌آموز یافت نشد.</div>")

    snap = db.student_snapshot(sid)

    mastery = "".join(
        f"<tr><td>{esc(x['subject'])}</td>"
        f"<td>{esc(x['chapter'])}</td><td>{esc(x['topic'])}</td>"
        f"<td>{round(x['mastery_score']*100)}٪</td>"
        f"<td>{x['attempts']}</td></tr>"
        for x in snap["mastery"]
    )

    body = f"""
    <h1>{esc(s['first_name'])} {esc(s['last_name'])}</h1>
    <p>پایه: {esc(s['grade'])} | رشته: {esc(s['track'])} |
       شهر: {esc(s['city'])} | تلفن: {esc(s['phone'])}</p>
    <p>منبع جذب: {esc(s['referral_source'])} | امتیاز: {s['points']}</p>
    <h2>تسلط در مباحث</h2>
    <table><tr><th>درس</th><th>فصل</th><th>مبحث</th><th>تسلط</th><th>تلاش</th></tr>
    {mastery}</table>
    <p>تعداد ارزیابی‌ها: {len(snap['assessments'])} |
       روان‌شناختی: {len(snap['psych'])} |
       مهارت یادگیری: {len(snap['learning'])}</p>
    """
    return page("پرونده دانش‌آموز", body)


@app.get("/admin/questions", response_class=HTMLResponse)
def questions(req: Request):
    if (g := guard(req)):
        return g

    rows = db.list_questions()

    trs = "".join(
        f"<tr><td>{r['id']}</td><td>{esc(r['grade'])}</td>"
        f"<td>{esc(r['track'])}</td><td>{esc(r['subject'])}</td>"
        f"<td>{esc(r['chapter'])}</td><td>{esc(r['topic'])}</td>"
        f"<td>{esc(r['difficulty'])}</td><td>{esc(r['source'])}</td></tr>"
        for r in rows
    )

    body = (
        f"<h1>بانک سؤال</h1><p>تعداد: {len(rows)}</p>"
        "<table><tr><th>ID</th><th>پایه</th><th>رشته</th><th>درس</th>"
        "<th>فصل</th><th>مبحث</th><th>سطح</th><th>منبع</th></tr>"
        + trs + "</table>"
    )
    return page("بانک سؤال", body)


@app.get("/admin/question/new", response_class=HTMLResponse)
def qnew(req: Request):
    if (g := guard(req)):
        return g

    body = """
    <h1>افزودن سؤال</h1>
    <form method="post">
      <input name="grade" placeholder="پایه" required>
      <input name="track" placeholder="رشته">
      <input name="subject" placeholder="درس" required>
      <input name="book" placeholder="کتاب">
      <input name="chapter" placeholder="فصل">
      <input name="topic" placeholder="مبحث">
      <input name="subtopic" placeholder="زیرمبحث">
      <input name="difficulty" value="متوسط" placeholder="سطح">
      <textarea name="question" placeholder="متن سؤال" required></textarea>
      <input name="option_a" placeholder="گزینه A" required>
      <input name="option_b" placeholder="گزینه B" required>
      <input name="option_c" placeholder="گزینه C" required>
      <input name="option_d" placeholder="گزینه D" required>
      <input name="correct_option" placeholder="پاسخ صحیح: A/B/C/D یا 1/2/3/4" required>
      <textarea name="explanation" placeholder="پاسخ تشریحی/نکته آموزشی"></textarea>
      <input name="source" placeholder="منبع">
      <input name="source_type" value="original" placeholder="نوع منبع">
      <input name="source_year" placeholder="سال">
      <button type="submit">ثبت سؤال</button>
    </form>
    """
    return page("افزودن سؤال", body)


@app.post("/admin/question/new")
async def qnew_post(req: Request):
    if (g := guard(req)):
        return g

    form = dict(await req.form())
    try:
        added = db.insert_question(form)
        if not added:
            return page("سؤال تکراری", "<div class='warn'><h2>این سؤال قبلاً در بانک وجود دارد.</h2><a class='btn' href='/admin/questions'>بانک سؤال</a></div>")
        return RedirectResponse("/admin/questions", status_code=303)
    except Exception as e:
        return page(
            "خطای ثبت سؤال",
            f"<div class='err'><h2>ثبت سؤال انجام نشد.</h2>"
            f"<pre class='code'>{esc(e)}</pre></div>",
        )


# ---------- CSV ----------

CANONICAL_FIELDS = [
    "grade", "track", "subject", "book", "chapter", "topic", "subtopic",
    "difficulty", "question", "option_a", "option_b", "option_c", "option_d",
    "correct_option", "explanation", "source", "source_type", "source_year",
]

PERSIAN_FIELDS = [
    "پایه", "رشته", "درس", "کتاب", "فصل", "مبحث", "زیرمبحث", "سطح",
    "متن سوال", "گزینه 1", "گزینه 2", "گزینه 3", "گزینه 4", "پاسخ",
    "توضیح", "منبع", "نوع منبع", "سال",
]

ALIASES = {
    "grade": ["grade", "پایه", "پايه"],
    "track": ["track", "رشته"],
    "subject": ["subject", "درس"],
    "book": ["book", "کتاب"],
    "chapter": ["chapter", "فصل"],
    "topic": ["topic", "مبحث"],
    "subtopic": ["subtopic", "زیرمبحث", "زيرمبحث"],
    "difficulty": ["difficulty", "سطح"],
    "question": ["question", "سؤال", "سوال", "متن سوال", "متن سؤال"],
    "option_a": ["option_a", "گزینه a", "گزينه a", "گزینه 1", "گزينه 1"],
    "option_b": ["option_b", "گزینه b", "گزينه b", "گزینه 2", "گزينه 2"],
    "option_c": ["option_c", "گزینه c", "گزينه c", "گزینه 3", "گزينه 3"],
    "option_d": ["option_d", "گزینه d", "گزينه d", "گزینه 4", "گزينه 4"],
    "correct_option": [
        "correct_option", "correct", "answer", "پاسخ", "پاسخ صحیح",
        "گزینه صحیح", "correct option"
    ],
    "explanation": ["explanation", "توضیح", "پاسخ تشریحی", "پاسخ تشریحی/نکته آموزشی"],
    "source": ["source", "منبع"],
    "source_type": ["source_type", "نوع منبع"],
    "source_year": ["source_year", "سال", "سال منبع"],
}


def norm_header(s):
    s = str(s or "").strip().lower()
    s = s.replace("\ufeff", "")
    s = s.replace("ي", "ی").replace("ك", "ک")
    s = " ".join(s.split())
    return s


def normalize_row(raw):
    normalized_headers = {norm_header(k): k for k in raw.keys() if k is not None}
    out = {}

    for canonical, candidates in ALIASES.items():
        value = ""
        for candidate in candidates:
            real_key = normalized_headers.get(norm_header(candidate))
            if real_key is not None:
                value = raw.get(real_key, "")
                break
        out[canonical] = str(value or "").strip()

    # Normalize answer: A/B/C/D or 1/2/3/4 -> A/B/C/D
    ans = out["correct_option"].strip().upper()
    ans_map = {
        "۱": "A", "1": "A", "A": "A",
        "۲": "B", "2": "B", "B": "B",
        "۳": "C", "3": "C", "C": "C",
        "۴": "D", "4": "D", "D": "D",
    }
    out["correct_option"] = ans_map.get(ans, ans)

    if not out["difficulty"]:
        out["difficulty"] = "متوسط"
    if not out["source_type"]:
        out["source_type"] = "original"

    return out


def existing_question(question, grade, subject):
    """
    Check only for an exact duplicate in the existing questions table.
    Never deletes or overwrites anything.
    """
    if not question:
        return False

    try:
        c = db.conn()
        row = c.execute(
            "SELECT id FROM questions "
            "WHERE question = ? AND COALESCE(grade,'') = ? "
            "AND COALESCE(subject,'') = ? LIMIT 1",
            (question, grade or "", subject or ""),
        ).fetchone()
        c.close()
        return row is not None
    except Exception:
        # If the installed DB schema differs, do not block a valid import.
        return False


def validate_row(r):
    missing = []
    for key, label in [
        ("grade", "پایه"),
        ("subject", "درس"),
        ("question", "متن سؤال"),
        ("option_a", "گزینه 1"),
        ("option_b", "گزینه 2"),
        ("option_c", "گزینه 3"),
        ("option_d", "گزینه 4"),
        ("correct_option", "پاسخ"),
    ]:
        if not r.get(key):
            missing.append(label)

    if r.get("correct_option") not in {"A", "B", "C", "D"}:
        missing.append("پاسخ باید A/B/C/D یا 1/2/3/4 باشد")

    return missing


@app.get("/admin/csv-template")
def csv_template(req: Request):
    if (g := guard(req)):
        return g

    sample = {
        "پایه": "ششم",
        "رشته": "عمومی",
        "درس": "ریاضی",
        "کتاب": "ریاضی ششم",
        "فصل": "عدد و الگو",
        "مبحث": "الگوهای عددی",
        "زیرمبحث": "",
        "سطح": "متوسط",
        "متن سوال": "عدد بعدی در الگوی 2، 5، 8، ... کدام است؟",
        "گزینه 1": "11",
        "گزینه 2": "10",
        "گزینه 3": "12",
        "گزینه 4": "13",
        "پاسخ": "1",
        "توضیح": "هر بار 3 واحد اضافه می‌شود.",
        "منبع": "تألیفی",
        "نوع منبع": "original",
        "سال": "",
    }

    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=PERSIAN_FIELDS,
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerow(sample)

    data = buf.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        io.BytesIO(data),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="taranom_question_template.csv"'
        },
    )


@app.get("/admin/import", response_class=HTMLResponse)
def import_page(req: Request):
    if (g := guard(req)):
        return g

    body = """
    <h1>ورود گروهی سؤال از CSV</h1>

    <div class="ok">
      <b>امن برای اطلاعات قبلی:</b>
      این بخش فقط سؤال‌های جدید را اضافه می‌کند و دانش‌آموزان،
      نتایج و سؤال‌های قبلی را حذف یا جایگزین نمی‌کند.
    </div>

    <div class="actions">
      <a class="btn primary" href="/admin/csv-template">دانلود قالب CSV</a>
      <a class="btn" href="/admin/questions">مشاهده بانک سؤال</a>
    </div>

    <h3>هر دو نوع فایل پذیرفته می‌شود</h3>
    <p class="muted">
      قالب فعلی سیستم با ستون‌های انگلیسی و قالب جدید فارسیِ کامل.
      فایل Excel را بهتر است با گزینه CSV UTF-8 ذخیره کنید.
    </p>

    <div class="code">
grade,track,subject,book,chapter,topic,subtopic,difficulty,question,option_a,option_b,option_c,option_d,correct_option,explanation,source,source_type,source_year
    </div>

    <p>یا قالب فارسی:</p>
    <div class="code">
پایه,رشته,درس,کتاب,فصل,مبحث,زیرمبحث,سطح,متن سوال,گزینه 1,گزینه 2,گزینه 3,گزینه 4,پاسخ,توضیح,منبع,نوع منبع,سال
    </div>

    <form method="post" enctype="multipart/form-data">
      <input type="file" name="file" accept=".csv,text/csv" required>
      <button type="submit">شروع ورود سؤال‌ها</button>
    </form>
    """
    return page("ورود CSV", body)


@app.post("/admin/import")
async def import_csv(req: Request, file: UploadFile = File(...)):
    if (g := guard(req)):
        return g

    raw = await file.read()

    if not raw:
        return page(
            "خطای CSV",
            "<div class='err'>فایل خالی است.</div>",
        )

    # UTF-8 BOM, UTF-8 and common Windows Persian encodings.
    text = None
    for enc in ("utf-8-sig", "utf-8", "cp1256", "cp1252"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue

    if text is None:
        return page(
            "خطای CSV",
            "<div class='err'>Encoding فایل قابل تشخیص نیست. "
            "فایل را به صورت CSV UTF-8 ذخیره کنید.</div>",
        )

    try:
        reader = csv.DictReader(io.StringIO(text))
        headers = [norm_header(x) for x in (reader.fieldnames or [])]

        required_any = [
            ("grade", ["grade", "پایه"]),
            ("subject", ["subject", "درس"]),
            ("question", ["question", "سوال", "سؤال", "متن سوال", "متن سؤال"]),
        ]

        missing_core = []
        for name, aliases in required_any:
            if not any(norm_header(a) in headers for a in aliases):
                missing_core.append(name)

        if missing_core:
            return page(
                "خطای ساختار CSV",
                f"""
                <div class="err">
                <h2>ستون‌های اصلی پیدا نشدند.</h2>
                <p>ستون‌های مشکل‌دار: {esc(", ".join(missing_core))}</p>
                <p>از دکمه «دانلود قالب CSV» در همین صفحه استفاده کنید.</p>
                </div>
                """,
            )

        added = 0
        duplicate = 0
        invalid = 0
        errors = []
        seen_in_file = set()

        for line_no, raw_row in enumerate(reader, start=2):
            r = normalize_row(raw_row)

            problems = validate_row(r)
            if problems:
                invalid += 1
                if len(errors) < 20:
                    errors.append(
                        f"ردیف {line_no}: " + "، ".join(problems)
                    )
                continue

            key = (
                r["grade"],
                r["track"],
                r["subject"],
                r["question"],
            )

            if key in seen_in_file:
                duplicate += 1
                continue

            seen_in_file.add(key)

            if existing_question(
                r["question"], r["grade"], r["subject"]
            ):
                duplicate += 1
                continue

            try:
                db.insert_question(r)
                added += 1
            except Exception as e:
                invalid += 1
                if len(errors) < 20:
                    errors.append(
                        f"ردیف {line_no}: خطای دیتابیس: {e}"
                    )

        error_html = ""
        if errors:
            error_html = (
                "<h3>نمونه خطاها</h3><ul>"
                + "".join(f"<li>{esc(x)}</li>" for x in errors)
                + "</ul>"
            )

        return page(
            "نتیجه ورود CSV",
            f"""
            <h1>نتیجه ورود CSV</h1>
            <div class="ok"><b>{added}</b> سؤال جدید اضافه شد.</div>
            <div class="warn">تکراری/قبلی: <b>{duplicate}</b></div>
            <div class="err">ردیف دارای خطا: <b>{invalid}</b></div>
            {error_html}
            <div class="actions">
              <a class="btn primary" href="/admin/questions">مشاهده بانک سؤال</a>
              <a class="btn" href="/admin/import">ورود فایل دیگر</a>
            </div>
            """,
        )

    except Exception as e:
        return page(
            "خطای ورود CSV",
            f"""
            <div class="err">
              <h2>فایل پردازش نشد.</h2>
              <pre class="code">{esc(e)}</pre>
              <a class="btn" href="/admin/import">بازگشت</a>
            </div>
            """,
        )


@app.get("/admin/questions/cleanup", response_class=HTMLResponse)
def cleanup_questions(req: Request):
    if (g := guard(req)):
        return g
    deleted = db.remove_duplicate_questions()
    return page("قرنطینه بانک", f"<h1>قرنطینه انجام شد</h1><div class='ok'><b>{deleted}</b> سؤال تکراری از حالت فعال خارج شد؛ هیچ رکوردی حذف نشد.</div><a class='btn' href='/admin/questions'>بازگشت به بانک سؤال</a>")

@app.get("/admin/questions/report", response_class=HTMLResponse)
def question_report(req: Request):
    if (g := guard(req)):
        return g
    c=db.conn()
    rows=c.execute("SELECT grade,COALESCE(track,'') track,subject,COALESCE(chapter,'') chapter,COALESCE(topic,'') topic,COALESCE(difficulty,'') difficulty,COUNT(*) n FROM questions WHERE active=1 GROUP BY grade,track,subject,chapter,topic,difficulty ORDER BY grade,track,subject,chapter,topic,difficulty").fetchall()
    c.close()
    audit=db.question_coverage_audit(10)
    topic_audit=db.question_topic_coverage_audit(10)
    quality=db.question_quality_distribution()
    quality_audit=db.question_quality_audit()
    trs="".join(f"<tr><td>{esc(r['grade'])}</td><td>{esc(r['track'])}</td><td>{esc(r['subject'])}</td><td>{esc(r['chapter'])}</td><td>{esc(r['topic'])}</td><td>{esc(r['difficulty'])}</td><td>{r['n']}</td></tr>" for r in rows)
    qrows="".join(f"<tr><td>{k}</td><td>{quality['correct'].get(k,0)}</td><td>{quality['correct_pct'].get(k,0)}٪</td></tr>" for k in ("A","B","C","D"))
    drows="".join(f"<tr><td>{esc(k)}</td><td>{v}</td><td>{round(v/max(quality['total'],1)*100,1)}٪</td></tr>" for k,v in quality["difficulty"].items())
    gaps="".join(f"<tr><td>{esc(g['grade'])}</td><td>{esc(g['track'])}</td><td>{esc(g['subject'])}</td><td>{g['count']}</td><td>{g['needed']}</td></tr>" for g in audit["gaps"])
    summary=f"<p><b>پوشش حداقل ۱۰ سؤال برای هر درس:</b> {audit['covered']} از {audit['expected']} ({audit['coverage_pct']}٪)</p>"
    gap_table="<h2>موارد نیازمند تکمیل در سطح درس</h2><table><tr><th>پایه</th><th>رشته</th><th>درس</th><th>موجود</th><th>نیاز</th></tr>"+gaps+"</table>"
    topic_gaps="".join(f"<tr><td>{esc(g['grade'])}</td><td>{esc(g['track'])}</td><td>{esc(g['subject'])}</td><td>{esc(g['chapter'])}</td><td>{esc(g['topic'])}</td><td>{g['count']}</td><td>{g['needed']}</td></tr>" for g in topic_audit["gaps"][:300])
    topic_table="<h2>مباحث کمتر از ۱۰ سؤال فعال</h2><p class='muted'>این گزارش فقط وضعیت بانک را می‌سنجد و هیچ رکوردی را حذف یا غیرفعال نمی‌کند.</p><table><tr><th>پایه</th><th>رشته</th><th>درس</th><th>فصل</th><th>مبحث</th><th>موجود</th><th>نیاز</th></tr>"+(topic_gaps if topic_gaps else "<tr><td colspan='7'>مبحثی با کمتر از ۱۰ سؤال فعال پیدا نشد.</td></tr>")+"</table>"
    quality_html="<h2>کنترل کیفیت بانک</h2><div class='grid'><div class='card'>کل سؤالات فعال<div class='n'>"+str(quality["total"])+"</div></div><div class='card'>سؤالات نیازمند بررسی<div class='n'>"+str(quality_audit["bad_total"])+"</div><div class='muted'>کیفیت فعلی: "+str(quality_audit["quality_pct"])+"٪</div></div></div><div class='grid'><div class='card'><h3>توزیع پاسخ صحیح</h3><table><tr><th>گزینه</th><th>تعداد</th><th>درصد</th></tr>"+qrows+"</table></div><div class='card'><h3>توزیع سطح دشواری</h3><table><tr><th>سطح</th><th>تعداد</th><th>درصد</th></tr>"+drows+"</table></div></div>"
    issues_html="<p class='muted'>این حسابرسی فقط گزارش می‌دهد و هیچ سؤالی را حذف یا غیرفعال نمی‌کند.</p><table><tr><th>نوع ایراد</th><th>تعداد</th></tr>"+"" .join(f"<tr><td>{esc(k)}</td><td>{v}</td></tr>" for k,v in quality_audit["issue_counts"].items())+"</table>" if quality_audit["issue_counts"] else "<p class='ok'>ایراد کیفیتی فعال شناسایی نشد.</p>"
    body="<h1>گزارش پوشش بانک سؤال</h1>"+summary+quality_html+issues_html+gap_table+"<h2>جزئیات فصل/مبحث</h2><table><tr><th>پایه</th><th>رشته</th><th>درس</th><th>فصل</th><th>مبحث</th><th>سطح</th><th>تعداد</th></tr>"+trs+"</table>"
    return page("گزارش پوشش", body)

@app.get("/admin/requests", response_class=HTMLResponse)
def requests(req: Request):
    if (g := guard(req)):
        return g

    c = db.conn()
    rows = c.execute(
        """
        SELECT cr.*,s.first_name,s.last_name
        FROM counseling_requests cr
        JOIN students s ON s.id=cr.student_id
        ORDER BY cr.id DESC LIMIT 500
        """
    ).fetchall()
    c.close()

    trs = "".join(
        f"<tr><td>{r['id']}</td>"
        f"<td>{esc(r['first_name'])} {esc(r['last_name'])}</td>"
        f"<td>{esc(r['request_type'])}</td>"
        f"<td>{esc(r['status'])}</td>"
        f"<td>{esc(r['created_at'])}</td></tr>"
        for r in rows
    )

    body = (
        "<h1>درخواست‌های مشاوره</h1>"
        "<table><tr><th>ID</th><th>دانش‌آموز</th><th>نوع</th>"
        "<th>وضعیت</th><th>تاریخ</th></tr>"
        + trs
        + "</table>"
    )
    return page("درخواست‌ها", body)


# ---------- Daily reports / counselor control ----------
@app.get("/admin/daily-reports", response_class=HTMLResponse)
def daily_reports_dashboard(req: Request):
    if (g := guard(req)):
        return g
    c = db.conn()
    today = __import__("datetime").date.today().isoformat()
    total = c.execute("SELECT COUNT(*) n FROM students WHERE registered=1").fetchone()["n"]
    today_reports = c.execute("SELECT COUNT(*) n FROM daily_reports WHERE report_date=?", (today,)).fetchone()["n"]
    status_rows = c.execute("SELECT status,COUNT(*) n FROM student_progress WHERE report_date=(SELECT MAX(report_date) FROM student_progress) GROUP BY status").fetchall()
    flags = c.execute("""SELECT f.*,s.first_name,s.last_name,s.grade,s.track
                         FROM ai_flags f JOIN students s ON s.id=f.student_id
                         WHERE f.status='open' ORDER BY CASE f.severity WHEN 'urgent_review' THEN 1 WHEN 'followup' THEN 2 ELSE 3 END,f.id DESC LIMIT 100""").fetchall()
    overdue = c.execute("""SELECT fu.*,s.first_name,s.last_name
                           FROM followups fu JOIN students s ON s.id=fu.student_id
                           WHERE fu.status='open' ORDER BY fu.id DESC LIMIT 100""").fetchall()
    c.close()
    status_map={r["status"]:r["n"] for r in status_rows}
    flag_rows="".join(
        f"<tr><td>{r['first_name']} {r['last_name']}</td><td>{esc(r['grade'])} {esc(r['track'])}</td>"
        f"<td>{esc(r['severity'])}</td><td>{esc(r['reason'])}</td><td>{esc(r['created_at'])}</td></tr>" for r in flags
    )
    follow_rows="".join(
        f"<tr><td>{r['first_name']} {r['last_name']}</td><td>{esc(r['followup_type'])}</td>"
        f"<td>{esc(r['priority'])}</td><td>{esc(r['status'])}</td><td>{esc(r['created_at'])}</td></tr>" for r in overdue
    )
    body=f"""
    <h1>🌙 گزارش‌های روزانه و پیگیری مشاور</h1>
    <div class="grid">
      <div class="card">دانش‌آموز فعال<div class="n">{total}</div></div>
      <div class="card">گزارش امروز<div class="n">{today_reports}</div></div>
      <div class="card">🟢 مناسب<div class="n">{status_map.get('normal',0)}</div></div>
      <div class="card">🟡 توجه<div class="n">{status_map.get('attention',0)}</div></div>
      <div class="card">🟠 پیگیری<div class="n">{status_map.get('followup',0)}</div></div>
      <div class="card">🔴 بررسی سریع<div class="n">{status_map.get('urgent_review',0)}</div></div>
    </div>
    <div class="actions">
      <a class="btn" href="/admin">داشبورد اصلی</a>
      <a class="btn" href="/admin/daily-reports">به‌روزرسانی</a>
    </div>
    <h2>🚩 موارد نیازمند توجه</h2>
    <table><tr><th>دانش‌آموز</th><th>پایه/رشته</th><th>شدت</th><th>دلیل</th><th>تاریخ</th></tr>
    {flag_rows if flag_rows else '<tr><td colspan="5">مورد باز ثبت نشده است.</td></tr>'}</table>
    <h2>📋 پیگیری‌های باز</h2>
    <table><tr><th>دانش‌آموز</th><th>نوع</th><th>اولویت</th><th>وضعیت</th><th>تاریخ</th></tr>
    {follow_rows if follow_rows else '<tr><td colspan="5">پیگیری بازی ثبت نشده است.</td></tr>'}</table>
    """
    return page("گزارش روزانه", body)

@app.get("/admin/student/{student_id}/reports", response_class=HTMLResponse)
def student_reports(req: Request, student_id: int):
    if (g := guard(req)):
        return g
    c=db.conn()
    s=c.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
    rows=c.execute("SELECT * FROM daily_reports WHERE student_id=? ORDER BY report_date DESC LIMIT 60",(student_id,)).fetchall()
    c.close()
    if not s:
        return page("پرونده", "<div class='err'>دانش‌آموز پیدا نشد.</div>")
    trs="".join(
        f"<tr><td>{r['report_date']}</td><td>{r['study_hours'] or 0:g}</td><td>{r['plan_execution'] or 0:g}%</td>"
        f"<td>{r['practice_count'] or 0}</td><td>{esc(r['main_problem'])}</td><td>{esc(r['status'])}</td>"
        f"<td>{esc(r['analysis_status'])}</td></tr>" for r in rows
    )
    counselors_rows="".join(f"<option value='{r['id']}'>{esc(r['name'])}</option>" for r in db.list_counselors(True))
    active=db.active_counselor(student_id)
    summary=db.weekly_summary(student_id,7)
    notes=db.list_counselor_notes(student_id,10)
    note_rows="".join(f"<li>{esc(n['note'])} <span class='muted'>({esc(n['created_at'])})</span></li>" for n in notes)
    body=f"""
    <h1>📋 گزارش‌های {esc(s['first_name'])} {esc(s['last_name'])}</h1>
    <p>پایه: {esc(s['grade'])} | رشته: {esc(s['track'])}</p>
    <div class="grid">
      <div class="card">مشاور فعلی<div class="n" style="font-size:20px">{esc(active['name']) if active else 'تخصیص نشده'}</div></div>
      <div class="card">روزهای گزارش‌شده<div class="n">{summary['days']}</div></div>
      <div class="card">ساعت مطالعه هفته<div class="n">{summary['study_hours']:.1f}</div></div>
      <div class="card">میانگین اجرای برنامه<div class="n">{summary['execution']:.0f}%</div></div>
      <div class="card">تست/تمرین هفته<div class="n">{summary['practice']}</div></div>
    </div>
    <form method="post" action="/admin/student/{student_id}/assign-counselor" class="card">
      <label>تخصیص مشاور</label>
      <select name="counselor_id" required>{counselors_rows or '<option value="">ابتدا مشاور اضافه کنید</option>'}</select>
      <button>ثبت تخصیص</button>
    </form>
    <form method="post" action="/admin/student/{student_id}/note" class="card">
      <label>یادداشت مشاور/مدیر</label><textarea name="note" required></textarea>
      <button>ثبت یادداشت</button>
    </form>
    <h3>یادداشت‌های اخیر</h3><ul>{note_rows or '<li>یادداشتی ثبت نشده است.</li>'}</ul>
    <table><tr><th>تاریخ</th><th>مطالعه</th><th>اجرای برنامه</th><th>تست/تمرین</th><th>مشکل اصلی</th><th>وضعیت</th><th>تحلیل</th></tr>
    {trs if trs else '<tr><td colspan="7">گزارشی ثبت نشده است.</td></tr>'}</table>
    """
    return page("گزارش‌های دانش‌آموز", body)


@app.post("/admin/followup/{followup_id}/complete")
def complete_followup(req: Request, followup_id: int):
    if (g := guard(req)): return g
    db.complete_followup(followup_id)
    return RedirectResponse("/admin/daily-reports", status_code=303)

@app.post("/admin/student/{student_id}/note")
def add_note(req: Request, student_id: int, note: str = Form(...)):
    if (g := guard(req)): return g
    db.add_counselor_note(student_id, None, note.strip())
    return RedirectResponse(f"/admin/student/{student_id}/reports", status_code=303)

@app.get("/admin/counselors", response_class=HTMLResponse)
def counselors(req: Request):
    if (g := guard(req)): return g
    rows=db.list_counselors(False)
    trs="".join(f"<tr><td>{r['id']}</td><td>{esc(r['name'])}</td><td>{esc(r['telegram_id'])}</td><td>{'فعال' if r['active'] else 'غیرفعال'}</td></tr>" for r in rows)
    body=f"""
    <h1>👨‍🏫 مشاوران</h1>
    <form method="post" action="/admin/counselors/add" class="card">
      <label>نام مشاور</label><input name="name" required>
      <label>Telegram ID (اختیاری)</label><input name="telegram_id">
      <button>افزودن مشاور</button>
    </form>
    <table><tr><th>ID</th><th>نام</th><th>Telegram ID</th><th>وضعیت</th></tr>
    {trs if trs else '<tr><td colspan="4">هنوز مشاوری ثبت نشده است.</td></tr>'}</table>
    """
    return page("مشاوران",body)

@app.post("/admin/counselors/add")
def add_counselor(req: Request, name: str = Form(...), telegram_id: str = Form("")):
    if (g := guard(req)): return g
    tid=int(telegram_id) if telegram_id.strip().isdigit() else None
    db.add_counselor(name.strip(),tid)
    return RedirectResponse("/admin/counselors", status_code=303)

@app.post("/admin/student/{student_id}/assign-counselor")
def assign_counselor_admin(req: Request, student_id: int, counselor_id: int = Form(...)):
    if (g := guard(req)): return g
    db.assign_counselor(student_id,counselor_id)
    return RedirectResponse(f"/admin/student/{student_id}/reports", status_code=303)


# ---------- CRM / Call-center / Sales ----------

@app.get("/admin/crm", response_class=HTMLResponse)
def crm_dashboard(req: Request):
    if (g := guard(req)):
        return g
    m=db.crm_stats()
    body=f"""
    <h1>📇 CRM و پیگیری فروش</h1>
    <div class="grid">
      <div class="card">کل سرنخ‌ها<div class="n">{m['total_leads']}</div></div>
      <div class="card">در انتظار تماس<div class="n">{m['lead']}</div></div>
      <div class="card">تماس گرفته‌شده<div class="n">{m['contacted']}</div></div>
      <div class="card">علاقه‌مند<div class="n">{m['interested']}</div></div>
      <div class="card">پیگیری<div class="n">{m['followup']}</div></div>
      <div class="card">ثبت‌نام‌شده<div class="n">{m['registered']}</div></div>
      <div class="card">از دست‌رفته<div class="n">{m['lost']}</div></div>
      <div class="card">پیگیری باز<div class="n">{m['open_followups']}</div></div>
      <div class="card">درآمد ثبت‌شده<div class="n">{m['revenue']:,.0f}</div></div>
    </div>
    <div class="actions">
      <a class="btn primary" href="/admin/leads">📞 صف تماس</a>
      <a class="btn" href="/admin/registrations">💰 ثبت خدمات</a>
      <a class="btn" href="/admin/kpi">📈 KPI مشاوران</a>
    </div>
    <p class="muted">تغییر وضعیت و ثبت تماس فقط به رکورد CRM اضافه می‌کند و اطلاعات پرونده دانش‌آموز را پاک یا بازنویسی نمی‌کند.</p>
    """
    return page("CRM",body)

@app.get("/admin/leads", response_class=HTMLResponse)
def leads(req: Request, status: str = ""):
    if (g := guard(req)):
        return g
    rows=db.list_leads(status.strip() or None)
    trs=""
    for r in rows:
        trs += f"""<tr>
        <td><a href="/admin/lead/{r['id']}">{r['id']}</a></td>
        <td>{esc(r['name'])}</td><td>{esc(r['phone'])}</td><td>{esc(r['source'])}</td>
        <td>{esc(r['status'])}</td><td>{r['contacts']}</td><td>{esc(r['updated_at'])}</td></tr>"""
    body=f"""<h1>📞 صف تماس و سرنخ‌ها</h1>
    <div class="actions">
      <a class="btn" href="/admin/leads?status=lead">فقط جدیدها</a>
      <a class="btn" href="/admin/leads?status=contacted">تماس‌شده</a>
      <a class="btn" href="/admin/leads?status=interested">علاقه‌مند</a>
      <a class="btn" href="/admin/leads?status=followup">پیگیری</a>
      <a class="btn" href="/admin/leads">همه</a>
    </div>
    <table><tr><th>ID</th><th>نام</th><th>تلفن</th><th>منبع</th><th>وضعیت</th><th>تعداد تماس</th><th>آخرین تغییر</th></tr>
    {trs or '<tr><td colspan="7">سرنخی ثبت نشده است.</td></tr>'}</table>"""
    return page("سرنخ‌ها",body)

@app.get("/admin/lead/{lid}", response_class=HTMLResponse)
def lead(req: Request,lid:int):
    if (g := guard(req)):
        return g
    d=db.lead_details(lid)
    l=d["lead"]
    if not l:
        return page("یافت نشد","<div class='err'>سرنخ یافت نشد.</div>")
    contacts="".join(f"<tr><td>{esc(x['contacted_at'])}</td><td>{esc(x['result'])}</td><td>{esc(x['note'])}</td></tr>" for x in d["contacts"])
    history="".join(f"<tr><td>{esc(x['created_at'])}</td><td>{esc(x['old_status'])}</td><td>{esc(x['new_status'])}</td></tr>" for x in d["history"])
    body=f"""
    <h1>📞 سرنخ #{l['id']}</h1>
    <p><b>{esc(l['name'])}</b> | تلفن: {esc(l['phone'])} | منبع: {esc(l['source'])}</p>
    <p>وضعیت فعلی: <b>{esc(l['status'])}</b></p>
    <h2>ثبت تماس</h2>
    <form method="post" action="/admin/lead/{lid}/contact">
      <select name="result" required>
        <option value="contacted">تماس برقرار شد</option>
        <option value="interested">علاقه‌مند شد</option>
        <option value="followup">نیاز به پیگیری</option>
        <option value="registered">ثبت‌نام کرد</option>
        <option value="lost">عدم پیگیری/از دست‌رفته</option>
      </select>
      <textarea name="note" placeholder="خلاصه تماس، نیاز، زمان پیگیری و نکات مهم"></textarea>
      <button type="submit">ثبت تماس و تغییر وضعیت</button>
    </form>
    <h2>تاریخچه تماس</h2>
    <table><tr><th>زمان</th><th>نتیجه</th><th>یادداشت</th></tr>{contacts or '<tr><td colspan="3">هنوز تماسی ثبت نشده است.</td></tr>'}</table>
    <h2>تاریخچه وضعیت</h2>
    <table><tr><th>زمان</th><th>قبلی</th><th>جدید</th></tr>{history or '<tr><td colspan="3">تغییری ثبت نشده است.</td></tr>'}</table>
    """
    return page("جزئیات سرنخ",body)

@app.post("/admin/lead/{lid}/contact")
async def lead_contact(req: Request,lid:int):
    if (g := guard(req)):
        return g
    form=dict(await req.form())
    result=str(form.get("result","contacted"))
    note=str(form.get("note","")).strip()
    if result not in {"contacted","interested","followup","registered","lost"}:
        result="contacted"
    db.add_lead_contact(lid,result,note)
    if result=="followup":
        d=db.lead_details(lid); l=d["lead"]
        if l:
            c=db.conn()
            s=c.execute("SELECT id FROM students WHERE telegram_id=?",(l["telegram_id"],)).fetchone() if l["telegram_id"] else None
            c.close()
            if s: db.create_followup(s["id"],"call_followup","normal",None,note)
    return RedirectResponse(f"/admin/lead/{lid}",status_code=303)

@app.get("/admin/registrations", response_class=HTMLResponse)
def registrations(req: Request):
    if (g := guard(req)):
        return g
    c=db.conn()
    rows=c.execute("""SELECT r.*,s.first_name,s.last_name FROM registrations r
                     JOIN students s ON s.id=r.student_id ORDER BY r.id DESC LIMIT 300""").fetchall()
    c.close()
    sales=db.sales_summary(30)
    trs="".join(f"<tr><td>{r['id']}</td><td><a href='/admin/student/{r['student_id']}'>{esc(r['first_name'])} {esc(r['last_name'])}</a></td><td>{esc(r['service'])}</td><td>{r['amount']:,.0f}</td><td>{esc(r['status'])}</td><td>{esc(r['created_at'])}</td></tr>" for r in rows)
    sr="".join(f"<tr><td>{esc(r['service'])}</td><td>{r['count']}</td><td>{r['revenue']:,.0f}</td></tr>" for r in sales)
    body=f"""
    <h1>💰 ثبت‌نام خدمات و فروش</h1>
    <div class="actions"><a class="btn primary" href="/admin/registration/new">➕ ثبت فروش/خدمت</a></div>
    <h2>فروش ۳۰ روز اخیر</h2>
    <table><tr><th>خدمت</th><th>تعداد</th><th>درآمد</th></tr>{sr or '<tr><td colspan="3">داده‌ای نیست.</td></tr>'}</table>
    <h2>ثبت‌نام‌ها</h2>
    <table><tr><th>ID</th><th>دانش‌آموز</th><th>خدمت</th><th>مبلغ</th><th>وضعیت</th><th>زمان</th></tr>{trs or '<tr><td colspan="6">ثبت‌نامی نیست.</td></tr>'}</table>
    """
    return page("فروش",body)

@app.get("/admin/registration/new", response_class=HTMLResponse)
def registration_new(req: Request):
    if (g := guard(req)):
        return g
    students=db.list_students(1000)
    opts="".join(f"<option value='{s['id']}'>{esc(s['first_name'])} {esc(s['last_name'])} — {esc(s['phone'])}</option>" for s in students)
    body=f"""<h1>➕ ثبت خدمت/فروش</h1>
    <form method="post">
      <select name="student_id" required>{opts}</select>
      <input name="service" placeholder="نام خدمت؛ مثال: کوچینگ سالانه" required>
      <input name="amount" type="number" step="1" min="0" placeholder="مبلغ تومان" required>
      <select name="status"><option value="registered">ثبت‌نام</option><option value="paid">پرداخت‌شده</option><option value="pending">در انتظار پرداخت</option></select>
      <button type="submit">ثبت</button>
    </form>"""
    return page("ثبت فروش",body)

@app.post("/admin/registration/new")
async def registration_new_post(req: Request):
    if (g := guard(req)):
        return g
    form=dict(await req.form())
    try:
        db.register_service(int(form["student_id"]),str(form["service"]).strip(),float(form["amount"]),str(form.get("status","registered")))
        return RedirectResponse("/admin/registrations",status_code=303)
    except Exception as e:
        return page("خطا",f"<div class='err'>{esc(e)}</div>")

@app.get("/admin/kpi", response_class=HTMLResponse)
def kpi(req: Request):
    if (g := guard(req)):
        return g
    m=db.crm_stats()
    rows=db.counselor_kpi(30)
    trs="".join(f"<tr><td>{esc(r['name'])}</td><td>{r['assigned']}</td><td>{r['notes']}</td><td>{r['followups_created']}</td><td>{r['followups_done']}</td></tr>" for r in rows)
    body=f"""
    <h1>📈 KPI تیم</h1>
    <p class="muted">بازه عملکرد مشاوران: ۳۰ روز اخیر. اعداد توصیفی‌اند و برای پایش عملیات استفاده می‌شوند.</p>
    <div class="grid">
      <div class="card">کل سرنخ<div class="n">{m['total_leads']}</div></div>
      <div class="card">کل تماس‌ها<div class="n">{m['contacts']}</div></div>
      <div class="card">پیگیری باز<div class="n">{m['open_followups']}</div></div>
      <div class="card">درآمد ثبت‌شده<div class="n">{m['revenue']:,.0f}</div></div>
    </div>
    <table><tr><th>مشاور</th><th>دانش‌آموز فعال</th><th>یادداشت ۳۰روزه</th><th>پیگیری ایجادشده</th><th>پیگیری تکمیل‌شده</th></tr>
    {trs or '<tr><td colspan="5">مشاوری ثبت نشده است.</td></tr>'}</table>
    """
    return page("KPI تیم",body)


@app.get("/admin/call-center", response_class=HTMLResponse)
def call_center_dashboard(req: Request):
    if (g := guard(req)):
        return g
    s=db.call_center_summary(30)
    rows=db.call_center_kpi(30)
    agents=db.list_call_center_agents(False)
    trs="".join(f"<tr><td>{esc(r['name'])}</td><td>{r['calls']}</td><td>{r['effective_calls']}</td><td>{r['conversions']}</td><td>{r['revenue']:,.0f}</td></tr>" for r in rows)
    opts="".join(f"<option value='{a['id']}'>{esc(a['name'])}</option>" for a in agents if a['active'])
    body=f"""
    <h1>📞 کال‌سنتر</h1>
    <div class="grid">
      <div class="card">کل تماس<div class="n">{s['calls']}</div></div>
      <div class="card">تماس مؤثر<div class="n">{s['effective_calls']}</div></div>
      <div class="card">تبدیل<div class="n">{s['conversions']}</div></div>
      <div class="card">درآمد ثبت‌شده<div class="n">{s['revenue']:,.0f}</div></div>
    </div>
    <div class="actions"><a class="btn" href="/admin/leads">📋 صف سرنخ</a><a class="btn" href="/admin/call-center/agents">👥 اعضای تیم</a></div>
    <table><tr><th>کارشناس</th><th>تماس</th><th>مؤثر</th><th>تبدیل</th><th>درآمد مرتبط</th></tr>{trs or '<tr><td colspan="5">داده‌ای ثبت نشده است.</td></tr>'}</table>
    """
    return page("کال‌سنتر",body)

@app.get("/admin/call-center/agents", response_class=HTMLResponse)
def call_center_agents(req: Request):
    if (g := guard(req)):
        return g
    rows=db.list_call_center_agents(False)
    trs="".join(f"<tr><td>{r['id']}</td><td>{esc(r['name'])}</td><td>{esc(r['phone'])}</td><td>{r['monthly_base']:,.0f}</td><td>{r['commission_rate']*100:.1f}%</td><td>{'فعال' if r['active'] else 'غیرفعال'}</td></tr>" for r in rows)
    body=f"""
    <h1>👥 اعضای کال‌سنتر</h1>
    <form method="post" action="/admin/call-center/agents/add" class="card">
      <input name="name" placeholder="نام کارشناس" required>
      <input name="phone" placeholder="تلفن">
      <input name="monthly_base" type="number" value="2500000" min="0">
      <input name="commission_rate" type="number" value="5" step="0.1" min="0" max="100">
      <button>افزودن</button>
    </form>
    <p class="muted">پیش‌فرض: ۲۵۰۰۰۰۰۰ ریال/تومان؟ مبلغ در این سیستم بر اساس تومان ثبت می‌شود. نرخ پیش‌فرض کمیسیون ۵٪ است.</p>
    <table><tr><th>ID</th><th>نام</th><th>تلفن</th><th>پایه ماهانه</th><th>کمیسیون</th><th>وضعیت</th></tr>{trs or '<tr><td colspan="6">اعضایی ثبت نشده‌اند.</td></tr>'}</table>
    """
    return page("اعضای کال‌سنتر",body)

@app.post("/admin/call-center/agents/add")
def call_center_agent_add(req: Request, name: str = Form(...), phone: str = Form(""), monthly_base: float = Form(2500000), commission_rate: float = Form(5)):
    if (g := guard(req)): return g
    db.add_call_center_agent(name,phone,monthly_base,commission_rate/100)
    return RedirectResponse("/admin/call-center/agents",status_code=303)


@app.get("/admin/access", response_class=HTMLResponse)
def access_page(req: Request):
    if (g := guard(req)):
        return g
    db.expire_access()
    pending=db.list_access_requests("pending",300)
    active=db.list_access_requests("active",300)
    rows=""
    for r in pending:
        rows += f"""<tr>
          <td>{r['student_id']}</td><td>{esc(r['first_name'])} {esc(r['last_name'])}</td>
          <td>{esc(r['grade'])}</td><td>{esc(r['track'])}</td>
          <td>{esc(r['phone'])}</td><td>{esc(r['plan_code'])}</td>
          <td><form method="post" action="/admin/access/grant">
             <input type="hidden" name="student_id" value="{r['student_id']}">
             <input type="hidden" name="plan_code" value="{esc(r['plan_code'])}">
             <input name="days" value="{30 if r['plan_code']!='access_60' and r['plan_code']!='access_90' else (60 if r['plan_code']=='access_60' else 90)}" style="width:70px">
             <button>تأیید و فعال‌سازی</button>
          </form></td>
        </tr>"""
    body=f"""
    <h1>🔐 دسترسی و تمدید دانش‌آموزان</h1>
    <p class="muted">دسترسی پیش‌فرض خودکار نیست. هر درخواست باید از پنل تأیید شود. تأیید ۳۰ روزه برای شروع در نظر گرفته شده و قابل تغییر است.</p>
    <table><tr><th>ID</th><th>دانش‌آموز</th><th>پایه</th><th>رشته</th><th>تماس</th><th>نوع درخواست</th><th>عملیات</th></tr>
    {rows or '<tr><td colspan="7">درخواست معلقی وجود ندارد.</td></tr>'}</table>
    <h2>دسترسی‌های فعال</h2>
    <table><tr><th>ID</th><th>دانش‌آموز</th><th>پایه</th><th>رشته</th><th>نوع</th><th>شروع</th><th>انقضا</th></tr>
    {"".join(f"<tr><td>{r['student_id']}</td><td>{esc(r['first_name'])} {esc(r['last_name'])}</td><td>{esc(r['grade'])}</td><td>{esc(r['track'])}</td><td>{esc(r['plan_code'])}</td><td>{esc(r['starts_at'])}</td><td>{esc(r['expires_at'])}</td></tr>" for r in active) or '<tr><td colspan="7">دسترسی فعالی وجود ندارد.</td></tr>'}</table>
    <div class="actions"><a class="btn" href="/admin/students">مشاهده دانش‌آموزان</a></div>
    """
    return page("دسترسی و تمدید",body)

@app.post("/admin/access/grant")
def access_grant(req: Request, student_id: int = Form(...), days: int = Form(30), plan_code: str = Form("approved")):
    if (g := guard(req)):
        return g
    days=max(1,min(int(days),365))
    plan_code=(plan_code or "approved").strip()[:50]
    db.grant_access(student_id,days,plan_code=plan_code,actor="admin",note=f"فعال‌سازی {days} روزه از پنل")
    return RedirectResponse("/admin/access",status_code=303)


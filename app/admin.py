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
      <a class="btn" href="/admin/questions/cleanup">🧹 حذف تکراری‌های بانک</a>
      <a class="btn" href="/admin/questions/report">📊 گزارش پوشش مباحث</a>
    </div>
    <p class="muted">ورود CSV فقط اضافه می‌کند و داده‌های دانش‌آموزان را حذف نمی‌کند. پاک‌سازی تکراری‌ها یک عملیات جدا و قابل مشاهده است.</p>
    """
    return page("داشبورد", body)


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
    return page("پاک‌سازی بانک", f"<h1>پاک‌سازی انجام شد</h1><div class='ok'><b>{deleted}</b> سؤال تکراری حذف شد.</div><a class='btn' href='/admin/questions'>بازگشت به بانک سؤال</a>")

@app.get("/admin/questions/report", response_class=HTMLResponse)
def question_report(req: Request):
    if (g := guard(req)):
        return g
    c=db.conn()
    rows=c.execute("SELECT grade,COALESCE(track,'') track,subject,COALESCE(chapter,'') chapter,COALESCE(topic,'') topic,COALESCE(difficulty,'') difficulty,COUNT(*) n FROM questions WHERE active=1 GROUP BY grade,track,subject,chapter,topic,difficulty ORDER BY grade,track,subject,chapter,topic,difficulty").fetchall()
    c.close()
    trs="".join(f"<tr><td>{esc(r['grade'])}</td><td>{esc(r['track'])}</td><td>{esc(r['subject'])}</td><td>{esc(r['chapter'])}</td><td>{esc(r['topic'])}</td><td>{esc(r['difficulty'])}</td><td>{r['n']}</td></tr>" for r in rows)
    body="<h1>گزارش پوشش بانک سؤال</h1><p class='muted'>ترکیب‌هایی که کمتر از ۱۰ سؤال دارند باید تکمیل شوند.</p><table><tr><th>پایه</th><th>رشته</th><th>درس</th><th>فصل</th><th>مبحث</th><th>سطح</th><th>تعداد</th></tr>"+trs+"</table>"
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

import hashlib
import hmac
import html
import secrets

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from . import db

router = APIRouter()
ITERATIONS = 310000

def _esc(value):
    return html.escape(str(value or ""))

def _hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS).hex()
    return f"pbkdf2_sha256\u0024{ITERATIONS}\u0024{salt}\u0024{digest}"

def _verify_password(password, stored):
    try:
        scheme, iterations, salt, expected = stored.split("$", 3)
        if scheme != "pbkdf2_sha256": return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False

def _counselor(req):
    cid = req.session.get("counselor_id")
    if not cid or not req.session.get("counselor_auth"): return None
    c = db.conn()
    row = c.execute("""SELECT co.id,co.name,co.telegram_id,co.active,ca.username
        FROM counselors co JOIN counselor_accounts ca ON ca.counselor_id=co.id
        WHERE co.id=? AND co.active=1 AND ca.active=1""", (int(cid),)).fetchone()
    c.close()
    return row

def _guard(req):
    return _counselor(req)

def _page(title, body, counselor=None):
    who = f"<p class='muted'>ورود: {_esc(counselor['name'])}</p>" if counselor else ""
    return HTMLResponse(f"""<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow,noarchive">
<title>{_esc(title)} | پنل مشاور ترنم همدلی</title>
<style>
body{{font-family:Tahoma,Arial,sans-serif;max-width:1100px;margin:24px auto;padding:0 14px;background:#f5f7fb;color:#1f2937;line-height:1.9}}
header,.card{{background:white;border:1px solid #e5e7eb;border-radius:14px;padding:16px;margin:12px 0}}
nav{{display:flex;gap:8px;flex-wrap:wrap}}nav a,.btn,button{{background:#1557b0;color:white;text-decoration:none;padding:8px 13px;border:0;border-radius:8px;font-family:inherit;cursor:pointer}}
input,textarea,select{{box-sizing:border-box;width:100%;padding:10px;margin:5px 0 12px;border:1px solid #cbd5e1;border-radius:8px;font-family:inherit}}
textarea{{min-height:90px}}table{{width:100%;border-collapse:collapse;background:white}}th,td{{padding:9px;border-bottom:1px solid #e5e7eb;text-align:right;vertical-align:top;font-size:13px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}}.muted{{color:#64748b;font-size:13px}}.warn{{background:#fff7ed;padding:12px;border-radius:10px}}.ok{{background:#ecfdf3;padding:12px;border-radius:10px}}
</style></head><body><header><h1>پنل اختصاصی مشاوران ترنم همدلی</h1>{who}
<nav><a href="/counselor">داشبورد</a><a href="/counselor/logout">خروج امن</a></nav></header>{body}</body></html>""", media_type="text/html; charset=utf-8")

@router.get("/counselor/login", response_class=HTMLResponse)
def login_page(req: Request):
    if _counselor(req): return RedirectResponse("/counselor", status_code=303)
    return HTMLResponse("""<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive"><title>ورود مشاور</title>
<body style="font-family:Tahoma;max-width:420px;margin:70px auto;background:#f5f7fb;padding:20px;line-height:2">
<h2>ورود مشاور ترنم همدلی</h2><form method="post"><label>نام کاربری</label><input name="username" required autocomplete="username">
<label>رمز عبور</label><input type="password" name="password" required autocomplete="current-password">
<button style="padding:10px 18px;background:#1557b0;color:white;border:0;border-radius:8px">ورود</button></form></body></html>""", media_type="text/html; charset=utf-8")

@router.post("/counselor/login")
def login(req: Request, username: str = Form(...), password: str = Form(...)):
    c = db.conn()
    row = c.execute("""SELECT ca.counselor_id,ca.password_hash FROM counselor_accounts ca
        JOIN counselors co ON co.id=ca.counselor_id
        WHERE ca.username=? AND ca.active=1 AND co.active=1""", (username.strip(),)).fetchone()
    c.close()
    if row and _verify_password(password, row["password_hash"]):
        req.session.clear()
        req.session["counselor_auth"] = True
        req.session["counselor_id"] = int(row["counselor_id"])
        return RedirectResponse("/counselor", status_code=303)
    return HTMLResponse("<meta charset='utf-8'><p dir='rtl'>نام کاربری یا رمز عبور نادرست است. <a href='/counselor/login'>تلاش دوباره</a></p>", status_code=401)

@router.get("/counselor/logout")
def logout(req: Request):
    req.session.pop("counselor_auth", None)
    req.session.pop("counselor_id", None)
    return RedirectResponse("/counselor/login", status_code=303)

@router.get("/counselor", response_class=HTMLResponse)
def dashboard(req: Request):
    co = _guard(req)
    if not co: return RedirectResponse("/counselor/login", status_code=303)
    c = db.conn()
    students = c.execute("""SELECT s.id,s.first_name,s.last_name,s.grade,s.track,
        (SELECT MAX(report_date) FROM daily_reports dr WHERE dr.student_id=s.id) last_report,
        (SELECT COUNT(*) FROM followups f WHERE f.student_id=s.id AND f.status='open') open_followups
        FROM students s JOIN student_counselor_assignments a ON a.student_id=s.id AND a.active=1
        WHERE a.counselor_id=? ORDER BY s.first_name,s.last_name""", (co["id"],)).fetchall()
    flags = c.execute("""SELECT f.id,f.severity,f.reason,f.created_at,s.id student_id,s.first_name,s.last_name
        FROM ai_flags f JOIN students s ON s.id=f.student_id
        JOIN student_counselor_assignments a ON a.student_id=s.id AND a.active=1 AND a.counselor_id=?
        WHERE f.status='open' ORDER BY CASE f.severity WHEN 'urgent_review' THEN 1 WHEN 'followup' THEN 2 ELSE 3 END,f.id DESC LIMIT 50""", (co["id"],)).fetchall()
    c.close()
    trs = "".join(f"<tr><td><a href='/counselor/student/{r['id']}'>{_esc(r['first_name'])} {_esc(r['last_name'])}</a></td><td>{_esc(r['grade'])}</td><td>{_esc(r['track'])}</td><td>{_esc(r['last_report'] or 'هنوز ندارد')}</td><td>{r['open_followups']}</td></tr>" for r in students)
    frows = "".join(f"<tr><td><a href='/counselor/student/{r['student_id']}'>{_esc(r['first_name'])} {_esc(r['last_name'])}</a></td><td>{_esc(r['severity'])}</td><td>{_esc(r['reason'])}</td><td>{_esc(r['created_at'])}</td></tr>" for r in flags)
    body = f"""<h2>داشبورد من</h2><div class="grid"><div class="card">دانش‌آموزان تخصیص‌یافته<h2>{len(students)}</h2></div><div class="card">موارد نیازمند بررسی<h2>{len(flags)}</h2></div></div>
<p class="muted">فقط پرونده‌هایی نمایش داده می‌شوند که در حال حاضر به شما تخصیص فعال دارند.</p>
<h2>پرونده دانش‌آموزان</h2><table><tr><th>نام</th><th>پایه</th><th>رشته</th><th>آخرین گزارش</th><th>پیگیری باز</th></tr>{trs or '<tr><td colspan="5">هنوز دانش‌آموزی به شما تخصیص داده نشده است.</td></tr>'}</table>
<h2>موارد نیازمند بررسی</h2><table><tr><th>دانش‌آموز</th><th>اولویت</th><th>خلاصه</th><th>تاریخ</th></tr>{frows or '<tr><td colspan="4">مورد بازی ثبت نشده است.</td></tr>'}</table>
<div class="warn">جزئیات حساس دانش‌آموز در پیام تلگرام ارسال نمی‌شود؛ اطلاعات پرونده فقط در پنل امن دیده می‌شود.</div>"""
    return _page("داشبورد مشاور", body, co)

@router.get("/counselor/student/{student_id}", response_class=HTMLResponse)
def student_page(req: Request, student_id: int):
    co = _guard(req)
    if not co: return RedirectResponse("/counselor/login", status_code=303)
    c = db.conn()
    s = c.execute("""SELECT s.* FROM students s JOIN student_counselor_assignments a
        ON a.student_id=s.id AND a.active=1 AND a.counselor_id=? WHERE s.id=?""", (co["id"], student_id)).fetchone()
    if not s:
        c.close()
        return _page("دسترسی مجاز نیست", "<div class='warn'>این پرونده به شما تخصیص فعال ندارد.</div>", co)
    reports = c.execute("""SELECT dr.*,
        (SELECT answer FROM daily_report_answers a WHERE a.report_id=dr.id AND a.question_key='mood') mood,
        (SELECT answer FROM daily_report_answers a WHERE a.report_id=dr.id AND a.question_key='stress') stress,
        (SELECT answer FROM daily_report_answers a WHERE a.report_id=dr.id AND a.question_key='motivation') motivation
        FROM daily_reports dr WHERE dr.student_id=? ORDER BY dr.report_date DESC LIMIT 45""", (student_id,)).fetchall()
    notes = c.execute("SELECT note,created_at FROM counselor_notes WHERE student_id=? ORDER BY id DESC LIMIT 25", (student_id,)).fetchall()
    followups = c.execute("SELECT id,followup_type,priority,due_at,note,created_at FROM followups WHERE student_id=? AND status='open' ORDER BY id DESC LIMIT 40", (student_id,)).fetchall()
    c.close()
    rrows = "".join(f"<tr><td>{_esc(r['report_date'])}</td><td>{float(r['study_hours'] or 0):.1f}</td><td>{float(r['plan_execution'] or 0):.0f}%</td><td>{int(r['practice_count'] or 0)}</td><td>{_esc(r['main_problem'])}</td><td>{_esc(r['mood'] or '—')}</td><td>{_esc(r['stress'] or '—')}</td><td>{_esc(r['motivation'] or '—')}</td><td>{_esc(r['status'])}</td></tr>" for r in reports)
    nrows = "".join(f"<li>{_esc(n['note'])} <span class='muted'>({_esc(n['created_at'])})</span></li>" for n in notes)
    furows = "".join(f"<tr><td>{_esc(f['followup_type'])}</td><td>{_esc(f['priority'])}</td><td>{_esc(f['due_at'] or '—')}</td><td>{_esc(f['note'])}</td><td><form method='post' action='/counselor/followup/{f['id']}/complete'><input type='hidden' name='student_id' value='{student_id}'><button>تکمیل شد</button></form></td></tr>" for f in followups)
    body = f"""<h2>پرونده {_esc(s['first_name'])} {_esc(s['last_name'])}</h2><p>پایه: {_esc(s['grade'])} | رشته: {_esc(s['track'])}</p>
<div class="card"><h3>ثبت یادداشت مشاور</h3><form method="post" action="/counselor/student/{student_id}/note"><textarea name="note" required maxlength="4000" placeholder="خلاصه جلسه، نکته مهم، اقدام بعدی..."></textarea><button>ثبت یادداشت</button></form></div>
<div class="card"><h3>ثبت پیگیری جدید</h3><form method="post" action="/counselor/student/{student_id}/followup"><label>نوع پیگیری</label><select name="followup_type"><option value="general">عمومی</option><option value="study_plan">برنامه درسی</option><option value="parent_contact">تماس با والدین</option><option value="daily_report_followup">گزارش روزانه</option></select><label>اولویت</label><select name="priority"><option value="normal">عادی</option><option value="high">بالا</option><option value="urgent">فوری</option></select><label>زمان پیگیری (اختیاری)</label><input name="due_at" placeholder="2026-10-12 16:00"><label>یادداشت</label><textarea name="note" maxlength="2000"></textarea><button>ثبت پیگیری</button></form></div>
<h3>یادداشت‌های اخیر</h3><ul>{nrows or '<li>یادداشتی ثبت نشده است.</li>'}</ul>
<h3>پیگیری‌های باز</h3><table><tr><th>نوع</th><th>اولویت</th><th>زمان</th><th>یادداشت</th><th>عملیات</th></tr>{furows or '<tr><td colspan="5">پیگیری بازی وجود ندارد.</td></tr>'}</table>
<h3>گزارش‌های روزانه</h3><table><tr><th>تاریخ</th><th>ساعت</th><th>اجرای برنامه</th><th>تمرین</th><th>مشکل اصلی</th><th>حال روحی</th><th>استرس</th><th>انگیزه</th><th>وضعیت</th></tr>{rrows or '<tr><td colspan="9">گزارشی ثبت نشده است.</td></tr>'}</table>
<p><a class="btn" href="/counselor">بازگشت به داشبورد</a></p>"""
    return _page("پرونده دانش‌آموز", body, co)

def _owns(counselor_id, student_id):
    c = db.conn()
    row = c.execute("SELECT 1 FROM student_counselor_assignments WHERE counselor_id=? AND student_id=? AND active=1 LIMIT 1", (counselor_id, student_id)).fetchone()
    c.close()
    return bool(row)

@router.post("/counselor/student/{student_id}/note")
def add_note(req: Request, student_id: int, note: str = Form(...)):
    co = _guard(req)
    if not co: return RedirectResponse("/counselor/login", status_code=303)
    note = note.strip()[:4000]
    if note and _owns(co["id"], student_id): db.add_counselor_note(student_id, co["id"], note)
    return RedirectResponse(f"/counselor/student/{student_id}", status_code=303)

@router.post("/counselor/student/{student_id}/followup")
def add_followup(req: Request, student_id: int, followup_type: str = Form("general"), priority: str = Form("normal"), due_at: str = Form(""), note: str = Form("")):
    co = _guard(req)
    if not co: return RedirectResponse("/counselor/login", status_code=303)
    types = {"general", "study_plan", "parent_contact", "daily_report_followup"}
    priorities = {"normal", "high", "urgent"}
    if _owns(co["id"], student_id):
        db.create_followup(student_id, followup_type if followup_type in types else "general", priority if priority in priorities else "normal", due_at.strip()[:40] or None, note.strip()[:2000], counselor_id=co["id"])
    return RedirectResponse(f"/counselor/student/{student_id}", status_code=303)

@router.post("/counselor/followup/{followup_id}/complete")
def finish_followup(req: Request, followup_id: int, student_id: int = Form(...)):
    co = _guard(req)
    if not co: return RedirectResponse("/counselor/login", status_code=303)
    if _owns(co["id"], student_id):
        c = db.conn()
        c.execute("""UPDATE followups SET status='completed',completed_at=CURRENT_TIMESTAMP
            WHERE id=? AND student_id=? AND counselor_id=? AND status='open'""", (followup_id, student_id, co["id"]))
        c.commit()
        c.close()
    return RedirectResponse(f"/counselor/student/{student_id}", status_code=303)

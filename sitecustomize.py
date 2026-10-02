"""Small admin extension loaded at Python startup.

Provides a safe lookup page for students who are registered in the bot but are
not currently present in the CRM/access request lists. It does not create,
delete, or overwrite student records.
"""

import html

try:
    from fastapi import Form, Request
    from fastapi.responses import HTMLResponse, RedirectResponse
    from app import db
    from app.admin import app as admin_app

    def _esc(value):
        return html.escape(str(value or ""))

    def _guard(req):
        return bool(req.session.get("admin"))

    @admin_app.get("/admin/access-search", response_class=HTMLResponse)
    def access_search(req: Request, q: str = ""):
        if not _guard(req):
            return RedirectResponse("/admin/login", status_code=303)

        q = (q or "").strip()
        rows = []
        if q:
            c = db.conn()
            like = f"%{q.lstrip('@')}%"
            rows = c.execute(
                """SELECT s.id, s.telegram_id, s.username, s.first_name, s.last_name,
                          s.grade, s.track, s.phone,
                          a.status access_status, a.plan_code, a.starts_at, a.expires_at
                   FROM students s
                   LEFT JOIN student_access a
                     ON a.id=(
                        SELECT a2.id FROM student_access a2
                        WHERE a2.student_id=s.id
                        ORDER BY CASE WHEN a2.status='active' THEN 0
                                      WHEN a2.status='pending' THEN 1
                                      ELSE 2 END,
                                 a2.id DESC
                        LIMIT 1
                     )
                   WHERE s.username LIKE ?
                      OR CAST(s.telegram_id AS TEXT) LIKE ?
                      OR s.first_name LIKE ?
                      OR s.last_name LIKE ?
                      OR (s.first_name || ' ' || s.last_name) LIKE ?
                   ORDER BY s.id DESC
                   LIMIT 50""",
                (like, like, like, like, like),
            ).fetchall()
            c.close()

        result_rows = ""
        for r in rows:
            access = r["access_status"] or "بدون دسترسی"
            result_rows += f"""
            <tr>
              <td>{r['id']}</td>
              <td>{_esc(r['first_name'])} {_esc(r['last_name'])}</td>
              <td>{_esc(r['username'])}</td>
              <td>{r['telegram_id']}</td>
              <td>{_esc(r['grade'])} / {_esc(r['track'])}</td>
              <td>{_esc(access)}</td>
              <td>{_esc(r['expires_at'])}</td>
              <td>
                <form method="post" action="/admin/access-search/grant">
                  <input type="hidden" name="student_id" value="{r['id']}">
                  <input type="hidden" name="q" value="{_esc(q)}">
                  <input name="days" type="number" min="1" max="365" value="30"
                         style="width:70px">
                  <button type="submit">فعال‌سازی</button>
                </form>
              </td>
            </tr>"""

        body = f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>جستجوی دانش‌آموز برای دسترسی</title>
<style>
body{{font-family:Tahoma,Arial,sans-serif;max-width:1200px;margin:24px auto;
padding:0 16px;background:#f6f7fb;color:#222;line-height:1.8}}
.card{{background:#fff;padding:18px;border-radius:14px;border:1px solid #e5e7eb}}
input{{box-sizing:border-box;padding:10px;border:1px solid #d0d5dd;border-radius:8px;font-family:inherit}}
button{{padding:10px 16px;border:0;border-radius:8px;background:#1557b0;color:#fff}}
table{{width:100%;border-collapse:collapse;background:#fff;margin-top:20px}}
th,td{{padding:9px;border-bottom:1px solid #eee;text-align:right;font-size:13px}}
a{{color:#1557b0}}
.warn{{background:#fffaeb;color:#b54708;padding:12px;border-radius:10px}}
</style>
</head>
<body>
<p><a href="/admin/access">← بازگشت به دسترسی و تمدید</a></p>
<h1>🔎 پیدا کردن دانش‌آموز برای فعال‌سازی دسترسی</h1>
<div class="card">
<p>نام، نام خانوادگی، نام کاربری تلگرام یا Telegram ID را وارد کنید.</p>
<form method="get">
<input name="q" value="{_esc(q)}" placeholder="مثلاً MohsenTsani یا محسن تصدیقی" style="width:70%" required>
<button type="submit">جستجو</button>
</form>
</div>
{("<div class='warn'>تعداد نتایج: " + str(len(rows)) + "</div>" if q else "")}
<table>
<tr><th>ID</th><th>نام</th><th>Username</th><th>Telegram ID</th><th>پایه/رشته</th>
<th>وضعیت دسترسی</th><th>انقضا</th><th>عملیات</th></tr>
{result_rows or "<tr><td colspan='8'>هنوز جستجویی انجام نشده یا نتیجه‌ای پیدا نشد.</td></tr>"}
</table>
</body></html>"""
        return HTMLResponse(body, media_type="text/html; charset=utf-8")

    @admin_app.post("/admin/access-search/grant")
    def access_search_grant(
        req: Request,
        student_id: int = Form(...),
        days: int = Form(30),
        q: str = Form(""),
    ):
        if not _guard(req):
            return RedirectResponse("/admin/login", status_code=303)

        days = max(1, min(int(days), 365))
        student = db.get_student(student_id)
        if not student:
            return RedirectResponse("/admin/access-search?q=" + q, status_code=303)

        db.grant_access(
            student_id,
            days,
            plan_code=f"access_{days}",
            actor="admin",
            note=f"فعال‌سازی {days} روزه از جستجوی مستقیم دانش‌آموز",
        )
        return RedirectResponse(
            "/admin/access-search?q=" + q,
            status_code=303,
        )

except Exception as exc:
    # Never prevent the main application from starting because this optional
    # admin extension is unavailable.
    print(f"[WARN] access-search extension not loaded: {exc}", flush=True)

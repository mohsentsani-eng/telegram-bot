"""Loopback-only Apex360 API with a temporary database and a synthetic student."""
import html
import os
import secrets
from tempfile import TemporaryDirectory
from pathlib import Path
from contextlib import closing

import uvicorn
from fastapi import FastAPI, Form, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import admin, counselor_portal, db, migrations, mobile_api

STUDENT_ID = -14
TELEGRAM_ID = -1400
COUNSELOR_USERNAME = "apex-test-counselor"
ADMIN_USERNAME = "apex-test-admin"


class LocalLogin(BaseModel):
    code: str = Field(min_length=1, max_length=128)


def create_app(code: str, *, telegram_id=TELEGRAM_ID, operator_code=None) -> FastAPI:
    app = FastAPI()
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    app.add_middleware(SessionMiddleware, secret_key=secrets.token_urlsafe(32))
    app.include_router(admin.app.router)

    @app.middleware("http")
    async def disable_cache(request, call_next):
        response: Response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.post("/api/v1/mobile/auth/local")
    def local_login(payload: LocalLogin):
        if not secrets.compare_digest(payload.code.encode(), code.encode()):
            raise HTTPException(status_code=401, detail="invalid_test_code")
        c = db.conn()
        try:
            registered = c.execute(
                "SELECT 1 FROM students WHERE telegram_id=? AND registered=1", (telegram_id,),
            ).fetchone()
            if not registered:
                raise HTTPException(409, "demo_registration_required")
            tokens = mobile_api._new_session(c, telegram_id)
            c.commit()
            return tokens
        finally:
            c.close()

    if operator_code:
        @app.get("/demo", response_class=HTMLResponse)
        def demo_setup():
            with closing(db.conn()) as c, c:
                student = c.execute(
                    """SELECT id,first_name,last_name FROM students WHERE telegram_id=?""", (telegram_id,),
                ).fetchone()
            if student is None:
                fields = """
                <label>نام <input name="first_name" value="آرین" required maxlength="40"></label>
                <label>نام خانوادگی <input name="last_name" value="نمونه" required maxlength="40"></label>
                <button name="action" value="register">ثبت دانش‌آموز ساختگی</button>"""
            else:
                fields = ""
            body = """<meta charset="utf-8"><meta name="viewport" content="width=device-width">
                <title>نمایش Apex360</title><main dir="rtl"><h1>آماده‌سازی نمایش Apex360</h1>
                <p>از نام و مشخصات ساختگی استفاده کنید.</p>"""
            if fields:
                body += f"""<form method="post"><label>کد راه‌اندازی
                    <input name="code" type="password" required></label>{fields}</form>"""
            else:
                name = html.escape(f"{student['first_name']} {student['last_name']}")
                body += f"""<p>{name} ثبت شد.</p>
                    <p><a href="/admin/student/{student['id']}/reports">پرونده در پنل مدیر</a></p>
                    <p><a href="/counselor/login">ورود مشاور</a></p>"""
            return body + "</main>"

        @app.post("/demo")
        def change_demo(action: str = Form(...), code: str = Form(..., max_length=128),
                        first_name: str = Form("", max_length=40),
                        last_name: str = Form("", max_length=40)):
            if not secrets.compare_digest(code.encode(), operator_code.encode()):
                raise HTTPException(403, "invalid_operator_code")
            if action == "register":
                if not first_name.strip() or not last_name.strip():
                    raise HTTPException(422, "demo_name_required")
                with closing(db.conn()) as c, c:
                    c.execute(
                        """INSERT INTO students(id,telegram_id,first_name,last_name,grade)
                           VALUES (?,?,?,?,'دهم') ON CONFLICT(telegram_id) DO NOTHING""",
                        (telegram_id, telegram_id, first_name.strip(), last_name.strip()),
                    )
            else:
                raise HTTPException(422, "invalid_demo_step")
            return RedirectResponse("/demo", status_code=303)

    return app


def seed(counselor_password: str, *, preconfigured=True):
    db.init_db()
    migrations.migrate()
    if preconfigured:
        with closing(db.conn()) as c, c:
            c.execute(
                """INSERT INTO students(id, telegram_id, first_name, last_name, grade)
                   VALUES (?, ?, 'دانش‌آموز', 'آزمایشی', 'دهم')""",
                (STUDENT_ID, TELEGRAM_ID),
            )
    counselor_id = db.add_counselor("مشاور آزمایشی ترنم")
    c = db.conn()
    try:
        c.execute(
            "INSERT INTO counselor_accounts(counselor_id,username,password_hash) VALUES(?,?,?)",
            (counselor_id, COUNSELOR_USERNAME, counselor_portal._hash_password(counselor_password)),
        )
        c.commit()
    finally:
        c.close()
    if preconfigured:
        db.assign_counselor(STUDENT_ID, counselor_id)
        db.publish_counselor_plan(STUDENT_ID, counselor_id, "برنامه آزمایشی مشاور", [
            ["شنبه", 960, 1005, "ریاضی"], ["یکشنبه", 1020, 1065, "زیست"],
        ])
    return counselor_id


def main():
    with TemporaryDirectory(prefix="apex360-mobile-") as directory:
        db.DB = Path(directory) / "test.sqlite3"
        code = secrets.token_urlsafe(18)
        counselor_password = secrets.token_urlsafe(18)
        operator_code = secrets.token_urlsafe(18)
        # A new server run uses a different account so old device queues stay scoped.
        telegram_id = -(2**40 + secrets.randbits(40))
        seed(counselor_password, preconfigured=False)
        os.environ.update(ADMIN_USERNAME=ADMIN_USERNAME, ADMIN_PASSWORD=secrets.token_urlsafe(18),
                          ADMIN_SECRET=secrets.token_urlsafe(32))
        print(f"Apex360 local admin: {ADMIN_USERNAME} / {os.environ['ADMIN_PASSWORD']}", flush=True)
        print(f"Apex360 demo setup: /demo — operator code: {operator_code}", flush=True)
        print(f"Apex360 local student code: {code}", flush=True)
        print(f"Apex360 local counselor: {COUNSELOR_USERNAME} / {counselor_password}", flush=True)
        uvicorn.run(create_app(code, telegram_id=telegram_id, operator_code=operator_code), host="127.0.0.1",
                    port=int(os.environ.get("APEX_TEST_PORT", "8765")),
                    access_log=False)


if __name__ == "__main__":
    main()

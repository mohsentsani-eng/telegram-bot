"""Loopback-only Apex360 API with a temporary database and a synthetic student."""
import os
import secrets
from tempfile import TemporaryDirectory
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

from app import counselor_portal, db, migrations, mobile_api

STUDENT_ID = -14
TELEGRAM_ID = -1400
COUNSELOR_USERNAME = "apex-test-counselor"


class LocalLogin(BaseModel):
    code: str = Field(min_length=1, max_length=128)


def create_app(code: str) -> FastAPI:
    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key=secrets.token_urlsafe(32))
    app.include_router(mobile_api.router)
    app.include_router(counselor_portal.router)

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
            tokens = mobile_api._new_session(c, TELEGRAM_ID)
            c.commit()
            return tokens
        finally:
            c.close()

    return app


def seed(counselor_password: str):
    db.init_db()
    migrations.migrate()
    c = db.conn()
    try:
        c.execute(
            """INSERT INTO students(id, telegram_id, first_name, last_name, grade)
               VALUES (?, ?, 'دانش‌آموز', 'آزمایشی', 'دهم')""",
            (STUDENT_ID, TELEGRAM_ID),
        )
        c.commit()
    finally:
        c.close()
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
    db.assign_counselor(STUDENT_ID, counselor_id)
    db.publish_counselor_plan(STUDENT_ID, counselor_id, "برنامه آزمایشی مشاور", [
        ["شنبه", 960, 1005, "ریاضی"], ["یکشنبه", 1020, 1065, "زیست"],
    ])


def main():
    with TemporaryDirectory(prefix="apex360-mobile-") as directory:
        db.DB = Path(directory) / "test.sqlite3"
        code = secrets.token_urlsafe(18)
        counselor_password = secrets.token_urlsafe(18)
        seed(counselor_password)
        print(f"Apex360 local student code: {code}", flush=True)
        print(f"Apex360 local counselor: {COUNSELOR_USERNAME} / {counselor_password}", flush=True)
        uvicorn.run(create_app(code), host="127.0.0.1",
                    port=int(os.environ.get("APEX_TEST_PORT", "8765")),
                    access_log=False)


if __name__ == "__main__":
    main()

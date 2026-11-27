"""Loopback-only Apex360 API with a temporary database and a synthetic student."""
import os
import secrets
from tempfile import TemporaryDirectory
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

from app import db, migrations, mobile_api

STUDENT_ID = -14
TELEGRAM_ID = -1400


class LocalLogin(BaseModel):
    code: str = Field(min_length=1, max_length=128)


def create_app(code: str) -> FastAPI:
    app = FastAPI()
    app.include_router(mobile_api.router)

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


def seed():
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
    db.save_plan(STUDENT_ID, "برنامه آزمایشی مشاور", {
        "schedule": [["شنبه", 960, 1005, "ریاضی"], ["یکشنبه", 1020, 1065, "زیست"]],
    })


def main():
    with TemporaryDirectory(prefix="apex360-mobile-") as directory:
        db.DB = Path(directory) / "test.sqlite3"
        seed()
        code = secrets.token_urlsafe(18)
        print(f"Apex360 local student code: {code}", flush=True)
        uvicorn.run(create_app(code), host="127.0.0.1",
                    port=int(os.environ.get("APEX_TEST_PORT", "8765")),
                    access_log=False)


if __name__ == "__main__":
    main()

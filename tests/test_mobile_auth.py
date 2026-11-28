"""Isolated mobile login smoke tests; never use the production database."""
import sqlite3

import pytest
from pathlib import Path

from app import db, mobile_api


def test_mobile_login_and_profile(tmp_path, monkeypatch):
    database = tmp_path / "mobile_auth_test.sqlite3"
    monkeypatch.setattr(db, "DB", database)
    c = db.conn()
    c.executescript("""
        CREATE TABLE students (
            id INTEGER PRIMARY KEY,
            telegram_id INTEGER UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            grade TEXT NOT NULL,
            track TEXT,
            city TEXT,
            registered INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE mobile_auth_challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_id TEXT NOT NULL UNIQUE,
            secret_hash TEXT NOT NULL,
            telegram_id INTEGER,
            status TEXT NOT NULL DEFAULT 'pending',
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            approved_at TEXT,
            consumed_at TEXT
        );
        CREATE TABLE mobile_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            access_token_hash TEXT NOT NULL UNIQUE,
            refresh_token_hash TEXT NOT NULL UNIQUE,
            access_expires_at TEXT NOT NULL,
            refresh_expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            revoked_at TEXT
        );
        INSERT INTO students (telegram_id,first_name,last_name,grade,track,city)
        VALUES (123456,'دانش','آموز','دهم','تجربی','سبزوار');
    """)
    c.commit()
    c.close()

    challenge = mobile_api.create_auth_challenge(mobile_api.ChallengeRequest())
    payload = challenge["verification_url"].split("start=", 1)[1].split("_")
    challenge_id, secret = payload[1], payload[2]
    poll = mobile_api.ChallengePollRequest(secret=secret)
    assert mobile_api.poll_auth_challenge(challenge_id, poll)["status"] == "pending"
    assert not mobile_api.approve_mobile_challenge(challenge_id, "wrong", 123456)
    assert mobile_api.approve_mobile_challenge(challenge_id, secret, 123456)
    login = mobile_api.poll_auth_challenge(challenge_id, poll)
    assert login["status"] == "authenticated"
    assert mobile_api.poll_auth_challenge(challenge_id, poll)["status"] == "consumed"

    bearer = "Bearer " + login["access_token"]
    profile = mobile_api.mobile_student_profile(authorization=bearer)
    assert profile["first_name"] == "دانش"
    assert profile["grade"] == "دهم"
    assert "phone" not in profile

    refreshed = mobile_api.refresh_session(
        mobile_api.RefreshRequest(refresh_token=login["refresh_token"])
    )
    assert refreshed["access_token"] != login["access_token"]
    try:
        mobile_api.refresh_session(
            mobile_api.RefreshRequest(refresh_token=login["refresh_token"])
        )
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 401
    else:
        raise AssertionError("Reused refresh token must be rejected")

    # Sync one event twice: server must store it once and acknowledge both requests.
    from datetime import datetime, timezone
    db_conn = db.conn()
    db_conn.executescript("""
        CREATE TABLE mobile_study_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL, event_id TEXT NOT NULL,
            subject TEXT NOT NULL, activity_type TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL, test_count INTEGER NOT NULL,
            client_created_at TEXT NOT NULL,
            received_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id,event_id)
        );
    """)
    db_conn.commit()
    db_conn.close()
    event = mobile_api.StudyActivityPayload(
        event_id="offline-event-0001", subject="زیست",
        activity_type="study", duration_minutes=45, test_count=10,
        created_at=datetime.now(timezone.utc),
    )
    request = mobile_api.StudySyncRequest(activities=[event])
    bearer_new = "Bearer " + refreshed["access_token"]
    first = mobile_api.sync_study_activities(request, authorization=bearer_new)
    second = mobile_api.sync_study_activities(request, authorization=bearer_new)
    assert first["accepted_event_ids"] == ["offline-event-0001"]
    assert second == first
    db_conn = db.conn()
    assert db_conn.execute("SELECT COUNT(*) FROM mobile_study_activities").fetchone()[0] == 1
    db_conn.close()

    # Logout revokes the refreshed session, not the previously rotated one.
    refreshed_bearer = "Bearer " + refreshed["access_token"]
    result = mobile_api.logout_session(
        mobile_api.LogoutRequest(refresh_token=refreshed["refresh_token"]),
        authorization=refreshed_bearer,
    )
    assert result == {"logged_out": True}
    for operation in (
        lambda: mobile_api.mobile_student_profile(authorization=refreshed_bearer),
        lambda: mobile_api.refresh_session(
            mobile_api.RefreshRequest(refresh_token=refreshed["refresh_token"])
        ),
    ):
        try:
            operation()
        except Exception as exc:
            assert getattr(exc, "status_code", None) == 401
        else:
            raise AssertionError("Logged-out session must not remain valid")


def test_approved_challenge_expires_without_issuing_tokens(tmp_path, monkeypatch):
    """An approved challenge must not be redeemable after its deadline."""
    from datetime import datetime, timedelta, timezone

    # Reuse the isolated schema and seeded student from the smoke test setup.
    database = tmp_path / "expiry.sqlite3"
    monkeypatch.setattr(db, "DB", database)
    c = db.conn()
    c.executescript("""
        CREATE TABLE students (
            id INTEGER PRIMARY KEY, telegram_id INTEGER UNIQUE NOT NULL,
            first_name TEXT NOT NULL, last_name TEXT NOT NULL,
            grade TEXT NOT NULL, track TEXT, city TEXT,
            registered INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE mobile_auth_challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_id TEXT NOT NULL UNIQUE, secret_hash TEXT NOT NULL,
            telegram_id INTEGER, status TEXT NOT NULL DEFAULT 'pending',
            expires_at TEXT NOT NULL, created_at TEXT NOT NULL,
            approved_at TEXT, consumed_at TEXT
        );
        CREATE TABLE mobile_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            access_token_hash TEXT NOT NULL UNIQUE,
            refresh_token_hash TEXT NOT NULL UNIQUE,
            access_expires_at TEXT NOT NULL, refresh_expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL, revoked_at TEXT
        );
        INSERT INTO students (telegram_id,first_name,last_name,grade)
        VALUES (123456,'دانش','آموز','دهم');
    """)
    c.commit()
    c.close()

    challenge = mobile_api.create_auth_challenge(mobile_api.ChallengeRequest())
    parts = challenge["verification_url"].split("start=", 1)[1].split("_")
    challenge_id, secret = parts[1], parts[2]
    assert mobile_api.approve_mobile_challenge(challenge_id, secret, 123456)
    c = db.conn()
    expired = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
    c.execute("UPDATE mobile_auth_challenges SET expires_at=? WHERE challenge_id=?",
              (expired, challenge_id))
    c.commit()
    c.close()
    assert mobile_api.poll_auth_challenge(
        challenge_id, mobile_api.ChallengePollRequest(secret=secret)
    )["status"] == "expired"
    c = db.conn()
    assert c.execute("SELECT COUNT(*) FROM mobile_sessions").fetchone()[0] == 0
    c.close()


def test_local_api_login_plan_and_report_retry(tmp_path, monkeypatch):
    import re

    from fastapi.testclient import TestClient

    from tools.mobile_test_api import COUNSELOR_USERNAME, STUDENT_ID, create_app, seed

    monkeypatch.setattr(db, "DB", tmp_path / "apex-local.sqlite3")
    seed("counselor-test-only")
    c = db.conn()
    try:
        other = c.execute(
            "INSERT INTO students(telegram_id,first_name,last_name,grade) VALUES(4,'B','B','B')"
        ).lastrowid
        c.commit()
    finally:
        c.close()
    db.save_plan(other, "Other student's plan", {"schedule": []})
    client = TestClient(create_app("test-only"), base_url="http://127.0.0.1")
    route = "/api/v1/mobile/student/counselor"
    assert client.get(route).status_code == 401
    db.save_plan(STUDENT_ID, "برنامه شخصی", {"schedule": []})
    path = "/api/v1/mobile/auth/local"
    assert client.post(path, json={"code": "incorrect"}).status_code == 401
    login = client.post(path, json={"code": "test-only"}).json()
    headers = {"Authorization": "Bearer " + login["access_token"]}
    profile = client.get("/api/v1/mobile/student/profile", headers=headers)
    assert profile.json()["student_id"] == STUDENT_ID
    plan = client.get(route, headers=headers)
    assert plan.json()["assignment"]["name"] == "مشاور آزمایشی ترنم"
    assert plan.json()["plan"]["title"] == "برنامه آزمایشی مشاور"
    assert plan.headers["Cache-Control"] == "no-store"

    activity = {
        "event_id": "apex-offline-report-001", "subject": "ریاضی",
        "activity_type": "practice", "duration_minutes": 45,
        "test_count": 5, "created_at": "2026-11-27T12:00:00Z",
    }
    sync = "/api/v1/mobile/student/study-activities/sync"
    for _ in range(2):
        response = client.post(sync, json={"activities": [activity]}, headers=headers)
        assert response.json() == {"accepted_event_ids": [activity["event_id"]]}
    assert client.post("/counselor/login", data={
        "username": COUNSELOR_USERNAME, "password": "counselor-test-only",
    }, follow_redirects=False).status_code == 303
    page = client.get(f"/counselor/student/{STUDENT_ID}")
    assert "گزارش‌های Apex360" in page.text and "تمرین" in page.text
    csrf = re.search(r'name="csrf" value="([^"]+)"', page.text)[1]
    form = {"csrf": csrf, "title": "برنامه تازه", "schedule": "شنبه | 18:00 | 18:45 | علوم"}
    publish_url = f"/counselor/student/{STUDENT_ID}/plan"
    assert client.post(publish_url, data={**form, "csrf": "wrong"}).status_code == 403
    assert client.post(publish_url, data={**form, "schedule": "شنبه | 18:50 | 18:45 | علوم"}).status_code == 422
    assert client.post(f"/counselor/student/{other}/plan", data=form).status_code == 403
    assert client.post(publish_url, data=form, follow_redirects=False).status_code == 303
    assert client.get(route, headers=headers).json()["plan"]["schedule"] == [["شنبه", 1080, 1125, "علوم"]]

    db.assign_counselor(STUDENT_ID, db.add_counselor("مشاور تازه"))
    reassigned = client.get(route, headers=headers).json()
    assert reassigned["assignment"]["name"] == "مشاور تازه"
    assert reassigned["plan"] is None
    assert client.post(publish_url, data=form).status_code == 403
    c = db.conn()
    try:
        assert c.execute("SELECT COUNT(*) FROM mobile_study_activities").fetchone()[0] == 1
        assert c.execute("SELECT COUNT(*) FROM plans").fetchone()[0] == 4
    finally:
        c.close()


def _serve_https(app, tmp_path, stack):
    import socket
    import ssl
    import subprocess
    import threading
    import time

    import httpx
    import uvicorn

    cert = tmp_path / "test-cert.pem"
    key = tmp_path / "test-key.pem"
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
        "-subj", "/CN=localhost", "-addext", "subjectAltName=IP:127.0.0.1",
        "-keyout", str(key), "-out", str(cert),
    ], check=True, capture_output=True)
    sock = stack.enter_context(socket.socket())
    sock.bind(("127.0.0.1", 0))
    origin = f"https://127.0.0.1:{sock.getsockname()[1]}"
    server = uvicorn.Server(uvicorn.Config(
        app, ssl_certfile=str(cert), ssl_keyfile=str(key), access_log=False,
    ))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()

    def stop():
        server.should_exit = True
        thread.join(timeout=10)
        assert not thread.is_alive()

    stack.callback(stop)
    for _ in range(100):
        if server.started:
            break
        time.sleep(.05)
    else:
        raise RuntimeError("HTTPS fixture did not start")
    tls = ssl.create_default_context(cafile=str(cert))

    def client():
        return stack.enter_context(httpx.Client(base_url=origin, verify=tls, trust_env=False))

    return origin, str(cert), client


@pytest.fixture
def https_service(tmp_path):
    from contextlib import ExitStack
    from app import admin

    with ExitStack() as stack:
        yield _serve_https(admin.app, tmp_path, stack)


def test_v18_central_https_with_synthetic_accounts(tmp_path, monkeypatch, https_service):
    import re

    import httpx
    from fastapi.testclient import TestClient

    from app import migrations
    from tools.mobile_check import check_origin
    from tools.mobile_test_api import ADMIN_USERNAME, COUNSELOR_USERNAME, create_app, seed

    monkeypatch.setattr(db, "DB", tmp_path / "demo.sqlite3")
    counselor = seed("fake-counselor-password", preconfigured=False)
    monkeypatch.setenv("ADMIN_USERNAME", ADMIN_USERNAME)
    monkeypatch.setenv("ADMIN_PASSWORD", "fake-admin-password")
    monkeypatch.setenv("ADMIN_SECRET", "temporary-test-value")
    inactive = db.add_counselor("مشاور غیرفعال")
    with db.conn() as connection:
        connection.execute("UPDATE counselors SET active=0 WHERE id=?", (inactive,))
    student = -1600
    origin, cert, make_client = https_service
    with pytest.raises(httpx.ConnectError):
        check_origin(origin)
    monkeypatch.setattr(mobile_api, "BOT_USERNAME", "ApexRehearsalBot")
    with pytest.raises(ValueError, match="Telegram bot differs"):
        check_origin(origin, ca_file=cert)
    check_origin(origin, bot="ApexRehearsalBot", ca_file=cert)
    central = make_client()
    central_login = central.post("/admin/login", data={
        "username": ADMIN_USERNAME, "password": "fake-admin-password",
    }, follow_redirects=False)
    assert "secure" in central_login.headers["set-cookie"].lower()
    assert central_login.headers["cache-control"] == "no-store"
    assert central.get("/demo").status_code == 404
    assert central.post("/api/v1/mobile/auth/local", json={"code": "student-code"}).status_code == 404
    client = TestClient(create_app("student-code", telegram_id=student,
                                   operator_code="operator-code"),
                        base_url="http://127.0.0.1")
    login_path = "/api/v1/mobile/auth/local"
    login_data = {"code": "student-code"}
    assert client.post(login_path, json=login_data).status_code == 409
    assert "ثبت دانش‌آموز ساختگی" in client.get("/demo").text
    registration = {"action": "register", "first_name": "آرین", "last_name": "نمونه"}
    assert client.post("/demo", data={**registration, "code": "student-code"}).status_code == 403
    for _ in range(2):
        assert client.post("/demo", data={**registration, "code": "operator-code"},
                           follow_redirects=False).status_code == 303
    assert client.post(login_path, json=login_data).status_code == 200
    assert central.get("/api/v1/mobile/capabilities").json()["student_workflow_version"] == 17
    # Use the same challenge endpoints and approval helper called by the Telegram bot.
    challenge_path = "/api/v1/mobile/auth/challenge"
    challenge = central.post(challenge_path, json={"platform": "flutter"}).json()
    assert challenge["verification_url"].startswith("https://t.me/ApexRehearsalBot?start=")
    _, challenge_id, secret = challenge["verification_url"].split("start=", 1)[1].split("_")
    poll = f"{challenge_path}/{challenge_id}"
    assert central.post(poll, json={"secret": secret}).json() == {"status": "pending"}
    assert not mobile_api.approve_mobile_challenge(challenge_id, secret, student - 1)
    assert mobile_api.approve_mobile_challenge(challenge_id, secret, student)
    token = central.post(poll, json={"secret": secret}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    context = "/api/v1/mobile/student/counselor"
    assert central.get(context, headers=headers).json() == {"assignment": None, "plan": None}
    assignment_url = f"/admin/student/{student}/assign-counselor"
    anonymous = make_client()
    assert anonymous.post(assignment_url, data={"counselor_id": counselor},
                       follow_redirects=False).headers["location"] == "/admin/login"

    manager = central
    assignment_form = manager.get(f"/admin/student/{student}/reports")
    assignment_csrf = re.search(r'name="csrf" value="([^"]+)"', assignment_form.text)[1]
    assert manager.post(assignment_url, data={"counselor_id": counselor}).status_code == 403
    assert manager.post(assignment_url, data={
        "counselor_id": inactive, "csrf": assignment_csrf,
    }).status_code == 404
    assert manager.post(assignment_url, data={
        "counselor_id": counselor, "csrf": assignment_csrf,
    }, follow_redirects=False).status_code == 303
    assigned = central.get(context, headers=headers).json()["assignment"]
    assert assigned["name"] == "مشاور آزمایشی ترنم"

    counselor_web = make_client()
    portal = f"/counselor/student/{student}"
    feedback_path = "/api/v1/mobile/student/study-activities/feedback"
    assert central.get(feedback_path).status_code == 401
    assert counselor_web.post("/counselor/login", data={
        "username": COUNSELOR_USERNAME, "password": "fake-counselor-password",
    }, follow_redirects=False).status_code == 303
    csrf = re.search(r'name="csrf" value="([^"]+)"', counselor_web.get(portal).text)[1]
    assert counselor_web.post(f"{portal}/plan", data={
        "csrf": csrf, "title": "مرور", "schedule": "شنبه | 16:00 | 16:45 | زیست",
    }, follow_redirects=False).status_code == 303
    # Repeating the same assignment must preserve the published plan and its assignment ID.
    assert manager.post(assignment_url, data={
        "counselor_id": counselor, "csrf": assignment_csrf,
    }, follow_redirects=False).status_code == 303
    assert central.get(context, headers=headers).json()["assignment"] == assigned
    plan = central.get(context, headers=headers).json()["plan"]
    assert plan["received_at"] is None
    receipt_path = f"{context}/plans/{plan['id']}/receipt"
    assert central.post(receipt_path).status_code == 401
    assert central.post(f"{context}/plans/999/receipt", headers=headers).status_code == 404
    second = db.create_student({
        "telegram_id": student - 1, "first_name": "نمونه", "last_name": "دوم", "grade": "دهم",
    })
    other_challenge = central.post(challenge_path, json={"platform": "flutter"}).json()
    _, other_id, other_secret = other_challenge["verification_url"].split("start=", 1)[1].split("_")
    assert mobile_api.approve_mobile_challenge(other_id, other_secret, second["telegram_id"])
    other_token = central.post(f"{challenge_path}/{other_id}", json={"secret": other_secret}).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}
    assert central.post(receipt_path, headers=other_headers).status_code == 404
    receipt = central.post(receipt_path, headers=headers).json()
    assert receipt["received_at"]
    assert central.post(receipt_path, headers=headers).json() == receipt
    assert "دریافت توسط دانش‌آموز تأیید شده" in counselor_web.get(portal).text

    event = {
        "event_id": "demo-v16-report-001", "subject": "زیست", "activity_type": "study",
        "duration_minutes": 45, "test_count": 12, "created_at": "2026-11-27T12:00:00Z",
    }
    submit = "/api/v1/mobile/student/study-activities/sync"
    assert central.post(submit, json={"activities": [event, event]}, headers=headers).json() == {
        "accepted_event_ids": [event["event_id"]],
    }
    proposed = {**event, "event_id": "atomic-retry-report-01"}
    conflict = {**event, "duration_minutes": 46}
    assert central.post(submit, json={"activities": [proposed, conflict]}, headers=headers).status_code == 409
    with db.conn() as connection:
        assert connection.execute("SELECT COUNT(*) FROM mobile_study_activities").fetchone()[0] == 1
    message = {"event_id": event["event_id"], "message": "یک مرور کوتاه کافی است.", "csrf": csrf}
    assert counselor_web.post(f"{portal}/feedback", data={**message, "csrf": "invalid"}).status_code == 403
    assert counselor_web.post(f"/counselor/student/{second['id']}/feedback", data=message).status_code == 404
    assert counselor_web.post(f"{portal}/feedback", data=message, follow_redirects=False).status_code == 303
    assert central.get(feedback_path, headers=other_headers).json() == {"feedback": []}
    feedback = central.get(feedback_path, headers=headers).json()["feedback"]
    assert [(row["event_id"], row["message"]) for row in feedback] == [
        (event["event_id"], message["message"]),
    ]

    db.assign_counselor(student, db.add_counselor("مشاور دوم"))
    assert counselor_web.post(f"{portal}/feedback", data=message).status_code == 404
    assert central.post(receipt_path, headers=headers).status_code == 404
    assert central.get("/api/v1/mobile/student/study-plan", headers=headers).json() == {"plan": None}
    assert central.get(feedback_path, headers=headers).json() == {"feedback": []}
    assert not migrations.migrate()

"""Isolated mobile login smoke tests; never use the production database."""
import sqlite3
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
    client = TestClient(create_app("test-only"))
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

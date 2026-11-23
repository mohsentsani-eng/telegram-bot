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

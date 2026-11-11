"""Telegram-verified authentication foundation for the Taranom Hamdeli mobile app.

Only already-registered student Telegram accounts can approve a login. No student
profile data is returned by these endpoints.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from . import db

router = APIRouter(prefix="/api/v1/mobile", tags=["mobile-app"])
BOT_USERNAME = "TaranomHamDeliBot"
CHALLENGE_TTL_MINUTES = 5
ACCESS_TTL_MINUTES = 15
REFRESH_TTL_DAYS = 30


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _utcnow():
    return datetime.now(timezone.utc)


class ChallengeRequest(BaseModel):
    platform: str = "mobile"


class RefreshRequest(BaseModel):
    refresh_token: str


def _new_session(c, telegram_id: int):
    access = secrets.token_urlsafe(32)
    refresh = secrets.token_urlsafe(48)
    now = _utcnow()
    access_exp = now + timedelta(minutes=ACCESS_TTL_MINUTES)
    refresh_exp = now + timedelta(days=REFRESH_TTL_DAYS)
    c.execute(
        """INSERT INTO mobile_sessions
           (telegram_id,access_token_hash,refresh_token_hash,access_expires_at,
            refresh_expires_at,created_at)
           VALUES(?,?,?,?,?,?)""",
        (telegram_id, _hash(access), _hash(refresh), access_exp.isoformat(),
         refresh_exp.isoformat(), now.isoformat()),
    )
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "Bearer",
        "expires_in": ACCESS_TTL_MINUTES * 60,
    }


@router.get("/health")
def mobile_health():
    return {"ok": True, "service": "taranom-mobile-api", "api_version": 1}


@router.get("/capabilities")
def mobile_capabilities():
    return {
        "api_version": 1,
        "minimum_client_version": "0.1.0",
        "roles": ["student"],
        "authentication": "telegram-deep-link-approval",
        "offline": {
            "downloadable_study_plans": False,
            "downloadable_assessments": False,
            "assessment_answer_queue": False,
            "daily_report_queue": False,
            "mood_checkin_queue": False,
            "automatic_sync": False,
        },
        "planned_offline_features": [
            "downloadable_study_plans", "downloadable_assessments",
            "assessment_answer_queue", "daily_report_queue",
            "mood_checkin_queue", "automatic_sync",
        ],
        "online_only": ["live_messaging", "ai_analysis", "push_notification_delivery"],
    }


@router.post("/auth/challenge")
def create_auth_challenge(payload: ChallengeRequest):
    challenge_id = secrets.token_hex(6)
    secret = secrets.token_hex(16)
    expires = (_utcnow() + timedelta(minutes=CHALLENGE_TTL_MINUTES)).isoformat()
    c = db.conn()
    c.execute(
        """INSERT INTO mobile_auth_challenges
           (challenge_id,secret_hash,status,expires_at,created_at)
           VALUES(?,?,'pending',?,?)""",
        (challenge_id, _hash(secret), expires, _utcnow().isoformat()),
    )
    c.commit()
    c.close()
    start_payload = f"mobile_{challenge_id}_{secret}"
    return {
        "challenge_id": challenge_id,
        "verification_url": f"https://t.me/{BOT_USERNAME}?start={start_payload}",
        "expires_in": CHALLENGE_TTL_MINUTES * 60,
        "poll_interval_seconds": 3,
    }


@router.get("/auth/challenge/{challenge_id}")
def poll_auth_challenge(challenge_id: str, secret: str):
    c = db.conn()
    row = c.execute(
        "SELECT * FROM mobile_auth_challenges WHERE challenge_id=?",
        (challenge_id,),
    ).fetchone()
    if not row or not secrets.compare_digest(row["secret_hash"], _hash(secret)):
        c.close()
        raise HTTPException(status_code=404, detail="challenge_not_found")
    if row["status"] == "pending" and row["expires_at"] <= _utcnow().isoformat():
        c.execute(
            "UPDATE mobile_auth_challenges SET status='expired' WHERE challenge_id=? AND status='pending'",
            (challenge_id,),
        )
        c.commit()
        row = c.execute(
            "SELECT * FROM mobile_auth_challenges WHERE challenge_id=?", (challenge_id,)
        ).fetchone()
    if row["status"] != "approved":
        status = row["status"]
        c.close()
        return {"status": status}
    if row["consumed_at"]:
        c.close()
        return {"status": "consumed"}
    student = c.execute(
        "SELECT id FROM students WHERE telegram_id=? AND registered=1",
        (row["telegram_id"],),
    ).fetchone()
    if not student:
        c.close()
        raise HTTPException(status_code=403, detail="registered_student_required")
    consumed = c.execute(
        """UPDATE mobile_auth_challenges SET consumed_at=?
           WHERE challenge_id=? AND status='approved' AND consumed_at IS NULL""",
        (_utcnow().isoformat(), challenge_id),
    )
    if consumed.rowcount != 1:
        c.commit()
        c.close()
        return {"status": "consumed"}
    tokens = _new_session(c, int(row["telegram_id"]))
    c.commit()
    c.close()
    return {"status": "authenticated", "role": "student", **tokens}


@router.get("/auth/me")
def mobile_identity(authorization: str | None = Header(default=None)):
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="missing_access_token")
    c = db.conn()
    row = c.execute(
        """SELECT telegram_id,access_expires_at FROM mobile_sessions
           WHERE access_token_hash=? AND revoked_at IS NULL""",
        (_hash(token),),
    ).fetchone()
    if not row or row["access_expires_at"] <= _utcnow().isoformat():
        c.close()
        raise HTTPException(status_code=401, detail="invalid_or_expired_access_token")
    student = c.execute(
        "SELECT id FROM students WHERE telegram_id=? AND registered=1",
        (row["telegram_id"],),
    ).fetchone()
    c.close()
    if not student:
        raise HTTPException(status_code=401, detail="account_unavailable")
    return {"authenticated": True, "role": "student"}


@router.post("/auth/refresh")
def refresh_session(payload: RefreshRequest):
    token_hash = _hash(payload.refresh_token)
    c = db.conn()
    row = c.execute(
        """SELECT * FROM mobile_sessions
           WHERE refresh_token_hash=? AND revoked_at IS NULL""",
        (token_hash,),
    ).fetchone()
    if not row or row["refresh_expires_at"] <= _utcnow().isoformat():
        c.close()
        raise HTTPException(status_code=401, detail="invalid_refresh_token")
    student = c.execute(
        "SELECT id FROM students WHERE telegram_id=? AND registered=1",
        (row["telegram_id"],),
    ).fetchone()
    if not student:
        c.execute("UPDATE mobile_sessions SET revoked_at=? WHERE id=?",
                  (_utcnow().isoformat(), row["id"]))
        c.commit()
        c.close()
        raise HTTPException(status_code=401, detail="account_unavailable")
    c.execute("UPDATE mobile_sessions SET revoked_at=? WHERE id=?",
              (_utcnow().isoformat(), row["id"]))
    tokens = _new_session(c, int(row["telegram_id"]))
    c.commit()
    c.close()
    return {"role": "student", **tokens}


def approve_mobile_challenge(challenge_id: str, secret: str, telegram_id: int) -> bool:
    """Approve a valid challenge only for an existing registered student."""
    student = db.get_student_by_tg(int(telegram_id))
    if not student or not student["registered"]:
        return False
    c = db.conn()
    row = c.execute(
        """SELECT secret_hash FROM mobile_auth_challenges
           WHERE challenge_id=? AND status='pending' AND expires_at>?""",
        (challenge_id, _utcnow().isoformat()),
    ).fetchone()
    if not row or not secrets.compare_digest(row["secret_hash"], _hash(secret)):
        c.close()
        return False
    cur = c.execute(
        """UPDATE mobile_auth_challenges
           SET status='approved',telegram_id=?,approved_at=?
           WHERE challenge_id=? AND status='pending'""",
        (int(telegram_id), _utcnow().isoformat(), challenge_id),
    )
    c.commit()
    ok = cur.rowcount == 1
    c.close()
    return ok

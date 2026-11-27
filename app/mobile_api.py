"""Telegram-verified authentication foundation for the Taranom Hamdeli mobile app.

Only already-registered student Telegram accounts can approve a login.
Student endpoints derive ownership from the authenticated session.
"""
import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Header, Response
from pydantic import BaseModel, Field

from . import db

def _disable_caching(response: Response):
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(prefix="/api/v1/mobile", tags=["mobile-app"], dependencies=[Depends(_disable_caching)])
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


class LogoutRequest(BaseModel):
    refresh_token: str


class ChallengePollRequest(BaseModel):
    secret: str


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
        "counselor_assignment": True,
        "authentication": "telegram-deep-link-approval",
        "offline": {
            "downloadable_study_plans": True,
            "downloadable_assessments": False,
            "assessment_answer_queue": False,
            "daily_report_queue": True,
            "mood_checkin_queue": False,
            "automatic_sync": True,
        },
        "planned_offline_features": [
            "downloadable_assessments", "assessment_answer_queue",
            "mood_checkin_queue",
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


@router.post("/auth/challenge/{challenge_id}")
def poll_auth_challenge(challenge_id: str, payload: ChallengePollRequest):
    secret = payload.secret
    c = db.conn()
    row = c.execute(
        "SELECT * FROM mobile_auth_challenges WHERE challenge_id=?",
        (challenge_id,),
    ).fetchone()
    if not row or not secrets.compare_digest(row["secret_hash"], _hash(secret)):
        c.close()
        raise HTTPException(status_code=404, detail="challenge_not_found")
    # Expiration applies to approved but not yet consumed challenges too.
    # A late poll must never mint tokens after the five-minute window.
    if row["expires_at"] <= _utcnow().isoformat() and not row["consumed_at"]:
        c.execute(
            """UPDATE mobile_auth_challenges SET status='expired'
               WHERE challenge_id=? AND status IN ('pending','approved')
               AND consumed_at IS NULL""",
            (challenge_id,),
        )
        c.commit()
        c.close()
        return {"status": "expired"}
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
           WHERE challenge_id=? AND status='approved' AND consumed_at IS NULL AND expires_at>?""",
        (_utcnow().isoformat(), challenge_id, _utcnow().isoformat()),
    )
    if consumed.rowcount != 1:
        c.commit()
        c.close()
        return {"status": "consumed"}
    tokens = _new_session(c, int(row["telegram_id"]))
    c.commit()
    c.close()
    return {"status": "authenticated", "role": "student", **tokens}


def _authenticated_student(authorization: str | None):
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="missing_access_token")
    c = db.conn()
    try:
        row = c.execute(
            """SELECT telegram_id FROM mobile_sessions
               WHERE access_token_hash=? AND revoked_at IS NULL
               AND access_expires_at>?""",
            (_hash(token), _utcnow().isoformat()),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="invalid_or_expired_access_token")
        student = c.execute(
            """SELECT id,first_name,last_name,grade,track,city
               FROM students WHERE telegram_id=? AND registered=1""",
            (row["telegram_id"],),
        ).fetchone()
        if not student:
            raise HTTPException(status_code=401, detail="account_unavailable")
        return dict(student)
    finally:
        c.close()



class StudyActivityPayload(BaseModel):
    event_id: str = Field(min_length=16, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    subject: str = Field(min_length=1, max_length=80)
    activity_type: str
    duration_minutes: int = Field(ge=1, le=720)
    test_count: int = Field(ge=0, le=1000)
    created_at: datetime


class StudySyncRequest(BaseModel):
    activities: list[StudyActivityPayload] = Field(min_length=1, max_length=50)


@router.post("/student/study-activities/sync")
def sync_study_activities(
    payload: StudySyncRequest,
    authorization: str | None = Header(default=None),
):
    """Idempotent, authenticated append-only sync. Never modify legacy reports."""
    student = _authenticated_student(authorization)
    student_id = int(student["id"])
    allowed = {"study", "practice", "review", "video"}
    for item in payload.activities:
        if item.activity_type not in allowed or not item.subject.strip():
            raise HTTPException(status_code=422, detail="invalid_activity")
        if item.created_at.tzinfo is None:
            raise HTTPException(status_code=422, detail="timezone_required")
    c = db.conn()
    try:
        accepted = []
        for item in payload.activities:
            c.execute(
                """INSERT OR IGNORE INTO mobile_study_activities
                   (student_id,event_id,subject,activity_type,duration_minutes,
                    test_count,client_created_at)
                   VALUES(?,?,?,?,?,?,?)""",
                (student_id, item.event_id, item.subject.strip(), item.activity_type,
                 item.duration_minutes, item.test_count,
                 item.created_at.astimezone(timezone.utc).isoformat()),
            )
            existing = c.execute(
                """SELECT subject,activity_type,duration_minutes,test_count,client_created_at
                   FROM mobile_study_activities WHERE student_id=? AND event_id=?""",
                (student_id, item.event_id),
            ).fetchone()
            # A repeated event ID with different content is a conflict, not a success.
            if not existing or (
                existing["subject"] != item.subject.strip()
                or existing["activity_type"] != item.activity_type
                or existing["duration_minutes"] != item.duration_minutes
                or existing["test_count"] != item.test_count
                or existing["client_created_at"] != item.created_at.astimezone(timezone.utc).isoformat()
            ):
                c.rollback()
                raise HTTPException(status_code=409, detail="event_id_conflict")
            accepted.append(item.event_id)
        c.commit()
        return {"accepted_event_ids": accepted}
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


@router.get("/student/counselor")
def mobile_counselor(authorization: str | None = Header(default=None)):
    student = _authenticated_student(authorization)
    return db.mobile_counselor_plan(student["id"])


@router.get("/student/study-plan")
def mobile_study_plan(authorization: str | None = Header(default=None)):
    student = _authenticated_student(authorization)
    c = db.conn()
    try:
        row = c.execute(
            """SELECT id,title,created_at,content_json FROM plans
               WHERE student_id=? AND status='active' ORDER BY id DESC LIMIT 1""",
            (student["id"],),
        ).fetchone()
    finally:
        c.close()
    if row is None:
        return {"plan": None}
    content = json.loads(row["content_json"] or "{}")
    return {"plan": {
        "id": row["id"],
        "title": row["title"],
        "created_at": row["created_at"],
        "schedule": content.get("schedule", []),
    }}


@router.get("/student/profile")
def mobile_student_profile(authorization: str | None = Header(default=None)):
    """Return only the authenticated student's minimal profile; no contact details."""
    student = _authenticated_student(authorization)
    return {
        "student_id": student["id"],
        "first_name": student["first_name"],
        "last_name": student["last_name"],
        "grade": student["grade"],
        "track": student["track"],
        "city": student["city"],
    }


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
    # Rotate the refresh token atomically. If another request already used it,
    # do not create a second session from the same token.
    revoked = c.execute(
        """UPDATE mobile_sessions SET revoked_at=?
           WHERE id=? AND refresh_token_hash=? AND revoked_at IS NULL""",
        (_utcnow().isoformat(), row["id"], token_hash),
    )
    if revoked.rowcount != 1:
        c.close()
        raise HTTPException(status_code=401, detail="invalid_refresh_token")
    tokens = _new_session(c, int(row["telegram_id"]))
    c.commit()
    c.close()
    return {"role": "student", **tokens}


@router.post("/auth/logout")
def logout_session(payload: LogoutRequest, authorization: str | None = Header(default=None)):
    """Revoke the current session, requiring both its access and refresh credentials."""
    scheme, _, access_token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not access_token:
        raise HTTPException(status_code=401, detail="missing_access_token")
    c = db.conn()
    try:
        session = c.execute(
            """SELECT id FROM mobile_sessions
               WHERE access_token_hash=? AND refresh_token_hash=?
               AND revoked_at IS NULL""",
            (_hash(access_token), _hash(payload.refresh_token)),
        ).fetchone()
        if not session:
            raise HTTPException(status_code=401, detail="invalid_session")
        c.execute(
            "UPDATE mobile_sessions SET revoked_at=? WHERE id=? AND revoked_at IS NULL",
            (_utcnow().isoformat(), session["id"]),
        )
        c.commit()
        return {"logged_out": True}
    finally:
        c.close()


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
           WHERE challenge_id=? AND status='pending' AND expires_at>?""",
        (int(telegram_id), _utcnow().isoformat(), challenge_id, _utcnow().isoformat()),
    )
    c.commit()
    ok = cur.rowcount == 1
    c.close()
    return ok

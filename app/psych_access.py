import json
from datetime import datetime

from . import db

MAX_ATTEMPTS_PER_ACCESS = 1


def _now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def active_access_id(student_id):
    row = db.has_active_access(student_id)
    return int(row["id"]) if row else None


def prepare(student_id, access_id, screening_version, max_attempts=MAX_ATTEMPTS_PER_ACCESS):
    """Return the entitlement/session state for one active service-access period.

    A student gets one completed psychological screening per active service-access
    record. An unfinished screening is resumable and does not consume the attempt.
    """
    if not access_id:
        return {"allowed": False, "reason": "no_access"}

    c = db.conn()
    row = c.execute(
        """SELECT * FROM psych_entitlements
           WHERE student_id=? AND access_id=?
           LIMIT 1""",
        (int(student_id), int(access_id)),
    ).fetchone()

    if not row:
        c.execute(
            """INSERT INTO psych_entitlements
               (student_id,access_id,screening_version,max_attempts,used_attempts,status)
               VALUES(?,?,?,?,0,'available')""",
            (int(student_id), int(access_id), screening_version, int(max_attempts)),
        )
        c.commit()
        row = c.execute(
            "SELECT * FROM psych_entitlements WHERE student_id=? AND access_id=? LIMIT 1",
            (int(student_id), int(access_id)),
        ).fetchone()

    session = c.execute(
        """SELECT * FROM psych_sessions
           WHERE student_id=? AND status='active'
           ORDER BY id DESC LIMIT 1""",
        (int(student_id),),
    ).fetchone()
    c.close()

    used = int(row["used_attempts"] or 0)
    max_attempts = int(row["max_attempts"] or max_attempts)
    allowed = used < max_attempts or bool(session)

    return {
        "allowed": allowed,
        "reason": "resume" if session else ("available" if used < max_attempts else "limit_reached"),
        "entitlement": dict(row) if row else None,
        "session": dict(session) if session else None,
    }


def create_session(student_id, access_id, screening_version, state_data):
    payload = {k: v for k, v in state_data.items() if k != "cfg"}
    c = db.conn()
    c.execute(
        """UPDATE psych_sessions SET status='abandoned',updated_at=CURRENT_TIMESTAMP
           WHERE student_id=? AND status='active'""",
        (int(student_id),),
    )
    cur = c.execute(
        """INSERT INTO psych_sessions
           (student_id,access_id,screening_version,status,state_json,consent_at)
           VALUES(?,?,?,'active',?,NULL)""",
        (int(student_id), int(access_id), screening_version,
         json.dumps(payload, ensure_ascii=False)),
    )
    c.commit()
    sid = cur.lastrowid
    c.close()
    return sid


def load_session(session_id):
    c = db.conn()
    row = c.execute("SELECT * FROM psych_sessions WHERE id=?", (int(session_id),)).fetchone()
    c.close()
    if not row:
        return None
    try:
        state = json.loads(row["state_json"] or "{}")
    except Exception:
        state = {}
    return {"row": dict(row), "state": state}


def load_active_session(student_id):
    c = db.conn()
    row = c.execute(
        """SELECT * FROM psych_sessions
           WHERE student_id=? AND status='active'
           ORDER BY id DESC LIMIT 1""",
        (int(student_id),),
    ).fetchone()
    c.close()
    if not row:
        return None
    try:
        state = json.loads(row["state_json"] or "{}")
    except Exception:
        state = {}
    return {"row": dict(row), "state": state}


def save_session(student_id, state_data, consent=False):
    payload = {k: v for k, v in state_data.items() if k != "cfg"}
    session = load_active_session(student_id)
    if not session:
        return None
    c = db.conn()
    if consent:
        c.execute(
            """UPDATE psych_sessions
               SET state_json=?,consent_at=COALESCE(consent_at,CURRENT_TIMESTAMP),
                   updated_at=CURRENT_TIMESTAMP
               WHERE id=? AND status='active'""",
            (json.dumps(payload, ensure_ascii=False), int(session["row"]["id"])),
        )
    else:
        c.execute(
            """UPDATE psych_sessions
               SET state_json=?,updated_at=CURRENT_TIMESTAMP
               WHERE id=? AND status='active'""",
            (json.dumps(payload, ensure_ascii=False), int(session["row"]["id"])),
        )
    c.commit()
    c.close()
    return session["row"]["id"]


def complete(student_id):
    session = load_active_session(student_id)
    if not session:
        return False

    sid = int(session["row"]["id"])
    access_id = int(session["row"]["access_id"])
    c = db.conn()
    c.execute(
        """UPDATE psych_sessions
           SET status='completed',completed_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP
           WHERE id=? AND status='active'""",
        (sid,),
    )
    c.execute(
        """UPDATE psych_entitlements
           SET used_attempts=used_attempts+1,status=CASE
               WHEN used_attempts+1 >= max_attempts THEN 'used'
               ELSE 'available' END,
               last_completed_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP
           WHERE student_id=? AND access_id=?""",
        (int(student_id), access_id),
    )
    c.execute(
        """INSERT INTO access_events(student_id,action,plan_code,actor,note)
           SELECT ?, 'psych_assessment_completed', a.plan_code, 'system',
                  'screening_version=' || ?
           FROM student_access a WHERE a.id=?""",
        (int(student_id), str(session["row"]["screening_version"] or ""), access_id),
    )
    c.commit()
    c.close()
    return True


def set_consent(student_id):
    session = load_active_session(student_id)
    if not session:
        return False
    c = db.conn()
    c.execute(
        "UPDATE psych_sessions SET consent_at=COALESCE(consent_at,CURRENT_TIMESTAMP),updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='active'",
        (int(session["row"]["id"]),),
    )
    c.commit()
    c.close()
    return True


def reset_for_new_access(student_id, access_id):
    """Admin/renewal helper: a new active access record naturally gets a fresh attempt."""
    return prepare(student_id, access_id, "", MAX_ATTEMPTS_PER_ACCESS)

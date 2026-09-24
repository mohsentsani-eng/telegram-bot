import os, sqlite3, json, re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_raw_db = os.getenv("DATABASE_PATH", "data/taranom.db")
DB = Path(_raw_db) if Path(_raw_db).is_absolute() else PROJECT_ROOT / _raw_db
DB.parent.mkdir(parents=True, exist_ok=True)

def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def init_db():
    c=conn()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        grade TEXT NOT NULL,
        track TEXT,
        city TEXT,
        phone TEXT,
        parent_name TEXT,
        parent_phone TEXT,
        referral_source TEXT,
        registered INTEGER DEFAULT 1,
        points INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grade TEXT NOT NULL,
        track TEXT,
        subject TEXT NOT NULL,
        book TEXT,
        chapter TEXT,
        topic TEXT,
        subtopic TEXT,
        difficulty TEXT DEFAULT 'متوسط',
        question TEXT NOT NULL,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT NOT NULL,
        option_d TEXT NOT NULL,
        correct_option TEXT NOT NULL,
        explanation TEXT,
        source TEXT,
        source_type TEXT DEFAULT 'original',
        source_year TEXT,
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        assessment_type TEXT NOT NULL,
        subject TEXT,
        chapter TEXT,
        topic TEXT,
        difficulty TEXT,
        score REAL,
        started_at TEXT DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT,
        FOREIGN KEY(student_id) REFERENCES students(id)
    );

    CREATE TABLE IF NOT EXISTS attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assessment_id INTEGER,
        student_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        answer TEXT,
        is_correct INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(question_id) REFERENCES questions(id)
    );

    CREATE TABLE IF NOT EXISTS mastery (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        subject TEXT NOT NULL,
        chapter TEXT,
        topic TEXT NOT NULL,
        mastery_score REAL DEFAULT 0.5,
        attempts INTEGER DEFAULT 0,
        correct_count INTEGER DEFAULT 0,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(student_id,subject,chapter,topic),
        FOREIGN KEY(student_id) REFERENCES students(id)
    );

    CREATE TABLE IF NOT EXISTS psych_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        domain TEXT NOT NULL,
        score REAL,
        level TEXT,
        raw_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id)
    );

    CREATE TABLE IF NOT EXISTS learning_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        skill TEXT NOT NULL,
        score REAL,
        level TEXT,
        raw_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id)
    );

    CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        title TEXT,
        content_json TEXT,
        status TEXT DEFAULT 'active',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id)
    );

    CREATE TABLE IF NOT EXISTS counseling_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        request_type TEXT,
        status TEXT DEFAULT 'new',
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id)
    );

    CREATE TABLE IF NOT EXISTS guidance_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        guidance_type TEXT NOT NULL,
        payload_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id)
    );

    CREATE TABLE IF NOT EXISTS channel_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        channel_id TEXT,
        status TEXT,
        checked_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS referral_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER,
        student_id INTEGER,
        source TEXT,
        event TEXT NOT NULL,
        metadata_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id)
    );

    CREATE TABLE IF NOT EXISTS ai_analyses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        analysis_type TEXT NOT NULL,
        title TEXT,
        content TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id)
    );
    """)
    c.commit()
    # Question seeding is OPT-IN. The admin CSV is the source of truth by default.
    # Set AUTO_SEED_QUESTIONS=1 only when you intentionally want bundled starter data.
    if os.getenv("AUTO_SEED_QUESTIONS", "0").strip().lower() in {"1", "true", "yes"}:
        try:
            import csv as _csv
            base_dir = Path(__file__).resolve().parent.parent / "data"
            seed_files = [base_dir / "seed_questions.csv"]
            for seed_path in seed_files:
                if not seed_path.exists():
                    continue
                with seed_path.open(encoding="utf-8-sig", newline="") as f:
                    for row in _csv.DictReader(f):
                        insert_question_if_new(row)
        except Exception as exc:
            print(f"[WARN] optional question seed failed: {exc}")
    c.close()

def get_student_by_tg(tg):
    c=conn(); r=c.execute("SELECT * FROM students WHERE telegram_id=?", (tg,)).fetchone(); c.close(); return r

def get_student(student_id):
    c=conn(); r=c.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone(); c.close(); return r

def track_referral_event(telegram_id, event, source="", student_id=None, metadata=None):
    """Record marketing-funnel events without changing student data."""
    c=conn()
    c.execute(
        "INSERT INTO referral_events(telegram_id,student_id,source,event,metadata_json) VALUES(?,?,?,?,?)",
        (telegram_id, student_id, source or "", event, json.dumps(metadata or {}, ensure_ascii=False))
    )
    c.commit()
    c.close()


def first_referral_source(telegram_id):
    c=conn()
    row=c.execute(
        "SELECT source FROM referral_events WHERE telegram_id=? AND source<>'' "
        "ORDER BY id ASC LIMIT 1", (telegram_id,)
    ).fetchone()
    c.close()
    return (row["source"] if row else "") or ""


def marketing_stats():
    c=conn()
    out={}
    out["starts"]=c.execute("SELECT COUNT(*) n FROM referral_events WHERE event='start'").fetchone()["n"]
    out["registrations"]=c.execute("SELECT COUNT(*) n FROM referral_events WHERE event='registration_complete'").fetchone()["n"]
    out["quick_completed"]=c.execute("SELECT COUNT(*) n FROM referral_events WHERE event='quick_assessment_complete'").fetchone()["n"]
    out["channel_joins"]=c.execute("SELECT COUNT(*) n FROM referral_events WHERE event='channel_join_verified'").fetchone()["n"]
    out["counseling_requests"]=c.execute("SELECT COUNT(*) n FROM referral_events WHERE event='counseling_request'").fetchone()["n"]
    out["instagram_clicks"]=c.execute("SELECT COUNT(*) n FROM referral_events WHERE event='instagram_click'").fetchone()["n"]
    out["instagram_views"]=c.execute("SELECT COUNT(*) n FROM referral_events WHERE event='instagram_view'").fetchone()["n"]
    out["instagram_returned"]=c.execute("SELECT COUNT(*) n FROM referral_events WHERE event='instagram_returned'").fetchone()["n"]
    rows=c.execute(
        "SELECT COALESCE(NULLIF(source,''),'بدون منبع') source, "
        "COUNT(*) starts, "
        "SUM(CASE WHEN event='registration_complete' THEN 1 ELSE 0 END) registrations, "
        "SUM(CASE WHEN event='quick_assessment_complete' THEN 1 ELSE 0 END) quick_completed, "
        "SUM(CASE WHEN event='channel_join_verified' THEN 1 ELSE 0 END) channel_joins, "
        "SUM(CASE WHEN event='counseling_request' THEN 1 ELSE 0 END) counseling_requests, SUM(CASE WHEN event='instagram_click' THEN 1 ELSE 0 END) instagram_clicks, SUM(CASE WHEN event='instagram_view' THEN 1 ELSE 0 END) instagram_views, SUM(CASE WHEN event='instagram_returned' THEN 1 ELSE 0 END) instagram_returned "
        "FROM referral_events GROUP BY COALESCE(NULLIF(source,''),'بدون منبع') "
        "ORDER BY starts DESC"
    ).fetchall()
    out["sources"]=[dict(x) for x in rows]
    c.close()
    return out


def recent_referral_events(limit=100):
    c=conn()
    rows=c.execute(
        "SELECT e.*, s.first_name, s.last_name FROM referral_events e "
        "LEFT JOIN students s ON s.id=e.student_id ORDER BY e.id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    c.close()
    return rows


def create_student(data):
    c=conn()
    c.execute("""INSERT INTO students
    (telegram_id,username,first_name,last_name,grade,track,city,phone,parent_name,parent_phone,referral_source)
    VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
    tuple(data.get(k) for k in ["telegram_id","username","first_name","last_name","grade","track","city","phone","parent_name","parent_phone","referral_source"]))
    c.commit()
    r=c.execute("SELECT * FROM students WHERE telegram_id=?", (data["telegram_id"],)).fetchone()
    c.close(); return r

def update_student(tg, **kwargs):
    allowed={"first_name","last_name","grade","track","city","phone","parent_name","parent_phone","points"}
    pairs=[(k,v) for k,v in kwargs.items() if k in allowed]
    if not pairs: return
    c=conn()
    sets=", ".join(f"{k}=?" for k,_ in pairs)
    c.execute(f"UPDATE students SET {sets}, updated_at=CURRENT_TIMESTAMP WHERE telegram_id=?",
              [v for _,v in pairs]+[tg])
    c.commit(); c.close()

def list_students(limit=500):
    c=conn(); rows=c.execute("SELECT * FROM students ORDER BY id DESC LIMIT ?",(limit,)).fetchall(); c.close(); return rows

def student_snapshot(student_id):
    c=conn()
    out={
        "assessments":[dict(x) for x in c.execute("SELECT * FROM assessments WHERE student_id=? ORDER BY id DESC LIMIT 50",(student_id,)).fetchall()],
        "mastery":[dict(x) for x in c.execute("SELECT * FROM mastery WHERE student_id=? ORDER BY mastery_score ASC",(student_id,)).fetchall()],
        "psych":[dict(x) for x in c.execute("SELECT * FROM psych_results WHERE student_id=? ORDER BY id DESC LIMIT 100",(student_id,)).fetchall()],
        "learning":[dict(x) for x in c.execute("SELECT * FROM learning_results WHERE student_id=? ORDER BY id DESC LIMIT 100",(student_id,)).fetchall()],
        "guidance":[dict(x) for x in c.execute("SELECT * FROM guidance_records WHERE student_id=? ORDER BY id DESC LIMIT 20",(student_id,)).fetchall()],
        "requests":[dict(x) for x in c.execute("SELECT * FROM counseling_requests WHERE student_id=? ORDER BY id DESC LIMIT 20",(student_id,)).fetchall()],
        "ai_history":[dict(x) for x in c.execute("SELECT analysis_type,title,content,created_at FROM ai_analyses WHERE student_id=? ORDER BY id DESC LIMIT 8",(student_id,)).fetchall()]
    }
    c.close(); return out

def _clean_question_payload(q):
    out={k:(str(q.get(k, "") or "").strip()) for k in [
        "grade","track","subject","book","chapter","topic","subtopic","difficulty",
        "question","option_a","option_b","option_c","option_d","correct_option",
        "explanation","source","source_type","source_year"]}
    out["correct_option"]=out["correct_option"].upper()
    amap={"1":"A","2":"B","3":"C","4":"D","۱":"A","۲":"B","۳":"C","۴":"D"}
    out["correct_option"]=amap.get(out["correct_option"],out["correct_option"])
    if not out["difficulty"]: out["difficulty"]="متوسط"
    if not out["source_type"]: out["source_type"]="original"
    return out

def _validate_question(q):
    required=["grade","subject","question","option_a","option_b","option_c","option_d","correct_option"]
    missing=[k for k in required if not q.get(k)]
    if q.get("correct_option") not in {"A","B","C","D"}: missing.append("correct_option")
    if q.get("difficulty") not in {"آسان","متوسط","سخت","تشخیصی"}: missing.append("difficulty")
    return missing

def insert_question_if_new(q):
    q=_clean_question_payload(q)
    problems=_validate_question(q)
    if problems: raise ValueError("Invalid question: " + ", ".join(problems))
    c=conn(); rows=c.execute("SELECT * FROM questions WHERE active=1").fetchall()
    key=_question_key(q)
    if any(_question_key(dict(r))==key for r in rows):
        c.close(); return False
    c.execute("""INSERT INTO questions
    (grade,track,subject,book,chapter,topic,subtopic,difficulty,question,option_a,option_b,option_c,option_d,correct_option,explanation,source,source_type,source_year)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", tuple(q[k] for k in [
        "grade","track","subject","book","chapter","topic","subtopic","difficulty","question",
        "option_a","option_b","option_c","option_d","correct_option","explanation","source","source_type","source_year"]))
    c.commit(); c.close(); return True

def insert_question(q):
    return insert_question_if_new(q)

def question(qid):
    c=conn(); r=c.execute("SELECT * FROM questions WHERE id=?",(qid,)).fetchone(); c.close(); return r

def _norm(v):
    if v is None:
        return ""
    s=str(v).strip()
    s=s.replace("ي","ی").replace("ى","ی").replace("ك","ک")
    s=s.replace("‌", "")
    s=re.sub(r"\s+", "", s)
    aliases={
        "زبانانگلیسی":"انگلیسی", "english":"انگلیسی", "انگلیسیزبان":"انگلیسی",
        "عمومی":"", "همه":""
    }
    return aliases.get(s.casefold(), s.casefold())

def _question_key(q):
    parts=[q.get(k, "") for k in ("grade","track","subject","book","chapter","topic","subtopic","difficulty",
                                   "question","option_a","option_b","option_c","option_d","correct_option")]
    return "|".join(_norm(x) for x in parts)

def _matches(row, filters):
    for k in ["grade","track","subject","book","chapter","topic","difficulty"]:
        v=filters.get(k)
        # Empty track means general/common content; an explicitly selected track is exact.
        if v not in (None, "") and _norm(row[k]) != _norm(v):
            return False
    return True

def list_questions(filters=None):
    filters=filters or {}
    c=conn()
    rows=c.execute("SELECT * FROM questions WHERE active=1 ORDER BY id DESC").fetchall()
    c.close()
    # De-duplicate at read time too, so legacy duplicated imports can never appear in an exam.
    out=[]; seen=set()
    for r in rows:
        key=_question_key(dict(r))
        if key in seen:
            continue
        if _matches(r, filters):
            seen.add(key); out.append(r)
    return out

def distinct_question_field(field, filters=None):
    allowed={"grade","track","subject","book","chapter","topic","difficulty"}
    if field not in allowed: return []
    filters=filters or {}
    rows=list_questions(filters)
    out=[]; seen=set()
    for r in rows:
        value=r[field]
        if value is None or not str(value).strip(): continue
        key=_norm(value)
        if key not in seen:
            seen.add(key); out.append(str(value).strip())
    return sorted(out, key=lambda x:_norm(x))

def count_questions(filters=None):
    return len(list_questions(filters or {}))

def remove_duplicate_questions():
    """Remove legacy exact duplicates while keeping the oldest record and its ID."""
    c=conn(); rows=c.execute("SELECT * FROM questions ORDER BY id ASC").fetchall()
    seen=set(); deleted=0
    for r in rows:
        key=_question_key(dict(r))
        if key in seen:
            c.execute("DELETE FROM questions WHERE id=?", (r["id"],)); deleted+=1
        else:
            seen.add(key)
    c.commit(); c.close(); return deleted

def assessment_snapshot(assessment_id):
    c=conn()
    assessment=c.execute("SELECT * FROM assessments WHERE id=?",(assessment_id,)).fetchone()
    attempts=c.execute("""SELECT a.*, q.subject, q.chapter, q.topic, q.difficulty, q.correct_option, q.explanation
        FROM attempts a JOIN questions q ON q.id=a.question_id WHERE a.assessment_id=? ORDER BY a.id""",(assessment_id,)).fetchall()
    c.close()
    return {"assessment": dict(assessment) if assessment else None, "attempts": [dict(x) for x in attempts]}

def start_assessment(student_id, typ, subject=None, chapter=None, topic=None, difficulty=None):
    c=conn(); cur=c.execute("""INSERT INTO assessments(student_id,assessment_type,subject,chapter,topic,difficulty)
        VALUES(?,?,?,?,?,?)""",(student_id,typ,subject,chapter,topic,difficulty)); c.commit(); aid=cur.lastrowid; c.close(); return aid

def save_attempt(aid, student_id, qid, answer, correct):
    c=conn()
    c.execute("INSERT INTO attempts(assessment_id,student_id,question_id,answer,is_correct) VALUES(?,?,?,?,?)",
              (aid,student_id,qid,answer,int(correct)))
    c.commit(); c.close()

def finish_assessment(aid, score):
    c=conn(); c.execute("UPDATE assessments SET score=?,completed_at=CURRENT_TIMESTAMP WHERE id=?",(score,aid)); c.commit(); c.close()

def update_mastery(student_id, subject, chapter, topic, correct):
    c=conn()
    row=c.execute("""SELECT * FROM mastery WHERE student_id=? AND subject=? AND COALESCE(chapter,'')=? AND topic=?""",
                  (student_id,subject,chapter or "",topic or "")).fetchone()
    old=float(row["mastery_score"]) if row else 0.5
    alpha=0.22
    new=old+alpha*((1.0 if correct else 0.0)-old)
    if row:
        c.execute("""UPDATE mastery SET mastery_score=?,attempts=attempts+1,correct_count=correct_count+?,updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                  (new,int(correct),row["id"]))
    else:
        c.execute("""INSERT INTO mastery(student_id,subject,chapter,topic,mastery_score,attempts,correct_count)
                     VALUES(?,?,?,?,?,?,?)""",(student_id,subject,chapter or "",topic or "",new,1,int(correct)))
    c.commit(); c.close(); return new

def save_psych(student_id, domain, score, level, raw):
    c=conn(); c.execute("INSERT INTO psych_results(student_id,domain,score,level,raw_json) VALUES(?,?,?,?,?)",
                        (student_id,domain,score,level,json.dumps(raw,ensure_ascii=False))); c.commit(); c.close()

def save_learning(student_id, skill, score, level, raw):
    c=conn(); c.execute("INSERT INTO learning_results(student_id,skill,score,level,raw_json) VALUES(?,?,?,?,?)",
                        (student_id,skill,score,level,json.dumps(raw,ensure_ascii=False))); c.commit(); c.close()

def save_guidance(student_id, kind, payload):
    c=conn(); c.execute("INSERT INTO guidance_records(student_id,guidance_type,payload_json) VALUES(?,?,?)",
                        (student_id,kind,json.dumps(payload,ensure_ascii=False))); c.commit(); c.close()

def save_plan(student_id, title, payload):
    c=conn(); c.execute("INSERT INTO plans(student_id,title,content_json) VALUES(?,?,?)",
                        (student_id,title,json.dumps(payload,ensure_ascii=False))); c.commit(); c.close()

def request_counseling(student_id, typ, note=""):
    c=conn(); c.execute("INSERT INTO counseling_requests(student_id,request_type,note) VALUES(?,?,?)",
                        (student_id,typ,note)); c.commit(); c.close()

def stats():
    c=conn()
    out={}
    for name,sql in {
        "students":"SELECT COUNT(*) n FROM students",
        "questions":"SELECT COUNT(*) n FROM questions WHERE active=1",
        "assessments":"SELECT COUNT(*) n FROM assessments",
        "requests":"SELECT COUNT(*) n FROM counseling_requests WHERE status='new'"
    }.items():
        out[name]=c.execute(sql).fetchone()["n"]
    c.close(); return out


def save_ai_analysis(student_id, analysis_type, title, content):
    c=conn()
    c.execute("INSERT INTO ai_analyses(student_id,analysis_type,title,content) VALUES(?,?,?,?)",
              (student_id, analysis_type, title, content))
    c.commit()
    rid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.close()
    return rid

def list_ai_analyses(student_id, limit=10):
    c=conn()
    rows=c.execute("SELECT * FROM ai_analyses WHERE student_id=? ORDER BY id DESC LIMIT ?",
                   (student_id, limit)).fetchall()
    c.close(); return rows

def latest_ai_analysis(student_id, analysis_type=None):
    c=conn()
    if analysis_type:
        r=c.execute("SELECT * FROM ai_analyses WHERE student_id=? AND analysis_type=? ORDER BY id DESC LIMIT 1",
                    (student_id,analysis_type)).fetchone()
    else:
        r=c.execute("SELECT * FROM ai_analyses WHERE student_id=? ORDER BY id DESC LIMIT 1",(student_id,)).fetchone()
    c.close(); return r

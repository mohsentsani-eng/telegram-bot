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
    # Performance indexes for academic-assessment lookups.
    # These are additive only and never delete or overwrite student/question data.
    c.executescript("""
    CREATE INDEX IF NOT EXISTS idx_questions_active_grade_track
        ON questions(active, grade, track);
    CREATE INDEX IF NOT EXISTS idx_questions_active_subject
        ON questions(active, subject);
    CREATE INDEX IF NOT EXISTS idx_questions_active_chapter_topic
        ON questions(active, chapter, topic);
    CREATE INDEX IF NOT EXISTS idx_questions_active_difficulty
        ON questions(active, difficulty);
    """)
    c.commit()
    c.close()
    ensure_question_bank_seed()

def ensure_question_bank_seed():
    """Seed bundled question banks additively and efficiently.
    Existing students/questions are never deleted or overwritten.
    """
    try:
        import csv as _csv
        base_dir = Path(__file__).resolve().parent.parent / "data"
        seed_files = [
            base_dir / "core_question_bank.csv",
            base_dir / "question_bank_coverage.csv",
            base_dir / "expanded_questions.csv",
            base_dir / "question_bank_expansion.csv",
            base_dir / "question_bank_completion.csv",
            base_dir / "question_bank_چهارم_min10.csv",
            base_dir / "question_bank_پنجم_min10.csv",
            base_dir / "question_bank_ششم_min10.csv",
            base_dir / "question_bank_هفتم_min10.csv",
            base_dir / "question_bank_هشتم_min10.csv",
            base_dir / "question_bank_نهم_min10.csv",
            base_dir / "question_bank_دهم_min10.csv",
            base_dir / "question_bank_یازدهم_min10.csv",
            base_dir / "question_bank_دوازدهم_min10.csv",
            base_dir / "d10_humanities_questions.csv",
            base_dir / "art_math_physics_bank.csv",
            base_dir / "seed_questions.csv",
            base_dir / "question_bank_rebuild_v1.csv",
            base_dir / "question_bank_rebuild_v2.csv",
            base_dir / "question_bank_rebuild_v2_clean.csv",
            base_dir / "question_bank_rebuild_v3.csv",
            base_dir / "question_bank_v4.csv",
        ]
        c = conn()
        existing = set()
        existing_stems = set()
        for row in c.execute("SELECT * FROM questions WHERE active=1").fetchall():
            item = dict(row)
            existing.add(_question_key(item))
            existing_stems.add(_question_stem_key(item))
        pending = []
        pending_stems = set()
        seed_stats = []
        for seed_path in seed_files:
            if not seed_path.exists():
                continue
            seen_rows = accepted_rows = duplicate_rows = invalid_rows = 0
            with seed_path.open(encoding="utf-8-sig", newline="") as f:
                for row in _csv.DictReader(f):
                    seen_rows += 1
                    try:
                        q = _clean_question_payload(row)
                        problems = _validate_question(q)
                        if problems:
                            invalid_rows += 1
                            continue
                        from .question_quality import quality_issues
                        quality = quality_issues(q)
                        if quality:
                            invalid_rows += 1
                            continue
                        key = _question_key(q)
                        stem_key = _question_stem_key(q)
                        if key in existing or stem_key in existing_stems or stem_key in pending_stems:
                            duplicate_rows += 1
                            continue
                        existing.add(key)
                        existing_stems.add(stem_key)
                        pending_stems.add(stem_key)
                        accepted_rows += 1
                        pending.append(tuple(q[k] for k in [
                            "grade","track","subject","book","chapter","topic","subtopic","difficulty",
                            "question","option_a","option_b","option_c","option_d","correct_option",
                            "explanation","source","source_type","source_year"
                        ]))
                    except Exception as exc:
                        invalid_rows += 1
                        print(f"[WARN] question row skipped ({seed_path.name}): {exc}", flush=True)
            seed_stats.append((seed_path.name, seen_rows, accepted_rows, duplicate_rows, invalid_rows))
        if pending:
            c.executemany(
                """INSERT INTO questions
                (grade,track,subject,book,chapter,topic,subtopic,difficulty,question,
                 option_a,option_b,option_c,option_d,correct_option,explanation,source,source_type,source_year)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                pending
            )
            c.commit()
        else:
            c.rollback()
        c.close()
        if pending:
            print(f"[QUESTION_BANK] inserted {len(pending)} bundled questions", flush=True)
        for name, seen, accepted, dup, invalid in seed_stats:
            if seen:
                print(f"[QUESTION_BANK] seed={name} rows={seen} accepted={accepted} duplicate={dup} invalid={invalid}", flush=True)
        quarantine_obvious_bad_questions()
        return len(pending)
    except Exception as exc:
        print(f"[WARN] question-bank seed failed: {exc}", flush=True)
        return 0

def quarantine_obvious_bad_questions():
    """Hide legacy questions with clear structural/cross-domain defects.

    This is non-destructive: rows remain in the database and are only marked
    inactive, so historical references are preserved.
    """
    try:
        from .question_quality import quality_issues
        c=conn()
        rows=c.execute("SELECT * FROM questions WHERE active=1").fetchall()
        bad=[]
        for row in rows:
            issues=quality_issues(dict(row))
            if issues:
                bad.append((json.dumps(issues, ensure_ascii=False), row["id"]))
        if bad:
            c.executemany(
                "UPDATE questions SET active=0 WHERE id=?",
                [(qid,) for _,qid in bad]
            )
            c.commit()
        else:
            c.rollback()
        c.close()
        if bad:
            print(f"[QUESTION_BANK] quarantined {len(bad)} legacy low-quality questions (non-destructive)", flush=True)
        return len(bad)
    except Exception as exc:
        print(f"[WARN] question quality quarantine skipped: {exc}", flush=True)
        return 0


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
    # Quality gate applies only to newly inserted questions. Existing records
    # are never deleted or rewritten by this check.
    from .question_quality import quality_issues
    quality=quality_issues(q)
    if quality:
        raise ValueError("Question quality gate: " + ", ".join(quality))
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

def _question_stem_key(q):
    """Detect repeated question stems even when answer options differ."""
    parts=[q.get(k, "") for k in ("grade","track","subject","book","chapter","topic","question")]
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

    # Push exact filters into SQLite first. This is important on the persistent
    # Railway database, where legacy imports may contain many duplicate rows.
    # We still run _matches() below, so normalization/legacy aliases keep the
    # same behavior as before.
    clauses=["active=1"]
    params=[]
    for k in ("grade","track","subject","book","chapter","topic","difficulty"):
        v=filters.get(k)
        if v not in (None, ""):
            clauses.append(f"{k}=?")
            params.append(str(v))

    sql="SELECT * FROM questions WHERE " + " AND ".join(clauses) + " ORDER BY id DESC"
    rows=c.execute(sql, tuple(params)).fetchall()
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

def list_questions_for_student(student_id, filters=None):
    """Return active questions not previously attempted by this student.

    This is deliberately non-destructive: attempts remain historical records,
    and only the exam candidate pool is filtered for the current student.
    """
    filters = filters or {}
    c = conn()
    clauses = ["q.active=1", "NOT EXISTS (SELECT 1 FROM attempts a WHERE a.student_id=? AND a.question_id=q.id)"]
    params = [int(student_id)]
    for k in ("grade","track","subject","book","chapter","topic","difficulty"):
        v = filters.get(k)
        if v not in (None, ""):
            clauses.append(f"q.{k}=?")
            params.append(str(v))
    rows = c.execute("SELECT q.* FROM questions q WHERE " + " AND ".join(clauses) + " ORDER BY q.id DESC", tuple(params)).fetchall()
    c.close()
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

def question_coverage_audit(min_per_subject=10):
    """Compare active bank coverage against the curriculum catalog."""
    catalog_path = PROJECT_ROOT / "data" / "question_bank_catalog.json"
    with catalog_path.open(encoding="utf-8") as fh:
        catalog = json.load(fh)
    c = conn()
    rows = c.execute(
        "SELECT grade,COALESCE(track,'') track,subject,COUNT(*) n "
        "FROM questions WHERE active=1 GROUP BY grade,COALESCE(track,''),subject"
    ).fetchall()
    c.close()
    counts = {(_norm(r["grade"]), _norm(r["track"]), _norm(r["subject"])): int(r["n"]) for r in rows}
    gaps = []
    covered = 0
    expected = 0
    for grade, tracks in catalog.items():
        if isinstance(tracks, list):
            track_items = [("", tracks)]
        else:
            track_items = list(tracks.items())
        for track, subjects in track_items:
            for subject in subjects:
                expected += 1
                n = counts.get((_norm(grade), _norm(track), _norm(subject)), 0)
                if n >= min_per_subject:
                    covered += 1
                else:
                    gaps.append({"grade": grade, "track": track, "subject": subject, "count": n,
                                 "needed": max(0, min_per_subject - n)})
    return {"expected": expected, "covered": covered, "gaps": gaps, "coverage_pct": round(covered * 100 / expected, 1) if expected else 0}

def question_topic_coverage_audit(min_per_topic=10):
    """Report active topic coverage without modifying any question or student record."""
    c = conn()
    rows = c.execute(
        "SELECT grade,COALESCE(track,'') track,subject,COALESCE(chapter,'') chapter,"
        "COALESCE(topic,'') topic,COUNT(*) n FROM questions WHERE active=1 "
        "AND TRIM(COALESCE(topic,''))<>'' GROUP BY grade,track,subject,chapter,topic "
        "ORDER BY grade,track,subject,chapter,topic"
    ).fetchall()
    c.close()
    gaps=[]
    for r in rows:
        n=int(r["n"])
        if n<min_per_topic:
            gaps.append({"grade":r["grade"],"track":r["track"],"subject":r["subject"],"chapter":r["chapter"],"topic":r["topic"],"count":n,"needed":min_per_topic-n})
    return {"topics":len(rows),"gaps":gaps,"min_per_topic":min_per_topic}

def question_quality_audit():
    """Summarize active questions that fail the current non-destructive quality rules."""
    from .question_quality import quality_issues
    c = conn()
    rows = c.execute("SELECT * FROM questions WHERE active=1").fetchall()
    c.close()
    issue_counts = {}
    bad_ids = []
    for r in rows:
        issues = quality_issues(dict(r))
        if issues:
            bad_ids.append(int(r["id"]))
            for issue in issues:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1
    return {
        "active_total": len(rows),
        "bad_total": len(bad_ids),
        "bad_ids": bad_ids[:100],
        "issue_counts": issue_counts,
        "quality_pct": round((len(rows)-len(bad_ids))*100/len(rows),1) if rows else 100.0,
    }

def question_quality_distribution():
    """Return active-bank balance metrics for correct options and difficulty."""
    c = conn()
    rows = c.execute(
        "SELECT correct_option,COALESCE(difficulty,'') difficulty,COUNT(*) n "
        "FROM questions WHERE active=1 GROUP BY correct_option,difficulty"
    ).fetchall()
    c.close()
    option_counts = {x: 0 for x in "ABCD"}
    difficulty_counts = {}
    for r in rows:
        opt = str(r["correct_option"] or "").upper()
        if opt in option_counts:
            option_counts[opt] += int(r["n"])
        d = str(r["difficulty"] or "نامشخص")
        difficulty_counts[d] = difficulty_counts.get(d, 0) + int(r["n"])
    total = sum(option_counts.values())
    return {
        "total": total,
        "correct_option": option_counts,
        "correct": option_counts,
        "difficulty": difficulty_counts,
        "option_pct": {k: round(v * 100 / total, 1) if total else 0 for k, v in option_counts.items()},
        "correct_pct": {k: round(v * 100 / total, 1) if total else 0 for k, v in option_counts.items()},
    }

def remove_duplicate_questions():
    """Legacy compatibility wrapper: quarantine duplicates without deleting history."""
    return quarantine_duplicate_questions()

def quarantine_duplicate_questions():
    """Deactivate exact duplicate active questions while preserving every row and ID."""
    c=conn()
    rows=c.execute("SELECT * FROM questions WHERE active=1 ORDER BY id ASC").fetchall()
    seen=set()
    quarantined=0
    for r in rows:
        key=_question_key(dict(r))
        if key in seen:
            c.execute("UPDATE questions SET active=0 WHERE id=?", (r["id"],))
            quarantined += 1
        else:
            seen.add(key)
    c.commit()
    c.close()
    return quarantined

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


def upsert_goal(student_id, goal, target_value=""):
    c=conn()
    c.execute("UPDATE student_goals SET status='closed', updated_at=CURRENT_TIMESTAMP WHERE student_id=? AND status='active'", (student_id,))
    cur=c.execute("INSERT INTO student_goals(student_id,goal,target_value) VALUES(?,?,?)",(student_id,goal,target_value or ""))
    c.commit(); rid=cur.lastrowid; c.close(); return rid

def active_goals(student_id, limit=10):
    c=conn(); rows=c.execute("SELECT * FROM student_goals WHERE student_id=? AND status='active' ORDER BY id DESC LIMIT ?",(student_id,limit)).fetchall(); c.close(); return rows

def add_counselor(name, telegram_id=None):
    c=conn(); cur=c.execute("INSERT INTO counselors(name,telegram_id) VALUES(?,?)",(name,telegram_id)); c.commit(); rid=cur.lastrowid; c.close(); return rid

def list_counselors(active_only=True):
    c=conn()
    sql="SELECT * FROM counselors"
    if active_only: sql+=" WHERE active=1"
    rows=c.execute(sql+" ORDER BY name").fetchall(); c.close(); return rows

def assign_counselor(student_id, counselor_id):
    c=conn()
    c.execute("UPDATE student_counselor_assignments SET active=0 WHERE student_id=? AND active=1",(student_id,))
    c.execute("INSERT INTO student_counselor_assignments(student_id,counselor_id,active) VALUES(?,?,1)",(student_id,counselor_id))
    c.commit(); c.close()

def active_counselor(student_id):
    c=conn()
    r=c.execute("""SELECT c.* FROM counselors c JOIN student_counselor_assignments a ON a.counselor_id=c.id
                   WHERE a.student_id=? AND a.active=1 ORDER BY a.id DESC LIMIT 1""",(student_id,)).fetchone()
    c.close(); return r

def add_counselor_note(student_id, counselor_id, note):
    c=conn(); c.execute("INSERT INTO counselor_notes(student_id,counselor_id,note) VALUES(?,?,?)",(student_id,counselor_id,note)); c.commit(); c.close()

def list_counselor_notes(student_id, limit=30):
    c=conn(); rows=c.execute("""SELECT n.*,c.name counselor_name FROM counselor_notes n
        LEFT JOIN counselors c ON c.id=n.counselor_id WHERE n.student_id=? ORDER BY n.id DESC LIMIT ?""",(student_id,limit)).fetchall(); c.close(); return rows

def create_followup(student_id, followup_type="general", priority="normal", due_at=None, note=""):
    c=conn()
    counselor=c.execute("""SELECT counselor_id FROM student_counselor_assignments
                           WHERE student_id=? AND active=1 ORDER BY id DESC LIMIT 1""",(student_id,)).fetchone()
    counselor_id=counselor["counselor_id"] if counselor else None
    cur=c.execute("""INSERT INTO followups(student_id,counselor_id,followup_type,priority,status,due_at,note)
                     VALUES(?,?,?,?,?,?,?)""",
                  (student_id,counselor_id,followup_type,priority,"open",due_at,note))
    c.commit(); rid=cur.lastrowid; c.close(); return rid

def list_open_followups(student_id=None, limit=100):
    c=conn()
    if student_id is None:
        rows=c.execute("SELECT f.*,s.first_name,s.last_name FROM followups f JOIN students s ON s.id=f.student_id WHERE f.status='open' ORDER BY f.id DESC LIMIT ?",(limit,)).fetchall()
    else:
        rows=c.execute("SELECT * FROM followups WHERE student_id=? AND status='open' ORDER BY id DESC LIMIT ?",(student_id,limit)).fetchall()
    c.close(); return rows

def complete_followup(followup_id):
    c=conn(); c.execute("UPDATE followups SET status='completed',completed_at=CURRENT_TIMESTAMP WHERE id=?",(followup_id,)); c.commit(); c.close()

def weekly_progress(student_id, days=7):
    c=conn()
    rows=c.execute("""SELECT * FROM student_progress WHERE student_id=?
                      AND report_date >= date('now', ?)
                      ORDER BY report_date""",(f"-{max(1,int(days))-1} days",)).fetchall()
    c.close()
    return rows

def weekly_summary(student_id, days=7):
    rows=weekly_progress(student_id,days)
    if not rows: return {"days":0,"study_hours":0,"execution":0,"practice":0,"trend":"داده کافی نیست"}
    study=sum(float(r["study_hours"] or 0) for r in rows)
    execution=sum(float(r["plan_execution"] or 0) for r in rows)/len(rows)
    practice=sum(int(r["practice_count"] or 0) for r in rows)
    trends=[str(r["trend"] or "").strip() for r in rows if r["trend"]]
    return {"days":len(rows),"study_hours":study,"execution":execution,"practice":practice,
            "trend":trends[-1] if trends else "نیازمند پایش"}


def get_daily_report(student_id, report_date):
    c=conn()
    row=c.execute("SELECT * FROM daily_reports WHERE student_id=? AND report_date=?",(student_id,report_date)).fetchone()
    c.close()
    return row

def save_daily_report(student_id, report_date, study_hours, plan_execution, subjects, practice_count,
                      main_problem, satisfaction, tomorrow_goal, answers=None, status="normal",
                      analysis_status="completed", analysis_json=None):
    """
    Insert/update one daily report for a student and mirror the objective progress
    into student_progress. This is an additive report operation; student profile
    and historical reports are never deleted.
    """
    c=conn()
    existing=c.execute(
        "SELECT id FROM daily_reports WHERE student_id=? AND report_date=?",
        (student_id,report_date)
    ).fetchone()
    payload=json.dumps(subjects or [],ensure_ascii=False) if not isinstance(subjects,str) else subjects
    analysis_payload=json.dumps(analysis_json or {},ensure_ascii=False) if not isinstance(analysis_json,str) else analysis_json
    if existing:
        report_id=existing["id"]
        c.execute("""UPDATE daily_reports SET study_hours=?,plan_execution=?,subjects_json=?,
                     practice_count=?,main_problem=?,satisfaction=?,tomorrow_goal=?,
                     status=?,analysis_status=?,analysis_json=?,updated_at=CURRENT_TIMESTAMP
                     WHERE id=?""",
                  (float(study_hours or 0),float(plan_execution or 0),payload,int(practice_count or 0),
                   main_problem or "",satisfaction or "",tomorrow_goal or "",status,
                   analysis_status,analysis_payload,report_id))
    else:
        cur=c.execute("""INSERT INTO daily_reports
            (student_id,report_date,study_hours,plan_execution,subjects_json,practice_count,
             main_problem,satisfaction,tomorrow_goal,status,analysis_status,analysis_json)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (student_id,report_date,float(study_hours or 0),float(plan_execution or 0),payload,
             int(practice_count or 0),main_problem or "",satisfaction or "",tomorrow_goal or "",
             status,analysis_status,analysis_payload))
        report_id=cur.lastrowid

    # Keep a compact objective-progress record for weekly summaries/charts.
    c.execute("""INSERT INTO student_progress
        (student_id,report_date,study_hours,plan_execution,practice_count,status,trend,evidence_json)
        VALUES(?,?,?,?,?,?,?,?)
        ON CONFLICT(student_id,report_date) DO UPDATE SET
          study_hours=excluded.study_hours,
          plan_execution=excluded.plan_execution,
          practice_count=excluded.practice_count,
          status=excluded.status,
          trend=excluded.trend,
          evidence_json=excluded.evidence_json""",
        (student_id,report_date,float(study_hours or 0),float(plan_execution or 0),
         int(practice_count or 0),status,"ثبت گزارش روزانه",payload))
    
    if answers:
        for key,value in answers.items():
            c.execute("""INSERT INTO daily_report_answers(report_id,question_key,answer)
                         VALUES(?,?,?)
                         ON CONFLICT(report_id,question_key) DO UPDATE SET
                         answer=excluded.answer""",
                      (report_id,str(key),str(value or "")))
    c.commit()
    c.close()
    return report_id

def list_daily_report_answers(report_id):
    c=conn()
    rows=c.execute("SELECT * FROM daily_report_answers WHERE report_id=? ORDER BY id",(report_id,)).fetchall()
    c.close()
    return rows

def save_ai_flag(student_id, report_id, flag_type, severity, reason):
    c=conn()
    cur=c.execute("""INSERT INTO ai_flags(student_id,report_id,flag_type,severity,reason)
                     VALUES(?,?,?,?,?)""",(student_id,report_id,flag_type,severity,reason))
    c.commit(); rid=cur.lastrowid; c.close()
    return rid

def save_ai_recommendation(student_id, report_id, recommendation, priority=1, source="rule_engine"):
    c=conn()
    cur=c.execute("""INSERT INTO ai_recommendations
                     (student_id,report_id,recommendation,priority,source)
                     VALUES(?,?,?,?,?)""",
                  (student_id,report_id,recommendation,int(priority or 1),source))
    c.commit(); rid=cur.lastrowid; c.close()
    return rid

def open_flag_exists(student_id, flag_type):
    c=conn()
    row=c.execute("""SELECT id FROM ai_flags
                     WHERE student_id=? AND flag_type=? AND status='open'
                     LIMIT 1""",(student_id,flag_type)).fetchone()
    c.close()
    return bool(row)

def open_followup_exists(student_id, followup_type):
    c=conn()
    row=c.execute("""SELECT id FROM followups
                     WHERE student_id=? AND followup_type=? AND status='open'
                     LIMIT 1""",(student_id,followup_type)).fetchone()
    c.close()
    return bool(row)

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


def save_ai_analysis(student_id, analysis_type, title, content, structured=None, status="completed"):
    c=conn()
    # Compatible with both pre-migration and migrated databases.
    if any(r[1] == "structured_json" for r in c.execute("PRAGMA table_info(ai_analyses)").fetchall()):
        c.execute("INSERT INTO ai_analyses(student_id,analysis_type,title,content,structured_json,status) VALUES(?,?,?,?,?,?)",
                  (student_id, analysis_type, title, content, json.dumps(structured, ensure_ascii=False) if structured is not None else None, status))
    else:
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


# ---------- CRM / Sales / Call-center helpers ----------

def upsert_lead_from_student(student_id, source=""):
    s=get_student(student_id)
    if not s:
        return None
    c=conn()
    row=c.execute("SELECT * FROM leads WHERE telegram_id=?", (s["telegram_id"],)).fetchone()
    src=source or s["referral_source"] or ""
    if row:
        c.execute("""UPDATE leads SET name=?,phone=?,source=COALESCE(NULLIF(source,''),?),updated_at=CURRENT_TIMESTAMP
                     WHERE id=?""",
                  (f"{s['first_name']} {s['last_name']}".strip(),s["phone"] or "",src,row["id"]))
        lead_id=row["id"]
    else:
        cur=c.execute("""INSERT INTO leads(telegram_id,name,phone,source,status)
                         VALUES(?,?,?,?,?)""",
                      (s["telegram_id"],f"{s['first_name']} {s['last_name']}".strip(),s["phone"] or "",src,"lead"))
        lead_id=cur.lastrowid
    c.commit(); c.close()
    return lead_id

def set_lead_status(lead_id, new_status):
    c=conn()
    row=c.execute("SELECT status FROM leads WHERE id=?", (lead_id,)).fetchone()
    if not row:
        c.close(); return False
    old=row["status"]
    if old != new_status:
        c.execute("UPDATE leads SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(new_status,lead_id))
        c.execute("INSERT INTO lead_status_history(lead_id,old_status,new_status) VALUES(?,?,?)",
                  (lead_id,old,new_status))
    c.commit(); c.close(); return True

def add_lead_contact(lead_id, result, note=""):
    c=conn()
    c.execute("INSERT INTO lead_contacts(lead_id,result,note) VALUES(?,?,?)",(lead_id,result,note or ""))
    c.commit(); c.close()
    return set_lead_status(lead_id, result)

def list_leads(status=None, limit=300):
    c=conn()
    if status:
        rows=c.execute("""SELECT l.*, 
                    (SELECT COUNT(*) FROM lead_contacts lc WHERE lc.lead_id=l.id) contacts
                    FROM leads l WHERE l.status=? ORDER BY l.updated_at DESC,l.id DESC LIMIT ?""",(status,limit)).fetchall()
    else:
        rows=c.execute("""SELECT l.*,
                    (SELECT COUNT(*) FROM lead_contacts lc WHERE lc.lead_id=l.id) contacts
                    FROM leads l ORDER BY l.updated_at DESC,l.id DESC LIMIT ?""",(limit,)).fetchall()
    c.close(); return rows

def lead_details(lead_id):
    c=conn()
    lead=c.execute("SELECT * FROM leads WHERE id=?",(lead_id,)).fetchone()
    contacts=c.execute("SELECT * FROM lead_contacts WHERE lead_id=? ORDER BY id DESC",(lead_id,)).fetchall()
    history=c.execute("SELECT * FROM lead_status_history WHERE lead_id=? ORDER BY id DESC",(lead_id,)).fetchall()
    c.close()
    return {"lead":lead,"contacts":contacts,"history":history}

def sync_students_to_leads():
    rows=list_students(10000)
    created=0
    for s in rows:
        before=conn()
        exists=before.execute("SELECT 1 FROM leads WHERE telegram_id=?",(s["telegram_id"],)).fetchone()
        before.close()
        upsert_lead_from_student(s["id"],s["referral_source"] or "")
        if not exists: created += 1
    return created

def crm_stats():
    c=conn()
    out={}
    for status in ("lead","contacted","interested","followup","registered","lost"):
        out[status]=c.execute("SELECT COUNT(*) n FROM leads WHERE status=?",(status,)).fetchone()["n"]
    out["total_leads"]=c.execute("SELECT COUNT(*) n FROM leads").fetchone()["n"]
    out["contacts"]=c.execute("SELECT COUNT(*) n FROM lead_contacts").fetchone()["n"]
    out["registrations"]=c.execute("SELECT COUNT(*) n FROM registrations").fetchone()["n"]
    out["revenue"]=c.execute("SELECT COALESCE(SUM(amount),0) n FROM registrations WHERE status IN ('registered','paid')").fetchone()["n"]
    out["open_followups"]=c.execute("SELECT COUNT(*) n FROM followups WHERE status='open'").fetchone()["n"]
    c.close()
    return out

def register_service(student_id, service, amount=0, status="registered"):
    c=conn()
    cur=c.execute("INSERT INTO registrations(student_id,service,amount,status) VALUES(?,?,?,?)",
                  (student_id,service,float(amount or 0),status))
    c.commit(); rid=cur.lastrowid; c.close()
    s=get_student(student_id)
    if s:
        lead_id=upsert_lead_from_student(student_id)
        if lead_id:
            set_lead_status(lead_id,"registered")
    return rid

def sales_summary(days=30):
    c=conn()
    rows=c.execute("""SELECT service,COUNT(*) count,COALESCE(SUM(amount),0) revenue
                      FROM registrations
                      WHERE date(created_at)>=date('now', ?)
                      GROUP BY service ORDER BY revenue DESC""",(f"-{max(1,int(days))-1} days",)).fetchall()
    c.close()
    return rows

def counselor_kpi(days=30):
    c=conn()
    rows=c.execute("""SELECT c.id,c.name,
        (SELECT COUNT(*) FROM student_counselor_assignments a WHERE a.counselor_id=c.id AND a.active=1) assigned,
        (SELECT COUNT(*) FROM counselor_notes n WHERE n.counselor_id=c.id AND date(n.created_at)>=date('now', ?)) notes,
        (SELECT COUNT(*) FROM followups f WHERE f.counselor_id=c.id AND date(f.created_at)>=date('now', ?)) followups_created,
        (SELECT COUNT(*) FROM followups f WHERE f.counselor_id=c.id AND f.status='completed' AND date(f.completed_at)>=date('now', ?)) followups_done
        FROM counselors c WHERE c.active=1 ORDER BY assigned DESC,c.name""",
        (f"-{max(1,int(days))-1} days",)*3).fetchall()
    c.close(); return rows


def add_call_center_agent(name, phone="", monthly_base=2500000, commission_rate=0.05):
    c=conn()
    cur=c.execute("INSERT INTO call_center_agents(name,phone,monthly_base,commission_rate) VALUES(?,?,?,?)",
                  (name.strip(),phone.strip(),float(monthly_base),float(commission_rate)))
    c.commit(); rid=cur.lastrowid; c.close(); return rid

def list_call_center_agents(active_only=True):
    c=conn()
    q="SELECT * FROM call_center_agents"
    if active_only: q += " WHERE active=1"
    rows=c.execute(q+" ORDER BY id").fetchall()
    c.close(); return rows

def log_call(lead_id, agent_id, result, effective=0, converted=0, note=""):
    c=conn()
    c.execute("INSERT INTO call_logs(lead_id,agent_id,result,effective,converted,note) VALUES(?,?,?,?,?,?)",
              (lead_id,agent_id,result,int(bool(effective)),int(bool(converted)),note or ""))
    c.commit(); c.close()
    return add_lead_contact(lead_id,result,note)

def call_center_kpi(days=30):
    c=conn(); since=f"-{max(1,int(days))-1} days"
    rows=c.execute("""SELECT a.id,a.name,a.monthly_base,a.commission_rate,
        COUNT(cl.id) calls,COALESCE(SUM(cl.effective),0) effective_calls,
        COALESCE(SUM(cl.converted),0) conversions,
        COALESCE((SELECT SUM(r.amount) FROM registrations r WHERE r.sales_agent_id=a.id
        AND r.status IN ('registered','paid') AND date(r.created_at)>=date('now',?)),0) revenue
        FROM call_center_agents a
        LEFT JOIN call_logs cl ON cl.agent_id=a.id AND date(cl.contacted_at)>=date('now',?)
        WHERE a.active=1 GROUP BY a.id,a.name,a.monthly_base,a.commission_rate
        ORDER BY calls DESC,a.id""",(since,since)).fetchall()
    c.close(); return rows


def monthly_call_center_payroll(year_month=None):
    ym=year_month or __import__("datetime").datetime.now().strftime("%Y-%m")
    c=conn()
    rows=c.execute("""SELECT a.id,a.name,a.monthly_base,a.commission_rate,
        COALESCE(SUM(CASE WHEN r.status IN ('registered','paid') THEN r.amount ELSE 0 END),0) revenue
        FROM call_center_agents a
        LEFT JOIN registrations r ON r.sales_agent_id=a.id AND substr(r.created_at,1,7)=?
        WHERE a.active=1 GROUP BY a.id,a.name,a.monthly_base,a.commission_rate ORDER BY a.id""",(ym,)).fetchall()
    c.close()
    return [{**dict(r),"commission":float(r["revenue"] or 0)*float(r["commission_rate"] or 0),
             "total_pay":float(r["monthly_base"] or 0)+float(r["revenue"] or 0)*float(r["commission_rate"] or 0)}
            for r in rows]

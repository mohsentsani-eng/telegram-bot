import os, shutil, sqlite3
from datetime import datetime
from pathlib import Path
from . import db

TARGET_VERSION = 2

def _backup_path():
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return db.DB.parent / f"{db.DB.name}.pre_migration_{stamp}.bak"

def backup_before_migration():
    if not db.DB.exists() or db.DB.stat().st_size == 0:
        return None
    # Only create a pre-migration backup when the target schema is not already applied.
    try:
        check = sqlite3.connect(db.DB)
        row = check.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        check.close()
        if (row and (row[0] or 0) >= TARGET_VERSION):
            return None
    except sqlite3.Error:
        # Old database without schema_migrations: backup before first migration.
        pass
    dest = _backup_path()
    shutil.copy2(db.DB, dest)
    print(f"[MIGRATION] database backup: {dest}", flush=True)
    return dest

def _column_exists(c, table, column):
    return any(r[1] == column for r in c.execute(f"PRAGMA table_info({table})").fetchall())

def _add_column(c, table, column, definition):
    if not _column_exists(c, table, column):
        c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

def migrate():
    c = db.conn()
    c.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    current = c.execute("SELECT COALESCE(MAX(version),0) v FROM schema_migrations").fetchone()["v"]
    if current >= TARGET_VERSION:
        c.close()
        return False

    c.executescript("""
    CREATE TABLE IF NOT EXISTS student_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        goal TEXT NOT NULL,
        target_value TEXT,
        status TEXT DEFAULT 'active',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id)
    );
    CREATE TABLE IF NOT EXISTS daily_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        report_date TEXT NOT NULL,
        study_hours REAL DEFAULT 0,
        plan_execution REAL DEFAULT 0,
        subjects_json TEXT,
        practice_count INTEGER DEFAULT 0,
        main_problem TEXT,
        satisfaction TEXT,
        tomorrow_goal TEXT,
        status TEXT DEFAULT 'pending',
        analysis_status TEXT DEFAULT 'pending',
        analysis_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(student_id, report_date),
        FOREIGN KEY(student_id) REFERENCES students(id)
    );
    CREATE TABLE IF NOT EXISTS daily_report_answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL,
        question_key TEXT NOT NULL,
        answer TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(report_id, question_key),
        FOREIGN KEY(report_id) REFERENCES daily_reports(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS student_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        report_date TEXT NOT NULL,
        study_hours REAL,
        plan_execution REAL,
        practice_count INTEGER,
        status TEXT DEFAULT 'normal',
        trend TEXT,
        evidence_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(student_id, report_date),
        FOREIGN KEY(student_id) REFERENCES students(id)
    );
    CREATE TABLE IF NOT EXISTS ai_flags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        report_id INTEGER,
        flag_type TEXT NOT NULL,
        severity TEXT NOT NULL,
        reason TEXT NOT NULL,
        status TEXT DEFAULT 'open',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        resolved_at TEXT,
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(report_id) REFERENCES daily_reports(id)
    );
    CREATE TABLE IF NOT EXISTS ai_recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        report_id INTEGER,
        recommendation TEXT NOT NULL,
        priority INTEGER DEFAULT 1,
        source TEXT DEFAULT 'rule_engine',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(report_id) REFERENCES daily_reports(id)
    );
    CREATE TABLE IF NOT EXISTS counselors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        telegram_id INTEGER UNIQUE,
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS student_counselor_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        counselor_id INTEGER NOT NULL,
        active INTEGER DEFAULT 1,
        assigned_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(counselor_id) REFERENCES counselors(id)
    );
    CREATE TABLE IF NOT EXISTS counselor_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        counselor_id INTEGER,
        note TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(counselor_id) REFERENCES counselors(id)
    );
    CREATE TABLE IF NOT EXISTS followups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        counselor_id INTEGER,
        followup_type TEXT DEFAULT 'general',
        priority TEXT DEFAULT 'normal',
        status TEXT DEFAULT 'open',
        due_at TEXT,
        note TEXT,
        completed_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(counselor_id) REFERENCES counselors(id)
    );
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER,
        name TEXT,
        phone TEXT,
        source TEXT,
        status TEXT DEFAULT 'lead',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS lead_contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER NOT NULL,
        result TEXT NOT NULL,
        note TEXT,
        contacted_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(lead_id) REFERENCES leads(id)
    );
    CREATE TABLE IF NOT EXISTS lead_status_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER NOT NULL,
        old_status TEXT,
        new_status TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(lead_id) REFERENCES leads(id)
    );
    CREATE TABLE IF NOT EXISTS evaluations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        lead_id INTEGER,
        evaluation_type TEXT,
        status TEXT DEFAULT 'new',
        result_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(lead_id) REFERENCES leads(id)
    );
    CREATE TABLE IF NOT EXISTS registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        service TEXT NOT NULL,
        amount REAL,
        status TEXT DEFAULT 'registered',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id)
    );
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        kind TEXT NOT NULL,
        scheduled_for TEXT,
        sent_at TEXT,
        status TEXT DEFAULT 'pending',
        payload_json TEXT,
        UNIQUE(student_id, kind, scheduled_for),
        FOREIGN KEY(student_id) REFERENCES students(id)
    );
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor_type TEXT NOT NULL,
        actor_id TEXT,
        action TEXT NOT NULL,
        entity_type TEXT,
        entity_id TEXT,
        old_value TEXT,
        new_value TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS imports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        import_type TEXT,
        status TEXT DEFAULT 'preview',
        total_rows INTEGER DEFAULT 0,
        new_rows INTEGER DEFAULT 0,
        duplicate_rows INTEGER DEFAULT 0,
        invalid_rows INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS import_rows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        import_id INTEGER NOT NULL,
        row_number INTEGER,
        status TEXT,
        reason TEXT,
        payload_json TEXT,
        FOREIGN KEY(import_id) REFERENCES imports(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_daily_reports_student_date ON daily_reports(student_id, report_date);
    CREATE INDEX IF NOT EXISTS idx_progress_student_date ON student_progress(student_id, report_date);
    CREATE INDEX IF NOT EXISTS idx_flags_student_status ON ai_flags(student_id, status);
    CREATE INDEX IF NOT EXISTS idx_followups_status_due ON followups(status, due_at);
    """)
    _add_column(c, "ai_analyses", "structured_json", "TEXT")
    _add_column(c, "ai_analyses", "status", "TEXT DEFAULT 'completed'")

    # v2: call-center agents, call logs and sales attribution.
    if current < 2:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS call_center_agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            active INTEGER DEFAULT 1,
            monthly_base REAL DEFAULT 2500000,
            commission_rate REAL DEFAULT 0.05,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS call_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER NOT NULL,
            agent_id INTEGER NOT NULL,
            result TEXT NOT NULL,
            effective INTEGER DEFAULT 0,
            converted INTEGER DEFAULT 0,
            note TEXT,
            contacted_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(lead_id) REFERENCES leads(id),
            FOREIGN KEY(agent_id) REFERENCES call_center_agents(id)
        );
        CREATE INDEX IF NOT EXISTS idx_call_logs_agent_date ON call_logs(agent_id,contacted_at);
        CREATE INDEX IF NOT EXISTS idx_call_logs_lead ON call_logs(lead_id);
        """)
        cols=[r[1] for r in c.execute("PRAGMA table_info(registrations)").fetchall()]
        if "sales_agent_id" not in cols:
            c.execute("ALTER TABLE registrations ADD COLUMN sales_agent_id INTEGER")

    c.execute("INSERT OR REPLACE INTO schema_migrations(version, applied_at) VALUES(?,CURRENT_TIMESTAMP)", (TARGET_VERSION,))
    c.commit()
    c.close()
    print(f"[MIGRATION] schema version {TARGET_VERSION} applied", flush=True)
    return True

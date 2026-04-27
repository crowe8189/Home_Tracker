import streamlit as st
import pandas as pd
import os
from datetime import date
from utils.seeder import seed_data

# ====================== MODE DETECTION ======================
def is_cloud_mode():
    return "TURSO_URL" in st.secrets and "TURSO_AUTH_TOKEN" in st.secrets

if is_cloud_mode():
    import libsql
    DB_MODE = "cloud"
else:
    import sqlite3
    DB_MODE = "local"
    DB_PATH = "home_build.db"

# ====================== CONNECTION ======================
def get_connection():
    if DB_MODE == "cloud":
        if "TURSO_URL" not in st.secrets or "TURSO_AUTH_TOKEN" not in st.secrets:
            st.error("❌ Turso credentials missing in .streamlit/secrets.toml")
            st.stop()
        return libsql.connect(
            database=st.secrets["TURSO_URL"],
            auth_token=st.secrets["TURSO_AUTH_TOKEN"]
        )
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row):
    """Robust row → dict for both sqlite3 and Turso/libsql."""
    if row is None:
        return None
    if hasattr(row, '_mapping'):
        return dict(row._mapping)
    if hasattr(row, 'keys'):
        return dict(row)
    try:
        return dict(row)
    except Exception:
        return None


def read_df(query, conn, params=None):
    """Execute SELECT and return pd.DataFrame — safe for both sqlite3 and libsql/Turso.

    pandas read_sql does not work with libsql connections, so in cloud mode we
    manually build the DataFrame from cursor results.
    """
    if DB_MODE == "local":
        return pd.read_sql(query, conn)
    # Cloud / Turso path
    cursor = conn.execute(query) if params is None else conn.execute(query, params)
    rows = cursor.fetchall()
    if not rows:
        try:
            cols = [d[0] for d in cursor.description]
        except Exception:
            cols = []
        return pd.DataFrame(columns=cols)
    return pd.DataFrame([row_to_dict(r) for r in rows])


# ====================== INIT DB ======================
def init_db():
    os.makedirs("uploads", exist_ok=True)
    conn = get_connection()
    c = conn.cursor()

    # === Create all tables ===
    c.execute("""CREATE TABLE IF NOT EXISTS project_config (
        id INTEGER PRIMARY KEY CHECK (id=1),
        name TEXT NOT NULL,
        total_budget REAL NOT NULL,
        start_date TEXT NOT NULL,
        address TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS budget_categories (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE,
        planned_amount REAL,
        notes TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY,
        category_id INTEGER,
        date TEXT,
        amount REAL,
        description TEXT,
        vendor TEXT,
        receipt_id INTEGER,
        FOREIGN KEY(category_id) REFERENCES budget_categories(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS phases (
        id INTEGER PRIMARY KEY,
        name TEXT,
        order_num INTEGER,
        description TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY,
        phase_id INTEGER,
        title TEXT,
        description TEXT,
        planned_start TEXT,
        planned_end TEXT,
        due_date TEXT,
        status TEXT CHECK(status IN ('not_started','in_progress','completed','delayed')),
        completed_date TEXT,
        notes TEXT,
        FOREIGN KEY(phase_id) REFERENCES phases(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS task_dependencies (
        id INTEGER PRIMARY KEY,
        task_id INTEGER,
        prerequisite_id INTEGER,
        FOREIGN KEY(task_id) REFERENCES tasks(id),
        FOREIGN KEY(prerequisite_id) REFERENCES tasks(id)
    )""")

    # Receipts — base columns only; new columns added via migration below
    c.execute("""CREATE TABLE IF NOT EXISTS receipts (
        id INTEGER PRIMARY KEY,
        file_path TEXT,
        original_filename TEXT,
        upload_date TEXT,
        vendor TEXT,
        amount REAL,
        category TEXT,
        notes TEXT,
        linked_expense_id INTEGER,
        ocr_text TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS permits (
        id INTEGER PRIMARY KEY,
        name TEXT,
        status TEXT,
        required_date TEXT,
        issued_date TEXT,
        notes TEXT,
        document_path TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS qol_ideas (
        id INTEGER PRIMARY KEY,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        estimated_cost REAL,
        status TEXT DEFAULT 'planned' CHECK(status IN ('planned', 'in_progress', 'implemented', 'deferred')),
        linked_phase_id INTEGER,
        linked_task_id INTEGER,
        notes TEXT,
        FOREIGN KEY(linked_phase_id) REFERENCES phases(id),
        FOREIGN KEY(linked_task_id) REFERENCES tasks(id)
    )""")

    conn.commit()

    # === TURSO-SAFE MIGRATION: add columns that didn't exist at initial deploy ===
    c.execute("PRAGMA table_info(receipts)")
    existing_cols = {row[1] for row in c.fetchall()}

    new_columns = {
        "file_category":    "TEXT DEFAULT 'receipt'",
        "linked_task_id":   "INTEGER",
        "linked_permit_id": "INTEGER",
        "document_type":    "TEXT",
    }

    for col_name, col_def in new_columns.items():
        if col_name not in existing_cols:
            try:
                c.execute(f"ALTER TABLE receipts ADD COLUMN {col_name} {col_def}")
                print(f"✅ Migrated receipts: added '{col_name}'")
            except Exception as e:
                print(f"⚠️ Migration note for '{col_name}': {e}")

    conn.commit()

    # Seed only once
    c.execute("SELECT COUNT(*) FROM project_config WHERE id=1")
    if c.fetchone()[0] == 0:
        seed_data(conn)
        print(f"✅ Crowe's Nest Build seeded in {DB_MODE} mode!")

    # Cloud: prune orphaned receipts on every cold start. Two passes:
    #   1. Local-path orphans  — file_path is NULL/empty/non-http (uploads/ is wiped on restart).
    #   2. Bucket-mismatch orphans — file_path looks like a Supabase URL but the file
    #      no longer exists in the bucket. These are the "ghosts that come back" because
    #      the URL pattern alone can't tell them apart from valid records.
    if DB_MODE == "cloud":
        local_row = conn.execute("""
            SELECT COUNT(*) FROM receipts
            WHERE file_path IS NULL OR file_path = '' OR file_path NOT LIKE 'http%'
        """).fetchone()
        local_count = local_row[0] if local_row else 0
        if local_count:
            conn.execute("""
                DELETE FROM receipts
                WHERE file_path IS NULL OR file_path = '' OR file_path NOT LIKE 'http%'
            """)
            conn.commit()
            print(f"🧹 Auto-cleaned {local_count} local-path orphan(s)")

        try:
            from utils.helpers import reconcile_supabase_with_db
            bucket_pruned = reconcile_supabase_with_db(conn)
            if bucket_pruned:
                print(f"🧹 Pruned {bucket_pruned} bucket-mismatch ghost(s)")
        except Exception as e:
            print(f"⚠️ Skipping bucket reconciliation: {e}")

    conn.close()


_CONFIG_FALLBACK = {
    "name": "Crowe's Nest Build",
    "total_budget": 450000.0,
    "start_date": "2026-04-07",
    "address": "450 SR 27, Whitwell, TN 37397",
}


def get_project_config():
    """Get project config — auto-initializes DB if missing (critical for Streamlit Cloud)."""
    row = None
    try:
        conn = get_connection()
        row = conn.execute("SELECT * FROM project_config WHERE id=1").fetchone()
        conn.close()
    except Exception as e:
        print(f"⚠️ DB connection error: {e} — running init_db() now...")
        try:
            init_db()
            conn = get_connection()
            row = conn.execute("SELECT * FROM project_config WHERE id=1").fetchone()
            conn.close()
        except Exception as e2:
            print(f"⚠️ init_db also failed: {e2}")

    if row is None:
        try:
            init_db()
            conn = get_connection()
            row = conn.execute("SELECT * FROM project_config WHERE id=1").fetchone()
            conn.close()
        except Exception as e3:
            print(f"⚠️ Could not load project_config: {e3}")

    result = row_to_dict(row)
    if result is None:
        # DB is unreachable — return a safe fallback so the UI doesn't crash.
        # The sidebar and pages will still render; they just won't have live data.
        st.error(
            "❌ Cannot connect to Turso database. Check that TURSO_URL and "
            "TURSO_AUTH_TOKEN are set correctly in Streamlit Cloud Secrets "
            "(share.streamlit.io → your app → Settings → Secrets)."
        )
        return dict(_CONFIG_FALLBACK)
    return result


def update_project_config(name, total_budget, start_date, address):
    conn = get_connection()
    conn.execute(
        "UPDATE project_config SET name=?, total_budget=?, start_date=?, address=? WHERE id=1",
        (name, total_budget, start_date, address)
    )
    conn.commit()
    conn.close()


def get_current_focus():
    """Returns current task + next pending permit for Quick Log and Dashboard."""
    conn = get_connection()

    task = conn.execute("""
        SELECT id, title, due_date, planned_start, status
        FROM tasks
        WHERE status != 'completed'
        ORDER BY planned_start LIMIT 1
    """).fetchone()

    permit = conn.execute("""
        SELECT id, name, required_date
        FROM permits
        WHERE status = 'pending'
        ORDER BY required_date LIMIT 1
    """).fetchone()

    conn.close()

    return {
        "task":   row_to_dict(task),
        "permit": row_to_dict(permit),
    }

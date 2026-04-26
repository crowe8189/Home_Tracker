import streamlit as st
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
        conn = libsql.connect(
            database=st.secrets["TURSO_URL"],
            auth_token=st.secrets["TURSO_AUTH_TOKEN"]
        )
        return conn
    else:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

def row_to_dict(row):
    """Robust row → dict that works for BOTH local SQLite AND Turso/libsql on Streamlit Cloud."""
    if row is None:
        return None
    
    # Turso / libsql rows (most common cause of crash on Cloud)
    if hasattr(row, '_mapping'):
        return dict(row._mapping)
    
    # Standard sqlite3.Row
    if hasattr(row, 'keys'):
        return dict(row)
    
    # Fallback for any other iterable/row-like object
    try:
        return dict(row)
    except Exception:
        return None

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

    # Receipts (updated for Quick Log + All Files Hub)
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
        ocr_text TEXT,
        -- NEW COLUMNS for Quick Log / Documents Hub
        file_category TEXT DEFAULT 'receipt',
        linked_task_id INTEGER,
        linked_permit_id INTEGER,
        document_type TEXT
    )""")
    new_cols = [
    ("file_category", "TEXT DEFAULT 'receipt'"),
    ("linked_task_id", "INTEGER"),
    ("linked_permit_id", "INTEGER"),
    ("document_type", "TEXT")
    ]

    for col_name, col_def in new_cols:
        if col_name not in existing_cols:
            c.execute(f"ALTER TABLE receipts ADD COLUMN {col_name} {col_def}")
            print(f"✅ Migrated receipts table: added {col_name}")

    conn.commit()

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

    # === Migrations (safe to run every time) ===
    c.execute("PRAGMA table_info(receipts)")
    columns = [row[1] for row in c.fetchall()]
    for col in ["linked_task_id", "linked_permit_id", "file_category", "tags"]:
        if col not in columns:
            c.execute(f"ALTER TABLE receipts ADD COLUMN {col} {'INTEGER' if 'id' in col else 'TEXT DEFAULT ''general'''}")
            print(f"✅ Added missing column: {col}")

    # Seed only once
    c.execute("SELECT COUNT(*) FROM project_config WHERE id=1")
    if c.fetchone()[0] == 0:
        seed_data(conn)
        print(f"✅ Crowe's Nest Build seeded in {DB_MODE} mode!")

    conn.close()

def get_project_config():
    """Get project config — auto-initializes DB if missing (critical for Streamlit Cloud)."""
    try:
        conn = get_connection()
        row = conn.execute("SELECT * FROM project_config WHERE id=1").fetchone()
        conn.close()
    except Exception as e:
        print(f"⚠️  DB connection error: {e} — running init_db() now...")
        init_db()
        conn = get_connection()
        row = conn.execute("SELECT * FROM project_config WHERE id=1").fetchone()
        conn.close()

    # If still no row, run full init
    if row is None:
        print("⚠️  No project_config found — running init_db() now...")
        init_db()
        conn = get_connection()
        row = conn.execute("SELECT * FROM project_config WHERE id=1").fetchone()
        conn.close()

    return row_to_dict(row)

def update_project_config(name, total_budget, start_date, address):
    conn = get_connection()
    conn.execute("UPDATE project_config SET name=?, total_budget=?, start_date=?, address=? WHERE id=1",
                 (name, total_budget, start_date, address))
    conn.commit()
    conn.close()

def get_current_focus():
    """Returns current task/permit for Quick Log linking"""
    conn = get_connection()
    task = conn.execute("""
        SELECT id, title FROM tasks 
        WHERE status != 'completed' 
        ORDER BY planned_start LIMIT 1
    """).fetchone()
    
    permit = conn.execute("""
        SELECT id, name FROM permits 
        WHERE status = 'pending' 
        ORDER BY required_date LIMIT 1
    """).fetchone()
    
    conn.close()
    return {
        "task": dict(task) if task else None,
        "permit": dict(permit) if permit else None
    }
import sqlite3
import os
from datetime import date
from utils.seeder import seed_data

DB_PATH = "home_build.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs("uploads", exist_ok=True)
    conn = get_connection()
    c = conn.cursor()

    # Project config
    c.execute("""CREATE TABLE IF NOT EXISTS project_config (
        id INTEGER PRIMARY KEY CHECK (id=1),
        name TEXT NOT NULL,
        total_budget REAL NOT NULL,
        start_date TEXT NOT NULL,
        address TEXT
    )""")

    # Budget categories, expenses, phases, tasks, dependencies, permits (unchanged)
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

    # ====================== RECEIPTS TABLE + TURSO-SAFE MIGRATION ======================
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
        file_category TEXT DEFAULT 'receipt',
        linked_task_id INTEGER,
        linked_permit_id INTEGER,
        document_type TEXT
    )""")

    # Robust migration for cloud (Turso) + local SQLite
    c.execute("PRAGMA table_info(receipts)")
    existing_cols = {row[1] for row in c.fetchall()}

    new_columns = {
        "file_category":    "TEXT DEFAULT 'receipt'",
        "linked_task_id":   "INTEGER",
        "linked_permit_id": "INTEGER",
        "document_type":    "TEXT"
    }

    for col_name, col_def in new_columns.items():
        if col_name not in existing_cols:
            try:
                c.execute(f"ALTER TABLE receipts ADD COLUMN {col_name} {col_def}")
                print(f"✅ Migrated: added column '{col_name}' to receipts")
            except Exception as e:
                print(f"⚠️ Column '{col_name}' already exists or migration skipped: {e}")

    conn.commit()
    print("✅ receipts table fully migrated (columns ready for Quick Log + All Files Hub)")

    # Seed only once
    c.execute("SELECT COUNT(*) FROM project_config WHERE id=1")
    if c.fetchone()[0] == 0:
        seed_data(conn)
        print("✅ Crowe's Nest Build seeded")

    conn.close()

def get_project_config():
    conn = get_connection()
    row = conn.execute("SELECT * FROM project_config WHERE id=1").fetchone()
    conn.close()
    return dict(row) if row else None

def update_project_config(name, total_budget, start_date, address):
    conn = get_connection()
    conn.execute("UPDATE project_config SET name=?, total_budget=?, start_date=?, address=? WHERE id=1",
                 (name, total_budget, start_date, address))
    conn.commit()
    conn.close()

# ====================== NEW HELPER FUNCTION ======================
def get_current_focus():
    """Used by Quick Log and All Files Hub"""
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
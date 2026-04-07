import libsql
import streamlit as st
import os
from datetime import date
from utils.seeder import seed_data

def get_connection():
    try:
        if "TURSO_URL" not in st.secrets or "TURSO_AUTH_TOKEN" not in st.secrets:
            st.error("❌ Turso credentials are missing in Streamlit Cloud Secrets")
            st.stop()
        
        conn = libsql.connect(
            database=st.secrets["TURSO_URL"],
            auth_token=st.secrets["TURSO_AUTH_TOKEN"]
        )
        return conn
        
    except Exception as e:
        st.error(f"❌ Turso Connection Failed: {str(e)}")
        st.stop()

def row_to_dict(cursor, row):
    if row is None:
        return None
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

def init_db():
    os.makedirs("uploads", exist_ok=True)
    conn = get_connection()
    c = conn.cursor()

    # === All tables (unchanged) ===
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
# Receipts table - now supports both receipts and general documents
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
        linked_task_id INTEGER,
        document_type TEXT DEFAULT 'receipt',   -- NEW: 'receipt' or 'document'
        ocr_text TEXT
    )""")

    # Safe migration
    c.execute("PRAGMA table_info(receipts)")
    columns = [row[1] for row in c.fetchall()]
    if "document_type" not in columns:
        c.execute("ALTER TABLE receipts ADD COLUMN document_type TEXT DEFAULT 'receipt'")
        print("✅ Added document_type column")

    conn.commit()

    # Seed only once
    c.execute("SELECT COUNT(*) FROM project_config WHERE id=1")
    if c.fetchone()[0] == 0:
        seed_data(conn)
        print("✅ Crowe's Nest Build seeded on Turso cloud")

    conn.close()

# Keep the rest unchanged (get_project_config, update_project_config, row_to_dict)
def get_project_config():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM project_config WHERE id=1")
    row = c.fetchone()
    conn.close()
    return row_to_dict(c, row) if row else None

def update_project_config(name, total_budget, start_date, address):
    conn = get_connection()
    conn.execute("UPDATE project_config SET name=?, total_budget=?, start_date=?, address=? WHERE id=1",
                 (name, total_budget, start_date, address))
    conn.commit()
    conn.close()
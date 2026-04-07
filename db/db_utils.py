import libsql
import streamlit as st
import os
from datetime import date
from utils.seeder import seed_data

def get_connection():
    """Connect to Turso cloud database"""
    if "TURSO_URL" not in st.secrets or "TURSO_AUTH_TOKEN" not in st.secrets:
        st.error("❌ Turso credentials missing in .streamlit/secrets.toml")
        st.stop()
    
    conn = libsql.connect(
        url=st.secrets["TURSO_URL"],
        auth_token=st.secrets["TURSO_AUTH_TOKEN"]
    )
    conn.row_factory = libsql.Row   # Makes rows behave like sqlite3.Row
    return conn

def init_db():
    os.makedirs("uploads", exist_ok=True)
    conn = get_connection()
    c = conn.cursor()

    # All your original CREATE TABLE statements (unchanged)
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

    conn.commit()

    # Seed only once (first time the database is empty)
    c.execute("SELECT COUNT(*) FROM project_config WHERE id=1")
    if c.fetchone()[0] == 0:
        seed_data(conn)
        print("✅ Seeded Crowe's Nest Build on Turso cloud database")

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
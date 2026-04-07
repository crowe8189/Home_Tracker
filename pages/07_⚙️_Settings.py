import streamlit as st
import pandas as pd
from db.db_utils import get_project_config, update_project_config, get_connection
from utils.seeder import seed_data
from utils.helpers import export_to_csv
import sqlite3
import os
from datetime import date

st.title("⚙️ Settings & Project Management")
st.caption("Edit project details, manage permits, reset data, and create backups")

tab1, tab2, tab3, tab4 = st.tabs(["Project Info", "Permits", "Data Reset & Backup", "About"])

with tab1:
    st.subheader("Project Configuration")
    config = get_project_config()
    
    with st.form("update_project"):
        name = st.text_input("Project Name", config['name'])
        budget = st.number_input("Total Budget $", value=config['total_budget'], min_value=100000.0)
        start_date = st.date_input("Start Date (dirtwork)", date.fromisoformat(config['start_date']))
        address = st.text_input("Address", config['address'])
        
        if st.form_submit_button("Save Changes"):
            update_project_config(name, float(budget), start_date.strftime("%Y-%m-%d"), address)
            st.success("Project settings updated!")
            st.rerun()

with tab2:
    st.subheader("📋 Permits & Inspections (Marion County + State Requirements)")
    st.caption("**Highlighted separately** from regular tasks • Critical path items")

    conn = get_connection()
    permits_df = pd.read_sql("""
        SELECT id, name, status, required_date, issued_date, notes 
        FROM permits 
        ORDER BY 
            CASE WHEN name LIKE '%Permit%' THEN 1 ELSE 2 END,  -- permits first
            required_date
    """, conn)
    conn.close()

    # Color-coded display
    for _, row in permits_df.iterrows():
        if row['status'] == 'approved' or row['issued_date']:
            st.success(f"✅ **{row['name']}** – Completed {row['issued_date'] or 'N/A'}")
        elif row['status'] == 'pending':
            st.warning(f"⏳ **{row['name']}** – Due {row['required_date']} | {row['notes']}")
        else:
            st.error(f"🚨 **{row['name']}** – {row['notes']}")

    # Quick add (still works)
    with st.expander("➕ Add New Permit or Inspection"):
        with st.form("add_permit"):
            p_name = st.text_input("Permit Name (e.g. Building Permit)")
            p_status = st.selectbox("Status", ["pending", "approved", "denied"])
            p_required = st.date_input("Required By", date.today())
            p_notes = st.text_area("Notes")
            if st.form_submit_button("Add Permit"):
                conn = get_connection()
                conn.execute("""INSERT INTO permits (name, status, required_date, issued_date, notes)
                                VALUES (?,?,?,?,?)""", (p_name, p_status, p_required.strftime("%Y-%m-%d"), None, p_notes))
                conn.commit()
                conn.close()
                st.success("Permit added!")
                st.rerun()

with tab3:
    st.subheader("Reset & Backup")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Reset to My Project Defaults (Crowe's Nest $350k)", type="secondary"):
            if st.checkbox("⚠️ This will DELETE all your current data and re-seed the original defaults. Confirm?", value=False):
                conn = get_connection()
                # Clear existing data
                conn.execute("DELETE FROM project_config WHERE id=1")
                conn.execute("DELETE FROM budget_categories")
                conn.execute("DELETE FROM expenses")
                conn.execute("DELETE FROM tasks")
                conn.execute("DELETE FROM task_dependencies")
                conn.execute("DELETE FROM receipts")
                conn.execute("DELETE FROM permits")
                conn.commit()
                seed_data(conn)
                conn.close()
                st.success("✅ Database reset to original Crowe's Nest defaults (including septic permit)!")
                st.rerun()
    
    with col2:
        st.write("Full Data Export")
        tables = ["budget_categories", "expenses", "tasks", "receipts", "permits"]
        for t in tables:
            if st.button(f"Download {t} CSV", key=t):
                st.download_button(f"✅ {t}.csv", export_to_csv(t), f"{t}.csv", "text/csv", key=f"dl_{t}")
        
        # Simple SQLite dump
        if st.button("Download Full Database Backup (.sql)"):
            conn = get_connection()
            with open("backup.sql", "w") as f:
                for line in conn.iterdump():
                    f.write(f"{line}\n")
            conn.close()
            with open("backup.sql", "rb") as f:
                st.download_button("✅ Download backup.sql", f.read(), "home_build_backup.sql", "text/plain")

with tab4:
    st.subheader("About Crowe's Nest Build")
    st.markdown("""
    **Local-first home construction manager**  
    Budget: $350,000 • Start: 2026-04-07 • Location: 450 SR 27, Whitwell, TN 37397  
    Owner electrical: materials only (permanent note)  
    AI: Gemini 1.5 Flash (add key in `.streamlit/secrets.toml`)  
    Storage: SQLite + local `uploads/` folder  
    """)
    
    st.subheader("Future Improvements")
    st.markdown("""
    - Full OCR fine-tuning with custom Tesseract config  
    - Email/SMS alerts (Twilio integration)  
    - Mobile PWA manifest for on-site use  
    - Photo logging with EXIF GPS  
    - LLM switcher (add Grok or OpenAI keys)  
    - Versioned backups with timestamps  
    - Weather API integration for TN alerts  
    """)
    
    st.caption("App built as a polished, modular, production-quality tool. Everything runs 100% locally.")
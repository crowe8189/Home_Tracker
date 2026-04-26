import streamlit as st
import pandas as pd
from datetime import date
import os

st.set_page_config(page_title="Settings", layout="wide", page_icon="⚙️")

from db.db_utils import (
    get_project_config, update_project_config, get_connection,
    init_db, read_df, is_cloud_mode, DB_MODE,
)
from utils.seeder import seed_data
from utils.helpers import export_to_csv
from utils.sidebar import render_sidebar

if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

render_sidebar()
st.title("⚙️ Settings & Project Management")
st.caption("Edit project details, manage permits, reset data, and create backups")

tab1, tab2, tab3, tab4 = st.tabs(["Project Info", "Permits", "Data Reset & Backup", "About"])

# ====================== TAB 1: Project Info ======================
with tab1:
    st.subheader("Project Configuration")
    config = get_project_config()

    with st.form("update_project"):
        name       = st.text_input("Project Name", config["name"])
        budget     = st.number_input("Total Budget $", value=float(config["total_budget"]), min_value=100000.0)
        start_date = st.date_input("Start Date (dirtwork)", date.fromisoformat(config["start_date"]))
        address    = st.text_input("Address", config["address"])

        if st.form_submit_button("Save Changes"):
            update_project_config(name, float(budget), start_date.strftime("%Y-%m-%d"), address)
            st.success("Project settings updated!")
            st.rerun()

# ====================== TAB 2: Permits ======================
with tab2:
    st.subheader("📋 Permits & Inspections (Marion County + State Requirements)")
    st.caption("Highlighted separately from regular tasks • Critical path items")

    conn = get_connection()
    permits_df = read_df("""
        SELECT id, name, status, required_date, issued_date, notes
        FROM permits
        ORDER BY
            CASE WHEN name LIKE '%Permit%' THEN 1 ELSE 2 END,
            required_date
    """, conn)
    conn.close()

    for _, row in permits_df.iterrows():
        if row["status"] == "approved" or row["issued_date"]:
            st.success(f"✅ **{row['name']}** – Completed {row['issued_date'] or 'N/A'}")
        elif row["status"] == "pending":
            st.warning(f"⏳ **{row['name']}** – Due {row['required_date']} | {row['notes']}")
        else:
            st.error(f"🚨 **{row['name']}** – {row['notes']}")

    with st.expander("➕ Add New Permit or Inspection"):
        with st.form("add_permit"):
            p_name     = st.text_input("Permit Name (e.g. Building Permit)")
            p_status   = st.selectbox("Status", ["pending", "approved", "denied"])
            p_required = st.date_input("Required By", date.today())
            p_notes    = st.text_area("Notes")
            if st.form_submit_button("Add Permit"):
                conn = get_connection()
                conn.execute("""
                    INSERT INTO permits (name, status, required_date, issued_date, notes)
                    VALUES (?,?,?,?,?)
                """, (p_name, p_status, p_required.strftime("%Y-%m-%d"), None, p_notes))
                conn.commit()
                conn.close()
                st.success("Permit added!")
                st.rerun()

# ====================== TAB 3: Reset & Backup ======================
with tab3:
    st.subheader("Reset & Backup")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**⚠️ Danger Zone**")
        confirm = st.checkbox(
            "I understand this will DELETE ALL current data and reset to the latest defaults "
            "(sitework complete, permits approved, footers this week)",
            key="reset_confirm",
        )
        if st.button("🔄 Reset to Current $450k Defaults", type="secondary", use_container_width=True):
            if confirm:
                conn = get_connection()
                for tbl in [
                    "project_config", "budget_categories", "expenses",
                    "tasks", "task_dependencies", "receipts", "permits", "qol_ideas",
                ]:
                    conn.execute(f"DELETE FROM {tbl}")
                conn.commit()
                seed_data(conn)
                conn.close()
                st.success(
                    "✅ Database fully reset! Site prep complete, septic + building permit "
                    "approved, footers being poured this week."
                )
                st.rerun()
            else:
                st.error("Please check the confirmation box first.")

    with col2:
        st.write("**Full Data Export**")
        tables = ["budget_categories", "expenses", "tasks", "receipts", "permits", "qol_ideas"]
        for t in tables:
            st.download_button(
                f"⬇️ {t}.csv",
                data=export_to_csv(t),
                file_name=f"{t}.csv",
                mime="text/csv",
                key=f"csv_{t}",
            )

        st.divider()

        if DB_MODE == "local":
            st.write("**SQLite Backup**")
            if st.button("Download Full Database Backup (.sql)"):
                conn = get_connection()
                lines = list(conn.iterdump())
                conn.close()
                sql_dump = "\n".join(lines)
                st.download_button(
                    "✅ Download backup.sql",
                    data=sql_dump.encode("utf-8"),
                    file_name="home_build_backup.sql",
                    mime="text/plain",
                )
        else:
            st.info(
                "☁️ Running on Turso (cloud DB) — SQL dump is not available. "
                "Use the CSV exports above to back up your data."
            )

        st.divider()
        st.subheader("📋 Professional Construction Binder")
        st.caption("Full project report with Gantt, budget, permits — perfect for inspectors")

        if st.button("📄 Generate & Download Construction Binder (PDF)", type="primary", use_container_width=True):
            if is_cloud_mode():
                st.warning(
                    "PDF generation with embedded charts requires kaleido, which may not be "
                    "available on Streamlit Cloud. If it fails, use the CSV exports instead."
                )
            with st.spinner("Generating PDF binder…"):
                try:
                    from utils.binder import generate_construction_binder
                    filename = generate_construction_binder()
                    with open(filename, "rb") as f:
                        st.download_button(
                            "✅ Download Construction Binder.pdf",
                            data=f.read(),
                            file_name=filename,
                            mime="application/pdf",
                            use_container_width=True,
                        )
                    st.success("Binder generated!")
                except Exception as e:
                    st.error(f"PDF generation failed: {e}")

# ====================== TAB 4: About ======================
with tab4:
    st.subheader("About Crowe's Nest Build")
    st.markdown(f"""
    **Home construction manager for the Crowe family**

    | Field | Value |
    |---|---|
    | Budget | $450,000 |
    | Start | 2026-04-07 |
    | Location | 450 SR 27, Whitwell, TN 37397 |
    | Owner electrical | Materials only (no labor cost tracked) |
    | DB mode | `{DB_MODE}` |
    | AI | Gemini 1.5 Flash (add key in `.streamlit/secrets.toml`) |
    """)

    st.subheader("Planned Future Improvements")
    st.markdown("""
    - Full OCR fine-tuning with custom Tesseract config
    - Email/SMS alerts (Twilio)
    - Photo EXIF GPS tagging
    - Weather API integration for TN storm alerts
    - Versioned timestamped backups
    - Full data export package (zip of CSVs + photos) at project completion
    """)

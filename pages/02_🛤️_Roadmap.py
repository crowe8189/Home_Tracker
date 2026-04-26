import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="Roadmap", layout="wide", page_icon="🛤️")

from db.db_utils import get_connection, init_db, read_df
from utils.charts import create_gantt
from utils.helpers import save_uploaded_file
from utils.sidebar import render_sidebar

if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

render_sidebar()
st.title("🛤️ Project Roadmap & Tasks")

tab1, tab2, tab3 = st.tabs(["📊 Gantt Timeline", "Tasks & Dependencies", "📋 Permits & Inspections"])

# ====================== TAB 1: Gantt ======================
with tab1:
    st.subheader("Full Project Gantt (Tasks + Permits & Inspections)")
    st.plotly_chart(create_gantt(), use_container_width=True)

# ====================== TAB 2: Tasks ======================
with tab2:
    st.subheader("Tasks & Dependencies")

    conn = get_connection()
    df_tasks = read_df("""
        SELECT
            t.id,
            p.name AS Phase,
            t.title,
            t.description,
            t.planned_start,
            t.planned_end,
            t.due_date,
            t.status,
            q.category AS QOL_Category,
            GROUP_CONCAT(pr.title) AS Blocked_By
        FROM tasks t
        JOIN phases p ON t.phase_id = p.id
        LEFT JOIN task_dependencies d  ON t.id = d.task_id
        LEFT JOIN tasks pr             ON d.prerequisite_id = pr.id
        LEFT JOIN qol_ideas q          ON t.id = q.linked_task_id
        GROUP BY t.id
        ORDER BY p.order_num, t.planned_start
    """, conn)
    conn.close()

    edited_df = st.data_editor(
        df_tasks,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config={
            "id":           st.column_config.NumberColumn("ID", disabled=True, width="small"),
            "status":       st.column_config.SelectboxColumn(
                "Status",
                options=["not_started", "in_progress", "completed", "delayed"],
                required=True,
            ),
            "Phase":        st.column_config.TextColumn(disabled=True),
            "Blocked_By":   st.column_config.TextColumn(disabled=True),
            "QOL_Category": st.column_config.TextColumn("From QOL Idea", disabled=True, width="medium"),
        },
    )

    colA, colB, colC = st.columns(3)
    with colA:
        if st.button("💾 Save All Task Changes", type="primary", use_container_width=True):
            conn = get_connection()
            for _, row in edited_df.iterrows():
                conn.execute("""
                    UPDATE tasks
                    SET title=?, description=?, planned_start=?, planned_end=?,
                        due_date=?, status=?
                    WHERE id=?
                """, (
                    row["title"], row["description"], row["planned_start"],
                    row["planned_end"], row["due_date"], row["status"], int(row["id"]),
                ))
            conn.commit()
            conn.close()
            st.success("✅ Tasks saved!")
            st.rerun()

    with colB:
        with st.expander("➕ Add New Task"):
            with st.form("add_task_full"):
                conn = get_connection()
                phases = [r[0] for r in conn.execute(
                    "SELECT name FROM phases ORDER BY order_num"
                ).fetchall()]
                conn.close()
                phase_name = st.selectbox("Phase", phases)
                title      = st.text_input("Task Title *")
                desc       = st.text_area("Description")
                start      = st.date_input("Planned Start", date.today())
                end        = st.date_input("Planned End",   date.today())
                due        = st.date_input("Due Date",      date.today())
                status     = st.selectbox("Initial Status",
                    ["not_started", "in_progress", "completed", "delayed"])
                if st.form_submit_button("Add Task") and title:
                    conn = get_connection()
                    phase_id = conn.execute(
                        "SELECT id FROM phases WHERE name=?", (phase_name,)
                    ).fetchone()[0]
                    conn.execute("""
                        INSERT INTO tasks
                            (phase_id, title, description, planned_start, planned_end,
                             due_date, status, notes)
                        VALUES (?,?,?,?,?,?,?,?)
                    """, (
                        phase_id, title, desc,
                        start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"),
                        due.strftime("%Y-%m-%d"), status, "Added manually",
                    ))
                    conn.commit()
                    conn.close()
                    st.success("Task added!")
                    st.rerun()

    with colC:
        if not df_tasks.empty:
            delete_title = st.selectbox("🗑️ Delete Task", df_tasks["title"].tolist(), key="delete_task")
            if st.button("Delete Selected Task", use_container_width=True):
                task_id = int(df_tasks[df_tasks["title"] == delete_title]["id"].iloc[0])
                conn = get_connection()
                conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
                conn.execute(
                    "DELETE FROM task_dependencies WHERE task_id=? OR prerequisite_id=?",
                    (task_id, task_id),
                )
                conn.commit()
                conn.close()
                st.success(f"Deleted: {delete_title}")
                st.rerun()

# ====================== TAB 3: Permits ======================
with tab3:
    st.subheader("📋 Permits & Inspections (Marion County TN)")
    st.caption("Separate from tasks • Appear on Gantt • Edit dates/status/notes here")

    if st.button("🔄 Load Default Marion County Permits & Inspections", type="primary", use_container_width=True):
        conn = get_connection()
        conn.execute("DELETE FROM permits")
        permits_data = [
            ("Septic System Permit",      "pending", "2026-04-14", None, "TDEC – must be approved BEFORE building permit. Soil test required first.", None),
            ("County Building Permit",    "pending", "2026-04-21", None, "Marion County – requires plans, septic approval, Owner/Builder Agreement", None),
            ("Electrical Permit (State)", "pending", "2026-05-01", None, "SFMO – required before rough electrical", None),
            ("Plumbing Permit",           "pending", "2026-05-01", None, "Required before rough plumbing", None),
            ("Mechanical/HVAC Permit",    "pending", "2026-05-01", None, "Required before rough HVAC", None),
            ("Footing Inspection",        "pending", "2026-04-28", None, "After trenches + rebar. TERMITE TREATMENT REQUIRED FIRST.", None),
            ("Foundation Inspection",     "pending", "2026-05-15", None, "After concrete cured + anchor bolts", None),
            ("Rough-In Inspection",       "pending", "2026-07-01", None, "After framing + all rough trades. Do NOT insulate yet.", None),
            ("Final Inspection & CO",     "pending", "2026-12-01", None, "All work complete + termite record on file", None),
        ]
        conn.executemany(
            "INSERT INTO permits (name, status, required_date, issued_date, notes, document_path) VALUES (?,?,?,?,?,?)",
            permits_data,
        )
        conn.commit()
        conn.close()
        st.success("✅ Default Marion County permits & inspections loaded!")
        st.rerun()

    conn = get_connection()
    df_permits = read_df(
        "SELECT id, name, status, required_date, issued_date, notes FROM permits ORDER BY required_date",
        conn,
    )
    conn.close()

    if df_permits.empty:
        st.info("No permits yet – click the button above to load defaults.")
    else:
        edited_permits = st.data_editor(
            df_permits,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "id":            st.column_config.NumberColumn("ID", disabled=True, width="small"),
                "status":        st.column_config.SelectboxColumn(
                    "Status", options=["pending", "approved", "denied"], required=True
                ),
                "required_date": st.column_config.TextColumn("Required By"),
                "issued_date":   st.column_config.TextColumn("Issued On (leave blank if pending)"),
                "name":          st.column_config.TextColumn("Permit / Inspection"),
                "notes":         st.column_config.TextColumn("Notes / Dependencies"),
            },
        )

        colP1, colP2, colP3 = st.columns(3)
        with colP1:
            if st.button("💾 Save Permit Changes", type="primary", use_container_width=True):
                conn = get_connection()
                for _, row in edited_permits.iterrows():
                    conn.execute("""
                        UPDATE permits
                        SET status=?, required_date=?, issued_date=?, notes=?
                        WHERE id=?
                    """, (row["status"], row["required_date"], row["issued_date"],
                          row["notes"], int(row["id"])))
                conn.commit()
                conn.close()
                st.success("✅ Permits & Inspections updated!")
                st.rerun()

        with colP2:
            with st.expander("➕ Add New Permit / Inspection"):
                with st.form("add_permit_form"):
                    name     = st.text_input("Name (e.g. Footing Inspection)")
                    status   = st.selectbox("Status", ["pending", "approved", "denied"])
                    req_date = st.date_input("Required By", date.today())
                    notes    = st.text_area("Notes / Dependencies")
                    if st.form_submit_button("Add") and name:
                        conn = get_connection()
                        conn.execute(
                            "INSERT INTO permits (name, status, required_date, issued_date, notes) VALUES (?,?,?,?,?)",
                            (name, status, req_date.strftime("%Y-%m-%d"), None, notes),
                        )
                        conn.commit()
                        conn.close()
                        st.success("Permit added!")
                        st.rerun()

        with colP3:
            st.caption("📎 Attach file to permit")
            selected_permit_name = st.selectbox(
                "Select permit", df_permits["name"].tolist(), key="attach_to_permit"
            )
            uploaded_attach = st.file_uploader(
                "Upload permit doc / photo / soil test",
                type=["jpg", "jpeg", "png", "pdf"],
                key="permit_upload",
            )
            if uploaded_attach and st.button("✅ Attach to Permit", use_container_width=True):
                file_url = save_uploaded_file(uploaded_attach)
                if file_url:
                    permit_id = int(
                        df_permits[df_permits["name"] == selected_permit_name]["id"].iloc[0]
                    )
                    conn = get_connection()
                    conn.execute("""
                        INSERT INTO receipts
                            (file_path, original_filename, upload_date, notes,
                             linked_permit_id, file_category, document_type)
                        VALUES (?,?,?,?,?,?,?)
                    """, (
                        file_url, uploaded_attach.name,
                        date.today().strftime("%Y-%m-%d"),
                        f"Attached to {selected_permit_name}",
                        permit_id, "permit", "document",
                    ))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ File attached to {selected_permit_name}!")
                    st.rerun()

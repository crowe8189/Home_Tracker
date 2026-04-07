import streamlit as st
import pandas as pd
from db.db_utils import get_connection
from utils.charts import create_gantt
from datetime import date

st.title("🛤️ Project Roadmap & Tasks")

tab1, tab2, tab3 = st.tabs(["📊 Gantt Timeline", "Tasks & Dependencies", "📋 Permits & Inspections"])

# ====================== TAB 1: Gantt ======================
with tab1:
    st.subheader("Full Project Gantt (Tasks + Permits & Inspections)")
    gantt_fig = create_gantt()
    st.plotly_chart(gantt_fig, use_container_width=True)

# ====================== TAB 2: Standard Tasks ======================
with tab2:
    st.subheader("Tasks & Dependencies")
    
    conn = get_connection()
    df_tasks = pd.read_sql("""
        SELECT t.id, p.name as Phase, t.title, t.description, 
               t.planned_start, t.planned_end, t.due_date, t.status,
               GROUP_CONCAT(pr.title) as Blocked_By
        FROM tasks t 
        JOIN phases p ON t.phase_id = p.id 
        LEFT JOIN task_dependencies d ON t.id = d.task_id 
        LEFT JOIN tasks pr ON d.prerequisite_id = pr.id 
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
            "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
            "status": st.column_config.SelectboxColumn(
                "Status", 
                options=["not_started", "in_progress", "completed", "delayed"],
                required=True
            ),
            "Phase": st.column_config.TextColumn(disabled=True),
            "Blocked_By": st.column_config.TextColumn(disabled=True),
        }
    )

    colA, colB, colC = st.columns([1, 1, 1])
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
                    row['title'], row['description'], row['planned_start'],
                    row['planned_end'], row['due_date'], row['status'], int(row['id'])
                ))
            conn.commit()
            conn.close()
            st.success("✅ Tasks saved!")
            st.rerun()

    with colB:
        with st.expander("➕ Add New Task"):
            with st.form("add_task_full"):
                conn = get_connection()
                phases = [row[0] for row in conn.execute("SELECT name FROM phases ORDER BY order_num").fetchall()]
                conn.close()
                phase_name = st.selectbox("Phase", phases)
                title = st.text_input("Task Title *")
                desc = st.text_area("Description")
                start = st.date_input("Planned Start", date.today())
                end = st.date_input("Planned End", date.today())
                due = st.date_input("Due Date", date.today())
                status = st.selectbox("Initial Status", ["not_started", "in_progress", "completed", "delayed"])
                submitted = st.form_submit_button("Add Task")
                if submitted and title:
                    conn = get_connection()
                    phase_id = conn.execute("SELECT id FROM phases WHERE name=?", (phase_name,)).fetchone()[0]
                    conn.execute("""INSERT INTO tasks 
                        (phase_id, title, description, planned_start, planned_end, due_date, status, notes)
                        VALUES (?,?,?,?,?,?,?,?)""",
                        (phase_id, title, desc, start.strftime("%Y-%m-%d"), 
                         end.strftime("%Y-%m-%d"), due.strftime("%Y-%m-%d"), status, "Added manually"))
                    conn.commit()
                    conn.close()
                    st.success("Task added!")
                    st.rerun()

    with colC:
        if not df_tasks.empty:
            delete_title = st.selectbox("🗑️ Delete Task", df_tasks['title'].tolist(), key="delete_task")
            if st.button("Delete Selected Task", use_container_width=True):
                task_id = df_tasks[df_tasks['title'] == delete_title]['id'].iloc[0]
                conn = get_connection()
                conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
                conn.execute("DELETE FROM task_dependencies WHERE task_id=? OR prerequisite_id=?", (task_id, task_id))
                conn.commit()
                conn.close()
                st.success(f"Deleted: {delete_title}")
                st.rerun()

# ====================== TAB 3: Permits & Inspections ======================
# ====================== TAB 3: Permits & Inspections ======================
with tab3:
    st.subheader("📋 Permits & Inspections (Marion County TN)")
    st.caption("Separate from tasks • Appear on Gantt • Edit dates/status/notes here")

    # NEW: One-click reload of all default permits
    if st.button("🔄 Load Default Marion County Permits & Inspections", type="primary", use_container_width=True):
        conn = get_connection()
        conn.execute("DELETE FROM permits")
        permits_data = [
            ("Septic System Permit", "pending", "2026-04-14", None, "TDEC – must be approved BEFORE building permit. Soil test required first.", None),
            ("County Building Permit", "pending", "2026-04-21", None, "Marion County – requires plans, septic approval, Owner/Builder Agreement", None),
            ("Electrical Permit (State)", "pending", "2026-05-01", None, "SFMO – required before rough electrical", None),
            ("Plumbing Permit", "pending", "2026-05-01", None, "Required before rough plumbing", None),
            ("Mechanical/HVAC Permit", "pending", "2026-05-01", None, "Required before rough HVAC", None),
            ("Footing Inspection", "pending", "2026-04-28", None, "After trenches + rebar. TERMITE TREATMENT REQUIRED FIRST.", None),
            ("Foundation Inspection", "pending", "2026-05-15", None, "After concrete cured + anchor bolts", None),
            ("Rough-In Inspection", "pending", "2026-07-01", None, "After framing + all rough trades. Do NOT insulate yet.", None),
            ("Final Inspection & CO", "pending", "2026-12-01", None, "All work complete + termite record on file", None),
        ]
        conn.executemany("""INSERT INTO permits 
            (name, status, required_date, issued_date, notes, document_path) 
            VALUES (?,?,?,?,?,?)""", permits_data)
        conn.commit()
        conn.close()
        st.success("✅ Default Marion County permits & inspections loaded!")
        st.rerun()

    conn = get_connection()
    df_permits = pd.read_sql("""
        SELECT id, name, status, required_date, issued_date, notes 
        FROM permits 
        ORDER BY required_date
    """, conn)
    conn.close()

    if df_permits.empty:
        st.info("No permits yet – click the button above to load defaults")
    else:
        edited_permits = st.data_editor(
            df_permits,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                "status": st.column_config.SelectboxColumn(
                    "Status", 
                    options=["pending", "approved", "denied"],
                    required=True
                ),
                "required_date": st.column_config.TextColumn("Required By"),
                "issued_date": st.column_config.TextColumn("Issued On (leave blank if pending)"),
                "name": st.column_config.TextColumn("Permit / Inspection"),
                "notes": st.column_config.TextColumn("Notes / Dependencies")
            }
        )

        colP1, colP2, colP3 = st.columns([1, 1, 1])
        with colP1:
            if st.button("💾 Save Permit Changes", type="primary", use_container_width=True):
                conn = get_connection()
                for _, row in edited_permits.iterrows():
                    conn.execute("""
                        UPDATE permits 
                        SET status=?, required_date=?, issued_date=?, notes=?
                        WHERE id=?
                    """, (
                        row['status'], row['required_date'], row['issued_date'], 
                        row['notes'], int(row['id'])
                    ))
                conn.commit()
                conn.close()
                st.success("✅ Permits & Inspections updated!")
                st.rerun()

        with colP2:
            with st.expander("➕ Add New Permit / Inspection"):
                with st.form("add_permit_form"):
                    name = st.text_input("Name (e.g. Footing Inspection)")
                    status = st.selectbox("Status", ["pending", "approved", "denied"])
                    req_date = st.date_input("Required By", date.today())
                    notes = st.text_area("Notes / Dependencies")
                    submitted = st.form_submit_button("Add")
                    if submitted and name:
                        conn = get_connection()
                        conn.execute("""INSERT INTO permits 
                            (name, status, required_date, issued_date, notes)
                            VALUES (?,?,?,?,?)""",
                            (name, status, req_date.strftime("%Y-%m-%d"), None, notes))
                        conn.commit()
                        conn.close()
                        st.success("Permit added!")
                        st.rerun()

        with colP3:
            if not df_permits.empty:
                del_name = st.selectbox("🗑️ Delete Permit/Inspection", df_permits['name'].tolist(), key="delete_permit")
                if st.button("Delete Selected", use_container_width=True):
                    perm_id = df_permits[df_permits['name'] == del_name]['id'].iloc[0]
                    conn = get_connection()
                    conn.execute("DELETE FROM permits WHERE id=?", (perm_id,))
                    conn.commit()
                    conn.close()
                    st.success(f"Deleted: {del_name}")
                    st.rerun()
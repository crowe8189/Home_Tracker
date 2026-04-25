import streamlit as st
import pandas as pd
from db.db_utils import get_connection, get_current_focus
from utils.sidebar import render_sidebar
render_sidebar()
st.set_page_config(page_title="🌳 QOL & Future-Proofing", layout="wide")
st.title("🌳 QOL & Future-Proofing Tracker")
st.caption("Your Master List • 20+ Year Forever Home • Mud, Horses, Kids, Durability")

conn = get_connection()
df = pd.read_sql("""
    SELECT q.id, q.category, q.description, q.estimated_cost,
           q.status, p.name as Phase, q.notes, q.linked_task_id,
           t.title as linked_task_title
    FROM qol_ideas q
    LEFT JOIN phases p ON q.linked_phase_id = p.id
    LEFT JOIN tasks t ON q.linked_task_id = t.id
    ORDER BY q.category, q.status
""", conn)
conn.close()

edited_df = st.data_editor(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "status": st.column_config.SelectboxColumn("Status", options=["planned", "in_progress", "implemented", "deferred"]),
        "estimated_cost": st.column_config.NumberColumn("Est. Cost $", format="$%.0f"),
        "linked_task_title": st.column_config.TextColumn("Linked Task", disabled=True),
    }
)

if st.button("💾 Save QOL Changes", type="primary"):
    conn = get_connection()
    for _, row in edited_df.iterrows():
        conn.execute("""UPDATE qol_ideas 
                        SET status=?, estimated_cost=?, notes=?, linked_task_id=?
                        WHERE id=?""",
                     (row['status'], row['estimated_cost'], row['notes'], 
                      row.get('linked_task_id'), int(row['id'])))
    conn.commit()
    conn.close()
    st.success("QOL tracker updated!")
    st.rerun()

# ====================== BIDIRECTIONAL CONVERTER ======================
with st.expander("➕ Turn QOL Idea into Task (or link existing task)", expanded=True):
    colA, colB = st.columns(2)
    with colA:
        selected = st.selectbox("Choose QOL Idea", df['description'].tolist(), key="qol_select")
        idea = df[df['description'] == selected].iloc[0]
        
        if st.button("✅ Convert to New Task + Link", type="primary", use_container_width=True):
            conn = get_connection()
            phase_id = idea['linked_phase_id'] or 1
            
            conn.execute("""INSERT INTO tasks 
                (phase_id, title, description, planned_start, planned_end, due_date, status, notes)
                VALUES (?,?,?,?,?,?,?,?)""",
                (phase_id, f"QOL: {idea['category']}", idea['description'],
                 "2026-04-22", "2026-05-15", "2026-05-15", "not_started", 
                 f"From QOL: {idea['category']}"))
            
            new_task_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            
            # Link both directions
            conn.execute("UPDATE qol_ideas SET linked_task_id = ? WHERE id = ?", 
                        (new_task_id, idea['id']))
            conn.commit()
            conn.close()
            st.success(f"✅ Task created and linked to QOL idea!")
            st.rerun()

    with colB:
        # Quick link to existing task
        conn = get_connection()
        tasks = pd.read_sql("SELECT id, title FROM tasks WHERE status != 'completed'", conn)
        conn.close()
        
        if not tasks.empty:
            task_to_link = st.selectbox("Or link to existing task", 
                                      tasks['title'].tolist(), key="link_existing")
            task_id = tasks[tasks['title'] == task_to_link]['id'].iloc[0]
            
            if st.button("🔗 Link Selected Task to this QOL", use_container_width=True):
                conn = get_connection()
                conn.execute("UPDATE qol_ideas SET linked_task_id = ? WHERE id = ?", 
                            (task_id, idea['id']))
                conn.commit()
                conn.close()
                st.success("✅ QOL idea linked to task!")
                st.rerun()

# Optional unlink
if not df.empty and df['linked_task_id'].notna().any():
    with st.expander("🔓 Unlink QOL from Task"):
        unlink_id = st.selectbox("Unlink which QOL?", 
                                df[df['linked_task_id'].notna()]['description'].tolist())
        if st.button("Unlink"):
            conn = get_connection()
            qol_id = df[df['description'] == unlink_id]['id'].iloc[0]
            conn.execute("UPDATE qol_ideas SET linked_task_id = NULL WHERE id = ?", (qol_id,))
            conn.commit()
            conn.close()
            st.success("Unlinked!")
            st.rerun()

st.subheader("Recently Added / Linked QOL Tasks")
conn = get_connection()
recent = pd.read_sql("""
    SELECT q.category, q.description, t.title as task_title, q.status 
    FROM qol_ideas q 
    LEFT JOIN tasks t ON q.linked_task_id = t.id 
    WHERE q.linked_task_id IS NOT NULL 
    ORDER BY q.id DESC LIMIT 8
""", conn)
st.dataframe(recent, use_container_width=True, hide_index=True)
conn.close()
import streamlit as st
import pandas as pd
from db.db_utils import get_project_config, get_connection, row_to_dict, get_current_focus
from utils.charts import create_budget_pie, create_spend_line, create_gantt
from utils.alerts import get_all_alerts
from datetime import date
from utils.helpers import save_uploaded_file
from utils.sidebar import render_sidebar
from db.db_utils import init_db

if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

st.set_page_config(page_title="Crowe's Nest Build", layout="wide", page_icon="🏠")

# Hide default Streamlit page navigation + your custom dark theme
st.markdown("""
<style>
    [data-testid="stSidebarNav"] { display: none; }
    .stApp { background-color: #0f1c12; color: #e8f5e9; }
    .stButton>button { background-color: #8B0000; color: white; border-radius: 8px; }
    h1, h2, h3 { color: #e8f5e9; }
    .metric-label { color: #90EE90; }
</style>
""", unsafe_allow_html=True)

# ====================== SHARED SIDEBAR (mobile-optimized + consistent) ======================
render_sidebar()

config = get_project_config()

# ====================== ALERTS ======================
alerts = get_all_alerts()
if alerts:
    st.subheader("🚨 Current Alerts")
    for alert in alerts:
        st.info(alert["message"])

# Specific permits due soon
conn = get_connection()
due_soon = pd.read_sql("""
    SELECT name, required_date
    FROM permits
    WHERE status = 'pending'
      AND required_date <= date('now','+14 days')
    ORDER BY required_date
""", conn)
conn.close()
if not due_soon.empty:
    st.caption("**Permits due soon (within 2 weeks):**")
    st.dataframe(due_soon, use_container_width=True, hide_index=True)

# ====================== METRICS ======================
conn = get_connection()
spent = pd.read_sql("SELECT COALESCE(SUM(amount),0) as spent FROM expenses", conn).iloc[0]['spent']
conn.close()
col1, col2, col3, col4 = st.columns(4)
with col1: st.metric("Total Budget", f"${config['total_budget']:,.0f}")
with col2: st.metric("Spent", f"${spent:,.0f}")
with col3: st.metric("Remaining", f"${config['total_budget']-spent:,.0f}")

# Realistic progress (your custom logic)
conn = get_connection()
completed = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='completed' AND phase_id > 1").fetchone()[0]
total_remaining = conn.execute("SELECT COUNT(*) FROM tasks WHERE phase_id > 1").fetchone()[0]
progress = int((completed / total_remaining * 100)) if total_remaining > 0 else 0
conn.close()
with col4: st.metric("Progress", f"{progress}%")
st.progress(progress / 100)

# ====================== URGENT ITEMS CARDS ======================
st.subheader("🚨 Urgent Items")
colU1, colU2, colU3 = st.columns(3)
current_focus = get_current_focus()
with colU1:
    if current_focus["task"]:
        st.error(f"**Overdue / Current Task**\n{current_focus['task']['title']}\nDue: {current_focus['task']['due_date']}")
    else:
        st.success("No pending tasks")
with colU2:
    if current_focus["permit"]:
        st.warning(f"**Permit Due Soon**\n{current_focus['permit']['name']}\nDue: {current_focus['permit']['required_date']}")
    else:
        st.success("All permits clear")
with colU3:
    conn = get_connection()
    next_qol = conn.execute("""
        SELECT category, description
        FROM qol_ideas
        WHERE status = 'planned'
        ORDER BY estimated_cost LIMIT 1
    """).fetchone()
    conn.close()
    if next_qol:
        st.info(f"**Next QOL Idea**\n{next_qol['category']}: {next_qol['description'][:60]}...")
    else:
        st.success("All QOL ideas implemented")

# ====================== QUICK PROGRESS PHOTO LOG + TASK COMPLETION ======================
st.subheader("📸 Quick Progress Photo Log + Task Completion")
st.caption("Mark current task done • Attach photo • Auto-links everything")
current_focus = get_current_focus()
col1, col2 = st.columns([2, 1])
with col1:
    if current_focus["task"]:
        st.metric("Current Task", current_focus["task"]["title"],
                 f"Due {current_focus['task']['due_date']}")
        
        if st.button("✅ Mark Current Task as Completed", type="primary", use_container_width=True):
            conn = get_connection()
            conn.execute("""
                UPDATE tasks
                SET status = 'completed',
                    completed_date = date('now')
                WHERE id = ?
            """, (current_focus["task"]["id"],))
            conn.commit()
            conn.close()
            st.success(f"✅ Task marked complete: {current_focus['task']['title']}")
            st.rerun()
    else:
        st.success("No pending tasks!")
with col2:
    uploaded_photo = st.file_uploader("Attach progress photo",
                                     type=["jpg", "jpeg", "png"],
                                     key="dash_photo_quick")
    
    if uploaded_photo and current_focus["task"]:
        notes = st.text_area("Photo notes",
                            value=f"Progress on {current_focus['task']['title']}",
                            height=80)
        
        if st.button("📸 Save Photo & Link to Task", type="secondary", use_container_width=True):
            file_url = save_uploaded_file(uploaded_photo)
            conn = get_connection()
            conn.execute("""INSERT INTO receipts
                (file_path, original_filename, upload_date, notes, file_category,
                 linked_task_id, document_type)
                VALUES (?,?,?,?,?,?,?)""",
                (file_url, uploaded_photo.name, date.today().strftime("%Y-%m-%d"),
                 notes, "photo", current_focus["task"]["id"], "document"))
            conn.commit()
            conn.close()
            st.success("Photo saved and linked to task!")
            st.rerun()

# ====================== CHARTS ======================
st.subheader("Budget Breakdown")
st.plotly_chart(create_budget_pie(), use_container_width=True)

st.subheader("Spending Over Time")
st.plotly_chart(create_spend_line(), use_container_width=True)

st.subheader("Full Gantt (Tasks + Permits)")
st.plotly_chart(create_gantt(), use_container_width=True)

# ====================== CURRENT + NEXT FOCUS ======================
conn = get_connection()
c = conn.cursor()
c.execute("""
    SELECT 'Task' as Type, title as Name, due_date as Due
    FROM tasks WHERE status != 'completed'
    ORDER BY planned_start ASC LIMIT 1
""")
current_task = row_to_dict(c.fetchone())
c.execute("""
    SELECT 'Permit' as Type, name as Name, required_date as Due
    FROM permits WHERE status = 'pending'
    ORDER BY required_date ASC LIMIT 1
""")
current_permit = row_to_dict(c.fetchone())
if current_task and current_permit:
    current_item = current_task if current_task['Due'] <= current_permit['Due'] else current_permit
elif current_task:
    current_item = current_task
elif current_permit:
    current_item = current_permit
else:
    current_item = None

if current_item:
    st.subheader(f"📍 **Current**: {current_item['Name']} ({current_item['Type']}) — Due {current_item['Due']}")
    
    c.execute("""
        SELECT 'Task' as Type, title as Name, due_date as Due
        FROM tasks WHERE status != 'completed'
        ORDER BY planned_start ASC LIMIT 1 OFFSET 1
    """)
    next_task = row_to_dict(c.fetchone())
    c.execute("""
        SELECT 'Permit' as Type, name as Name, required_date as Due
        FROM permits WHERE status = 'pending'
        ORDER BY required_date ASC LIMIT 1 OFFSET 1
    """)
    next_permit = row_to_dict(c.fetchone())
    
    if next_task and next_permit:
        next_item = next_task if next_task['Due'] <= next_permit['Due'] else next_permit
    elif next_task:
        next_item = next_task
    elif next_permit:
        next_item = next_permit
    else:
        next_item = None
    
    if next_item:
        st.info(f"➡️ **Next**: {next_item['Name']} ({next_item['Type']}) — Due {next_item['Due']}")
conn.close()

st.caption("Crowe's Nest Build • Local-first Dashboard")
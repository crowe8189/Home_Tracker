import streamlit as st
from db.db_utils import init_db, get_project_config, get_connection, row_to_dict
import pandas as pd
from utils.alerts import get_all_alerts
from datetime import date

if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

st.set_page_config(page_title="Crowe's Nest Build", page_icon="🏠", layout="wide")

config = get_project_config()

with st.sidebar:
    st.title("🐦‍⬛ Crowe's Nest Build")
    st.caption(f"📍 {config['address']}\n🗓️ Started {config['start_date']}")
    st.divider()
    st.metric("Total Budget", f"${config['total_budget']:,.0f}")
    conn = get_connection()
    spent = conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0]
    conn.close()
    st.metric("Spent", f"${spent:,.0f}", f"Remaining ${config['total_budget']-spent:,.0f}")

st.title(f"🏠 {config['name']} — Current Status")
st.caption(f"📍 {config['address']} | Started {config['start_date']}")

# Metrics
col1, col2, col3, col4 = st.columns(4)
with col1: st.metric("Total Budget", f"${config['total_budget']:,.0f}")
with col2: st.metric("Spent", f"${spent:,.0f}")
with col3: st.metric("Remaining", f"${config['total_budget']-spent:,.0f}")
with col4:
    conn = get_connection()
    completed = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='completed'").fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    progress = int((completed / total * 100)) if total > 0 else 0
    st.metric("Progress", f"{progress}%")
    conn.close()
st.progress(progress / 100)

# Summary alerts only
alerts = get_all_alerts()
if alerts:
    st.subheader("🚨 Current Alerts")
    for alert in alerts:
        st.info(alert["message"])

# Current + Next focus (now safe with Turso)
conn = get_connection()

c = conn.cursor()
c.execute("""
    SELECT 'Task' as Type, title as Name, due_date as Due 
    FROM tasks WHERE status != 'completed' 
    ORDER BY planned_start ASC LIMIT 1
""")
current_task = row_to_dict(c, c.fetchone())

c.execute("""
    SELECT 'Permit' as Type, name as Name, required_date as Due 
    FROM permits WHERE status = 'pending' 
    ORDER BY required_date ASC LIMIT 1
""")
current_permit = row_to_dict(c, c.fetchone())

# Pick the earliest one
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

    # Next item
    c.execute("""
        SELECT 'Task' as Type, title as Name, due_date as Due 
        FROM tasks WHERE status != 'completed' 
        ORDER BY planned_start ASC LIMIT 1 OFFSET 1
    """)
    next_task = row_to_dict(c, c.fetchone())

    c.execute("""
        SELECT 'Permit' as Type, name as Name, required_date as Due 
        FROM permits WHERE status = 'pending' 
        ORDER BY required_date ASC LIMIT 1 OFFSET 1
    """)
    next_permit = row_to_dict(c, c.fetchone())

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

st.caption("Crowe's Nest Build v1.0 • Fully shared on Turso + Supabase")
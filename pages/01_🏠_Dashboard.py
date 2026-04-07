import streamlit as st
import pandas as pd
from db.db_utils import get_project_config, get_connection
from utils.charts import create_budget_pie, create_spend_line, create_gantt
from utils.alerts import get_all_alerts
from datetime import date

st.set_page_config(page_title="Crowe's Nest Build", layout="wide", page_icon="🏠")

config = get_project_config()
st.title(f"🏠 {config['name']} — Dashboard")

# Summary alerts only
alerts = get_all_alerts()
if alerts:
    st.subheader("🚨 Current Alerts")
    for alert in alerts:
        st.info(alert["message"])

# Metrics + progress
conn = get_connection()
spent = pd.read_sql("SELECT COALESCE(SUM(amount),0) as spent FROM expenses", conn).iloc[0]['spent']
conn.close()
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

st.subheader("Budget Breakdown")
st.plotly_chart(create_budget_pie(), use_container_width=True)

st.subheader("Spending Over Time")
st.plotly_chart(create_spend_line(), use_container_width=True)

st.subheader("Full Gantt (Tasks + Permits)")
st.plotly_chart(create_gantt(), use_container_width=True)

# Current + Next focus (FIXED SQL - identical to app.py)
conn = get_connection()

current_task = conn.execute("""
    SELECT 'Task' as Type, title as Name, due_date as Due 
    FROM tasks WHERE status != 'completed' 
    ORDER BY planned_start ASC LIMIT 1
""").fetchone()

current_permit = conn.execute("""
    SELECT 'Permit' as Type, name as Name, required_date as Due 
    FROM permits WHERE status = 'pending' 
    ORDER BY required_date ASC LIMIT 1
""").fetchone()

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

    next_task = conn.execute("""
        SELECT 'Task' as Type, title as Name, due_date as Due 
        FROM tasks WHERE status != 'completed' 
        ORDER BY planned_start ASC LIMIT 1 OFFSET 1
    """).fetchone()

    next_permit = conn.execute("""
        SELECT 'Permit' as Type, name as Name, required_date as Due 
        FROM permits WHERE status = 'pending' 
        ORDER BY required_date ASC LIMIT 1 OFFSET 1
    """).fetchone()

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
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from db.db_utils import get_connection
from datetime import timedelta
import streamlit as st

def create_gantt():
    """Responsive Gantt – much better on mobile (smaller height, tighter margins, better fonts)"""
    conn = get_connection()

    # === TASKS (keep phase order) ===
    df_tasks = pd.read_sql("""
        SELECT 
            t.id,
            t.title as Task, 
            p.name as Phase, 
            t.planned_start as Start, 
            t.planned_end as Finish, 
            t.status as Status,
            'Task' as Type,
            GROUP_CONCAT(pr.title) as Blocked_By
        FROM tasks t 
        JOIN phases p ON t.phase_id = p.id 
        LEFT JOIN task_dependencies d ON t.id = d.task_id 
        LEFT JOIN tasks pr ON d.prerequisite_id = pr.id 
        GROUP BY t.id
        ORDER BY p.order_num, t.planned_start
    """, conn)

    # === PERMITS (forced to bottom) ===
    df_permits = pd.read_sql("""
        SELECT 
            name as Task,
            'Permits & Inspections' as Phase,
            required_date as Start,
            COALESCE(issued_date, required_date) as Finish,
            CASE 
                WHEN issued_date IS NOT NULL OR status = 'approved' THEN 'completed'
                ELSE status 
            END as Status,
            'Permit' as Type,
            NULL as Blocked_By
        FROM permits
        ORDER BY required_date
    """, conn)

    conn.close()

    # Combine: Tasks first, then Permits
    df = pd.concat([df_tasks, df_permits], ignore_index=True)

    if df.empty:
        fig = go.Figure()
        fig.update_layout(title="No tasks or permits yet", height=400)
        return fig

    # Convert dates
    df['Start'] = pd.to_datetime(df['Start'], errors='coerce')
    df['Finish'] = pd.to_datetime(df['Finish'], errors='coerce')

    # Visible duration for pending permits
    mask = (df['Type'] == 'Permit') & (df['Status'] == 'pending')
    df.loc[mask, 'Finish'] = df.loc[mask, 'Start'] + pd.Timedelta(days=14)

    # Identify blocked tasks
    df['Blocked_By'] = df['Blocked_By'].fillna('')
    df['is_blocked'] = df['Blocked_By'].apply(lambda x: bool(x) and x.strip() != '')

    # Color map
    color_map = {
        'completed': '#32CD32',
        'in_progress': "#190AEC",
        'not_started': "#ABCC17",
        'delayed': '#FF0000',
        'pending': '#BA55D3',
        'approved': '#32CD32',
        'denied': '#FF0000'
    }

    # === RESPONSIVE HEIGHT FOR MOBILE ===
    # Auto-detect mobile based on screen width (works in PWA and browser)
    is_mobile = st.session_state.get("mobile", False) or st.session_state.get("width", 1200) < 768
    height = 520 if is_mobile else 720   # 520px on phone, 720px on desktop

    fig = px.timeline(
        df,
        x_start="Start",
        x_end="Finish",
        y="Task",
        color="Status",
        color_discrete_map=color_map,
        title="Project Gantt – Tasks + Permits & Inspections",
        hover_data=["Phase", "Type", "Blocked_By"],
        height=height,
    )

    fig.update_layout(
        autosize=True,
        margin=dict(l=10, r=10, t=50, b=40),
        xaxis_title="Timeline",
        yaxis_title="",
        legend_title="Status",
        bargap=0.25,
        xaxis=dict(tickformat="%b %d", tickangle=-45),
        font=dict(size=11 if is_mobile else 12),
    )

    # FORCE correct vertical order: Tasks on top, Permits at bottom
    task_list = df[df['Type'] == 'Task']['Task'].tolist()
    permit_list = df[df['Type'] == 'Permit']['Task'].tolist()
    fig.update_yaxes(
        categoryorder="array",
        categoryarray=task_list + permit_list
    )

    return fig


# === Unchanged helper charts ===
def create_budget_pie():
    conn = get_connection()
    df = pd.read_sql("SELECT name, planned_amount as value FROM budget_categories", conn)
    conn.close()
    fig = px.pie(df, names='name', values='value', title='Budget Allocation by Category')
    fig.update_traces(textinfo='percent+label')
    return fig


def create_spend_line():
    conn = get_connection()
    df = pd.read_sql("SELECT date, SUM(amount) as spend FROM expenses GROUP BY date ORDER BY date", conn)
    conn.close()
    if df.empty:
        df = pd.DataFrame({'date': [pd.Timestamp.now().date()], 'spend': [0]})
    fig = px.line(df, x='date', y='spend', title='Cumulative Spending Over Time', markers=True)
    return fig
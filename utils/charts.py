import plotly.express as px
import pandas as pd
from db.db_utils import get_connection
from datetime import timedelta

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

def create_gantt():
    """Gantt with full-width auto-scaling + monthly x-axis + visible permit bars"""
    conn = get_connection()

    # Tasks
    df_tasks = pd.read_sql("""
        SELECT 
            t.title as Task, 
            p.name as Phase, 
            t.planned_start as Start, 
            t.planned_end as Finish, 
            t.status as Status,
            'Task' as Type
        FROM tasks t 
        JOIN phases p ON t.phase_id = p.id 
        ORDER BY p.order_num, t.planned_start
    """, conn)

    # Permits
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
            'Permit' as Type
        FROM permits
    """, conn)

    conn.close()

    # Combine
    df = pd.concat([df_tasks, df_permits], ignore_index=True)

    if df.empty:
        return px.timeline(title="No tasks or permits yet")

    # Safe date conversion
    df['Start'] = pd.to_datetime(df['Start'], errors='coerce')
    df['Finish'] = pd.to_datetime(df['Finish'], errors='coerce')

    # Visible duration for pending permits
    mask = (df['Type'] == 'Permit') & (df['Status'] == 'pending')
    df.loc[mask, 'Finish'] = df.loc[mask, 'Start'] + pd.Timedelta(days=14)

    # Color map
    color_map = {
        'not_started': '#87CEEB',
        'in_progress': '#FFA500',
        'completed':   '#32CD32',
        'delayed':     '#FF0000',
        'pending':     '#BA55D3',
        'approved':    '#32CD32',
        'denied':      '#FF0000'
    }

    fig = px.timeline(
        df,
        x_start="Start",
        x_end="Finish",
        y="Task",
        color="Status",
        color_discrete_map=color_map,
        title="Project Gantt – Tasks + Permits & Inspections",
        hover_data=["Phase", "Type"],
        height=750
    )

    # === FULL-WIDTH AUTO-SCALE + EVERY MONTH ON X-AXIS ===
    fig.update_xaxes(
        dtick="M1",           # Show every single month
        tickformat="%b %Y",   # Apr 2026, May 2026, etc.
        tickangle=0,
        showgrid=True,
        automargin=True
    )

    fig.update_layout(
        autosize=True,        # ← Key for auto-scaling
        width=None,           # ← Let Streamlit control full width
        height=750,
        xaxis_title="Timeline",
        yaxis_title="",
        legend_title="Status",
        bargap=0.15,
        margin=dict(l=40, r=40, t=60, b=40)  # clean padding
    )

    fig.update_yaxes(categoryorder="total ascending")

    return fig
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st
from db.db_utils import get_connection, read_df


def create_gantt():
    """Responsive Gantt chart — works in both local and cloud (Turso) mode."""
    conn = get_connection()

    df_tasks = read_df("""
        SELECT
            t.id,
            t.title  AS Task,
            p.name   AS Phase,
            t.planned_start AS Start,
            t.planned_end   AS Finish,
            t.status        AS Status,
            'Task'          AS Type,
            GROUP_CONCAT(pr.title) AS Blocked_By
        FROM tasks t
        JOIN phases p ON t.phase_id = p.id
        LEFT JOIN task_dependencies d  ON t.id = d.task_id
        LEFT JOIN tasks pr             ON d.prerequisite_id = pr.id
        GROUP BY t.id
        ORDER BY p.order_num, t.planned_start
    """, conn)

    df_permits = read_df("""
        SELECT
            name AS Task,
            'Permits & Inspections' AS Phase,
            required_date AS Start,
            COALESCE(issued_date, required_date) AS Finish,
            CASE
                WHEN issued_date IS NOT NULL OR status = 'approved' THEN 'completed'
                ELSE status
            END AS Status,
            'Permit' AS Type,
            NULL AS Blocked_By
        FROM permits
        ORDER BY required_date
    """, conn)

    conn.close()

    df = pd.concat([df_tasks, df_permits], ignore_index=True)

    if df.empty:
        fig = go.Figure()
        fig.update_layout(title="No tasks or permits yet", height=400)
        return fig

    df["Start"]  = pd.to_datetime(df["Start"],  errors="coerce")
    df["Finish"] = pd.to_datetime(df["Finish"], errors="coerce")

    # Give pending permits a 14-day visible bar
    mask = (df["Type"] == "Permit") & (df["Status"] == "pending")
    df.loc[mask, "Finish"] = df.loc[mask, "Start"] + pd.Timedelta(days=14)

    df["Blocked_By"] = df["Blocked_By"].fillna("")

    color_map = {
        "completed":   "#32CD32",
        "in_progress": "#190AEC",
        "not_started": "#ABCC17",
        "delayed":     "#FF0000",
        "pending":     "#BA55D3",
        "approved":    "#32CD32",
        "denied":      "#FF0000",
    }

    # Mobile: use a shorter chart height via CSS rather than session_state guessing
    fig = px.timeline(
        df,
        x_start="Start",
        x_end="Finish",
        y="Task",
        color="Status",
        color_discrete_map=color_map,
        title="Project Gantt – Tasks + Permits & Inspections",
        hover_data=["Phase", "Type", "Blocked_By"],
        height=680,
    )

    fig.update_layout(
        autosize=True,
        margin=dict(l=5, r=5, t=45, b=35),
        xaxis_title="",
        yaxis_title="",
        legend_title="Status",
        bargap=0.22,
        xaxis=dict(tickformat="%b %d", tickangle=-40),
        font=dict(size=11),
    )

    task_list   = df[df["Type"] == "Task"]["Task"].tolist()
    permit_list = df[df["Type"] == "Permit"]["Task"].tolist()
    fig.update_yaxes(categoryorder="array", categoryarray=task_list + permit_list)

    return fig


def create_budget_pie():
    conn = get_connection()
    df = read_df("SELECT name, planned_amount AS value FROM budget_categories", conn)
    conn.close()
    fig = px.pie(df, names="name", values="value", title="Budget Allocation by Category")
    fig.update_traces(textinfo="percent+label")
    return fig


def create_spend_line():
    conn = get_connection()
    df = read_df(
        "SELECT date, SUM(amount) AS spend FROM expenses GROUP BY date ORDER BY date",
        conn,
    )
    conn.close()
    if df.empty:
        df = pd.DataFrame({"date": [pd.Timestamp.now().date()], "spend": [0]})
    df["spend"] = pd.to_numeric(df["spend"], errors="coerce").cumsum()
    fig = px.line(df, x="date", y="spend", title="Cumulative Spending Over Time", markers=True)
    return fig

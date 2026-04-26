import streamlit as st
import pandas as pd
from datetime import date, timedelta
import calendar

st.set_page_config(page_title="Checklist", layout="wide", page_icon="✅")

from db.db_utils import get_connection, init_db, read_df
from utils.sidebar import render_sidebar

if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

render_sidebar()
st.title("✅ Smart Checklist Generator")
st.caption("Auto-generate phase-specific checklists and push items directly into your task list")

CHECKLISTS = {
    "1. Site Preparation": [
        "Clear trees and debris",
        "Install silt fence and erosion control",
        "Grade lot for drainage",
        "Install temporary power pole",
        "Mark utility lines (call 811)",
        "Secure septic permit (applying this week)",
    ],
    "2. Foundation": [
        "Dig footings per engineering plans",
        "Install rebar and vapor barrier",
        "Pour concrete foundation",
        "Allow proper cure time (7 days min)",
        "Backfill and compact",
        "Install termite treatment",
    ],
    "3. Framing": [
        "Frame walls and floors",
        "Install roof trusses",
        "Sheathe exterior walls",
        "Install house wrap",
        "Verify rough opening sizes for windows",
    ],
    "4. Rough-ins": [
        "Rough plumbing (owner coord)",
        "Rough electrical materials (owner install)",
        "Rough HVAC ductwork",
        "Install bath vents and exhausts",
        "Get rough-in inspection",
    ],
    "5. Roofing": [
        "Install underlayment",
        "Lay shingles and ridge vent",
        "Flash all penetrations",
        "Install gutters and downspouts",
    ],
    "6. Exterior Finishes": [
        "Install windows and exterior doors",
        "Apply house siding",
        "Paint exterior trim",
        "Install garage doors",
    ],
    "7. Insulation & Drywall": [
        "Install insulation (walls + attic)",
        "Hang drywall",
        "Tape, mud, and sand",
        "Install vapor barrier where required",
    ],
    "8. Interior Finishes": [
        "Install trim and baseboards",
        "Paint interior walls",
        "Install interior doors",
        "Hang cabinets and vanities",
    ],
    "9. Fixtures & Appliances": [
        "Install lighting fixtures (owner electrical)",
        "Set plumbing fixtures",
        "Install kitchen appliances",
        "Final electrical trim-out",
    ],
    "10. Landscaping & Punch List": [
        "Final grading and driveway",
        "Seed or sod lawn",
        "Install landscaping plants",
        "Complete punch list items",
    ],
}


def end_of_month(d: date) -> str:
    """Return the last day of d's month as a YYYY-MM-DD string."""
    last_day = calendar.monthrange(d.year, d.month)[1]
    return d.replace(day=last_day).strftime("%Y-%m-%d")


phase_name = st.selectbox("Select Phase", list(CHECKLISTS.keys()), index=0)

st.subheader(f"Checklist for {phase_name}")
items = CHECKLISTS[phase_name]

selected_items = []
for item in items:
    if st.checkbox(item, key=item):
        selected_items.append(item)

col1, col2 = st.columns(2)
with col1:
    if st.button("➕ Add Selected Items to Tasks", type="primary", use_container_width=True):
        if selected_items:
            today = date.today()
            conn  = get_connection()
            phase_row = conn.execute(
                "SELECT id FROM phases WHERE name=?", (phase_name,)
            ).fetchone()
            if phase_row:
                phase_id = phase_row[0]
                for title in selected_items:
                    conn.execute("""
                        INSERT INTO tasks
                            (phase_id, title, description, planned_start, planned_end,
                             due_date, status, notes)
                        VALUES (?,?,?,?,?,?,?,?)
                    """, (
                        phase_id, title, "From smart checklist",
                        today.strftime("%Y-%m-%d"),
                        end_of_month(today),
                        today.strftime("%Y-%m-%d"),
                        "not_started", "Added via checklist",
                    ))
                conn.commit()
                st.success(f"✅ {len(selected_items)} task(s) added to Roadmap!")
            else:
                st.error(f"Phase '{phase_name}' not found in database.")
            conn.close()
            st.rerun()
        else:
            st.warning("Select at least one item")

with col2:
    if st.button("🔄 Regenerate Checklist", use_container_width=True):
        st.rerun()

with st.expander("✏️ Add Custom Checklist Item"):
    custom = st.text_input("Custom task for this phase")
    if st.button("Add Custom") and custom:
        today = date.today()
        conn  = get_connection()
        phase_row = conn.execute(
            "SELECT id FROM phases WHERE name=?", (phase_name,)
        ).fetchone()
        if phase_row:
            conn.execute("""
                INSERT INTO tasks
                    (phase_id, title, description, planned_start, planned_end,
                     due_date, status, notes)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                phase_row[0], custom, "Custom checklist item",
                today.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"),
                today.strftime("%Y-%m-%d"), "not_started", "Custom",
            ))
            conn.commit()
            st.success("Custom task added!")
        conn.close()
        st.rerun()

st.subheader("Recently Added Checklist Tasks")
conn = get_connection()
recent = read_df(
    "SELECT title, phase_id, status FROM tasks WHERE notes LIKE '%checklist%' ORDER BY id DESC LIMIT 10",
    conn,
)
conn.close()
st.dataframe(recent, use_container_width=True, hide_index=True)

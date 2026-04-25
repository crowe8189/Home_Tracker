import streamlit as st
import pandas as pd
from db.db_utils import get_connection
from datetime import date
from utils.sidebar import render_sidebar
render_sidebar()
st.title("✅ Smart Checklist Generator")
st.caption("Auto-generate phase-specific checklists and push items directly into your task list")

# Predefined checklists per phase (tailored to your build)
CHECKLISTS = {
    "1. Site Preparation": [
        "Clear trees and debris",
        "Install silt fence and erosion control",
        "Grade lot for drainage",
        "Install temporary power pole",
        "Mark utility lines (call 811)",
        "Secure septic permit (applying this week)"
    ],
    "2. Foundation": [
        "Dig footings per engineering plans",
        "Install rebar and vapor barrier",
        "Pour concrete foundation",
        "Allow proper cure time (7 days min)",
        "Backfill and compact",
        "Install termite treatment"
    ],
    "3. Framing": [
        "Frame walls and floors",
        "Install roof trusses",
        "Sheathe exterior walls",
        "Install house wrap",
        "Verify rough opening sizes for windows"
    ],
    "4. Rough-ins": [
        "Rough plumbing (owner coord)",
        "Rough electrical materials (owner install)",
        "Rough HVAC ductwork",
        "Install bath vents and exhausts",
        "Get rough-in inspection"
    ],
    "5. Roofing": [
        "Install underlayment",
        "Lay shingles and ridge vent",
        "Flash all penetrations",
        "Install gutters and downspouts"
    ],
    "6. Exterior Finishes": [
        "Install windows and exterior doors",
        "Apply house siding",
        "Paint exterior trim",
        "Install garage doors"
    ],
    "7. Insulation & Drywall": [
        "Install insulation (walls + attic)",
        "Hang drywall",
        "Tape, mud, and sand",
        "Install vapor barrier where required"
    ],
    "8. Interior Finishes": [
        "Install trim and baseboards",
        "Paint interior walls",
        "Install interior doors",
        "Hang cabinets and vanities"
    ],
    "9. Fixtures & Appliances": [
        "Install lighting fixtures (owner electrical)",
        "Set plumbing fixtures",
        "Install kitchen appliances",
        "Final electrical trim-out"
    ],
    "10. Landscaping & Punch List": [
        "Final grading and driveway",
        "Seed or sod lawn",
        "Install landscaping plants",
        "Complete punch list items"
    ]
}

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
            conn = get_connection()
            # Get phase_id
            phase_id = conn.execute("SELECT id FROM phases WHERE name=?", (phase_name,)).fetchone()[0]
            
            for title in selected_items:
                conn.execute("""INSERT INTO tasks 
                    (phase_id, title, description, planned_start, planned_end, due_date, status, notes)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (phase_id, title, "From smart checklist", date.today().strftime("%Y-%m-%d"), 
                     (date.today().replace(day=1) + pd.offsets.MonthEnd(1)).strftime("%Y-%m-%d"),
                     date.today().strftime("%Y-%m-%d"), "not_started", "Added via checklist"))
            conn.commit()
            conn.close()
            st.success(f"✅ {len(selected_items)} tasks added to Roadmap!")
            st.rerun()
        else:
            st.warning("Select at least one item")

with col2:
    if st.button("🔄 Regenerate Checklist", use_container_width=True):
        st.rerun()

# Optional custom item
with st.expander("✏️ Add Custom Checklist Item"):
    custom = st.text_input("Custom task for this phase")
    if st.button("Add Custom") and custom:
        conn = get_connection()
        phase_id = conn.execute("SELECT id FROM phases WHERE name=?", (phase_name,)).fetchone()[0]
        conn.execute("""INSERT INTO tasks 
            (phase_id, title, description, planned_start, planned_end, due_date, status, notes)
            VALUES (?,?,?,?,?,?,?,?)""",
            (phase_id, custom, "Custom checklist item", date.today().strftime("%Y-%m-%d"), 
             date.today().strftime("%Y-%m-%d"), date.today().strftime("%Y-%m-%d"), "not_started", "Custom"))
        conn.commit()
        conn.close()
        st.success("Custom task added!")
        st.rerun()

st.subheader("Recently Added Checklist Tasks")
conn = get_connection()
recent = pd.read_sql("SELECT title, phase_id, status FROM tasks WHERE notes LIKE '%checklist%' ORDER BY id DESC LIMIT 10", conn)
st.dataframe(recent, use_container_width=True, hide_index=True)
conn.close()
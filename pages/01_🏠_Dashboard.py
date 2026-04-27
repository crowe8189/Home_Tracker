import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="Crowe's Nest Build", layout="wide", page_icon="🏠")

from db.db_utils import (
    get_project_config, get_connection,
    get_current_focus, init_db, read_df, is_cloud_mode,
)
from utils.charts import create_budget_pie, create_spend_line, create_gantt
from utils.alerts import get_all_alerts
from utils.sidebar import render_sidebar, quick_log_dialog

if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

# Dark construction theme + FAB CSS + metric responsive grid
st.markdown("""
<style>
    .stApp { background-color: #0f1c12; color: #e8f5e9; }
    .stButton > button { background-color: #8B0000; color: white; border-radius: 8px; }
    h1, h2, h3 { color: #e8f5e9; }

    /* ── Quick Log pill FAB — fixed bottom-right on mobile ─────────── */
    @media (max-width: 768px) {
        [data-testid="stButton"][data-fab="true"] {
            position: fixed !important;
            bottom: calc(72px + env(safe-area-inset-bottom, 0px)) !important;
            right: 16px !important;
            z-index: 999 !important;
            width: auto !important;
            margin: 0 !important;
        }
        [data-testid="stButton"][data-fab="true"] button {
            min-width: 140px !important;
            height: 48px !important;
            border-radius: 24px !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5) !important;
            font-size: 1rem !important;
        }
    }

    /* ── 4-metric row wraps to 2×2 on narrow screens ───────────────── */
    @media (max-width: 640px) {
        [data-testid="column"]:has([data-testid="stMetric"]) {
            min-width: 48% !important;
            flex: 0 0 48% !important;
        }
    }
</style>
<script>
(function () {
    /* Tag the Quick Log button so CSS can float it as a FAB on mobile */
    function tagFAB() {
        var btns = document.querySelectorAll('button[kind="primary"]');
        for (var i = 0; i < btns.length; i++) {
            if (btns[i].innerText.indexOf('Quick Log') !== -1) {
                var wrap = btns[i].closest('[data-testid="stButton"]');
                if (wrap) { wrap.setAttribute('data-fab', 'true'); }
                return;
            }
        }
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', tagFAB);
    } else {
        tagFAB();
    }
    new MutationObserver(tagFAB).observe(document.body, { childList: true, subtree: true });
})();
</script>
""", unsafe_allow_html=True)

render_sidebar()

config = get_project_config()

# ── Storage health banner (cloud mode, missing Supabase secrets) ─────────
if is_cloud_mode():
    _missing = [k for k in ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_BUCKET")
                if k not in st.secrets]
    if _missing:
        st.warning(
            f"⚠️ **File uploads disabled** — missing secrets: {', '.join(_missing)}. "
            "Go to ⚙️ Settings → Storage Diagnostics for help."
        )

# ── Quick Log FAB (floats on mobile, inline on desktop) ──────────────────
if st.button("➕ Quick Log", type="primary", key="fab_ql",
             help="Capture a photo or receipt on site"):
    quick_log_dialog()

# ── Alerts ───────────────────────────────────────────────────────────────
for alert in get_all_alerts():
    st.info(alert["message"])

# ── Bulk DB fetch (single connection) ────────────────────────────────────
conn = get_connection()

spent_row = conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()
spent = spent_row[0] if spent_row else 0

completed = conn.execute(
    "SELECT COUNT(*) FROM tasks WHERE status='completed' AND phase_id > 1"
).fetchone()[0]
total_tasks = conn.execute(
    "SELECT COUNT(*) FROM tasks WHERE phase_id > 1"
).fetchone()[0]

due_soon = read_df("""
    SELECT name, required_date FROM permits
    WHERE status = 'pending' AND required_date <= date('now','+14 days')
    ORDER BY required_date
""", conn)

recent_photos = read_df("""
    SELECT id, original_filename, file_path, upload_date
    FROM receipts
    WHERE file_category IN ('photo', 'quick_log')
      AND file_path LIKE 'http%'
    ORDER BY upload_date DESC
    LIMIT 3
""", conn)

conn.close()

# ── Budget metrics ────────────────────────────────────────────────────────
progress  = int(completed / total_tasks * 100) if total_tasks > 0 else 0
remaining = config["total_budget"] - spent

c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("Budget",    f"${config['total_budget']:,.0f}")
with c2: st.metric("Spent",     f"${spent:,.0f}")
with c3: st.metric("Remaining", f"${remaining:,.0f}")
with c4: st.metric("Progress",  f"{progress}%")
st.progress(progress / 100)

if not due_soon.empty:
    row = due_soon.iloc[0]
    st.warning(f"⏳ Permit due soon: **{row['name']}** — {row['required_date']}")

st.divider()

# ── Today's Focus — primary action card ───────────────────────────────────
st.subheader("📍 Today's Focus")
current_focus = get_current_focus()

if current_focus["task"]:
    task = current_focus["task"]
    with st.container(border=True):
        col_info, col_btn = st.columns([3, 1])
        with col_info:
            st.markdown(f"**{task['title']}**")
            if task.get("due_date"):
                st.caption(f"Due: {task['due_date']}")
        with col_btn:
            if st.button("✅ Done", type="primary", use_container_width=True, key="mark_done"):
                conn2 = get_connection()
                conn2.execute(
                    "UPDATE tasks SET status='completed', completed_date=date('now') WHERE id=?",
                    (task["id"],),
                )
                conn2.commit()
                conn2.close()
                st.success(f"✅ Completed: {task['title']}")
                st.rerun()
else:
    st.success("✅ No pending tasks — great progress!")

if current_focus["permit"]:
    permit = current_focus["permit"]
    st.info(f"⏳ **Next permit:** {permit['name']} — Due {permit['required_date']}")

st.divider()

# ── Recent photos strip ───────────────────────────────────────────────────
st.subheader("📸 Recent Photos")
if not recent_photos.empty:
    img_cols = st.columns(len(recent_photos))
    for i, (_, row) in enumerate(recent_photos.iterrows()):
        with img_cols[i]:
            fname = str(row.get("original_filename", "")).lower()
            if fname.endswith((".jpg", ".jpeg", ".png")):
                st.image(str(row["file_path"]), use_container_width=True)
            st.caption(str(row.get("upload_date", ""))[:10])
    st.page_link("pages/04_📖_Site_Diary.py", label="📖 See all photos in Site Diary →")
else:
    st.caption("No photos yet — tap ➕ Quick Log above to capture your first site photo")

st.divider()

# ── Charts (collapsed by default — keeps above-the-fold clean on mobile) ──
with st.expander("💰 Budget Breakdown", expanded=False):
    st.plotly_chart(create_budget_pie(), use_container_width=True)

with st.expander("📈 Spending Over Time", expanded=False):
    st.plotly_chart(create_spend_line(), use_container_width=True)

with st.expander("🗓️ Full Project Gantt", expanded=False):
    st.plotly_chart(create_gantt(), use_container_width=True)

st.caption("Crowe's Nest Build • Dashboard")

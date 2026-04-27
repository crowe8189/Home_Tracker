import streamlit as st
from datetime import date
from db.db_utils import get_project_config, get_connection, get_current_focus, is_cloud_mode
from utils.helpers import save_uploaded_file
from utils.mobile_css import apply_mobile_optimizations


def render_sidebar():
    """Shared sidebar — mobile/PWA CSS, hidden default nav, Quick Log dialog."""

    apply_mobile_optimizations()

    config = get_project_config()

    with st.sidebar:
        st.title("🐦‍⬛ Crowe's Nest Build")

        if not config:
            st.error(
                "❌ Database connection failed.\n\n"
                "Check that **TURSO_URL** and **TURSO_AUTH_TOKEN** are set correctly "
                "in Streamlit Cloud → Settings → Secrets. "
                "Make sure you paste the full token with no truncation."
            )
            # Still render nav so user can reach Settings page to diagnose
            st.page_link("pages/09_⚙️_Settings.py", label="⚙️ Settings", icon="⚙️")
            return

        st.caption(f"📍 {config['address']}\n🗓️ Started {config['start_date']}")
        st.divider()

        # Budget snapshot
        st.metric("Total Budget", f"${config['total_budget']:,.0f}")
        try:
            conn = get_connection()
            spent = conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0]
            conn.close()
        except Exception:
            spent = 0
        st.metric("Spent", f"${spent:,.0f}", f"Remaining ${config['total_budget'] - spent:,.0f}")

        st.divider()

        # Navigation
        st.page_link("pages/01_🏠_Dashboard.py",           label="🏠 Dashboard",    icon="🏠")
        st.page_link("pages/02_🛤️_Roadmap.py",            label="🛤️ Roadmap",      icon="🛤️")
        st.page_link("pages/03_💰_Budget.py",              label="💰 Budget",        icon="💰")
        st.page_link("pages/04_📸_Photos.py",              label="📸 Photos",        icon="📸")
        st.page_link("pages/05_📄_Documents.py",           label="📁 All Files Hub", icon="📁")
        st.page_link("pages/06_✅_Checklist.py",           label="✅ Checklist",     icon="✅")
        st.page_link("pages/07_🌳_QOL_Futureproofing.py", label="🌳 QOL Tracker",   icon="🌳")
        st.page_link("pages/10_🌿_Inspo_Board.py",         label="🌿 Inspo Board",   icon="🌿")
        st.page_link("pages/08_🤖_AI_Assistant.py",        label="🤖 AI Assistant",  icon="🤖")
        st.page_link("pages/09_⚙️_Settings.py",           label="⚙️ Settings",      icon="⚙️")

        st.divider()

        # Storage health — warn only when Supabase is missing in cloud mode
        if is_cloud_mode():
            _missing = [k for k in ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_BUCKET")
                        if k not in st.secrets]
            if _missing:
                st.warning(f"⚠️ File uploads disabled\nMissing secrets: {', '.join(_missing)}")

        if st.button("➕ Quick Log (Photo / Receipt)", type="primary", use_container_width=True):
            quick_log_dialog()


# ====================== QUICK LOG DIALOG ======================
@st.dialog("Quick Log — On-Site Capture")
def quick_log_dialog():
    """Full-screen-friendly dialog optimised for one-handed phone use."""
    current_focus = get_current_focus()

    # Camera first (primary use case on site), file upload as fallback
    camera_photo = st.camera_input("📷 Take photo", key="sidebar_cam")
    uploaded = st.file_uploader(
        "Or choose a file",
        type=["jpg", "jpeg", "png", "pdf"],
        key="sidebar_file",
    )

    file_to_save = camera_photo if camera_photo is not None else uploaded
    if file_to_save:
        st.caption("✅ File ready")

    notes = st.text_area("Notes / Description", height=80)

    # Smart auto-link to current task / permit
    link_options = ["None"]
    default_index = 0
    if current_focus.get("task"):
        link_options.append(f"Task: {current_focus['task']['title']}")
        default_index = 1
    if current_focus.get("permit"):
        link_options.append(f"Permit: {current_focus['permit']['name']}")
        if not current_focus.get("task"):
            default_index = 1

    link_choice = st.selectbox("Link to", link_options, index=default_index)

    task_id = permit_id = None
    if "Task:" in link_choice and current_focus.get("task"):
        task_id = current_focus["task"]["id"]
    elif "Permit:" in link_choice and current_focus.get("permit"):
        permit_id = current_focus["permit"]["id"]

    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("✅ Save", type="primary", use_container_width=True):
            if file_to_save:
                file_url = save_uploaded_file(file_to_save)
                if file_url:
                    conn = get_connection()
                    conn.execute(
                        """INSERT INTO receipts
                            (file_path, original_filename, upload_date, notes,
                             file_category, linked_task_id, linked_permit_id, document_type)
                           VALUES (?,?,?,?,?,?,?,?)""",
                        (
                            file_url,
                            getattr(file_to_save, "name", "camera_photo.jpg"),
                            date.today().strftime("%Y-%m-%d"),
                            notes,
                            "photo",        # consistent with Site Diary filter
                            task_id,
                            permit_id,
                            "document",
                        ),
                    )
                    conn.commit()
                    conn.close()
                    st.success("✅ Saved!")
                    st.rerun()
            else:
                st.warning("Take a photo or choose a file first.")

    with col_cancel:
        if st.button("Cancel", use_container_width=True):
            st.rerun()

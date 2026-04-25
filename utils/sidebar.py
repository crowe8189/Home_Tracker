import streamlit as st
from datetime import date
from db.db_utils import get_project_config, get_connection, get_current_focus
from utils.helpers import save_uploaded_file
from utils.mobile_css import apply_mobile_optimizations   # ← NEW

def render_sidebar():
    """Shared sidebar – now also applies mobile CSS + hides default nav on ALL pages."""
    # === GLOBAL FIXES (applies to every page) ===
    st.markdown("""
    <style>
        /* Hide Streamlit's default page navigation to prevent duplication */
        [data-testid="stSidebarNav"] { 
            display: none !important; 
        }
    </style>
    """, unsafe_allow_html=True)

    from utils.mobile_css import apply_mobile_optimizations
    apply_mobile_optimizations()   # mobile styling

    # ←←← YOUR EXISTING CODE STARTS HERE (config, metrics, navigation, Quick Log, etc.)
    config = get_project_config()
    
    with st.sidebar:
        st.title("🐦‍⬛ Crowe's Nest Build")
        st.caption(f"📍 {config['address']}\n🗓️ Started {config['start_date']}")
        st.divider()
        
        # Budget metrics
        st.metric("Total Budget", f"${config['total_budget']:,.0f}")
        conn = get_connection()
        spent = conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0]
        conn.close()
        st.metric("Spent", f"${spent:,.0f}", f"Remaining ${config['total_budget']-spent:,.0f}")
        
        st.divider()
        
        # Navigation
        st.page_link("pages/01_🏠_Dashboard.py", label="🏠 Dashboard", icon="🏠")
        st.page_link("pages/02_🛤️_Roadmap.py", label="🛤️ Roadmap", icon="🛤️")
        st.page_link("pages/03_💰_Budget.py", label="💰 Budget", icon="💰")
        st.page_link("pages/04_📖_Site_Diary.py", label="📖 Site Diary", icon="📖")
        st.page_link("pages/05_📄_Documents.py", label="📁 All Files Hub", icon="📁")
        st.page_link("pages/06_✅_Checklist.py", label="✅ Checklist", icon="✅")
        st.page_link("pages/07_🌳_QOL_Futureproofing.py", label="🌳 QOL Tracker", icon="🌳")
        st.page_link("pages/08_🤖_AI_Assistant.py", label="🤖 AI Assistant", icon="🤖")
        st.page_link("pages/09_⚙️_Settings.py", label="⚙️ Settings", icon="⚙️")
        
        # ====================== GLOBAL QUICK LOG (Mobile Optimized) ======================
        if st.button("➕ Quick Log (Photo / Receipt)", type="primary", use_container_width=True):
            with st.dialog("Quick Log — On-Site Capture"):
                st.subheader("📸 Quick Log")
                current_focus = get_current_focus()
                
                col_cam, col_file = st.columns(2)
                with col_cam:
                    camera_photo = st.camera_input("Take photo now", key="sidebar_cam")
                with col_file:
                    uploaded = st.file_uploader("Or upload file", 
                                              type=["jpg","jpeg","png","pdf"], 
                                              key="sidebar_file")
                
                file_to_save = camera_photo if camera_photo is not None else uploaded
                notes = st.text_area("Notes / Description", height=100)
                
                # Smart auto-link
                link_options = ["None"]
                default_index = 0
                if current_focus.get("task"):
                    link_options.append(f"Current Task: {current_focus['task']['title']}")
                    default_index = 1
                if current_focus.get("permit"):
                    link_options.append(f"Current Permit: {current_focus['permit']['name']}")
                    if not current_focus.get("task"):
                        default_index = 1
                
                link_choice = st.selectbox("Link to", link_options, index=default_index)
                
                task_id = permit_id = None
                if "Task" in link_choice and current_focus.get("task"):
                    task_id = current_focus["task"]["id"]
                elif "Permit" in link_choice and current_focus.get("permit"):
                    permit_id = current_focus["permit"]["id"]
                
                if st.button("✅ Save & Close", type="primary", use_container_width=True):
                    if file_to_save:
                        file_url = save_uploaded_file(file_to_save)
                        conn = get_connection()
                        conn.execute("""INSERT INTO receipts 
                            (file_path, original_filename, upload_date, notes, file_category,
                             linked_task_id, linked_permit_id, document_type)
                            VALUES (?,?,?,?,?,?,?,?)""",
                            (file_url, 
                             getattr(file_to_save, 'name', 'camera_photo.jpg'),
                             date.today().strftime("%Y-%m-%d"),
                             notes, "quick_log", task_id, permit_id, "document"))
                        conn.commit()
                        conn.close()
                        st.success("✅ Saved and auto-linked!")
                        st.rerun()
                    else:
                        st.warning("Please take a photo or upload a file")
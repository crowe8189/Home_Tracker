import streamlit as st
import pandas as pd
from datetime import date
import os
from db.db_utils import get_connection, get_current_focus
from utils.helpers import save_uploaded_file, delete_receipt_file
from utils.sidebar import render_sidebar

render_sidebar()

st.set_page_config(page_title="📖 Site Diary", layout="wide")
st.title("📖 Site Diary")
st.caption("Chronological progress timeline • Family photos • Progress shots • Receipts")

# ====================== DIRECT UPLOAD ======================
st.subheader("➕ Upload New Progress Photo / Moment")
current_focus = get_current_focus()

uploaded = st.file_uploader("Take or upload a photo (JPG, PNG)", 
                           type=["jpg", "jpeg", "png"], 
                           key="diary_upload")

if uploaded:
    with st.form("diary_upload_form"):
        notes = st.text_area("Notes / Description", height=80)
        
        link_options = ["None"]
        default_index = 0
        if current_focus.get("task"):
            link_options.append(f"Current Task: {current_focus['task']['title']}")
            default_index = 1
        if current_focus.get("permit"):
            link_options.append(f"Current Permit: {current_focus['permit']['name']}")
            if not current_focus.get("task"):
                default_index = 1
        
        link_to = st.selectbox("Link to (optional)", link_options, index=default_index)
        
        task_id = permit_id = None
        if "Task" in link_to and current_focus.get("task"):
            task_id = current_focus["task"]["id"]
        elif "Permit" in link_to and current_focus.get("permit"):
            permit_id = current_focus["permit"]["id"]
        
        if st.form_submit_button("✅ Save to Site Diary", type="primary"):
            file_url = save_uploaded_file(uploaded)
            conn = get_connection()
            conn.execute("""INSERT INTO receipts 
                (file_path, original_filename, upload_date, notes, file_category,
                 linked_task_id, linked_permit_id)
                VALUES (?,?,?,?,?,?,?)""",
                (file_url, uploaded.name, date.today().strftime("%Y-%m-%d"),
                 notes, "photo", task_id, permit_id))
            conn.commit()
            conn.close()
            st.success("✅ Saved!")
            st.rerun()

# ====================== TIMELINE ======================
st.divider()
st.subheader("📅 All Diary Entries")

# Refresh button
if st.button("🔄 Refresh Diary", use_container_width=True):
    st.rerun()

# Clean missing images button
if st.button("🧹 Clean All Missing Images", type="secondary", use_container_width=True):
    conn = get_connection()
    records = conn.execute("""
        SELECT id, file_path 
        FROM receipts 
        WHERE file_category = 'photo' 
          AND file_path NOT LIKE 'http%'
    """).fetchall()
    
    deleted_count = 0
    for row in records:
        if not os.path.exists(row['file_path']):
            conn.execute("DELETE FROM receipts WHERE id=?", (row['id'],))
            deleted_count += 1
    
    conn.commit()
    conn.close()
    st.success(f"✅ Cleaned up {deleted_count} missing image records")
    st.rerun()

# Load fresh data
conn = get_connection()
df = pd.read_sql("""
    SELECT 
        r.id,
        r.upload_date,
        r.original_filename,
        r.file_path,
        r.notes,
        r.file_category,
        t.title as linked_task_title,
        p.name as linked_permit_name
    FROM receipts r
    LEFT JOIN tasks t ON r.linked_task_id = t.id
    LEFT JOIN permits p ON r.linked_permit_id = p.id
    ORDER BY r.upload_date DESC
""", conn)
conn.close()

if df.empty:
    st.info("No entries yet. Upload some photos above!")
    st.stop()

df['upload_date'] = pd.to_datetime(df['upload_date'])

for date_str, group in df.groupby(df['upload_date'].dt.date):
    st.subheader(f"📅 {date_str.strftime('%A, %B %d, %Y')}")
    
    for _, row in group.iterrows():
        filepath = row['file_path']
        file_exists = os.path.exists(filepath) if not str(filepath).startswith("http") else True

        with st.container(border=True):
            col_img, col_info = st.columns([1, 3])
            
            with col_img:
                if str(row['original_filename']).lower().endswith(('.jpg', '.jpeg', '.png')):
                    if file_exists:
                        st.image(filepath, use_container_width=True)
                    else:
                        st.error("🖼️ Image missing (file deleted)")
                else:
                    st.markdown("📄")
            
            with col_info:
                st.markdown(f"**{row['file_category'].title()}** • {row['original_filename']}")
                if row['linked_task_title']:
                    st.caption(f"🔗 Task: **{row['linked_task_title']}**")
                if row['linked_permit_name']:
                    st.caption(f"🔗 Permit: **{row['linked_permit_name']}**")
                if row['notes']:
                    st.write(row['notes'])
                
                col_dl, col_del = st.columns([3, 1])
                with col_dl:
                    if file_exists and not str(filepath).startswith("http"):
                        with open(filepath, "rb") as f:
                            st.download_button(
                                label="⬇️ Download",
                                data=f.read(),
                                file_name=row['original_filename'],
                                mime="application/octet-stream",
                                key=f"dl_{row['id']}"
                            )
                with col_del:
                    if st.button("🗑️", key=f"del_{row['id']}"):
                        if delete_receipt_file(filepath):
                            conn = get_connection()
                            conn.execute("DELETE FROM receipts WHERE id=?", (row['id'],))
                            conn.commit()
                            conn.close()
                            st.success("✅ Photo deleted")
                            st.rerun()

st.caption("📖 Site Diary • All photos and linked documents appear here automatically")
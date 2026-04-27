import streamlit as st
import pandas as pd
from datetime import date
import os

st.set_page_config(page_title="Site Diary", layout="wide", page_icon="📖")

from db.db_utils import get_connection, get_current_focus, init_db, read_df, is_cloud_mode
from utils.helpers import save_uploaded_file, delete_receipt_file
from utils.sidebar import render_sidebar

if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

render_sidebar()

st.title("📖 Site Diary")
st.caption("Progress photos • Family moments • Quick Log captures — in chronological order")

# ====================== UPLOAD NEW PHOTO ======================
st.subheader("➕ Upload New Progress Photo")
current_focus = get_current_focus()

uploaded = st.file_uploader(
    "Take or upload a photo (JPG, PNG)",
    type=["jpg", "jpeg", "png"],
    key="diary_upload",
)

if uploaded:
    with st.form("diary_upload_form"):
        notes = st.text_area("Notes / Description", height=80)

        link_options  = ["None"]
        default_index = 0
        if current_focus.get("task"):
            link_options.append(f"Current Task: {current_focus['task']['title']}")
            default_index = 1
        if current_focus.get("permit"):
            link_options.append(f"Current Permit: {current_focus['permit']['name']}")
            if not current_focus.get("task"):
                default_index = 1

        link_to  = st.selectbox("Link to (optional)", link_options, index=default_index)
        task_id  = permit_id = None
        if "Task" in link_to and current_focus.get("task"):
            task_id = current_focus["task"]["id"]
        elif "Permit" in link_to and current_focus.get("permit"):
            permit_id = current_focus["permit"]["id"]

        if st.form_submit_button("✅ Save to Site Diary", type="primary"):
            file_url = save_uploaded_file(uploaded)
            if file_url:
                conn = get_connection()
                conn.execute("""
                    INSERT INTO receipts
                        (file_path, original_filename, upload_date, notes,
                         file_category, linked_task_id, linked_permit_id)
                    VALUES (?,?,?,?,?,?,?)
                """, (
                    file_url, uploaded.name,
                    date.today().strftime("%Y-%m-%d"),
                    notes, "photo", task_id, permit_id,
                ))
                conn.commit()
                conn.close()
                st.success("✅ Saved!")
                st.rerun()

# ====================== CLEANUP TOOLBAR ======================
st.divider()
col_r, col_c = st.columns(2)
with col_r:
    if st.button("🔄 Refresh Diary", use_container_width=True):
        st.rerun()

with col_c:
    if is_cloud_mode():
        # Cloud: any record whose file_path is not a URL is an orphan (file was never uploaded to Supabase)
        if st.button("🧹 Clean Orphaned Records (Cloud)", type="secondary", use_container_width=True):
            conn = get_connection()
            count_row = conn.execute("""
                SELECT COUNT(*) FROM receipts
                WHERE file_category IN ('photo', 'quick_log')
                  AND (file_path IS NULL OR file_path = ''
                       OR file_path NOT LIKE 'http%')
            """).fetchone()
            orphan_count = count_row[0] if count_row else 0
            conn.execute("""
                DELETE FROM receipts
                WHERE file_category IN ('photo', 'quick_log')
                  AND (file_path IS NULL OR file_path = ''
                       OR file_path NOT LIKE 'http%')
            """)
            conn.commit()
            conn.close()
            st.success(f"✅ Removed {orphan_count} orphaned record(s)")
            st.rerun()
    else:
        # Local: ghost records are rows whose local file no longer exists on disk
        if st.button("🧹 Clean Missing Local Images", type="secondary", use_container_width=True):
            conn = get_connection()
            records = conn.execute("""
                SELECT id, file_path FROM receipts
                WHERE file_category IN ('photo', 'quick_log')
                  AND file_path NOT LIKE 'http%'
            """).fetchall()
            deleted = 0
            for r in records:
                if not os.path.exists(r[1]):
                    conn.execute("DELETE FROM receipts WHERE id=?", (r[0],))
                    deleted += 1
            conn.commit()
            conn.close()
            st.success(f"✅ Cleaned {deleted} missing image record(s)")
            st.rerun()

# ====================== TIMELINE ======================
st.subheader("📅 All Diary Entries")

conn = get_connection()
# Site Diary shows only photo-type entries (direct upload or Quick Log)
df = read_df("""
    SELECT
        r.id,
        r.upload_date,
        r.original_filename,
        r.file_path,
        r.notes,
        r.file_category,
        t.title AS linked_task_title,
        p.name  AS linked_permit_name
    FROM receipts r
    LEFT JOIN tasks   t ON r.linked_task_id   = t.id
    LEFT JOIN permits p ON r.linked_permit_id  = p.id
    WHERE r.file_category IN ('photo', 'quick_log')
    ORDER BY r.upload_date DESC
""", conn)
conn.close()

if df.empty:
    st.info("No diary entries yet. Upload photos above or use Quick Log from the sidebar!")
    st.stop()

df["upload_date"] = pd.to_datetime(df["upload_date"], errors="coerce")

for date_val, group in df.groupby(df["upload_date"].dt.date, sort=False):
    st.subheader(f"📅 {date_val.strftime('%A, %B %d, %Y')}")

    for _, row in group.iterrows():
        filepath    = row["file_path"] or ""
        is_url      = filepath.startswith(("http://", "https://"))
        file_exists = is_url or os.path.exists(filepath)
        is_image    = str(row["original_filename"]).lower().endswith((".jpg", ".jpeg", ".png"))

        with st.container(border=True):
            col_img, col_info = st.columns([1, 3])

            with col_img:
                if is_image and file_exists:
                    st.image(filepath, use_container_width=True)
                elif is_image:
                    st.error("🖼️ Image missing")
                else:
                    st.markdown("📄")

            with col_info:
                st.markdown(f"**{str(row['file_category']).title()}** • {row['original_filename']}")
                if row.get("linked_task_title"):
                    st.caption(f"🔗 Task: **{row['linked_task_title']}**")
                if row.get("linked_permit_name"):
                    st.caption(f"🔗 Permit: **{row['linked_permit_name']}**")
                if row.get("notes"):
                    st.write(row["notes"])

                col_dl, col_del = st.columns([3, 1])
                with col_dl:
                    if is_url:
                        st.link_button("⬇️ Download", url=filepath, key=f"lnk_{row['id']}")
                    elif file_exists:
                        with open(filepath, "rb") as f:
                            st.download_button(
                                "⬇️ Download",
                                data=f.read(),
                                file_name=row["original_filename"],
                                mime="application/octet-stream",
                                key=f"dl_{row['id']}",
                            )
                with col_del:
                    if st.button("🗑️", key=f"del_{row['id']}"):
                        bucket_ok = delete_receipt_file(filepath)
                        conn = get_connection()
                        conn.execute("DELETE FROM receipts WHERE id=?", (int(row["id"]),))
                        conn.commit()
                        conn.close()
                        if bucket_ok:
                            st.success("✅ Deleted")
                        else:
                            st.warning("✅ Removed from diary — file may not have been in bucket")
                        st.rerun()

st.caption("📖 Site Diary • Photos and Quick Log captures appear here automatically")

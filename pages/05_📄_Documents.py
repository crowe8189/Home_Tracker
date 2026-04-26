import streamlit as st
import pandas as pd
import os
from datetime import date

st.set_page_config(page_title="All Files Hub", layout="wide", page_icon="📁")

from db.db_utils import get_connection, get_current_focus, init_db, read_df, is_cloud_mode
from utils.helpers import save_uploaded_file, delete_receipt_file
from utils.sidebar import render_sidebar

if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

render_sidebar()

st.title("📁 All Files Hub")
st.caption("Receipts • Permits • Plans • Progress Photos • Contracts • Inspo")

# ====================== FILTERS ======================
colA, colB, colC = st.columns([2, 1, 1])
with colA:
    search = st.text_input("🔍 Search files (filename, notes, OCR)", "")
with colB:
    category_filter = st.selectbox(
        "File Category",
        ["All", "receipt", "permit", "plan", "photo", "quick_log", "contract", "general", "inspo"],
        index=0,
    )
with colC:
    date_filter = st.date_input("Uploaded after", value=None, label_visibility="collapsed")

# ====================== LOAD ALL FILES ======================
conn = get_connection()
df = read_df("""
    SELECT id, original_filename, upload_date, file_category, notes,
           linked_task_id, linked_permit_id, linked_expense_id,
           file_path, ocr_text
    FROM receipts
    ORDER BY upload_date DESC
""", conn)
conn.close()

# ====================== CLOUD GHOST CLEANUP ======================
if is_cloud_mode() and not df.empty:
    ghost_mask = (
        df["file_path"].isna() |
        (df["file_path"] == "") |
        ~df["file_path"].str.startswith("http", na=True)
    )
    ghost_count = ghost_mask.sum()
    if ghost_count > 0:
        st.warning(
            f"⚠️ {ghost_count} record(s) have local file paths that won't load on cloud. "
            "Use the button below to remove them."
        )
        if st.button(f"🧹 Remove {ghost_count} Orphaned Record(s)", type="secondary"):
            ghost_ids = df[ghost_mask]["id"].tolist()
            conn = get_connection()
            for gid in ghost_ids:
                conn.execute("DELETE FROM receipts WHERE id=?", (int(gid),))
            conn.commit()
            conn.close()
            st.success(f"✅ Removed {ghost_count} orphaned record(s)")
            st.rerun()

# ====================== APPLY FILTERS ======================
if not df.empty:
    if search:
        mask = (
            df["original_filename"].str.contains(search, case=False, na=False) |
            df["notes"].str.contains(search, case=False, na=False) |
            df["ocr_text"].str.contains(search, case=False, na=False)
        )
        df = df[mask]
    if category_filter != "All":
        df = df[df["file_category"] == category_filter]
    if date_filter:
        df = df[pd.to_datetime(df["upload_date"], errors="coerce") >= pd.to_datetime(date_filter)]

if df.empty:
    st.info("No files yet — upload below!")
else:
    # ====================== FILE TABLE ======================
    st.subheader("📋 All Files")
    edited_df = st.data_editor(
        df[["id", "original_filename", "file_category", "notes", "upload_date"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "id":                st.column_config.NumberColumn(disabled=True),
            "original_filename": st.column_config.TextColumn("Filename"),
            "file_category":     st.column_config.SelectboxColumn(
                "Category",
                options=["receipt", "permit", "plan", "photo", "quick_log",
                         "contract", "general", "inspo"],
            ),
            "notes":             st.column_config.TextColumn("Notes"),
            "upload_date":       st.column_config.TextColumn("Uploaded", disabled=True),
        },
    )

    if st.button("💾 Save All Changes", type="primary"):
        conn = get_connection()
        for _, row in edited_df.iterrows():
            conn.execute("""
                UPDATE receipts
                SET original_filename=?, file_category=?, notes=?
                WHERE id=?
            """, (row["original_filename"], row["file_category"], row["notes"], int(row["id"])))
        conn.commit()
        conn.close()
        st.success("✅ Changes saved!")
        st.rerun()

    # ====================== FILE PREVIEW ======================
    st.subheader("📸 Preview / Download / Delete")
    selected_id = st.selectbox(
        "Choose file to preview",
        df["id"].tolist(),
        format_func=lambda x: df[df["id"] == x]["original_filename"].iloc[0],
    )

    if selected_id:
        sel = df[df["id"] == selected_id].iloc[0]
        file_path = sel["file_path"] or ""
        filename  = sel["original_filename"]
        is_url    = file_path.startswith(("http://", "https://"))

        st.caption(f"📄 {filename}")

        if is_url or (file_path and os.path.exists(file_path)):
            if filename.lower().endswith((".jpg", ".jpeg", ".png")):
                st.image(file_path, use_container_width=True)
            else:
                st.info(f"📄 {filename} — non-image file")
        else:
            st.warning("⚠️ File not found on storage (orphaned record)")

        col_dl, col_del = st.columns(2)
        with col_dl:
            if is_url:
                st.link_button("📥 Download File", url=file_path, key=f"link_{selected_id}")
            elif file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    st.download_button(
                        "📥 Download File", data=f.read(),
                        file_name=filename, key=f"dl_{selected_id}",
                    )
        with col_del:
            if st.button("🗑️ Delete File", type="secondary", key=f"del_{selected_id}"):
                delete_receipt_file(file_path)
                conn = get_connection()
                conn.execute("DELETE FROM receipts WHERE id=?", (int(selected_id),))
                conn.commit()
                conn.close()
                st.success("✅ File deleted")
                st.rerun()

        if sel.get("ocr_text"):
            st.text_area("OCR Text", sel["ocr_text"], height=120, key=f"ocr_{selected_id}")

# ====================== QUICK UPLOAD ======================
st.divider()
st.subheader("➕ Upload New File")
new_upload = st.file_uploader(
    "Any file (receipt, permit, plan, photo, inspo…)", type=["jpg", "jpeg", "png", "pdf"]
)

if new_upload:
    current_focus = get_current_focus()
    with st.form("quick_file_form"):
        cat   = st.selectbox("Category",
            ["receipt", "permit", "plan", "photo", "contract", "general", "inspo"])
        notes = st.text_area("Notes / Description")

        link_options  = ["None"]
        default_index = 0
        if current_focus.get("task"):
            link_options.append(f"Current Task: {current_focus['task']['title']}")
            default_index = 1
        if current_focus.get("permit"):
            link_options.append(f"Current Permit: {current_focus['permit']['name']}")
            if not current_focus.get("task"):
                default_index = 1

        link_to  = st.selectbox("Link to", link_options, index=default_index)
        task_id  = permit_id = None
        if "Task" in link_to and current_focus.get("task"):
            task_id = current_focus["task"]["id"]
        elif "Permit" in link_to and current_focus.get("permit"):
            permit_id = current_focus["permit"]["id"]

        if st.form_submit_button("💾 Save File"):
            file_url = save_uploaded_file(new_upload)
            if file_url:
                conn = get_connection()
                conn.execute("""
                    INSERT INTO receipts
                        (file_path, original_filename, upload_date, notes,
                         file_category, linked_task_id, linked_permit_id, document_type)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (
                    file_url, new_upload.name,
                    date.today().strftime("%Y-%m-%d"),
                    notes, cat, task_id, permit_id, "document",
                ))
                conn.commit()
                conn.close()
                st.success("✅ File saved!")
                st.rerun()

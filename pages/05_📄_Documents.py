import streamlit as st
import pandas as pd
import os
from datetime import date
from db.db_utils import get_connection, row_to_dict, get_current_focus
from utils.helpers import save_uploaded_file, perform_ocr, export_to_csv, delete_receipt_file
from utils.sidebar import render_sidebar

render_sidebar()

st.title("📁 All Files Hub")
st.caption("Receipts • Permits • Plans • Progress Photos • Contracts • Everything")

# Filters
colA, colB, colC = st.columns([2, 1, 1])
with colA:
    search = st.text_input("🔍 Search files (filename, notes, OCR)", "")
with colB:
    category_filter = st.selectbox("File Category",
                                   ["All", "receipt", "permit", "plan", "photo", "contract", "general"],
                                   index=0)
with colC:
    date_filter = st.date_input("Uploaded after", value=None, label_visibility="collapsed")

# Load data
conn = get_connection()
df = pd.read_sql("""
    SELECT id, original_filename, upload_date, file_category, notes,
           linked_task_id, linked_permit_id, linked_expense_id,
           file_path, ocr_text
    FROM receipts
    ORDER BY upload_date DESC
""", conn)
conn.close()

# Apply filters
if search:
    mask = (df['original_filename'].str.contains(search, case=False, na=False)) | \
           (df['notes'].str.contains(search, case=False, na=False)) | \
           (df['ocr_text'].str.contains(search, case=False, na=False))
    df = df[mask]

if category_filter != "All":
    df = df[df['file_category'] == category_filter]

if date_filter:
    df = df[pd.to_datetime(df['upload_date']) >= pd.to_datetime(date_filter)]

if df.empty:
    st.info("No files yet — upload below!")
else:
    st.dataframe(df[['original_filename', 'upload_date', 'file_category', 'notes']],
                 use_container_width=True, hide_index=True)

    # ====================== GALLERY / PREVIEW ======================
    st.subheader("📸 Preview Selected File")
    selected_id = st.selectbox(
        "Choose file",
        df['id'].tolist() if not df.empty else [None],
        format_func=lambda x: df[df['id'] == x]['original_filename'].iloc[0] if x else "None"
    )

    if selected_id:
        row = df[df['id'] == selected_id].iloc[0]
        file_path = row['file_path']
        filename = row['original_filename']

        st.caption(f"📄 {filename}")

        # === FIXED: Handle Supabase URLs + local paths ===
        if file_path and (file_path.startswith("http://") or file_path.startswith("https://")):
            # Cloud mode (Supabase public URL)
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                st.image(file_path, use_container_width=True)
            else:
                st.info(f"📄 {filename} (PDF or other document)")
        elif file_path and os.path.exists(file_path):
            # Local mode
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                st.image(file_path, use_container_width=True)
            else:
                st.info(f"📄 {filename} (PDF or other document)")
        else:
            st.warning("⚠️ File not found")

        # Download button (works for both URLs and local files)
        if file_path and (file_path.startswith("http://") or file_path.startswith("https://")):
            st.link_button("📥 Download File", url=file_path, use_container_width=True)
        else:
            with open(file_path, "rb") as f:
                st.download_button(
                    "📥 Download File",
                    data=f.read(),
                    file_name=filename,
                    use_container_width=True
                )

        # Delete button
        if st.button("🗑️ Delete File", type="secondary"):
            delete_receipt_file(file_path)
            conn = get_connection()
            conn.execute("DELETE FROM receipts WHERE id=?", (selected_id,))
            conn.commit()
            conn.close()
            st.success("File deleted")
            st.rerun()

        if row['ocr_text']:
            st.text_area("OCR Text", row['ocr_text'], height=120)

# ====================== QUICK GLOBAL UPLOAD ======================
st.subheader("➕ Upload New File")
uploaded = st.file_uploader("Any file (receipt, permit doc, plan, photo…)",
                           type=["jpg", "jpeg", "png", "pdf"])

if uploaded:
    file_url = save_uploaded_file(uploaded)
    st.success("✅ Uploaded!")

    current_focus = get_current_focus()

    with st.form("quick_file_form"):
        cat = st.selectbox("Category", ["receipt", "permit", "plan", "photo", "contract", "general"])
        notes = st.text_area("Notes / Description")

        # Smart auto-linking
        link_options = ["None"]
        default_index = 0
        if current_focus["task"]:
            link_options.append(f"Current Task: {current_focus['task']['title']}")
            default_index = 1
        if current_focus["permit"]:
            link_options.append(f"Current Permit: {current_focus['permit']['name']}")
            if not current_focus["task"]:
                default_index = 1

        link_to = st.selectbox("Link to", link_options, index=default_index)

        task_id = permit_id = None
        if "Task" in link_to and current_focus["task"]:
            task_id = current_focus["task"]["id"]
        elif "Permit" in link_to and current_focus["permit"]:
            permit_id = current_focus["permit"]["id"]

        submitted = st.form_submit_button("Save File")
        if submitted:
            conn = get_connection()
            conn.execute("""INSERT INTO receipts
                (file_path, original_filename, upload_date, notes, file_category,
                 linked_task_id, linked_permit_id, document_type)
                VALUES (?,?,?,?,?,?,?,?)""",
                (file_url, uploaded.name, date.today().strftime("%Y-%m-%d"),
                 notes, cat, task_id, permit_id, "document"))
            conn.commit()
            conn.close()
            st.success("✅ File saved with smart auto-link!")
            st.rerun()
import streamlit as st
import pandas as pd
from datetime import date
from db.db_utils import get_connection
from utils.helpers import save_uploaded_file, perform_ocr, export_to_csv, delete_receipt_file

st.title("📄 Project Documents")
st.caption("Floor plans, contracts, permits, specifications, photos, and other general documents")

# ====================== UPLOAD SECTION ======================
st.subheader("Upload New Document")
uploaded_file = st.file_uploader("Choose file (JPG, PNG, PDF)", type=["jpg", "jpeg", "png", "pdf"])

if uploaded_file:
    file_url = save_uploaded_file(uploaded_file)
    st.success("✅ Uploaded to Supabase Cloud!")

    with st.form("general_document_form"):
        title = st.text_input("Document Title / Description *", placeholder="e.g. Main Floor Plan - Revision 3")
        notes = st.text_area("Notes / Context")
        upload_date = st.date_input("Upload Date", date.today())

        link_to_task = st.checkbox("Link to an existing task")
        task_id = None
        if link_to_task:
            conn = get_connection()
            task_options = pd.read_sql("SELECT id, title as label FROM tasks ORDER BY planned_start ASC", conn)
            conn.close()
            if not task_options.empty:
                selected = st.selectbox("Select Task", task_options['label'])
                task_id = task_options[task_options['label'] == selected]['id'].iloc[0]
            else:
                st.info("No tasks found yet.")

        submitted = st.form_submit_button("Save Document")
        if submitted and title:
            conn = get_connection()
            conn.execute("""INSERT INTO receipts 
                (file_path, original_filename, upload_date, vendor, amount, category, notes, 
                 linked_expense_id, linked_task_id, document_type, ocr_text)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""", 
                (file_url, uploaded_file.name, upload_date.strftime("%Y-%m-%d"), 
                 None, None, "General Document", notes, None, task_id, "document",
                 perform_ocr(uploaded_file) if uploaded_file.type.startswith("image") else None))
            conn.commit()
            conn.close()
            st.success("✅ Document saved permanently!")
            st.rerun()

# ====================== ALL DOCUMENTS WITH FILTER ======================
st.subheader("All Documents")

filter_option = st.selectbox("Filter Documents", 
                             ["All Documents", "Linked to a Task", "Not Linked to any Task"])

conn = get_connection()
if filter_option == "Linked to a Task":
    df = pd.read_sql("""
        SELECT r.id, r.original_filename, r.upload_date, r.notes, 
               t.title as linked_task
        FROM receipts r
        LEFT JOIN tasks t ON r.linked_task_id = t.id
        WHERE r.document_type = 'document' AND r.linked_task_id IS NOT NULL
        ORDER BY r.upload_date DESC
    """, conn)
elif filter_option == "Not Linked to any Task":
    df = pd.read_sql("""
        SELECT r.id, r.original_filename, r.upload_date, r.notes, 
               NULL as linked_task
        FROM receipts r
        WHERE r.document_type = 'document' AND r.linked_task_id IS NULL
        ORDER BY r.upload_date DESC
    """, conn)
else:
    df = pd.read_sql("""
        SELECT r.id, r.original_filename, r.upload_date, r.notes, 
               t.title as linked_task
        FROM receipts r
        LEFT JOIN tasks t ON r.linked_task_id = t.id
        WHERE r.document_type = 'document'
        ORDER BY r.upload_date DESC
    """, conn)
conn.close()

if df.empty:
    st.info("No general documents uploaded yet.")
else:
    st.dataframe(df.drop(columns=['id']), use_container_width=True, hide_index=True)

    # ====================== ENHANCED PREVIEW ======================
    st.subheader("Preview Selected Document")
    selected_id = st.selectbox("Choose document", df['id'] if not df.empty else [None],
                               format_func=lambda x: df[df['id']==x]['original_filename'].iloc[0] if x else "None")
    if selected_id:
        conn = get_connection()
        row = conn.execute("SELECT * FROM receipts WHERE id=?", (selected_id,)).fetchone()
        conn.close()
        
        st.caption(f"**{row['original_filename']}**")

        if row['original_filename'].lower().endswith(('.jpg', '.jpeg', '.png')):
            st.image(row['file_path'], use_column_width=True)
        else:
            st.info("📄 PDF or other document – preview not available inline. Use the download button below.")
        
        col1, col2 = st.columns([3,1])
        with col1:
            st.link_button("📥 Download File", url=row['file_path'], use_container_width=True)
        with col2:
            if st.button("🗑️ Delete Document", type="secondary"):
                delete_receipt_file(row['file_path'])
                conn = get_connection()
                conn.execute("DELETE FROM receipts WHERE id=?", (selected_id,))
                conn.commit()
                conn.close()
                st.success("Document deleted")
                st.rerun()

st.download_button("Export Documents CSV", export_to_csv("receipts"), "general_documents.csv", "text/csv")
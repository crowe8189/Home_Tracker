import streamlit as st
import pandas as pd
from datetime import date
from db.db_utils import get_connection
from utils.helpers import save_uploaded_file, perform_ocr, export_to_csv, delete_receipt_file

st.title("📸 Documents & Receipts")
st.caption("Receipts auto-create expenses • General documents (floor plans, contracts, etc.) are also supported")

tab1, tab2, tab3 = st.tabs(["Upload New", "All Documents", "Linked Items"])

with tab1:
    st.subheader("Upload Document / Receipt")
    uploaded_file = st.file_uploader("Choose file (JPG, PNG, PDF)", type=["jpg", "jpeg", "png", "pdf"])
    
    if uploaded_file:
        file_url = save_uploaded_file(uploaded_file)
        st.success("✅ Uploaded to Supabase Cloud!")

        with st.form("upload_form"):
            doc_type = st.radio("Document Type", ["Receipt", "General Document (floor plan, contract, etc.)"], horizontal=True)

            vendor = st.text_input("Vendor / Source", value="" if doc_type == "General Document (floor plan, contract, etc.)" else "")
            amount = st.number_input("Amount $", min_value=0.01, value=0.01, disabled=doc_type != "Receipt")
            category = st.text_input("Category", value="Electrical – Materials Only" if doc_type == "Receipt" else "")
            notes = st.text_area("Notes")
            upload_date = st.date_input("Upload Date", date.today())

            # Link to Task (available for both types)
            link_to_task = st.checkbox("Link to an existing task")
            task_id = None
            if link_to_task:
                conn = get_connection()
                task_options = pd.read_sql("SELECT id, title as label FROM tasks ORDER BY planned_start ASC", conn)
                conn.close()
                if not task_options.empty:
                    selected = st.selectbox("Select Task", task_options['label'])
                    task_id = task_options[task_options['label'] == selected]['id'].iloc[0]

            submitted = st.form_submit_button("Save Document")
            if submitted:
                conn = get_connection()
                expense_id = None

                if doc_type == "Receipt":
                    # Auto-create expense for receipts
                    cat_row = conn.execute("SELECT id FROM budget_categories WHERE name=?", (category,)).fetchone()
                    cat_id = cat_row[0] if cat_row else conn.execute("SELECT id FROM budget_categories LIMIT 1").fetchone()[0]
                    
                    conn.execute("""INSERT INTO expenses 
                        (category_id, date, amount, description, vendor)
                        VALUES (?,?,?,?,?)""",
                        (cat_id, upload_date.strftime("%Y-%m-%d"), amount, 
                         f"{vendor} - {notes[:80]}...", vendor))
                    expense_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

                # Save document/receipt
                conn.execute("""INSERT INTO receipts 
                    (file_path, original_filename, upload_date, vendor, amount, category, notes, 
                     linked_expense_id, linked_task_id, document_type, ocr_text)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)""", 
                    (file_url, uploaded_file.name, upload_date.strftime("%Y-%m-%d"), 
                     vendor if doc_type == "Receipt" else None, 
                     amount if doc_type == "Receipt" else None,
                     category if doc_type == "Receipt" else "General Document",
                     notes, expense_id, task_id, 
                     "receipt" if doc_type == "Receipt" else "document",
                     perform_ocr(uploaded_file) if uploaded_file.type.startswith("image") else None))
                
                conn.commit()
                conn.close()
                st.success(f"✅ {doc_type} saved permanently!")
                st.rerun()

with tab2:
    st.subheader("All Documents & Receipts")
    conn = get_connection()
    df = pd.read_sql("""
        SELECT id, original_filename, upload_date, vendor, amount, category, notes, 
               document_type, file_path, linked_task_id 
        FROM receipts ORDER BY upload_date DESC
    """, conn)
    conn.close()
    
    st.dataframe(df.drop(columns=['file_path']), use_container_width=True, hide_index=True)

    # Preview + Download + Delete (same as before)
    # ... (keep your existing preview code - it already works)

with tab3:
    st.subheader("Linked Items")
    # You can keep or expand this tab as needed
    st.info("Linked receipts and documents will appear here in future updates.")

st.download_button("Export All Documents CSV", export_to_csv("receipts"), "documents.csv", "text/csv")
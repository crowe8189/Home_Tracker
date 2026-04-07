import streamlit as st
import pandas as pd
from datetime import date
from db.db_utils import get_connection
from utils.helpers import save_uploaded_file, perform_ocr, export_to_csv, delete_receipt_file

st.title("📸 Receipt & Document Management")
st.caption("Files stored permanently in Supabase • Link to expenses or tasks")

tab1, tab2, tab3 = st.tabs(["💰 Upload Receipt", "📋 All Receipts", "🔗 Linked Receipts"])

# ====================== TAB 1: Upload Receipt ======================
with tab1:
    st.subheader("Upload Receipt")
    uploaded_file = st.file_uploader("Choose file (JPG, PNG, PDF)", type=["jpg", "jpeg", "png", "pdf"])
    
    if uploaded_file:
        file_url = save_uploaded_file(uploaded_file)
        st.success(f"✅ Uploaded to Supabase Cloud!")
        
        with st.form("receipt_metadata"):
            vendor = st.text_input("Vendor")
            amount = st.number_input("Amount $", min_value=0.01, value=0.01)
            category = st.text_input("Category", value="Electrical – Materials Only")
            notes = st.text_area("Notes")
            upload_date = st.date_input("Upload Date", date.today())

            # Link to Task (optional)
            link_to_task = st.checkbox("Link receipt to an existing task")
            task_id = None
            if link_to_task:
                conn = get_connection()
                task_options = pd.read_sql("""
                    SELECT id, title as label
                    FROM tasks
                    ORDER BY planned_start ASC
                """, conn)
                conn.close()
                if not task_options.empty:
                    selected_task = st.selectbox("Select Task", task_options['label'])
                    task_id = task_options[task_options['label'] == selected_task]['id'].iloc[0]
                else:
                    st.info("No tasks yet – add some in the Roadmap tab.")

            # OCR option
            if uploaded_file.type.startswith("image"):
                if st.form_submit_button("🔍 Run OCR"):
                    ocr_text = perform_ocr(uploaded_file)
                    st.text_area("OCR Result", ocr_text, height=150)

            submitted = st.form_submit_button("Save Receipt")
            if submitted:
                conn = get_connection()
                
                # Auto-create new expense from receipt data
                cat_id = conn.execute("SELECT id FROM budget_categories WHERE name=?", (category,)).fetchone()
                if cat_id:
                    cat_id = cat_id[0]
                else:
                    cat_id = conn.execute("SELECT id FROM budget_categories LIMIT 1").fetchone()[0]

                conn.execute("""INSERT INTO expenses
                    (category_id, date, amount, description, vendor)
                    VALUES (?,?,?,?,?)""",
                    (cat_id, upload_date.strftime("%Y-%m-%d"), amount,
                     f"Receipt: {vendor} - {notes[:50]}...", vendor))
                expense_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

                # Save the receipt
                conn.execute("""INSERT INTO receipts
                    (file_path, original_filename, upload_date, vendor, amount, category, notes,
                     linked_expense_id, linked_task_id, document_type, ocr_text)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (file_url, uploaded_file.name, upload_date.strftime("%Y-%m-%d"),
                     vendor, amount, category, notes, expense_id, task_id, "receipt",
                     perform_ocr(uploaded_file) if uploaded_file.type.startswith("image") else None))
                
                conn.commit()
                conn.close()
                st.success("✅ Receipt saved and new expense automatically created!")
                st.rerun()

# ====================== TAB 2: All Receipts (only shows receipts) ======================
with tab2:
    st.subheader("All Receipts")
    conn = get_connection()
    df = pd.read_sql("""
        SELECT id, original_filename, upload_date, vendor, amount, category, notes,
               file_path, linked_expense_id, linked_task_id
        FROM receipts 
        WHERE document_type = 'receipt'
        ORDER BY upload_date DESC
    """, conn)
    conn.close()
    
    st.dataframe(df.drop(columns=['file_path', 'linked_expense_id', 'linked_task_id']),
                 use_container_width=True, hide_index=True)
    
    st.subheader("Preview Selected Receipt")
    selected_id = st.selectbox("Choose receipt", df['id'] if not df.empty else [None],
                               format_func=lambda x: df[df['id']==x]['original_filename'].iloc[0] if x else "None")
    if selected_id:
        row = df[df['id'] == selected_id].iloc[0]
        
        st.image(row['file_path'], caption=row['original_filename'], use_column_width=True)
        
        col1, col2 = st.columns([3,1])
        with col1:
            st.link_button("📥 Download File", url=row['file_path'], use_container_width=True)
        with col2:
            if st.button("🗑️ Delete Receipt", type="secondary"):
                delete_receipt_file(row['file_path'])
                conn = get_connection()
                conn.execute("DELETE FROM receipts WHERE id=?", (selected_id,))
                conn.commit()
                conn.close()
                st.success("Receipt and file deleted")
                st.rerun()

# ====================== TAB 3: Linked Receipts ======================
with tab3:
    st.subheader("Receipts Linked to Expenses or Tasks")
    conn = get_connection()
    linked_df = pd.read_sql("""
        SELECT r.original_filename, r.amount, r.vendor,
               e.description as expense_desc, t.title as task_title, r.upload_date
        FROM receipts r
        LEFT JOIN expenses e ON r.linked_expense_id = e.id
        LEFT JOIN tasks t ON r.linked_task_id = t.id
        WHERE r.document_type = 'receipt'
        ORDER BY r.upload_date DESC
    """, conn)
    conn.close()
    st.dataframe(linked_df, use_container_width=True)

st.download_button("Export All Receipts CSV", export_to_csv("receipts"), "receipts.csv", "text/csv")
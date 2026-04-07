import streamlit as st
import pandas as pd
from datetime import date
from db.db_utils import get_connection
from utils.helpers import save_uploaded_file, perform_ocr, export_to_csv, delete_receipt_file
import os

st.title("📸 Receipt & Document Management")
st.caption("Uploads are now stored permanently in Supabase Cloud")

tab1, tab2, tab3 = st.tabs(["Upload New", "All Documents", "Linked Receipts"])

with tab1:
    st.subheader("Upload Receipt / Document")
    uploaded_file = st.file_uploader("Choose file (JPG, PNG, PDF)", type=["jpg", "jpeg", "png", "pdf"])
    
    if uploaded_file:
        file_url = save_uploaded_file(uploaded_file)
        st.success(f"✅ Uploaded to Supabase Cloud!")
        
        with st.form("receipt_metadata"):
            vendor = st.text_input("Vendor")
            amount = st.number_input("Amount $", min_value=0.01, value=0.01)
            category = st.text_input("Category (e.g. Electrical Materials)", value="Electrical – Materials Only")
            notes = st.text_area("Notes")
            upload_date = st.date_input("Upload Date", date.today())
            
            # OCR for images
            if uploaded_file.type.startswith("image"):
                if st.form_submit_button("🔍 Run OCR"):
                    ocr_text = perform_ocr(uploaded_file)  # local copy for OCR
                    st.text_area("OCR Result", ocr_text, height=150)
            
            link_to_expense = st.checkbox("Link to an existing expense")
            expense_id = None
            if link_to_expense:
                conn = get_connection()
                exp_options = pd.read_sql("SELECT id, description || ' ($' || amount || ')' as label FROM expenses", conn)
                conn.close()
                if not exp_options.empty:
                    selected = st.selectbox("Select Expense", exp_options['label'])
                    expense_id = exp_options[exp_options['label'] == selected]['id'].iloc[0]
            
            submitted = st.form_submit_button("Save Receipt")
            if submitted:
                conn = get_connection()
                conn.execute("""INSERT INTO receipts 
                    (file_path, original_filename, upload_date, vendor, amount, category, notes, linked_expense_id, ocr_text)
                    VALUES (?,?,?,?,?,?,?,?,?)""", 
                    (file_url, uploaded_file.name, upload_date.strftime("%Y-%m-%d"), 
                     vendor, amount, category, notes, expense_id, 
                     perform_ocr(uploaded_file) if uploaded_file.type.startswith("image") else None))
                conn.commit()
                conn.close()
                st.success("Receipt saved permanently in Supabase!")
                st.rerun()

with tab2:
    st.subheader("All Uploaded Documents")
    conn = get_connection()
    df = pd.read_sql("SELECT id, original_filename, upload_date, vendor, amount, category, notes, file_path FROM receipts ORDER BY upload_date DESC", conn)
    conn.close()
    
    st.dataframe(df.drop(columns=['file_path']), use_container_width=True, hide_index=True)
    
    # Preview
    st.subheader("Preview Selected Receipt")
    selected_id = st.selectbox("Choose receipt", df['id'] if not df.empty else [None], 
                               format_func=lambda x: df[df['id']==x]['original_filename'].iloc[0] if x else "None")
    if selected_id:
        row = df[df['id'] == selected_id].iloc[0]
        
        st.image(row['file_path'], caption=row['original_filename'], use_column_width=True)  # Supabase public URL works directly
        
        col1, col2 = st.columns([3,1])
        with col1:
            st.download_button("Download File", data="", file_name=row['original_filename'], 
                               url=row['file_path'])  # direct Supabase link
        with col2:
            if st.button("🗑️ Delete Receipt", type="secondary"):
                delete_receipt_file(row['file_path'])
                conn = get_connection()
                conn.execute("DELETE FROM receipts WHERE id=?", (selected_id,))
                conn.commit()
                conn.close()
                st.success("Receipt and file deleted from Supabase")
                st.rerun()

with tab3:
    st.subheader("Receipts Linked to Expenses")
    conn = get_connection()
    linked_df = pd.read_sql("""
        SELECT r.original_filename, r.amount, r.vendor, e.description as expense_desc, e.date
        FROM receipts r JOIN expenses e ON r.linked_expense_id = e.id
        ORDER BY r.upload_date DESC
    """, conn)
    conn.close()
    st.dataframe(linked_df, use_container_width=True)

st.download_button("Export All Receipts CSV", export_to_csv("receipts"), "receipts.csv", "text/csv")
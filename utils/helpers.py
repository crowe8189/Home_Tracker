import os
from datetime import datetime
from PIL import Image
import pandas as pd
from db.db_utils import get_connection
from supabase import create_client, Client
import streamlit as st

# Initialize Supabase client once
@st.cache_resource
def get_supabase_client() -> Client:
    if "SUPABASE_URL" not in st.secrets or "SUPABASE_ANON_KEY" not in st.secrets:
        st.error("❌ Supabase credentials missing in .streamlit/secrets.toml")
        st.stop()
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_ANON_KEY"]
    )

def save_uploaded_file(uploaded_file):
    """Upload to Supabase Storage and return permanent public URL"""
    supabase = get_supabase_client()
    bucket = st.secrets["SUPABASE_BUCKET"]
    
    # Create unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = f"receipts/{timestamp}_{uploaded_file.name}"
    
    # Upload - FIXED: use getvalue() to get bytes
    with st.spinner("Uploading receipt to Supabase Cloud..."):
        res = supabase.storage.from_(bucket).upload(
            file_path,
            uploaded_file.getvalue(),                    # ← This was the fix
            file_options={"content-type": uploaded_file.type}
        )
    
    # Get public URL
    public_url = supabase.storage.from_(bucket).get_public_url(file_path)
    return public_url

def delete_receipt_file(file_url: str):
    """Delete file from Supabase Storage"""
    if not file_url or "supabase.co" not in file_url:
        return
    supabase = get_supabase_client()
    bucket = st.secrets["SUPABASE_BUCKET"]
    # Extract path from URL
    path = file_url.split("/storage/v1/object/public/receipts/")[-1]
    supabase.storage.from_(bucket).remove([f"receipts/{path}"])

def perform_ocr(uploaded_file):
    try:
        import pytesseract
        # For OCR we need a file-like object or path
        text = pytesseract.image_to_string(Image.open(uploaded_file))
        return text.strip() or "No text detected."
    except Exception:
        return "OCR unavailable – install Tesseract OCR on your system."

def export_to_csv(table_name):
    conn = get_connection()
    df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return df.to_csv(index=False).encode('utf-8')

def import_csv(uploaded_csv, table_name):
    df = pd.read_csv(uploaded_csv)
    conn = get_connection()
    df.to_sql(table_name, conn, if_exists='append', index=False)
    conn.close()
import os
from datetime import datetime
from PIL import Image
import pandas as pd
import streamlit as st

# Local copy to avoid circular import
def is_cloud_mode():
    return "TURSO_URL" in st.secrets and "TURSO_AUTH_TOKEN" in st.secrets

# ====================== SUPABASE (only loaded in cloud mode) ======================
if is_cloud_mode():
    from supabase import create_client, Client

    @st.cache_resource
    def get_supabase_client() -> Client:
        return create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_ANON_KEY"]
        )

# ====================== SAVE / DELETE / OCR ======================
def save_uploaded_file(uploaded_file):
    if is_cloud_mode():
        supabase = get_supabase_client()
        bucket = st.secrets["SUPABASE_BUCKET"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = f"receipts/{timestamp}_{uploaded_file.name}"
        supabase.storage.from_(bucket).upload(
            file_path, uploaded_file.getvalue(),
            file_options={"content-type": uploaded_file.type}
        )
        return supabase.storage.from_(bucket).get_public_url(file_path)
    else:
        os.makedirs("uploads", exist_ok=True)
        path = os.path.join("uploads", uploaded_file.name)
        with open(path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return path

def delete_receipt_file(file_url: str):
    if is_cloud_mode() and "supabase.co" in str(file_url):
        try:
            supabase = get_supabase_client()
            bucket = st.secrets["SUPABASE_BUCKET"]
            path = file_url.split("/storage/v1/object/public/receipts/")[-1]
            supabase.storage.from_(bucket).remove([f"receipts/{path}"])
        except:
            pass
    elif not is_cloud_mode() and os.path.exists(file_url):
        try:
            os.remove(file_url)
        except:
            pass

def perform_ocr(uploaded_file):
    try:
        import pytesseract
        text = pytesseract.image_to_string(Image.open(uploaded_file))
        return text.strip() or "No text detected."
    except Exception:
        return "OCR unavailable – install Tesseract OCR on your system."

def export_to_csv(table_name):
    from db.db_utils import get_connection
    conn = get_connection()
    df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return df.to_csv(index=False).encode('utf-8')

def import_csv(uploaded_csv, table_name):
    from db.db_utils import get_connection
    df = pd.read_csv(uploaded_csv)
    conn = get_connection()
    df.to_sql(table_name, conn, if_exists='append', index=False)
    conn.close()
import os
from datetime import datetime
from PIL import Image
import pandas as pd
import streamlit as st


def is_cloud_mode():
    return "TURSO_URL" in st.secrets and "TURSO_AUTH_TOKEN" in st.secrets


# ====================== SUPABASE CLIENT ======================
@st.cache_resource
def get_supabase_client():
    """Cached Supabase client — only created when first called in cloud mode."""
    from supabase import create_client
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_ANON_KEY"]
    )


# ====================== FILE SAVE / DELETE / OCR ======================
def save_uploaded_file(uploaded_file):
    """Save file to Supabase (cloud) or local uploads/ (local). Returns URL or path."""
    if is_cloud_mode():
        try:
            supabase = get_supabase_client()
            bucket = st.secrets.get("SUPABASE_BUCKET", "receipts")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            object_path = f"receipts/{timestamp}_{uploaded_file.name}"
            supabase.storage.from_(bucket).upload(
                object_path,
                uploaded_file.getvalue(),
                file_options={"content-type": uploaded_file.type},
            )
            return supabase.storage.from_(bucket).get_public_url(object_path)
        except Exception as e:
            st.error(f"☁️ Cloud storage upload failed: {e}")
            return None
    else:
        os.makedirs("uploads", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = f"{timestamp}_{uploaded_file.name}"
        path = os.path.join("uploads", safe_name)
        with open(path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return path


def delete_receipt_file(file_url: str) -> bool:
    """Delete file from Supabase (cloud) or local filesystem (local)."""
    if not file_url:
        return False

    if is_cloud_mode() and "supabase.co" in str(file_url):
        try:
            supabase = get_supabase_client()
            bucket = st.secrets.get("SUPABASE_BUCKET", "receipts")
            marker = f"/storage/v1/object/public/{bucket}/"
            if marker in file_url:
                object_path = file_url.split(marker)[-1]
                supabase.storage.from_(bucket).remove([object_path])
            return True
        except Exception:
            return False
    elif not is_cloud_mode() and os.path.exists(file_url):
        try:
            os.remove(file_url)
            return True
        except Exception:
            return False
    return False


def perform_ocr(uploaded_file) -> str:
    try:
        import pytesseract
        uploaded_file.seek(0)
        text = pytesseract.image_to_string(Image.open(uploaded_file))
        return text.strip() or "No text detected."
    except Exception:
        return "OCR unavailable – install Tesseract OCR on your system."


# ====================== IMPORT / EXPORT ======================

_ALLOWED_TABLES = frozenset({
    "budget_categories", "expenses", "tasks", "receipts",
    "permits", "qol_ideas", "phases", "project_config",
})


def export_to_csv(table_name: str) -> bytes:
    if table_name not in _ALLOWED_TABLES:
        raise ValueError(f"Cannot export unknown table: {table_name}")
    from db.db_utils import get_connection, read_df
    conn = get_connection()
    df = read_df(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return df.to_csv(index=False).encode("utf-8")


def import_csv(uploaded_csv, table_name: str):
    if table_name not in _ALLOWED_TABLES:
        raise ValueError(f"Cannot import into unknown table: {table_name}")
    from db.db_utils import get_connection, DB_MODE
    df = pd.read_csv(uploaded_csv)
    conn = get_connection()
    if DB_MODE == "local":
        df.to_sql(table_name, conn, if_exists="append", index=False)
    else:
        # libsql: insert row by row
        cols = ", ".join(df.columns)
        placeholders = ", ".join(["?"] * len(df.columns))
        for _, row in df.iterrows():
            conn.execute(
                f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})",
                list(row),
            )
    conn.commit()
    conn.close()

import os
from datetime import datetime
from urllib.parse import urlsplit, unquote
from PIL import Image
import pandas as pd
import streamlit as st


def is_cloud_mode():
    return "TURSO_URL" in st.secrets and "TURSO_AUTH_TOKEN" in st.secrets


def _supabase_object_path_from_url(file_url: str, bucket: str) -> str | None:
    """Extract the object path (e.g. 'receipts/20260424_x.jpg') from a public URL.

    Returns None if the URL doesn't belong to this bucket. Strips query string
    and fragment, decodes percent-encoding.
    """
    if not file_url or not bucket:
        return None
    marker = f"/storage/v1/object/public/{bucket}/"
    parts = urlsplit(file_url)
    clean = f"{parts.scheme}://{parts.netloc}{parts.path}"
    if marker not in clean:
        return None
    tail = clean.split(marker, 1)[1]
    if not tail:
        return None
    return unquote(tail)


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
        missing = [k for k in ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_BUCKET")
                   if k not in st.secrets]
        if missing:
            st.error(
                f"⚠️ File uploads are not configured. Add the following to your Streamlit Cloud "
                f"secrets (share.streamlit.io → your app → Settings → Secrets): "
                f"{', '.join(missing)}"
            )
            return None
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
    """Delete the underlying file from Supabase (cloud) or local disk (local).

    Returns True only when the storage backend confirms the file was removed.
    Returns False on any of: empty URL, non-matching bucket, missing file,
    Supabase reporting an empty result, or any exception.
    """
    if not file_url:
        return False

    if is_cloud_mode() and "supabase.co" in str(file_url):
        try:
            bucket = st.secrets.get("SUPABASE_BUCKET", "receipts")
            object_path = _supabase_object_path_from_url(file_url, bucket)
            if not object_path:
                return False

            supabase = get_supabase_client()
            response = supabase.storage.from_(bucket).remove([object_path])

            # supabase-py v2 returns a list of removed FileObject dicts.
            if isinstance(response, list):
                return len(response) > 0
            # Some client versions wrap the result as {"data": [...], "error": ...}.
            if isinstance(response, dict):
                err = response.get("error")
                data = response.get("data") or []
                return bool(data) and not err
            return False
        except Exception:
            return False

    if not is_cloud_mode():
        if file_url and os.path.exists(file_url):
            try:
                os.remove(file_url)
                return True
            except Exception:
                return False
        return False

    return False


def reconcile_supabase_with_db(conn) -> int:
    """Cloud only: list bucket objects and delete DB rows whose Supabase file is gone.

    Returns the number of ghost rows pruned. Safely no-ops (returns 0) when
    Supabase isn't fully configured or any error occurs, so app startup is
    never blocked by a transient Supabase outage.
    """
    if not is_cloud_mode():
        return 0
    for k in ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_BUCKET"):
        if k not in st.secrets:
            return 0

    try:
        bucket = st.secrets["SUPABASE_BUCKET"]
        supabase = get_supabase_client()

        objects = supabase.storage.from_(bucket).list(
            "receipts", {"limit": 1000, "offset": 0}
        )
        if not isinstance(objects, list):
            return 0
        valid_paths = {
            f"receipts/{obj['name']}"
            for obj in objects
            if isinstance(obj, dict) and obj.get("name")
        }

        rows = conn.execute(
            "SELECT id, file_path FROM receipts WHERE file_path LIKE 'http%'"
        ).fetchall()

        ghost_ids = []
        for row in rows:
            rid = row[0]
            url = row[1] or ""
            object_path = _supabase_object_path_from_url(url, bucket)
            if object_path is None:
                continue
            if object_path not in valid_paths:
                ghost_ids.append(rid)

        for rid in ghost_ids:
            conn.execute("DELETE FROM receipts WHERE id=?", (int(rid),))
        if ghost_ids:
            conn.commit()
        return len(ghost_ids)
    except Exception as e:
        print(f"⚠️ Bucket reconciliation skipped: {e}")
        return 0


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

import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="Inspo Board", layout="wide", page_icon="🌿")

from db.db_utils import get_connection, init_db, read_df
from utils.helpers import save_uploaded_file, delete_receipt_file
from utils.sidebar import render_sidebar

if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

render_sidebar()

st.title("🌿 Inspo Board")
st.caption("Design ideas and inspiration — upload photos for rooms and finishes you want in the build")

# ── Upload ────────────────────────────────────────────────────────────────
with st.container(border=True):
    st.subheader("➕ Add Inspiration Photo")
    uploaded = st.file_uploader(
        "Upload a photo or screenshot",
        type=["jpg", "jpeg", "png"],
        key="inspo_upload",
    )
    if uploaded:
        with st.form("inspo_form"):
            room = st.text_input(
                "Room / Area",
                placeholder="e.g. Kitchen, Master Bath, Living Room, Exterior…",
            )
            description = st.text_area("Notes (optional)", height=60)

            if st.form_submit_button("✅ Save to Inspo Board", type="primary"):
                notes_combined = (
                    f"{room}: {description}" if room and description
                    else room or description or ""
                )
                url = save_uploaded_file(uploaded)
                if url:
                    conn = get_connection()
                    conn.execute("""
                        INSERT INTO receipts
                            (file_path, original_filename, upload_date, notes, file_category)
                        VALUES (?,?,?,?,?)
                    """, (url, uploaded.name, date.today().strftime("%Y-%m-%d"),
                          notes_combined, "inspo"))
                    conn.commit()
                    conn.close()
                    st.success("✅ Added to Inspo Board!")
                    st.rerun()

st.divider()

# ── Inspo grid ────────────────────────────────────────────────────────────
conn = get_connection()
inspo_df = read_df("""
    SELECT id, file_path, original_filename, upload_date, notes
    FROM receipts
    WHERE file_category = 'inspo'
    ORDER BY upload_date DESC
""", conn)
conn.close()

if inspo_df.empty:
    st.info("No inspo photos yet — add some above to build your mood board!")
else:
    # Extract room label (text before first ":" in notes, if present)
    def _room(notes_val):
        s = str(notes_val or "").strip()
        if ":" in s:
            return s.split(":", 1)[0].strip() or "General"
        return s or "General"

    inspo_df["room"] = inspo_df["notes"].apply(_room)
    rooms = inspo_df["room"].unique()

    COLS = 3
    for room in rooms:
        grp = inspo_df[inspo_df["room"] == room]
        st.subheader(f"🏠 {room}  ({len(grp)})")

        for i in range(0, len(grp), COLS):
            chunk = grp.iloc[i:i + COLS]
            cols  = st.columns(COLS)
            for j, (_, photo) in enumerate(chunk.iterrows()):
                pid = int(photo["id"])
                fp  = str(photo.get("file_path", ""))
                fn  = str(photo.get("original_filename", "")).lower()
                with cols[j]:
                    with st.container(border=True):
                        if fn.endswith((".jpg", ".jpeg", ".png")) and fp.startswith("http"):
                            st.image(fp, use_container_width=True)

                        # Show description (the part after "Room: ")
                        notes_raw = str(photo.get("notes", "") or "")
                        desc = notes_raw.split(":", 1)[1].strip() if ":" in notes_raw else notes_raw
                        if desc:
                            st.caption(desc[:120])
                        st.caption(str(photo.get("upload_date", ""))[:10])

                        col_dl, col_del = st.columns([3, 1])
                        with col_dl:
                            if fp.startswith("http"):
                                st.link_button("⬇️", url=fp, key=f"inspo_dl_{pid}")
                        with col_del:
                            if st.button("🗑️", key=f"inspo_del_{pid}"):
                                delete_receipt_file(fp)
                                c = get_connection()
                                c.execute("DELETE FROM receipts WHERE id=?", (pid,))
                                c.commit()
                                c.close()
                                st.rerun()

st.caption("🌿 Inspo Board")

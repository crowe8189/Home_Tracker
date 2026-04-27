import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="Build Photos", layout="wide", page_icon="📸")

from db.db_utils import get_connection, init_db, read_df, get_current_focus
from utils.helpers import save_uploaded_file, delete_receipt_file
from utils.ai_assistant import classify_photo_url
from utils.sidebar import render_sidebar

if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

render_sidebar()

st.title("📸 Build Photos")
st.caption("Progress photos organized by phase, timeline, and search")


# ── Photo grid helper ─────────────────────────────────────────────────────
def _render_grid(df, key_prefix, cols=3):
    """Render photos as a responsive grid with download + delete per card."""
    for i in range(0, len(df), cols):
        chunk = df.iloc[i:i + cols]
        grid  = st.columns(cols)
        for j, (_, photo) in enumerate(chunk.iterrows()):
            pid = int(photo["id"])
            fp  = str(photo.get("file_path", ""))
            fn  = str(photo.get("original_filename", "")).lower()
            with grid[j]:
                with st.container(border=True):
                    if fn.endswith((".jpg", ".jpeg", ".png")) and fp.startswith("http"):
                        st.image(fp, use_container_width=True)
                    elif fn.endswith((".jpg", ".jpeg", ".png")):
                        st.caption("🖼️ Missing")
                    notes_val = str(photo.get("notes", "") or "")
                    if notes_val:
                        st.caption(notes_val[:80])
                    auto_tag  = str(photo.get("auto_tag", "") or "")
                    date_str  = str(photo.get("upload_date", ""))[:10]
                    st.caption(f"{date_str}{'  🏷️ ' + auto_tag if auto_tag else ''}")
                    col_dl, col_del = st.columns([3, 1])
                    with col_dl:
                        if fp.startswith("http"):
                            st.link_button("⬇️", url=fp, key=f"{key_prefix}_dl_{pid}")
                    with col_del:
                        if st.button("🗑️", key=f"{key_prefix}_del_{pid}"):
                            delete_receipt_file(fp)
                            c = get_connection()
                            c.execute("DELETE FROM receipts WHERE id=?", (pid,))
                            c.commit()
                            c.close()
                            st.rerun()


# ── Upload ────────────────────────────────────────────────────────────────
with st.expander("➕ Upload Build Photo", expanded=False):
    current_focus = get_current_focus()
    uploaded = st.file_uploader(
        "Take or choose a photo", type=["jpg", "jpeg", "png"], key="photos_up"
    )
    if uploaded:
        with st.form("photo_upload_form"):
            notes_in = st.text_area("Notes / Description", height=60)

            conn_t = get_connection()
            tasks_df = read_df("""
                SELECT t.id, t.title, p.name AS phase_name
                FROM tasks t JOIN phases p ON t.phase_id = p.id
                ORDER BY p.order_num, t.planned_start
            """, conn_t)
            conn_t.close()

            task_opts = ["(none)"] + [
                f"{r['phase_name']} → {r['title']}" for _, r in tasks_df.iterrows()
            ]
            default_i = 0
            if current_focus.get("task"):
                for idx, opt in enumerate(task_opts):
                    if current_focus["task"]["title"] in opt:
                        default_i = idx
                        break

            link_to = st.selectbox("Link to task (optional)", task_opts, index=default_i)
            task_id = None
            if link_to != "(none)":
                sel_idx = task_opts.index(link_to) - 1
                task_id = int(tasks_df.iloc[sel_idx]["id"])

            if st.form_submit_button("✅ Save", type="primary"):
                url = save_uploaded_file(uploaded)
                if url:
                    conn2 = get_connection()
                    conn2.execute("""
                        INSERT INTO receipts
                            (file_path, original_filename, upload_date, notes,
                             file_category, linked_task_id)
                        VALUES (?,?,?,?,?,?)
                    """, (url, uploaded.name, date.today().strftime("%Y-%m-%d"),
                          notes_in, "photo", task_id))
                    conn2.commit()
                    conn2.close()
                    st.success("✅ Saved!")
                    st.rerun()

# ── Tabs ──────────────────────────────────────────────────────────────────
tab_phase, tab_timeline, tab_search = st.tabs(["📂 By Phase", "📅 Timeline", "🔍 Search"])


# ====================== TAB 1: BY PHASE ======================
with tab_phase:
    conn = get_connection()
    photos = read_df("""
        SELECT
            r.id, r.file_path, r.original_filename,
            r.upload_date, r.notes, r.linked_task_id, r.auto_tag,
            t.title     AS task_title,
            p.name      AS phase_name,
            p.order_num AS phase_order
        FROM receipts r
        LEFT JOIN tasks  t ON r.linked_task_id = t.id
        LEFT JOIN phases p ON t.phase_id = p.id
        WHERE r.file_category IN ('photo', 'quick_log')
        ORDER BY
            CASE WHEN p.order_num IS NULL THEN 999999 ELSE p.order_num END,
            r.upload_date DESC
    """, conn)
    all_tasks = read_df("""
        SELECT t.id, t.title, p.name AS phase_name
        FROM tasks t JOIN phases p ON t.phase_id = p.id
        ORDER BY p.order_num, t.planned_start
    """, conn)
    conn.close()

    if photos.empty:
        st.info("No build photos yet — upload one above or use ➕ Quick Log from the sidebar.")
    else:
        tagged   = photos[photos["phase_name"].notna()].copy()
        untagged = photos[photos["phase_name"].isna()].copy()

        # ── AI auto-tag backfill ──────────────────────────────────────────
        with st.expander("🤖 AI Auto-Tag", expanded=False):
            needs_tag = photos[photos["auto_tag"].isna() | (photos["auto_tag"] == "")]
            if "GROQ_API_KEY" not in st.secrets:
                st.info(
                    "Add **GROQ_API_KEY** to Streamlit Cloud Secrets to enable AI photo tagging. "
                    "Llama Vision via Groq will classify each photo into a construction category."
                )
            elif needs_tag.empty:
                st.success("✅ All photos have an AI tag.")
            else:
                st.caption(f"{len(needs_tag)} photo(s) without an AI tag")
                if st.button("🤖 Auto-Tag All", type="primary", key="autotag_all"):
                    bar   = st.progress(0, text="Classifying…")
                    total = len(needs_tag)
                    for i, (_, photo) in enumerate(needs_tag.iterrows()):
                        tag = classify_photo_url(str(photo["file_path"]))
                        if tag:
                            c_tag = get_connection()
                            c_tag.execute(
                                "UPDATE receipts SET auto_tag=? WHERE id=?",
                                (tag, int(photo["id"])),
                            )
                            c_tag.commit()
                            c_tag.close()
                        bar.progress((i + 1) / total, text=f"Tagged {i + 1}/{total}…")
                    st.success("✅ Done!")
                    st.rerun()

        # ── Filter chips by AI tag ────────────────────────────────────────
        available_tags = sorted(t for t in photos["auto_tag"].dropna().unique() if t)
        active_tags: list = []
        if available_tags:
            active_tags = st.multiselect(
                "🏷️ Filter by AI tag", available_tags, key="phase_tag_filter"
            )
            if active_tags:
                tagged   = tagged[tagged["auto_tag"].isin(active_tags)]
                untagged = untagged[untagged["auto_tag"].isin(active_tags)]

        # Render one section per phase, in phase order
        if not tagged.empty:
            phase_order = (
                tagged[["phase_name", "phase_order"]]
                .drop_duplicates()
                .sort_values("phase_order")
            )
            for _, pr in phase_order.iterrows():
                grp = tagged[tagged["phase_name"] == pr["phase_name"]]
                st.subheader(f"🏗️ {pr['phase_name']}  ({len(grp)})")
                _render_grid(grp.reset_index(drop=True),
                             key_prefix=f"ph_{pr['phase_name'].replace(' ', '_')}")

        # Untagged section with inline task-backfill
        if not untagged.empty:
            with st.expander(
                f"📎 Untagged — {len(untagged)} photo(s) (tap Tag to assign)", expanded=True
            ):
                task_opts_bf = ["(skip)"] + [
                    f"{r['phase_name']} → {r['title']}" for _, r in all_tasks.iterrows()
                ]
                for i in range(0, len(untagged), 3):
                    chunk = untagged.iloc[i:i + 3]
                    grid  = st.columns(3)
                    for j, (_, photo) in enumerate(chunk.iterrows()):
                        pid = int(photo["id"])
                        fp  = str(photo.get("file_path", ""))
                        fn  = str(photo.get("original_filename", "")).lower()
                        with grid[j]:
                            with st.container(border=True):
                                if fn.endswith((".jpg", ".jpeg", ".png")) and fp.startswith("http"):
                                    st.image(fp, use_container_width=True)
                                st.caption(str(photo.get("upload_date", ""))[:10])
                                sel = st.selectbox(
                                    "Link to",
                                    task_opts_bf,
                                    key=f"tag_sel_{pid}",
                                    label_visibility="collapsed",
                                )
                                col_t, col_d = st.columns(2)
                                with col_t:
                                    if st.button("🏷️ Tag", key=f"tag_btn_{pid}",
                                                 use_container_width=True):
                                        if sel != "(skip)":
                                            new_tid = int(
                                                all_tasks.iloc[
                                                    task_opts_bf.index(sel) - 1
                                                ]["id"]
                                            )
                                            c3 = get_connection()
                                            c3.execute(
                                                "UPDATE receipts SET linked_task_id=? WHERE id=?",
                                                (new_tid, pid),
                                            )
                                            c3.commit()
                                            c3.close()
                                            st.rerun()
                                with col_d:
                                    if st.button("🗑️", key=f"del_ut_{pid}",
                                                 use_container_width=True):
                                        delete_receipt_file(fp)
                                        c4 = get_connection()
                                        c4.execute("DELETE FROM receipts WHERE id=?", (pid,))
                                        c4.commit()
                                        c4.close()
                                        st.rerun()


# ====================== TAB 2: TIMELINE ======================
with tab_timeline:
    conn = get_connection()
    tl_df = read_df("""
        SELECT id, file_path, original_filename, upload_date, notes, auto_tag
        FROM receipts
        WHERE file_category IN ('photo', 'quick_log')
        ORDER BY upload_date DESC
    """, conn)
    conn.close()

    if tl_df.empty:
        st.info("No build photos yet.")
    else:
        tl_df["upload_date"] = pd.to_datetime(tl_df["upload_date"], errors="coerce")
        tl_df["month"] = tl_df["upload_date"].dt.to_period("M")

        for month, grp in tl_df.groupby("month", sort=False):
            label = pd.Period(month, "M").strftime("%B %Y")
            with st.expander(f"📅 {label} — {len(grp)} photo(s)", expanded=True):
                _render_grid(grp.reset_index(drop=True), key_prefix=f"tl_{month}")


# ====================== TAB 3: SEARCH ======================
with tab_search:
    q = st.text_input(
        "Search", placeholder="foundation, pour, crane, dirtwork…",
        label_visibility="collapsed", key="photos_search"
    )
    if q.strip():
        conn = get_connection()
        results = read_df("""
            SELECT id, file_path, original_filename, upload_date, notes, auto_tag
            FROM receipts
            WHERE file_category IN ('photo', 'quick_log')
              AND (notes LIKE ? OR original_filename LIKE ? OR auto_tag LIKE ?)
            ORDER BY upload_date DESC
        """, conn, params=(f"%{q}%", f"%{q}%", f"%{q}%"))
        conn.close()

        if results.empty:
            st.info(f'No photos match "{q}"')
        else:
            st.caption(f"{len(results)} result(s) for **{q}**")
            _render_grid(results.reset_index(drop=True), key_prefix="srch")
    else:
        st.caption("Type above to search across photo notes, filenames, and AI tags.")

st.caption("📸 Build Photos")

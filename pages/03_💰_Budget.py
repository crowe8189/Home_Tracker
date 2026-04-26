import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="Budget", layout="wide", page_icon="💰")

from db.db_utils import get_connection, get_current_focus, init_db, read_df
from utils.helpers import save_uploaded_file, perform_ocr, export_to_csv, import_csv
from utils.sidebar import render_sidebar

if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

render_sidebar()
st.title("💰 Budget & Financial Tracking")

tab1, tab2, tab3 = st.tabs(["Categories", "Expenses + Receipts", "Import/Export"])

# ====================== TAB 1: Categories ======================
with tab1:
    st.subheader("Budget Categories")
    conn = get_connection()
    df = read_df("SELECT * FROM budget_categories", conn)
    conn.close()
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption("Electrical category: owner labor — materials cost only.")

# ====================== TAB 2: Expenses + Receipts ======================
with tab2:
    st.subheader("Expenses & Receipts")

    with st.expander("➕ Add New Expense + Receipt", expanded=True):
        with st.form("add_expense_form"):
            colA, colB = st.columns(2)
            with colA:
                date_input = st.date_input("Date", date.today())
                amount     = st.number_input("Amount $", min_value=0.01, value=0.01, step=0.01)
                vendor     = st.text_input("Vendor")

            with colB:
                conn = get_connection()
                cats = read_df("SELECT id, name FROM budget_categories", conn)
                conn.close()
                category = st.selectbox("Category", cats["name"].tolist(), index=0)
                cat_id   = int(cats[cats["name"] == category]["id"].iloc[0])

            description = st.text_input("Description", placeholder="e.g. Lumber for framing")
            uploaded_receipt = st.file_uploader(
                "Attach receipt / scan (JPG, PNG, PDF)", type=["jpg", "jpeg", "png", "pdf"]
            )

            # Smart auto-link
            current_focus = get_current_focus()
            link_options  = ["None"]
            default_index = 0
            if current_focus.get("task"):
                link_options.append(f"Current Task: {current_focus['task']['title']}")
                default_index = 1
            if current_focus.get("permit"):
                link_options.append(f"Current Permit: {current_focus['permit']['name']}")
                if not current_focus.get("task"):
                    default_index = 1

            link_to  = st.selectbox("Link to", link_options, index=default_index)
            task_id  = permit_id = None
            if "Task" in link_to and current_focus.get("task"):
                task_id = current_focus["task"]["id"]
            elif "Permit" in link_to and current_focus.get("permit"):
                permit_id = current_focus["permit"]["id"]

            if st.form_submit_button("💾 Save Expense + Receipt", type="primary"):
                conn = get_connection()
                conn.execute("""
                    INSERT INTO expenses (category_id, date, amount, description, vendor)
                    VALUES (?,?,?,?,?)
                """, (cat_id, date_input.strftime("%Y-%m-%d"), amount, description, vendor))
                expense_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

                if uploaded_receipt:
                    file_url = save_uploaded_file(uploaded_receipt)
                    ocr_text = (
                        perform_ocr(uploaded_receipt)
                        if uploaded_receipt.type.startswith("image")
                        else None
                    )
                    if file_url:
                        conn.execute("""
                            INSERT INTO receipts
                                (file_path, original_filename, upload_date, vendor, amount, notes,
                                 linked_expense_id, linked_task_id, linked_permit_id,
                                 file_category, document_type, ocr_text)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                        """, (
                            file_url, uploaded_receipt.name,
                            date_input.strftime("%Y-%m-%d"),
                            vendor, amount, description,
                            expense_id, task_id, permit_id,
                            "receipt", "document", ocr_text,
                        ))

                conn.commit()
                conn.close()
                st.success("✅ Expense and receipt saved!")
                st.rerun()

    # Existing expenses
    st.subheader("All Expenses")
    conn = get_connection()
    df_exp = read_df("""
        SELECT e.id, e.date, e.amount, e.description, e.vendor,
               c.name AS category, r.original_filename AS receipt
        FROM expenses e
        LEFT JOIN budget_categories c ON e.category_id = c.id
        LEFT JOIN receipts r          ON e.id = r.linked_expense_id
        ORDER BY e.date DESC
    """, conn)
    conn.close()

    edited_exp = st.data_editor(
        df_exp,
        use_container_width=True,
        num_rows="fixed",
        hide_index=True,
        column_config={"id": st.column_config.NumberColumn(disabled=True)},
    )

    if st.button("💾 Save Expense Changes", type="primary"):
        conn = get_connection()
        for _, row in edited_exp.iterrows():
            cat_id_row = conn.execute(
                "SELECT id FROM budget_categories WHERE name=?", (row["category"],)
            ).fetchone()
            if cat_id_row:
                conn.execute("""
                    UPDATE expenses
                    SET date=?, amount=?, description=?, vendor=?, category_id=?
                    WHERE id=?
                """, (
                    row["date"], row["amount"], row["description"],
                    row["vendor"], cat_id_row[0], int(row["id"]),
                ))
        conn.commit()
        conn.close()
        st.success("Expenses updated!")
        st.rerun()

# ====================== TAB 3: Import / Export ======================
with tab3:
    st.subheader("Import / Export")
    st.download_button(
        "⬇️ Export Expenses CSV",
        export_to_csv("expenses"),
        "expenses.csv",
        "text/csv",
    )
    if uploaded := st.file_uploader("Import CSV", type="csv"):
        import_csv(uploaded, "expenses")
        st.success("Imported!")

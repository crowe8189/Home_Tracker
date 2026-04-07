import streamlit as st
from db.db_utils import get_connection
from utils.helpers import export_to_csv, import_csv
import pandas as pd
from datetime import date

st.title("💰 Budget & Financial Tracking")

tab1, tab2, tab3, tab4 = st.tabs(["Categories", "Expenses", "Forecast", "Import/Export"])

with tab1:
    st.subheader("Budget Categories")
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM budget_categories", conn)
    st.dataframe(df, use_container_width=True)
    conn.close()
    st.caption("Electrical category has permanent owner-labor note")

with tab2:
    st.subheader("Expenses")
    conn = get_connection()
    df_exp = pd.read_sql("SELECT * FROM expenses", conn)
    conn.close()

    edited_exp = st.data_editor(
        df_exp,
        use_container_width=True,
        num_rows="fixed",
        column_config={"id": st.column_config.NumberColumn(disabled=True)}
    )

    if st.button("💾 Save Expense Changes", type="primary"):
        conn = get_connection()
        for _, row in edited_exp.iterrows():
            conn.execute("""UPDATE expenses 
                            SET date=?, amount=?, description=?, vendor=?, category_id=?
                            WHERE id=?""",
                         (row['date'], row['amount'], row['description'], 
                          row['vendor'], row['category_id'], row['id']))
        conn.commit()
        conn.close()
        st.success("Expenses updated!")
        st.rerun()

    # Delete
    if not df_exp.empty:
        del_id = st.selectbox("Delete Expense", df_exp['id'].tolist(), format_func=lambda x: f"ID {x}")
        if st.button("🗑️ Delete"):
            conn = get_connection()
            conn.execute("DELETE FROM expenses WHERE id=?", (del_id,))
            conn.commit()
            conn.close()
            st.success("Expense deleted")
            st.rerun()

with tab3:
    st.subheader("Forecast")
    st.info("Based on current spend rate, projected finish cost is under budget (mock – real forecast uses trend line above).")

with tab4:
    st.download_button("Export Expenses CSV", export_to_csv("expenses"), "expenses.csv", "text/csv")
    if uploaded := st.file_uploader("Import CSV", type="csv"):
        import_csv(uploaded, "expenses")
        st.success("Imported!")
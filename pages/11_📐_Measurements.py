import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="Measurements", layout="wide", page_icon="📐")

from db.db_utils import (
    init_db, get_measurements, get_measurement_categories,
    save_measurement_actual, upsert_measurement_rows, measurement_progress,
)
from utils.sidebar import render_sidebar
from utils.measurement_seed import get_seed_rows

if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

# Seed the model values once (if the table is empty). Re-import refreshes them.
if get_measurements().empty:
    upsert_measurement_rows(get_seed_rows())

render_sidebar()

st.title("📐 Field Measurements")
st.caption("Model dimensions vs. your tape readings at the framed house. "
           "Enter actuals on-site; we'll use them to refine the FreeCAD model.")


# ---------- helpers ----------
def ft_to_label(v):
    if v is None or pd.isna(v):
        return "—"
    sign = "-" if v < 0 else ""
    v = abs(float(v))
    ft = int(v)
    inch = round((v - ft) * 12.0)
    if inch == 12:
        ft += 1; inch = 0
    return "%s%d'-%d\"" % (sign, ft, inch)


STATUS_ICON = {"verified": "✅", "mismatch": "⚠️", "not_measured": "⬜"}


# ---------- progress + tools ----------
done, total = measurement_progress()
pct = (done / total) if total else 0
c1, c2 = st.columns([3, 1])
with c1:
    st.progress(pct, text=f"{done} / {total} measured ({pct*100:.0f}%)")
with c2:
    if st.button("🔄 Re-import model", use_container_width=True,
                 help="Refresh model values from the latest FreeCAD export "
                      "(keeps your entered actuals)."):
        st.session_state["_show_import"] = True

if st.session_state.get("_show_import"):
    with st.expander("Refresh model values", expanded=True):
        st.write("Upload the **house_measurements.csv** exported by the FreeCAD "
                 "macro, or it will load from the local `exports/` folder if found.")
        up = st.file_uploader("house_measurements.csv", type=["csv"], key="meas_csv")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Import uploaded CSV", type="primary", use_container_width=True,
                         disabled=up is None):
                try:
                    df = pd.read_csv(up)
                    rows = df.to_dict("records")
                    ins, upd = upsert_measurement_rows(rows)
                    st.success(f"Imported: {ins} new, {upd} updated.")
                    st.session_state["_show_import"] = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Import failed: {e}")
        with col_b:
            if st.button("Load from exports/ folder", use_container_width=True):
                try:
                    df = pd.read_csv("exports/house_measurements.csv")
                    ins, upd = upsert_measurement_rows(df.to_dict("records"))
                    st.success(f"Loaded: {ins} new, {upd} updated.")
                    st.session_state["_show_import"] = False
                    st.rerun()
                except FileNotFoundError:
                    st.warning("No exports/house_measurements.csv found.")
                except Exception as e:
                    st.error(f"Load failed: {e}")

st.divider()

# ---------- filter ----------
cats = get_measurement_categories()
view = st.radio("Show", ["To measure", "All"], horizontal=True, index=0)

# ---------- per-category, per-item entry (mobile friendly) ----------
for cat in cats:
    df = get_measurements(cat)
    if df.empty:
        continue
    if view == "To measure":
        df = df[df["status"] == "not_measured"]
        if df.empty:
            continue

    cat_done = (get_measurements(cat)["status"] != "not_measured").sum()
    cat_total = len(get_measurements(cat))
    with st.expander(f"{cat}  ·  {cat_done}/{cat_total} measured",
                     expanded=(cat in ("Envelope", "Division lines"))):

        # group rows by item so all dims of one room sit together
        for item, grp in df.groupby("item", sort=False):
            st.markdown(f"**{item}**")
            for _, r in grp.iterrows():
                icon = STATUS_ICON.get(r["status"], "⬜")
                model_lbl = r["model_value_label"] or ft_to_label(r["model_value_ft"])
                actual = None if pd.isna(r["actual_value_ft"]) else float(r["actual_value_ft"])
                delta = (actual - float(r["model_value_ft"])) if actual is not None else None

                cc = st.columns([2.2, 2, 2, 1.4])
                with cc[0]:
                    st.markdown(f"{icon} {r['dimension']}")
                    st.caption(f"model: {model_lbl}")
                with cc[1]:
                    new_actual = st.number_input(
                        "actual (ft)", value=actual if actual is not None else 0.0,
                        step=0.0833, format="%.3f", key=f"act_{r['key']}",
                        label_visibility="collapsed",
                    )
                with cc[2]:
                    if delta is not None:
                        sign = "+" if delta >= 0 else "−"
                        st.metric("Δ", f"{sign}{ft_to_label(abs(delta))}",
                                  label_visibility="collapsed")
                    else:
                        st.caption("Δ —")
                with cc[3]:
                    if st.button("Save", key=f"save_{r['key']}", use_container_width=True):
                        d = new_actual - float(r["model_value_ft"])
                        # within ~1/4" => verified, else mismatch
                        status = "verified" if abs(d) <= 0.021 else "mismatch"
                        save_measurement_actual(
                            r["key"], new_actual, status, r["notes"] or "",
                            date.today().strftime("%Y-%m-%d"),
                        )
                        st.rerun()
            st.divider()

# ---------- summary of mismatches (drives model revisions) ----------
all_df = get_measurements()
mm = all_df[all_df["status"] == "mismatch"].copy()
if not mm.empty:
    st.subheader("⚠️ Mismatches to revise in the model")
    mm["model"] = mm["model_value_ft"].apply(ft_to_label)
    mm["actual"] = mm["actual_value_ft"].apply(ft_to_label)
    mm["Δ"] = (mm["actual_value_ft"] - mm["model_value_ft"]).apply(
        lambda v: ("+" if v >= 0 else "−") + ft_to_label(abs(v)))
    st.dataframe(
        mm[["category", "item", "dimension", "model", "actual", "Δ"]],
        use_container_width=True, hide_index=True,
    )
    st.download_button(
        "⬇️ Download actuals (CSV)",
        all_df.to_csv(index=False).encode("utf-8"),
        file_name=f"measured_actuals_{date.today()}.csv",
        mime="text/csv",
    )

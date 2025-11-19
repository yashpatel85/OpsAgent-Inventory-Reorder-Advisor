"""
Streamlit UI for OpsAgent — Inventory & Reorder Advisor.

Features added:
 - Upload sales & suppliers or use sample data
 - Editable suppliers table (st.data_editor) with pack_size, lead_time, current/target stock
 - Compute recommendations and download as JSON or CSV
 - Simple parameter controls (z-score, window, min_order_qty)
"""
import os
import json
from datetime import datetime
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import sys, pathlib

ROOT = str(pathlib.Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.data_utils import load_sales, load_suppliers, aggregate_daily, compute_rolling_features
from app.heuristics import compute_recommendation

# optional OpenAI wrapper (same as run_reorder)
try:
    import openai
except Exception:
    openai = None

def get_llm_callable():
    key = os.environ.get("OPENAI_API_KEY")
    if key and openai is not None:
        def _call(prompt: str) -> str:
            openai.api_key = key
            resp = openai.Completion.create(
                engine="text-davinci-003",
                prompt=prompt,
                max_tokens=40,
                temperature=0.3,
                n=1,
            )
            return resp["choices"][0]["text"].strip()
        return _call
    return None

st.set_page_config(page_title="OpsAgent — Inventory & Reorder Advisor", layout="wide")
st.title("OpsAgent — Inventory & Reorder Advisor")
st.markdown("Upload sales and supplier CSVs, inspect demand, edit supplier parameters, and compute reorder recommendations.")

# Sidebar for parameters
with st.sidebar:
    st.header("Global parameters")
    z = st.number_input("z-score (safety stock)", value=1.65, step=0.01, format="%.2f")
    window = st.selectbox("Rolling window for avg/sigma", options=[7,14,28], index=1)
    min_order_qty = st.number_input("Min order quantity if >0", value=1, step=1)
    as_of_date = st.date_input("As of date (for recommendation)", value=datetime.today().date())
    st.markdown("---")
    st.markdown("LLM")
    if os.environ.get("OPENAI_API_KEY"):
        st.success("OpenAI key detected — will generate short rationales.")
    else:
        st.info("No OpenAI key — using deterministic template rationales.")

# Data upload / sample toggle
col1, col2 = st.columns([2,1])
with col1:
    st.header("Data upload / sample")
    sales_file = st.file_uploader("Upload sales_history.csv (date, sku, qty_sold)", type=["csv"])
    suppliers_file = st.file_uploader("Upload suppliers.csv (sku,lead_time_days,current_stock,target_stock[,pack_size])", type=["csv"])
    use_sample = st.checkbox("Use sample CSVs in /data/ (if no upload)", value=True)

    if not sales_file and not use_sample:
        st.warning("Please upload sales_history.csv or enable sample data.")
        st.stop()

    # load sales
    if sales_file:
        sales = pd.read_csv(sales_file, parse_dates=["date"])
    else:
        sales = load_sales(os.path.join(ROOT, "data", "sales_history.csv"))

    # load or default suppliers
    if suppliers_file:
        suppliers = pd.read_csv(suppliers_file)
    else:
        suppliers = load_suppliers(os.path.join(ROOT, "data", "suppliers.csv"))

    st.success("Data loaded.")
    st.write("Sales sample (first 10 rows):")
    st.dataframe(sales.head(10))

with col2:
    st.header("Quick actions")
    if st.button("Generate sample data"):
        os.system(f'python "{os.path.join(ROOT,"scripts","generate_sample_data.py")}"')
        st.experimental_rerun()

# Editable suppliers table
st.header("Supplier parameters (editable)")
# Ensure columns exist and types
sup_df = suppliers.copy()
for c in ["lead_time_days","current_stock","target_stock"]:
    if c in sup_df.columns:
        sup_df[c] = pd.to_numeric(sup_df[c], errors="coerce").fillna(0).astype(int)
if "pack_size" in sup_df.columns:
    sup_df["pack_size"] = pd.to_numeric(sup_df["pack_size"], errors="coerce").fillna(1).astype(int)
else:
    sup_df["pack_size"] = 1

edited = st.data_editor(sup_df, num_rows="dynamic", use_container_width=True)

col_left, col_right = st.columns(2)
with col_left:
    if st.button("Save suppliers to data/suppliers.csv"):
        edited.to_csv(os.path.join(ROOT, "data", "suppliers.csv"), index=False)
        st.success("Saved to data/suppliers.csv")
with col_right:
    if st.button("Reset suppliers to file"):
        edited = load_suppliers(os.path.join(ROOT, "data", "suppliers.csv"))
        st.experimental_rerun()

# Exploration & features
st.header("Exploration & features")
daily = aggregate_daily(sales)
features = compute_rolling_features(daily, windows=[7,14,28])

# summary table (latest)
latest = features.sort_values("date").groupby("sku").tail(1)[["sku","qty_sold",f"roll_mean_{window}",f"roll_std_{window}"]]
latest = latest.rename(columns={f"roll_mean_{window}":"avg_daily", f"roll_std_{window}":"sigma"}).merge(edited, on="sku", how="left")
st.dataframe(latest)

# Per-SKU demand chart
st.header("Per-SKU demand chart")
sku_list = sorted(features["sku"].unique().tolist())
selected = st.selectbox("Choose SKU to plot", sku_list)
sku_df = features[features["sku"] == selected].sort_values("date")
fig, ax = plt.subplots(figsize=(8,3))
ax.plot(sku_df["date"], sku_df["qty_sold"], label="qty_sold")
ax.plot(sku_df["date"], sku_df[f"roll_mean_{window}"], label=f"roll_mean_{window}")
ax.set_title(f"Demand for {selected}")
ax.set_xlabel("date")
ax.set_ylabel("units")
ax.legend()
st.pyplot(fig)

# Recommendations section
st.header("Recommendations")
if st.button("Compute recommendations"):
    llm_callable = get_llm_callable()
    # latest features per SKU
    latest_feat = features.sort_values("date").groupby("sku").tail(1).set_index("sku")
    recs = []
    for sku, row in latest_feat.iterrows():
        avg_daily = float(row.get(f"roll_mean_{window}", row["qty_sold"]))
        sigma = float(row.get(f"roll_std_{window}", 0.0))
        sup_row = edited[edited["sku"] == sku].iloc[0]
        lead_time = int(sup_row["lead_time_days"])
        current_stock = float(sup_row["current_stock"])
        target_stock = float(sup_row["target_stock"])
        pack_size = int(sup_row["pack_size"]) if "pack_size" in sup_row.index else 1
        r = compute_recommendation(
            sku=sku,
            avg_daily=avg_daily,
            sigma=sigma,
            lead_time_days=lead_time,
            current_stock=current_stock,
            target_stock=target_stock,
            as_of_date=datetime.combine(as_of_date, datetime.min.time()),
            z=float(z),
            min_order_qty=int(min_order_qty),
            llm_callable=llm_callable,
            pack_size=pack_size,
        )
        recs.append(r)

    st.subheader("JSON")
    st.json(recs)

    # create CSV for download
    csv_rows = []
    for r in recs:
        debug = r.get("debug", {})
        csv_rows.append({
            "sku": r["sku"],
            "recommended_qty": r["recommended_qty"],
            "reorder_by_date": r["reorder_by_date"],
            "confidence": r["confidence"],
            "rationale": r["rationale"],
            "avg_daily": debug.get("avg_daily"),
            "sigma": debug.get("sigma"),
            "lead_time_days": debug.get("lead_time_days"),
            "safety_stock": debug.get("safety_stock"),
            "reorder_point": debug.get("reorder_point"),
            "current_stock": debug.get("current_stock"),
            "target_stock": debug.get("target_stock"),
            "pack_size": debug.get("pack_size", 1)
        })
    csv_df = pd.DataFrame(csv_rows)
    st.download_button("Download recommendations (CSV)", csv_df.to_csv(index=False), file_name=f"recommendations_{as_of_date}.csv")
    st.download_button("Download recommendations (JSON)", json.dumps(recs, indent=2), file_name=f"recommendations_{as_of_date}.json")

"""
Exploratory script for OpsAgent.

Usage:
  python scripts/explore.py            # runs summary for all SKUs and saves example plots
  python scripts/explore.py SKU-A     # show/plot only SKU-A

Outputs:
 - prints per-SKU summary: total units, avg daily demand, std daily demand
 - creates PNG plots in data/plots/ for a sample SKU showing qty_sold and rolling means
"""

import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


import matplotlib.pyplot as plt
import pandas as pd

from app.data_utils import load_sales, load_suppliers, aggregate_daily, compute_rolling_features

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(ROOT, "data")
PLOTS_DIR = os.path.join(DATA_DIR, "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

def summarize(sales_df, suppliers_df):
    # aggregate overall per-sku totals & basic stats
    totals = sales_df.groupby("sku")["qty_sold"].agg(total_sales="sum", avg_daily="mean", std_daily="std").reset_index()
    merged = totals.merge(suppliers_df, on="sku", how="left")
    print("\n=== Per-SKU summary ===")
    print(merged.to_string(index=False))
    return merged

def plot_sku(df_with_features, sku, out_path):
    s = df_with_features[df_with_features["sku"] == sku].sort_values("date")
    plt.figure(figsize=(10,4))
    plt.plot(s["date"], s["qty_sold"], label="qty_sold")
    if "roll_mean_7" in s.columns:
        plt.plot(s["date"], s["roll_mean_7"], label="roll_mean_7")
    if "roll_mean_14" in s.columns:
        plt.plot(s["date"], s["roll_mean_14"], label="roll_mean_14")
    plt.title(f"Demand for {sku}")
    plt.xlabel("date")
    plt.ylabel("units")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    print(f"Saved plot for {sku} -> {out_path}")

def main():
    sales_csv = os.path.join(DATA_DIR, "sales_history.csv")
    suppliers_csv = os.path.join(DATA_DIR, "suppliers.csv")

    sales = load_sales(sales_csv)
    suppliers = load_suppliers(suppliers_csv)

    # 1. summary
    summary = summarize(sales, suppliers)

    # 2. aggregate to daily per SKU
    daily = aggregate_daily(sales)
    # show a tiny sample
    print("\n--- daily (sample) ---")
    print(daily.head(8).to_string(index=False))

    # 3. compute rolling features
    features = compute_rolling_features(daily, windows=[7,14,28])
    print("\n--- features (sample rows) ---")
    sample = features.groupby("sku").tail(1).reset_index(drop=True)  # last row per sku
    print(sample[["date","sku","qty_sold","roll_mean_7","roll_std_7","roll_mean_14","roll_std_14"]].to_string(index=False))

    # 4. plot a SKU (either from args or top SKU)
    sku = sys.argv[1] if len(sys.argv) > 1 else summary.sort_values("total_sales", ascending=False).iloc[0]["sku"]
    out_path = os.path.join(PLOTS_DIR, f"{sku}_demand.png")
    plot_sku(features, sku, out_path)

if __name__ == "__main__":
    main()

"""
Run reorder heuristics on the sample data and print JSON for all SKUs.
Usage:
  python scripts/run_reorder.py            # uses template rationale (no LLM)
  OPENAI_API_KEY=... python scripts/run_reorder.py  # will try OpenAI for short rationale (if key present)

Outputs:
  - prints a JSON list with recommendation dicts (readable)
  - writes `data/recommendations_<date>.json`
"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


import os
import json
import sys
import pandas as pd

from datetime import datetime
from typing import Optional


from app.data_utils import load_sales, load_suppliers, aggregate_daily, compute_rolling_features
from app.heuristics import compute_recommendation

# optional import for OpenAI — we try but fall back gracefully
try:
    import openai
except Exception:
    openai = None

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(ROOT, "data")
OUT_DIR = DATA_DIR

def llm_wrapper_openai(prompt: str) -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if not key or openai is None:
        raise RuntimeError("OpenAI not configured")
    openai.api_key = key
    resp = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=40,
        temperature=0.3,
        n=1,
    )
    text = resp["choices"][0]["text"].strip()
    return text

def get_llm_callable() -> Optional[callable]:
    if os.environ.get("OPENAI_API_KEY") and openai is not None:
        return llm_wrapper_openai
    return None

def main():
    sales = load_sales(os.path.join(DATA_DIR, "sales_history.csv"))
    suppliers = load_suppliers(os.path.join(DATA_DIR, "suppliers.csv"))

    # aggregate and compute rolling features
    daily = aggregate_daily(sales)
    features = compute_rolling_features(daily, windows=[7,14,28])

    # pick the last available date as "as_of"
    last_date = features["date"].max()
    as_of = datetime.combine(last_date, datetime.min.time())

    # compute per-sku latest avg and sigma (we use roll_mean_14 and roll_std_14 as main signals)
    latest = features.sort_values("date").groupby("sku").tail(1).set_index("sku")

    recs = []
    llm_callable = get_llm_callable()
    for sku, row in latest.iterrows():
        avg_daily = float(row.get("roll_mean_14", row.get("roll_mean_7", row["qty_sold"])))
        sigma = float(row.get("roll_std_14", row.get("roll_std_7", 0.0)))
        sup = suppliers[suppliers["sku"] == sku].iloc[0]
        lead_time = int(sup["lead_time_days"])
        current_stock = float(sup["current_stock"])
        target_stock = float(sup["target_stock"])
        # read optional pack_size column if present
        pack_size = int(sup["pack_size"]) if "pack_size" in sup.index and not pd.isna(sup["pack_size"]) else 1
        r = compute_recommendation(
            sku=sku,
            avg_daily=avg_daily,
            sigma=sigma,
            lead_time_days=lead_time,
            current_stock=current_stock,
            target_stock=target_stock,
            as_of_date=as_of,
            z=1.65,
            min_order_qty=1,
            llm_callable=llm_callable,
            pack_size=pack_size,
        )
        recs.append(r)

    # output
    out_path = os.path.join(OUT_DIR, f"recommendations_{last_date.strftime('%Y%m%d')}.json")
    with open(out_path, "w", encoding="utf8") as f:
        json.dump(recs, f, indent=2)
    print("Wrote recommendations to:", out_path)
    print(json.dumps(recs, indent=2))

if __name__ == "__main__":
    main()

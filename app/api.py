# app/api.py
"""
Lightweight FastAPI that returns JSON recommendations.
Run with:
  uvicorn app.api:app --reload --port 8000
"""
from fastapi import FastAPI
from pydantic import BaseModel
import os
from datetime import datetime
import pandas as pd

import sys, pathlib
ROOT = str(pathlib.Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.data_utils import load_sales, load_suppliers, aggregate_daily, compute_rolling_features
from app.heuristics import compute_recommendation

# attempt OpenAI import (optional)
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

app = FastAPI(title="OpsAgent API", version="0.1")

class ReorderRequest(BaseModel):
    sales_path: str = None  # optional paths — by default use data/
    suppliers_path: str = None
    window: int = 14
    z: float = 1.65
    min_order_qty: int = 1

@app.post("/recommend")
def recommend(req: ReorderRequest):
    sales_path = req.sales_path or os.path.join(ROOT, "data", "sales_history.csv")
    suppliers_path = req.suppliers_path or os.path.join(ROOT, "data", "suppliers.csv")

    sales = load_sales(sales_path)
    suppliers = load_suppliers(suppliers_path)
    daily = aggregate_daily(sales)
    features = compute_rolling_features(daily, windows=[7,14,28])
    latest = features.sort_values("date").groupby("sku").tail(1).set_index("sku")

    llm_callable = get_llm_callable()
    recs = []
    for sku, row in latest.iterrows():
        avg_daily = float(row.get(f"roll_mean_{req.window}", row["qty_sold"]))
        sigma = float(row.get(f"roll_std_{req.window}", 0.0))

        sup_row = suppliers[suppliers["sku"] == sku].iloc[0]
        lead_time = int(sup_row["lead_time_days"])
        current_stock = float(sup_row["current_stock"])
        target_stock = float(sup_row["target_stock"])

        # NEW: read optional pack_size (default 1)
        pack_size = 1
        if "pack_size" in sup_row.index and not pd.isna(sup_row["pack_size"]):
            try:
                pack_size = int(sup_row["pack_size"])
                if pack_size <= 0:
                    pack_size = 1
            except Exception:
                pack_size = 1

        r = compute_recommendation(
            sku=sku,
            avg_daily=avg_daily,
            sigma=sigma,
            lead_time_days=lead_time,
            current_stock=current_stock,
            target_stock=target_stock,
            as_of_date=datetime.utcnow(),
            z=req.z,
            min_order_qty=req.min_order_qty,
            llm_callable=llm_callable,
            pack_size=pack_size,
        )
        recs.append(r)
    return {"as_of": str(datetime.utcnow().date()), "recommendations": recs}

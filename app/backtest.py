"""
Simple backtesting utilities for OpsAgent.

Given:
 - sales_history: tidy DataFrame (date, sku, qty_sold)
 - suppliers: DataFrame with sku, lead_time_days, starting_stock, target_stock, pack_size

Simulates day-by-day inventory and places replenishment orders using compute_recommendation logic
(we use rolling historical averages up to the day to compute features for each decision point).

Outputs:
 - summary per SKU: service_level (pct days without stockout), total_stockouts, avg_inventory
 - history DataFrame with daily inventory and orders
"""
from typing import Dict, Any
import pandas as pd
import numpy as np
from datetime import timedelta
from app.data_utils import aggregate_daily, compute_rolling_features
from app.heuristics import compute_recommendation

def _safe_int_from_series(series, default=1):
    """
    Helper: return int(series.iloc[0]) if available and not NaN; otherwise return default.
    """
    if series.empty:
        return default
    v = series.iloc[0]
    if pd.isna(v):
        return default
    try:
        return int(v)
    except Exception:
        return default

def run_backtest(sales_df: pd.DataFrame, suppliers_df: pd.DataFrame, start_date=None, end_date=None, z=1.65, window=14):
    daily = aggregate_daily(sales_df)
    daily = daily.sort_values("date")
    if start_date:
        daily = daily[daily["date"] >= pd.to_datetime(start_date)]
    if end_date:
        daily = daily[daily["date"] <= pd.to_datetime(end_date)]

    # initial inventory from suppliers_df current_stock
    skus = suppliers_df["sku"].unique().tolist()
    if daily.empty:
        return {"summary": {}, "history": pd.DataFrame()}

    min_date = daily["date"].min()
    max_date = daily["date"].max()

    # initialize inventory dict and orders list
    inventory = {sku: _safe_int_from_series(suppliers_df[suppliers_df["sku"]==sku]["current_stock"], default=0) for sku in skus}
    target_stock = {sku: _safe_int_from_series(suppliers_df[suppliers_df["sku"]==sku]["target_stock"], default=0) for sku in skus}
    lead_time = {sku: _safe_int_from_series(suppliers_df[suppliers_df["sku"]==sku]["lead_time_days"], default=0) for sku in skus}
    # safe pack_size extraction
    pack_size = {sku: _safe_int_from_series(suppliers_df[suppliers_df["sku"]==sku]["pack_size"], default=1) if "pack_size" in suppliers_df.columns else 1 for sku in skus}

    # orders: list of (sku, arrival_date, qty)
    outstanding = []

    history = []

    # iterate day by day
    all_dates = pd.date_range(min_date, max_date, freq="D")
    for cur_date in all_dates:
        # first, receive orders arriving today
        arrivals = [o for o in outstanding if o[1] == cur_date]
        for sku, arr_date, qty in arrivals:
            inventory[sku] = inventory.get(sku,0) + int(qty)
        # remove arrivals from outstanding
        outstanding = [o for o in outstanding if o[1] > cur_date]

        # apply today's sales (if any)
        todays = daily[daily["date"]==cur_date]
        # ensure we process all SKUs daily even if zero demand to record inventory snapshots
        processed_skus = set()
        for _, row in todays.iterrows():
            sku = row["sku"]
            demand = int(row["qty_sold"])
            prev = inventory.get(sku, 0)
            sold = min(prev, demand)
            inventory[sku] = prev - sold
            stockout = demand - sold  # unmet demand
            history.append({
                "date": cur_date,
                "sku": sku,
                "demand": int(demand),
                "sold": int(sold),
                "stockout": int(stockout),
                "inventory_end": int(inventory[sku]),
            })
            processed_skus.add(sku)

        # For SKUs with no demand recorded today, append a snapshot row (demand=0)
        for sku in skus:
            if sku not in processed_skus:
                history.append({
                    "date": cur_date,
                    "sku": sku,
                    "demand": 0,
                    "sold": 0,
                    "stockout": 0,
                    "inventory_end": int(inventory.get(sku,0)),
                })

        # decide whether to place order (use rolling features computed up to previous day)
        hist_until_yesterday = daily[daily["date"] < cur_date]
        if hist_until_yesterday.empty:
            continue
        features = compute_rolling_features(hist_until_yesterday, windows=[7,14,28])
        latest = features.sort_values("date").groupby("sku").tail(1).set_index("sku")

        for sku in skus:
            if sku not in latest.index:
                continue
            row = latest.loc[sku]
            avg_daily = float(row.get(f"roll_mean_{window}", row["qty_sold"]))
            sigma = float(row.get(f"roll_std_{window}", 0.0))
            cur_stock = int(inventory.get(sku,0))
            tgt = int(target_stock.get(sku,0))
            lt = int(lead_time.get(sku,0))
            pk = int(pack_size.get(sku,1))
            rec = compute_recommendation(
                sku=sku, avg_daily=avg_daily, sigma=sigma, lead_time_days=lt,
                current_stock=cur_stock, target_stock=tgt,
                as_of_date=cur_date, z=z, min_order_qty=1, llm_callable=None, pack_size=pk
            )
            # place order if recommended_qty > 0 and reorder_by_date is today or earlier
            if rec["recommended_qty"] > 0 and rec["reorder_by_date"] is not None:
                reorder_by = pd.to_datetime(rec["reorder_by_date"]).date()
                if reorder_by <= cur_date.date():
                    qty = int(rec["recommended_qty"])
                    arrival = cur_date + timedelta(days=lt)
                    outstanding.append((sku, arrival, qty))

    # aggregate history for metrics
    hist_df = pd.DataFrame(history)
    if hist_df.empty:
        return {"summary": {}, "history": hist_df}
    results = {}
    for sku in skus:
        s = hist_df[hist_df["sku"]==sku]
        total_days = s.shape[0]
        stockout_days = (s["stockout"] > 0).sum()
        service_level = None
        avg_inventory = None
        if total_days > 0:
            service_level = 1.0 - (stockout_days / total_days)
            avg_inventory = float(s["inventory_end"].mean())
        results[sku] = {"service_level": service_level, "stockout_days": int(stockout_days), "total_days": int(total_days), "avg_inventory": avg_inventory}
    return {"summary": results, "history": hist_df}

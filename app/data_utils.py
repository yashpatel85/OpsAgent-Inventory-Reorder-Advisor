"""
Data utilities for OpsAgent.
Functions:
 - load_sales: read sales_history.csv and parse dates
 - load_suppliers: read suppliers.csv
 - aggregate_daily: pivot sales into daily demand per SKU (fills missing dates with 0)
 - compute_rolling_features: compute rolling mean/std for given windows and return tidy dataframe
"""
from typing import List
import pandas as pd


def load_sales(path: str) -> pd.DataFrame:
    """
    Load sales CSV. Expected columns: date, sku, qty_sold
    Returns dataframe with parsed date column.
    """
    df = pd.read_csv(path, parse_dates=["date"])
    # normalize column names
    df = df.rename(columns=lambda c: c.strip())
    return df


def load_suppliers(path: str) -> pd.DataFrame:
    """
    Load suppliers CSV. Expected columns: sku, lead_time_days, current_stock, target_stock
    """
    df = pd.read_csv(path)
    df = df.rename(columns=lambda c: c.strip())
    return df


def aggregate_daily(sales_df: pd.DataFrame, sku_list: List[str] = None) -> pd.DataFrame:
    """
    Aggregate sales to a dataframe with columns: date, sku, qty_sold (daily).
    Ensures all dates in the period appear for each SKU (fills missing with 0).
    Returns a tidy DataFrame with date, sku, qty_sold.
    """
    if "date" not in sales_df.columns or "sku" not in sales_df.columns:
        raise ValueError("sales_df must contain 'date' and 'sku' columns")

    # determine full date range
    min_date = sales_df["date"].min()
    max_date = sales_df["date"].max()
    full_dates = pd.date_range(min_date, max_date, freq="D")

    # limit SKUs if requested
    skus = sku_list if sku_list is not None else sorted(sales_df["sku"].unique())

    # aggregate daily
    daily = sales_df.groupby(["date", "sku"], as_index=False)["qty_sold"].sum()

    # reindex to full grid (date x sku), fill missing with 0
    all_rows = []
    for sku in skus:
        sku_df = daily[daily["sku"] == sku].set_index("date").reindex(full_dates, fill_value=0).rename_axis("date").reset_index()
        sku_df["sku"] = sku
        # ensure qty_sold column exists
        if "qty_sold" not in sku_df.columns:
            sku_df["qty_sold"] = 0
        all_rows.append(sku_df[["date", "sku", "qty_sold"]])
    result = pd.concat(all_rows, ignore_index=True)
    return result


def compute_rolling_features(daily_df: pd.DataFrame, windows: List[int] = [7, 14, 28]) -> pd.DataFrame:
    """
    For a tidy daily_df (date, sku, qty_sold), compute rolling mean and std for each window.
    Returns dataframe with columns:
      date, sku, qty_sold, roll_mean_{w}, roll_std_{w} for each w in windows
    Rolling is computed with .shift(1) so today's features don't include today's sales.
    """
    out_frames = []
    for sku, group in daily_df.groupby("sku"):
        g = group.sort_values("date").set_index("date")
        df = g.copy()
        for w in windows:
            # compute rolling mean/std over past w days, shift by 1 so it's causal
            df[f"roll_mean_{w}"] = df["qty_sold"].rolling(window=w, min_periods=1).mean().shift(1).fillna(0)
            df[f"roll_std_{w}"] = df["qty_sold"].rolling(window=w, min_periods=1).std().shift(1).fillna(0)
        df = df.reset_index()
        df["sku"] = sku
        out_frames.append(df.reset_index(drop=True))
    result = pd.concat(out_frames, ignore_index=True)
    return result
"""
Run a simple backtest for OpsAgent.

Usage:
    python scripts/backtest_run.py

This version includes a bullet-proof sys.path fix so that 'app' is always importable.
"""

import os
import sys
import json

# ---------------------------------------------------------------------
# FIX: ensure project root (folder containing `app/`) is always on sys.path
# ---------------------------------------------------------------------
THIS_FILE = os.path.abspath(__file__)
SCRIPTS_DIR = os.path.dirname(THIS_FILE)
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))

# DEBUG PRINT (optional): print(PROJECT_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Now imports ALWAYS work:
from app.backtest import run_backtest
from app.data_utils import load_sales, load_suppliers


def main():
    sales_path = os.path.join(PROJECT_ROOT, "data", "sales_history.csv")
    suppliers_path = os.path.join(PROJECT_ROOT, "data", "suppliers.csv")

    print("Loading data...")
    sales = load_sales(sales_path)
    suppliers = load_suppliers(suppliers_path)

    print("Running backtest on sample data...")
    res = run_backtest(sales, suppliers)

    print("Backtest summary:")
    print(json.dumps(res["summary"], indent=2, default=str))

    # save history
    hist = res.get("history")
    if hist is not None and not hist.empty:
        out_path = os.path.join(PROJECT_ROOT, "data", "backtest_history.csv")
        hist.to_csv(out_path, index=False)
        print(f"Saved history to: {out_path}")


if __name__ == "__main__":
    main()

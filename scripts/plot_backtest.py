"""
Plot backtest results for a single SKU.

Usage:
  python scripts/plot_backtest.py SKU-A
  python scripts/plot_backtest.py SKU-A --out data/plots/SKU-A-backtest.png
"""
import os, sys
import argparse
import pandas as pd
import matplotlib.pyplot as plt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
hist_path = os.path.join(ROOT, "data", "backtest_history.csv")
plots_dir = os.path.join(ROOT, "data", "plots")
os.makedirs(plots_dir, exist_ok=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sku", help="SKU to plot (e.g., SKU-A)")
    parser.add_argument("--out", help="Output PNG path", default=None)
    args = parser.parse_args()

    if not os.path.exists(hist_path):
        print("Backtest history not found:", hist_path)
        sys.exit(1)

    df = pd.read_csv(hist_path, parse_dates=["date"])
    sku = args.sku
    s = df[df["sku"] == sku].sort_values("date")
    if s.empty:
        print("No data for SKU:", sku)
        sys.exit(1)

    out_file = args.out or os.path.join(plots_dir, f"{sku}_backtest.png")

    fig, ax1 = plt.subplots(figsize=(12,4))
    ax1.plot(s["date"], s["inventory_end"], label="inventory_end")
    ax1.set_ylabel("Inventory")
    ax1.tick_params(axis="y")
    ax1.set_title(f"Backtest inventory & stockouts — {sku}")

    # demand as bars (secondary axis)
    ax2 = ax1.twinx()
    ax2.bar(s["date"], s["demand"], alpha=0.3, label="demand")
    ax2.set_ylabel("Demand")

    # mark stockout days
    stockout_days = s[s["stockout"] > 0]
    if not stockout_days.empty:
        ax1.scatter(stockout_days["date"], stockout_days["inventory_end"], color="red", zorder=5, label="stockout")

    # legends
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc="upper left")

    fig.tight_layout()
    plt.savefig(out_file, dpi=150)
    print("Saved plot:", out_file)

if __name__ == "__main__":
    main()

"""
Generate a cleaner, more realistic D2C-style sample dataset for OpsAgent.

Produces:
 - data/sales_history.csv  (date, sku, qty_sold)  -- daily records for ~120 days
 - data/suppliers.csv      (sku, lead_time_days, current_stock, target_stock, pack_size)

Designed to show:
 - weekday seasonality (weekends higher)
 - promotions (2 short spikes)
 - mix of fast + slow movers
 - realistic lead times and pack sizes
"""
import os
import math
import random
from datetime import date, timedelta, datetime
import csv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# SKU list - D2C-style
SKUS = [
    ("PROTEIN_01", "Whey Protein 1kg"),      # high volume, repeat buy
    ("PREWORKOUT_02", "Pre-Workout 300g"),   # medium-high, promo-sensitive
    ("CREATINE_03", "Creatine Mono 300g"),   # steady low-medium
    ("BARS_04", "Protein Bars (box)"),       # steady medium
    ("BAND_05", "Resistance Band"),          # low volume, seasonal
    ("SHAKER_06", "Shaker Bottle"),          # low volume, one-off
]

# base daily demand (mean) per SKU
BASE_MEAN = {
    "PROTEIN_01": 40,
    "PREWORKOUT_02": 20,
    "CREATINE_03": 8,
    "BARS_04": 18,
    "BAND_05": 4,
    "SHAKER_06": 2,
}

# variability factor (std as fraction of mean)
VAR_F = {
    "PROTEIN_01": 0.25,
    "PREWORKOUT_02": 0.45,
    "CREATINE_03": 0.35,
    "BARS_04": 0.30,
    "BAND_05": 0.6,
    "SHAKER_06": 0.5,
}

# pack sizes for SKUs (some sold in multiples)
PACK_SIZES = {
    "PROTEIN_01": 4,    # order in 4-unit packs (e.g., cases)
    "PREWORKOUT_02": 1,
    "CREATINE_03": 1,
    "BARS_04": 6,       # box multiples
    "BAND_05": 1,
    "SHAKER_06": 12,    # pallet packs
}

# supplier lead times (days)
LEAD_TIMES = {
    "PROTEIN_01": 10,
    "PREWORKOUT_02": 7,
    "CREATINE_03": 5,
    "BARS_04": 14,
    "BAND_05": 21,
    "SHAKER_06": 14,
}

# initial current_stock and target_stock heuristics (target roughly 30-90 days cover)
TODAY = date.today()
DAYS = 120
START_DATE = TODAY - timedelta(days=DAYS-1)

suppliers = []
sales_rows = []

random.seed(42)

# Define two promotion windows to create spikes (dates relative to end)
promo1_start = TODAY - timedelta(days=28)  # a month ago
promo1_days = 3
promo2_start = TODAY - timedelta(days=70)  # earlier promo
promo2_days = 2

for sku, _name in SKUS:
    mean = BASE_MEAN[sku]
    var_frac = VAR_F[sku]
    lead = LEAD_TIMES[sku]
    pack = PACK_SIZES.get(sku, 1)

    # set target_stock as mean * days_cover + buffer
    days_cover = 45 if mean >= 20 else 60  # fast movers have shorter target cover
    target = int(max(10, round(mean * days_cover * (1.0 + random.uniform(0.05, 0.25)))))

    # current stock: somewhere between 10%-80% of target (to create reorder opportunities)
    current = max(0, int(round(target * random.uniform(0.08, 0.8))))

    suppliers.append({
        "sku": sku,
        "lead_time_days": lead,
        "current_stock": current,
        "target_stock": target,
        "pack_size": pack,
    })

    # generate daily sales
    for i in range(DAYS):
        d = START_DATE + timedelta(days=i)
        # weekday seasonality: +20% on weekends
        weekday = d.weekday()  # 0=Mon .. 6=Sun
        weekend_bonus = 1.25 if weekday >= 5 else 1.0

        # promotion spikes
        promo_multiplier = 1.0
        if promo1_start <= d <= (promo1_start + timedelta(days=promo1_days-1)):
            # stronger promo for high-margin fast movers
            if sku in ("PROTEIN_01", "PREWORKOUT_02", "BARS_04"):
                promo_multiplier = 2.5
            else:
                promo_multiplier = 1.7
        if promo2_start <= d <= (promo2_start + timedelta(days=promo2_days-1)):
            if sku in ("PROTEIN_01", "PREWORKOUT_02"):
                promo_multiplier = max(promo_multiplier, 2.0)
            else:
                promo_multiplier = max(promo_multiplier, 1.4)

        # trending: slight upward trend for PROTEIN_01 over last 60 days
        trend = 1.0
        if sku == "PROTEIN_01":
            # small linear trend: +10% over full period
            trend = 1.0 + (i / DAYS) * 0.10

        mu = mean * weekend_bonus * promo_multiplier * trend
        sd = max(0.5, var_frac * mu)

        # sample from a rounded normal-like distribution (clamped >=0)
        qty = int(round(random.gauss(mu, sd)))
        if qty < 0:
            qty = 0

        sales_rows.append((d.isoformat(), sku, qty))

# Write sales_history.csv
sales_path = os.path.join(DATA_DIR, "sales_history.csv")
with open(sales_path, "w", newline="", encoding="utf8") as f:
    w = csv.writer(f)
    w.writerow(["date", "sku", "qty_sold"])
    for r in sales_rows:
        w.writerow(r)

# Write suppliers.csv
sup_path = os.path.join(DATA_DIR, "suppliers.csv")
with open(sup_path, "w", newline="", encoding="utf8") as f:
    w = csv.writer(f)
    w.writerow(["sku", "lead_time_days", "current_stock", "target_stock", "pack_size"])
    for s in suppliers:
        w.writerow([s["sku"], s["lead_time_days"], s["current_stock"], s["target_stock"], s["pack_size"]])

print("Generated:")
print(" -", sales_path)
print(" -", sup_path)
print()
print("Sample supplier rows:")
for s in suppliers:
    print(s)
print()
print("Sample sales rows (first 10):")
for r in sales_rows[:10]:
    print(r)

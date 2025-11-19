import os
from datetime import datetime, timedelta
import random
import csv

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(OUT_DIR, exist_ok = True)

start_date = datetime.today() - timedelta(days = 89)
skus = [
    ("SKU-A", 10),
    ("SKU-B", 3),
    ("SKU-C", 8),
    ("SKU-D", 1),
    ("SKU-E", 5),
    ("SKU-F", 12)
]

sales_file = os.path.join(OUT_DIR, "sales_history.csv")
with open(sales_file, "w", newline = "") as f:
    writer = csv.writer(f)
    writer.writerow(["date", "sku", "qty_sold"])
    for i in range(90):
        date = (start_date + timedelta(days = i)).strftime("%Y-%m-%d")
        for sku, mean in skus:
            base = max(0, int(random.gauss(mean, max(1, mean * 0.35))))
            if random.random() < 0.03:
                spike = int(base * random.uniform(2, 5))
                qty = base + spike
            else:
                qty = base
            writer.writerow([date, sku, qty])


suppliers_file = os.path.join(OUT_DIR, "suppliers.csv")
with open(suppliers_file, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["sku", "lead_time_days", "current_stock", "target_stock"])
    
    supplier_info = {
        "SKU-A": (7, 35, 150),
        "SKU-B": (14, 10, 200),
        "SKU-C": (3, 60, 120),
        "SKU-D": (21, 5, 300),
        "SKU-E": (10, 80, 100),
        "SKU-F": (5, 20, 180),
    }
    for sku, (lt, cur, tgt) in supplier_info.items():
        writer.writerow([sku, lt, cur, tgt])

print("Generated:")
print(" -", sales_file)
print(" -", suppliers_file)
import os
import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(ROOT, "data")

sales_csv = os.path.join(DATA_DIR, "sales_history.csv")
suppliers_csv = os.path.join(DATA_DIR, "suppliers.csv")

def load_csv(path):
    df = pd.read_csv(path, parse_dates=["date"] if "sales_history" in path else None)
    return df

def main():
    print("Loading files from:", DATA_DIR)
    if not os.path.exists(sales_csv) or not os.path.exists(suppliers_csv):
        print("One or both CSVs missing. If you haven't generated them, run:")
        print("  python scripts/generate_sample_data.py")
        return

    sales = load_csv(sales_csv)
    suppliers = load_csv(suppliers_csv)

    print("\n--- sales_history.csv: first 10 rows ---")
    print(sales.head(10).to_string(index=False))

    print("\n--- suppliers.csv: first 10 rows ---")
    print(suppliers.head(10).to_string(index=False))

if __name__ == "__main__":
    main()
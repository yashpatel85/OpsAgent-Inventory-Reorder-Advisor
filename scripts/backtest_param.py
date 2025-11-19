import os, sys, argparse
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
sys.path.insert(0, ROOT)
from app.data_utils import load_sales, load_suppliers
from app.backtest import run_backtest
import json

parser = argparse.ArgumentParser()
parser.add_argument("--z", type=float, default=1.65)
parser.add_argument("--window", type=int, default=14)
args = parser.parse_args()

sales = load_sales(os.path.join(ROOT,"data","sales_history.csv"))
suppliers = load_suppliers(os.path.join(ROOT,"data","suppliers.csv"))
res = run_backtest(sales, suppliers, z=args.z, window=args.window)
print(json.dumps(res["summary"], indent=2))

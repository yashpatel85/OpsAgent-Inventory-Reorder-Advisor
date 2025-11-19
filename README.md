🚀 Overview

OpsAgent is an AI-powered inventory advisor that analyzes recent sales history and supplier lead times to recommend:

Optimal reorder quantities

Recommended reorder-by dates

Pack-size–aware rounding

Confidence scores

Short AI rationales (LLM-powered or deterministic fallback)

It includes:

Streamlit UI (interactive dashboard)

FastAPI service (JSON endpoint)

Backtesting engine (service-level & inventory performance)

Docker Compose (UI + API, production-style)

Unit tests (pytest)

Synthetic D2C dataset (protein powders, bars, accessories)

Example scripts (batch generation, reorder CLI, plotting)

This project demonstrates how an intern or early engineer can design, build, and deliver a real-world AI tool used inside a fast-moving supply-chain environment.

🧠 What the Agent Does

Given:

Daily sales data

Supplier lead times

Current stock

Target stock

Pack sizes

OpsAgent computes:

Rolling demand (7/14/28 days)

Volatility (std dev)

Safety stock using

safety_stock = z * sigma * sqrt(lead_time)


Reorder point using

reorder_point = avg_daily_demand * lead_time + safety_stock


Reorder recommendation:

If current stock < reorder point → reorder

Quantity = top up to target stock

Rounded to pack_size (cases, boxes, pallets)

Generates a human-friendly rationale:

If OpenAI API available → concise LLM explanation

Otherwise fallback → deterministic template

🧩 Why this matters for D2C operations

Fast-moving brands struggle with:

Out-of-stock issues

Overstock due to poor forecasting

Long supplier lead times

Purchase inefficiencies due to pack sizes

Daily operational guesswork

This tool:

Automates reorder decisions

Reduces working capital wastage

Prevents stockouts

Creates an audit trail of reorder logic

Fits directly into procurement workflows via API + CSV exports

📁 Project Structure


<img width="375" height="650" alt="image" src="https://github.com/user-attachments/assets/d4a1f0b7-6644-476a-a5e4-de813f86677b" />




📦 Installation
Option A — Run with Python
pip install -r requirements.txt

Option B — Run with Docker Compose (recommended)
docker compose up -d


The UI opens at:
👉 http://localhost:8501

The API opens at:
👉 http://localhost:8000/docs

🖥️ Using the Streamlit UI (Main Tool)

Launch:

python -m streamlit run app/ui_streamlit.py


Then:

1️⃣ Upload your data or use built-in D2C sample

✔ sales_history.csv
✔ suppliers.csv
OR
✔ check “Use sample CSVs”

2️⃣ Edit supplier parameters

You can edit:

lead_time_days

current_stock

target_stock

pack_size

(Just click in the table—like Excel.)

3️⃣ Explore demand

Per-SKU:

raw demand curve

rolling average

volatility patterns

promotion spikes

seasonality

4️⃣ Compute recommendations

Click:

👉 Compute recommendations

You'll see:

Recommended quantity

Reorder-by date

Confidence score

Rationale

Debug values (avg_daily, sigma, lead_time, reorder_point)

5️⃣ Download results

As:

CSV

JSON

Perfect for procurement workflows.

⚡ Using the FastAPI Endpoint

Start API:

uvicorn app.api:app --reload --port 8000


Call:

curl -X POST "http://localhost:8000/recommend" \
     -H "Content-Type: application/json" \
     -d "{\"window\":14}"


You’ll get structured JSON with detailed fields.

📊 Backtesting (Service-level Simulation)

Run:

python scripts/backtest_run.py


Outputs:

data/backtest_history.csv

Summary per SKU:

service_level  
stockout_days  
avg_inventory  


Plot a SKU:

python scripts/plot_backtest.py PROTEIN_01


Produces:

data/plots/PROTEIN_01_backtest.png

🍫 Included D2C-style Dataset (120 days)
SKUs:

PROTEIN_01 — Whey Protein (fast mover)

PREWORKOUT_02 — Promo-sensitive

CREATINE_03 — Steady

BARS_04 — Box packs (pack_size=6)

BAND_05 — Slow mover

SHAKER_06 — Sold in batch packs (pack_size=12)

Features:

Weekday seasonality

Two promotion periods

Trend component

Different lead times

Realistic pack sizes

Inventory levels designed to trigger reorders

This dataset is deliberately crafted to create:

Interesting reorder signals

Visible promo effects

Inventory depletion cycles

High-quality demo outputs

🧪 Tests

Run all tests:

pytest -q


Tests include:

Safety stock calculations

Reorder logic

Pack-size rounding

Backtest simulation

API response structure

🚢 Docker Deployment

Build locally:

docker build -t opsagent:latest .


Run (UI + API):

docker compose up -d


🧭 Business Value Summary (One-Pager for Non-Technical Reviewers)

OpsAgent automates the most painful recurring decision in inventory management: What to reorder, when, and how much.

Key benefits:

Prevent stockouts

Reduce excess inventory

Improve working capital efficiency

Reduce manual spreadsheet work

Simple API integration into ERP/WhatsApp workflows

Explainable logic (auditable, predictable)

Ideal for:

D2C brands

Sports nutrition

Cosmetics

FMCG

Any SKU-based ecommerce operations

🔮 Future Improvements (Roadmap)

ML-based forecasting (LightGBM, Prophet, ARIMA)

Supplier reliability scoring

Automated purchase order creation

Webhook triggers for WhatsApp / Slack alerts

Cost-based EOQ optimization

Multi-warehouse support

🤝 About this Project

Built end-to-end as a practical AI/ops agent for real operational teams:

Python

Pandas

Streamlit

FastAPI

Docker

Pytest

LLM (OpenAI / fallback)

Designed to show how an intern can think clearly, ship fast, and build real agents used inside companies.

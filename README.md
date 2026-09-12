#  Inventory Intelligence & Stockout Optimization System

An end-to-end data analytics project for a retail/e-commerce business that struggles with
**stockouts, overstock, and unreliable suppliers**. It uses historical sales, inventory,
and supplier data to quantify *where* and *why* inventory problems happen, estimate their
**financial impact**, and generate **replenishment recommendations**.

Delivered as: a relational **MySQL** database → **SQL** analysis → **Python** EDA →
**Power BI** dashboard.

---

## Core Question

> What inventory problems are occurring, why, how much are they costing the business,
> and which products should be prioritized for replenishment?

---

## Project Structure

```
inventory-intelligence-system/
├── README.md                          <- you are here
├── requirements.txt                   <- Python dependencies
├── .gitignore
├── database/
│   ├── schema.sql                     <- MySQL DDL (5-table star-ish schema)
│   └── load_data.sql                  <- LOAD DATA INFILE scripts for the CSVs
├── data_generation/
│   └── generate_synthetic_data.py     <- generates realistic, pattern-embedded data
├── data/                              <- generated CSVs land here (git-ignored by default)
│   ├── products.csv
│   ├── suppliers.csv
│   ├── purchase_orders.csv
│   ├── sales.csv
│   └── inventory.csv
├── sql_analysis/                      <- the 5 "showcase" queries
│   ├── 01_rolling_demand.sql
│   ├── 02_reorder_point_status.sql
│   ├── 03_supplier_on_time_ranking.sql
│   ├── 04_top_stockout_days.sql
│   └── 05_consistent_demand_growth.sql
├── python_eda/
│   └── eda_analysis.py                <- data quality checks, EDA, reorder-formula validation
├── powerbi/
│   └── README.md                      <- how to build the 4-page dashboard from this data
└── docs/
    ├── reorder_point_methodology.md   <- the Z / safety-stock write-up
    ├── limitations.md
    └── business_findings_template.md
```

---

## Quickstart

```bash
# 1. Set up environment
python -m venv venv && source venv/bin/activate      # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# 2. Generate the synthetic (but pattern-embedded, defensible) dataset
python data_generation/generate_synthetic_data.py

# 3. Load into MySQL
mysql -u root -p < database/schema.sql
mysql -u root -p inventory_intelligence < database/load_data.sql
# (adjust the LOCAL INFILE path in load_data.sql to your machine)

# 4. Run the SQL showcase queries
mysql -u root -p inventory_intelligence < sql_analysis/01_rolling_demand.sql

# 5. Run Python EDA + reorder-point validation
python python_eda/eda_analysis.py

# 6. Open Power BI, connect to MySQL (or the CSVs), follow powerbi/README.md
```

---

## Key Design Decisions (locked in upfront)

### Reorder Point Formula
```
Safety Stock   = Z × σ(demand) × √(Lead Time)
Reorder Point  = (Average Daily Demand × Lead Time) + Safety Stock
```
`Z = 1.65` → target ~95% service level. Full justification in
`docs/reorder_point_methodology.md`.

### Synthetic Data Strategy
Data is **not** pure `random.randint()` noise. Patterns are deliberately embedded so the
"findings" are real and defensible — not a dashboard built on meaningless numbers:

| Product group | Embedded pattern | Expected downstream signal |
|---|---|---|
| Group A (~15%) | Long / highly variable supplier lead times | Shows up as stockout-prone in Query 04 |
| Group B (~15%) | Seasonal / trending demand | Exercises the rolling-demand window function (Query 01) |
| Group C (~15%) | Demand growth outpacing reorder logic | Becomes the "🔴 Critical" / at-risk list (Query 02) |
| Group D (~15%) | Low demand + high stock | Becomes the "🔵 Overstocked" list |
| Remaining (~40%) | Normal, stable demand/supply | Baseline / control group |

See `data_generation/generate_synthetic_data.py` for the exact generation logic.

---

## Deliverables Mapping

| Objective | Output |
|---|---|
| Identify stockout problems | Product/category/region stockout frequency + duration |
| Quantify financial impact | ₹ lost revenue, ₹ inventory carrying cost |
| Analyze demand | Trend, seasonality, volatility per product |
| Evaluate suppliers | Lead time, delay %, on-time delivery, stockout correlation |
| Identify overstock | Turnover ratio, days-of-inventory outliers |
| Recommend replenishment | 🔴 Critical / 🟠 Reorder Soon / 🟢 Healthy / 🔵 Overstocked classification |

## Tech Stack
MySQL · SQL (joins, CTEs, window functions, time-series) · Python (Pandas, NumPy,
Matplotlib, Seaborn) · Power BI (Power Query, DAX, star schema) · Git/GitHub

## Limitations
See `docs/limitations.md` — included deliberately, since stating a project's limits
signals analytical maturity.

## License
MIT — use freely for portfolio purposes.

"""
eda_analysis.py
---------------------------------
Python component of the Inventory Intelligence & Stockout Optimization System.

1. Data quality checks
2. Exploratory Data Analysis (demand distribution, seasonality, stockout
   patterns, supplier delay distribution)
3. Validation of the reorder-point / safety-stock formula against the
   actual embedded demand variability in the synthetic data

Run:
    python python_eda/eda_analysis.py

Outputs:
    - Console report (data quality + validation summary)
    - PNG charts saved to python_eda/output/
"""

import os
import math
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings("ignore")
sns.set_theme(style="whitegrid")

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUT_DIR, exist_ok=True)

Z_SCORE = 1.65  # must match data_generation/generate_synthetic_data.py and docs/reorder_point_methodology.md


def load_data():
    products = pd.read_csv(os.path.join(DATA_DIR, "products.csv"))
    suppliers = pd.read_csv(os.path.join(DATA_DIR, "suppliers.csv"))
    sales = pd.read_csv(os.path.join(DATA_DIR, "sales.csv"), parse_dates=["sale_date"])
    inventory = pd.read_csv(os.path.join(DATA_DIR, "inventory.csv"), parse_dates=["snapshot_date"])
    pos = pd.read_csv(
        os.path.join(DATA_DIR, "purchase_orders.csv"),
        parse_dates=["order_date", "expected_delivery_date", "actual_delivery_date"],
    )
    return products, suppliers, sales, inventory, pos


# ------------------------------------------------------------------
# 1. DATA QUALITY CHECKS
# ------------------------------------------------------------------
def data_quality_checks(products, suppliers, sales, inventory, pos):
    print("\n" + "=" * 60)
    print("1. DATA QUALITY CHECKS")
    print("=" * 60)

    checks = []

    for name, df in [("products", products), ("suppliers", suppliers),
                      ("sales", sales), ("inventory", inventory), ("purchase_orders", pos)]:
        nulls = df.isnull().sum().sum()
        dupes = df.duplicated().sum()
        checks.append((name, len(df), nulls, dupes))

    report = pd.DataFrame(checks, columns=["table", "rows", "null_cells", "duplicate_rows"])
    print(report.to_string(index=False))

    # domain-specific checks
    neg_sales = (sales["units_sold"] < 0).sum()
    neg_demand = (sales["units_demanded"] < 0).sum()
    demand_lt_sold = (sales["units_demanded"] < sales["units_sold"]).sum()
    neg_stock = (inventory["stock_on_hand"] < 0).sum()
    bad_dates = (sales["sale_date"] < "2020-01-01").sum() + (sales["sale_date"] > "2030-01-01").sum()
    unknown_category = (~products["category"].notna()).sum()

    print("\nDomain-specific checks:")
    print(f"  Negative units_sold rows          : {neg_sales}")
    print(f"  Negative units_demanded rows       : {neg_demand}")
    print(f"  units_demanded < units_sold rows   : {demand_lt_sold}  (should be 0 -- data integrity issue if not)")
    print(f"  Negative stock_on_hand rows        : {neg_stock}")
    print(f"  Out-of-range sale dates            : {bad_dates}")
    print(f"  Products with missing category     : {unknown_category}")

    all_clean = (neg_sales == neg_demand == demand_lt_sold == neg_stock == bad_dates == unknown_category == 0)
    print(f"\n  => Overall data quality: {'PASS' if all_clean else 'ISSUES FOUND -- see above'}")


# ------------------------------------------------------------------
# 2. EDA
# ------------------------------------------------------------------
def run_eda(products, suppliers, sales, inventory, pos):
    print("\n" + "=" * 60)
    print("2. EXPLORATORY DATA ANALYSIS")
    print("=" * 60)

    merged_sales = sales.merge(products[["product_id", "category", "pattern_group"]], on="product_id")
    merged_inv = inventory.merge(products[["product_id", "category", "pattern_group"]], on="product_id")

    # --- Demand distribution ---
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    sns.histplot(merged_sales["units_sold"], bins=40, ax=axes[0], color="#4C72B0")
    axes[0].set_title("Distribution of Daily Units Sold (all products)")
    axes[0].set_xlabel("Units sold / day")

    sns.boxplot(data=merged_sales, x="pattern_group", y="units_sold", ax=axes[1])
    axes[1].set_title("Daily Demand by Synthetic Pattern Group")
    axes[1].tick_params(axis="x", rotation=30)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "01_demand_distribution.png"), dpi=120)
    plt.close()
    print("Saved: 01_demand_distribution.png")

    # --- Seasonality (weekly + monthly) ---
    daily = merged_sales.groupby("sale_date")["units_sold"].sum().reset_index()
    daily["dow"] = daily["sale_date"].dt.day_name()
    daily["month"] = daily["sale_date"].dt.to_period("M").astype(str)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    sns.boxplot(data=daily, x="dow", y="units_sold", order=dow_order, ax=axes[0])
    axes[0].set_title("Total Daily Demand by Day of Week")
    axes[0].tick_params(axis="x", rotation=30)

    monthly = daily.groupby("month")["units_sold"].sum()
    monthly.plot(kind="line", marker="o", ax=axes[1], color="#DD8452")
    axes[1].set_title("Total Monthly Demand Over Time")
    axes[1].tick_params(axis="x", rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "02_seasonality.png"), dpi=120)
    plt.close()
    print("Saved: 02_seasonality.png")

    # --- Stockout patterns ---
    stockout_by_pattern = merged_inv.groupby("pattern_group")["is_stockout"].mean().sort_values(ascending=False)
    stockout_by_category = merged_inv.groupby("category")["is_stockout"].mean().sort_values(ascending=False)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    stockout_by_pattern.plot(kind="bar", ax=axes[0], color="#C44E52")
    axes[0].set_title("Stockout Rate by Pattern Group")
    axes[0].set_ylabel("Stockout rate")
    axes[0].tick_params(axis="x", rotation=30)

    stockout_by_category.plot(kind="bar", ax=axes[1], color="#55A868")
    axes[1].set_title("Stockout Rate by Category")
    axes[1].set_ylabel("Stockout rate")
    axes[1].tick_params(axis="x", rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "03_stockout_patterns.png"), dpi=120)
    plt.close()
    print("Saved: 03_stockout_patterns.png")
    print("\nStockout rate by pattern group:\n", stockout_by_pattern.round(3))

    # --- Supplier delay distribution ---
    delivered = pos.dropna(subset=["actual_delivery_date"]).copy()
    delivered["actual_lead_days"] = (delivered["actual_delivery_date"] - delivered["order_date"]).dt.days
    delivered["delay_days"] = (delivered["actual_delivery_date"] - delivered["expected_delivery_date"]).dt.days
    delivered = delivered.merge(suppliers[["supplier_id", "supplier_name"]], on="supplier_id")

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.boxplot(data=delivered, x="supplier_name", y="delay_days", ax=ax)
    ax.axhline(0, color="black", linestyle="--", linewidth=1)
    ax.set_title("Delivery Delay Distribution by Supplier (0 = on time)")
    ax.tick_params(axis="x", rotation=90)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "04_supplier_delay_distribution.png"), dpi=120)
    plt.close()
    print("Saved: 04_supplier_delay_distribution.png")


# ------------------------------------------------------------------
# 3. REORDER POINT / SAFETY STOCK FORMULA VALIDATION
# ------------------------------------------------------------------
def validate_reorder_formula(products, sales, inventory):
    print("\n" + "=" * 60)
    print("3. REORDER POINT FORMULA VALIDATION")
    print("=" * 60)
    print("Formula: Safety Stock = Z * sigma(demand) * sqrt(Lead Time)")
    print("         Reorder Point = (Avg Daily Demand * Lead Time) + Safety Stock")
    print(f"         Z = {Z_SCORE} (~95% target service level)\n")

    # For each product, compute actual achieved service level (1 - stockout rate)
    # against the reorder point that was actually used in the simulation, and see
    # whether it clusters near the ~95% target -- and where/why it breaks down.
    inv_with_group = inventory.merge(products[["product_id", "pattern_group", "category"]], on="product_id")
    service_level = (
        inv_with_group.groupby(["product_id", "pattern_group"])["is_stockout"]
        .apply(lambda x: 1 - x.mean())
        .reset_index(name="achieved_service_level")
    )

    summary = service_level.groupby("pattern_group")["achieved_service_level"].agg(["mean", "std", "min", "max"])
    print("Achieved service level by pattern group (target ~0.95 for baseline/stable-demand groups):")
    print(summary.round(3))

    print(
        "\nInterpretation:\n"
        "  - 'baseline' and 'overstock' groups should sit close to or above the ~95% target,\n"
        "    confirming the formula holds under stable/declining demand.\n"
        "  - 'demand_outpace' and 'seasonal_trend' groups are expected to fall BELOW target --\n"
        "    this is the whole point: a reorder point calculated from early-window demand\n"
        "    statistics cannot keep up once demand shifts, which is exactly the population\n"
        "    the replenishment recommendations need to flag.\n"
        "  - 'long_lead_time' group underperforms primarily due to supply-side variability\n"
        "    (delays), not a formula error -- see 04_supplier_delay_distribution.png."
    )

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(data=service_level, x="pattern_group", y="achieved_service_level", ax=ax, errorbar="sd")
    ax.axhline(0.95, color="red", linestyle="--", label="95% target")
    ax.set_title("Achieved Service Level vs. 95% Target, by Pattern Group")
    ax.legend()
    ax.tick_params(axis="x", rotation=30)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "05_reorder_formula_validation.png"), dpi=120)
    plt.close()
    print("\nSaved: 05_reorder_formula_validation.png")


def main():
    products, suppliers, sales, inventory, pos = load_data()
    data_quality_checks(products, suppliers, sales, inventory, pos)
    run_eda(products, suppliers, sales, inventory, pos)
    validate_reorder_formula(products, sales, inventory)
    print("\nAll EDA outputs written to:", os.path.abspath(OUT_DIR))


if __name__ == "__main__":
    main()

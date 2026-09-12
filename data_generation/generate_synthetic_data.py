"""
generate_synthetic_data.py
---------------------------------
Generates a realistic, PATTERN-EMBEDDED synthetic dataset for the
Inventory Intelligence & Stockout Optimization System.

This is deliberately NOT pure random noise. Specific product groups are
seeded with specific behaviours so that downstream SQL/Python/Power BI
findings are real, explainable, and defensible:

    - long_lead_time  : long/highly-variable supplier lead times -> stockout-prone
    - seasonal_trend   : demand has seasonality/trend -> exercises rolling-demand SQL
    - demand_outpace   : demand growth outpaces reorder logic -> "at risk" / Critical list
    - overstock        : low demand + high stock -> "Overstocked" list
    - baseline         : normal, stable demand/supply -> control group

Run:
    python data_generation/generate_synthetic_data.py

Outputs (in ../data/):
    suppliers.csv, products.csv, purchase_orders.csv, sales.csv, inventory.csv
"""

import os
import math
import random
from datetime import date, timedelta

import numpy as np
import pandas as pd

# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(OUT_DIR, exist_ok=True)

N_SUPPLIERS = 15
N_PRODUCTS = 150
START_DATE = date(2024, 1, 1)
END_DATE = date(2025, 6, 30)          # 18 months of daily history
N_DAYS = (END_DATE - START_DATE).days + 1

REGIONS = ["North", "South", "East", "West", "Central"]
CATEGORIES = [
    "Electronics", "Home & Kitchen", "Apparel", "Beauty & Personal Care",
    "Sports & Outdoors", "Toys & Games", "Grocery", "Office Supplies",
]

Z_SCORE = 1.65  # ~95% service level, matches docs/reorder_point_methodology.md

PATTERN_MIX = {
    "long_lead_time": 0.15,
    "seasonal_trend": 0.15,
    "demand_outpace": 0.15,
    "overstock": 0.15,
    "baseline": 0.40,
}

# ------------------------------------------------------------------
# 1. SUPPLIERS
# ------------------------------------------------------------------
def generate_suppliers():
    rows = []
    for sid in range(1, N_SUPPLIERS + 1):
        # A handful of suppliers are deliberately "bad" (long & variable lead times).
        # These get intentionally over-represented among the long_lead_time product group.
        is_bad_supplier = sid <= 4  # suppliers 1-4 are the problem suppliers
        if is_bad_supplier:
            avg_lead = round(np.random.uniform(14, 25), 1)
            lead_std = round(np.random.uniform(4, 9), 1)
            reliability = round(np.random.uniform(0.55, 0.75), 2)
        else:
            avg_lead = round(np.random.uniform(4, 10), 1)
            lead_std = round(np.random.uniform(1, 3), 1)
            reliability = round(np.random.uniform(0.85, 0.99), 2)

        rows.append({
            "supplier_id": sid,
            "supplier_name": f"Supplier {sid:02d}",
            "region": random.choice(REGIONS),
            "avg_lead_time_days": avg_lead,
            "lead_time_std_dev": lead_std,
            "reliability_score": reliability,
            "is_bad_supplier": is_bad_supplier,  # kept for internal use, dropped before export
        })
    return pd.DataFrame(rows)


# ------------------------------------------------------------------
# 2. PRODUCTS
# ------------------------------------------------------------------
def generate_products(suppliers_df):
    n_groups = {k: int(round(v * N_PRODUCTS)) for k, v in PATTERN_MIX.items()}
    # fix rounding drift
    diff = N_PRODUCTS - sum(n_groups.values())
    n_groups["baseline"] += diff

    pattern_labels = []
    for k, n in n_groups.items():
        pattern_labels += [k] * n
    random.shuffle(pattern_labels)

    bad_suppliers = suppliers_df.loc[suppliers_df.is_bad_supplier, "supplier_id"].tolist()
    good_suppliers = suppliers_df.loc[~suppliers_df.is_bad_supplier, "supplier_id"].tolist()

    rows = []
    for i, pattern in enumerate(pattern_labels, start=1):
        category = random.choice(CATEGORIES)
        unit_cost = round(np.random.uniform(50, 3000), 2)          # INR
        margin = np.random.uniform(1.25, 1.9)
        unit_price = round(unit_cost * margin, 2)

        # long_lead_time products are deliberately sourced mostly from bad suppliers
        if pattern == "long_lead_time":
            supplier_id = random.choice(bad_suppliers) if random.random() < 0.85 else random.choice(good_suppliers)
        else:
            supplier_id = random.choice(good_suppliers) if random.random() < 0.85 else random.choice(bad_suppliers)

        rows.append({
            "product_id": i,
            "sku": f"SKU-{i:04d}",
            "product_name": f"{category.split()[0]} Product {i:04d}",
            "category": category,
            "unit_cost": unit_cost,
            "unit_price": unit_price,
            "supplier_id": supplier_id,
            "pattern_group": pattern,
        })
    return pd.DataFrame(rows)


# ------------------------------------------------------------------
# 3. DEMAND SIMULATION (per-product daily "true" demand, pre-stockout)
# ------------------------------------------------------------------
def simulate_daily_demand(pattern, base_demand, n_days, start_date):
    """Returns an array of length n_days of raw customer demand (units wanted)."""
    t = np.arange(n_days)
    noise = np.random.normal(0, base_demand * 0.15, n_days)

    if pattern == "seasonal_trend":
        # strong weekly seasonality + a slow upward yearly trend + a festive spike
        weekly = 1 + 0.35 * np.sin(2 * np.pi * t / 7)
        yearly_trend = 1 + (t / n_days) * 0.6
        demand = base_demand * weekly * yearly_trend
        # festive spike around Oct-Nov each year (day-of-year 280-320)
        doy = np.array([(start_date + timedelta(days=int(d))).timetuple().tm_yday for d in t])
        festive_mask = (doy >= 280) & (doy <= 320)
        demand = np.where(festive_mask, demand * 1.8, demand)

    elif pattern == "demand_outpace":
        # aggressive, sustained growth that a static reorder point can't keep up with
        growth = 1 + (t / n_days) * 2.2   # up to +220% by end of window
        demand = base_demand * growth

    elif pattern == "overstock":
        # demand quietly declines over time while stock keeps getting reordered
        decline = np.clip(1 - (t / n_days) * 0.6, 0.25, 1.0)
        demand = base_demand * decline

    elif pattern == "long_lead_time":
        # demand itself is fairly normal/stable; the PROBLEM is supply side
        weekly = 1 + 0.15 * np.sin(2 * np.pi * t / 7)
        demand = base_demand * weekly

    else:  # baseline
        weekly = 1 + 0.15 * np.sin(2 * np.pi * t / 7)
        demand = base_demand * weekly

    demand = demand + noise
    demand = np.clip(np.round(demand), 0, None).astype(int)
    return demand


# ------------------------------------------------------------------
# 4. FULL SIMULATION: sales, inventory, purchase orders per product
# ------------------------------------------------------------------
def simulate_product(product, supplier):
    pattern = product["pattern_group"]

    if pattern == "overstock":
        base_demand = np.random.uniform(2, 6)      # low demand
        initial_stock_multiplier = 4.0              # over-ordered
    elif pattern == "demand_outpace":
        base_demand = np.random.uniform(8, 20)
        initial_stock_multiplier = 1.2
    else:
        base_demand = np.random.uniform(6, 18)
        initial_stock_multiplier = 1.5

    demand_series = simulate_daily_demand(pattern, base_demand, N_DAYS, START_DATE)

    avg_lead = supplier["avg_lead_time_days"]
    lead_std = supplier["lead_time_std_dev"]
    # long_lead_time products additionally suffer worse-than-supplier-average lead times
    lead_penalty = 1.6 if pattern == "long_lead_time" else 1.0

    avg_daily_demand_est = np.mean(demand_series[:60])  # est. from first ~2 months
    std_daily_demand_est = np.std(demand_series[:60]) if np.std(demand_series[:60]) > 0 else 1.0

    safety_stock = Z_SCORE * std_daily_demand_est * math.sqrt(avg_lead * lead_penalty)
    reorder_point = (avg_daily_demand_est * avg_lead * lead_penalty) + safety_stock
    reorder_point = max(reorder_point, avg_daily_demand_est * 2)

    order_qty = max(int(round(avg_daily_demand_est * avg_lead * lead_penalty * 2.5)), 20)
    stock = int(round(reorder_point * initial_stock_multiplier))

    sales_rows, inventory_rows, po_rows = [], [], []
    open_pos = []  # list of dicts: {"arrival_day": int, "qty": int, "po_id": ..}
    region = random.choice(REGIONS)
    po_id_counter = [0]

    def place_po(order_day):
        lead = max(1, int(round(np.random.normal(avg_lead * lead_penalty, lead_std * lead_penalty))))
        order_dt = START_DATE + timedelta(days=order_day)
        expected_dt = order_dt + timedelta(days=lead)
        # bad suppliers occasionally slip further (delay on top of already-long lead)
        delay_days = 0
        status = "Delivered"
        if random.random() < (0.25 if pattern == "long_lead_time" else 0.06):
            delay_days = int(np.random.uniform(2, 10))
            status = "Delayed"
        actual_dt = expected_dt + timedelta(days=delay_days)
        arrival_day = min(order_day + lead + delay_days, N_DAYS - 1)

        po_id_counter[0] += 1
        po_rows.append({
            "product_id": product["product_id"],
            "supplier_id": product["supplier_id"],
            "order_date": order_dt.isoformat(),
            "expected_delivery_date": expected_dt.isoformat(),
            "actual_delivery_date": actual_dt.isoformat() if arrival_day < N_DAYS else None,
            "quantity_ordered": order_qty,
            "unit_cost": product["unit_cost"],
            "status": status,
        })
        open_pos.append({"arrival_day": arrival_day, "qty": order_qty})

    # seed with one PO in transit so the sim doesn't start starved
    place_po(0)

    for day in range(N_DAYS):
        current_date = START_DATE + timedelta(days=day)

        # receive any POs arriving today
        arrived = [po for po in open_pos if po["arrival_day"] == day]
        for po in arrived:
            stock += po["qty"]
        open_pos = [po for po in open_pos if po["arrival_day"] != day]

        demand_today = int(demand_series[day])
        units_sold = min(demand_today, stock)
        is_stockout = 1 if (demand_today > 0 and stock <= 0) else (1 if units_sold < demand_today else 0)
        stock -= units_sold
        revenue = round(units_sold * product["unit_price"], 2)

        sales_rows.append({
            "product_id": product["product_id"],
            "sale_date": current_date.isoformat(),
            "region": region,
            "units_sold": units_sold,
            "units_demanded": demand_today,
            "revenue": revenue,
        })
        inventory_rows.append({
            "product_id": product["product_id"],
            "snapshot_date": current_date.isoformat(),
            "stock_on_hand": stock,
            "is_stockout": is_stockout,
            "reorder_point_snapshot": round(reorder_point, 2),
        })

        # reorder logic: place a new PO if stock has fallen to/below reorder point
        # and there's no PO already in flight (avoid duplicate ordering)
        if stock <= reorder_point and len(open_pos) == 0 and day < N_DAYS - 5:
            place_po(day)

    return sales_rows, inventory_rows, po_rows


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
def main():
    print("Generating suppliers...")
    suppliers_df = generate_suppliers()

    print("Generating products...")
    products_df = generate_products(suppliers_df)

    print(f"Simulating {N_PRODUCTS} products across {N_DAYS} days "
          f"({START_DATE} to {END_DATE})... this covers sales, inventory, and purchase orders.")

    all_sales, all_inventory, all_pos = [], [], []
    suppliers_lookup = suppliers_df.set_index("supplier_id").to_dict("index")

    for _, product in products_df.iterrows():
        supplier = suppliers_lookup[product["supplier_id"]]
        sales_rows, inventory_rows, po_rows = simulate_product(product, supplier)
        all_sales.extend(sales_rows)
        all_inventory.extend(inventory_rows)
        all_pos.extend(po_rows)
        if product["product_id"] % 25 == 0:
            print(f"  ...done product {product['product_id']}/{N_PRODUCTS}")

    sales_df = pd.DataFrame(all_sales)
    inventory_df = pd.DataFrame(all_inventory)
    po_df = pd.DataFrame(all_pos)
    po_df.insert(0, "po_id", range(1, len(po_df) + 1))

    # finalize export frames (drop internal-only helper columns)
    suppliers_export = suppliers_df.drop(columns=["is_bad_supplier"])
    products_export = products_df.copy()

    suppliers_export.to_csv(os.path.join(OUT_DIR, "suppliers.csv"), index=False)
    products_export.to_csv(os.path.join(OUT_DIR, "products.csv"), index=False)
    po_df.to_csv(os.path.join(OUT_DIR, "purchase_orders.csv"), index=False)
    sales_df.to_csv(os.path.join(OUT_DIR, "sales.csv"), index=False)
    inventory_df.to_csv(os.path.join(OUT_DIR, "inventory.csv"), index=False)

    print("\nDone. Files written to:", os.path.abspath(OUT_DIR))
    print(f"  suppliers.csv        : {len(suppliers_export):>7,} rows")
    print(f"  products.csv         : {len(products_export):>7,} rows")
    print(f"  purchase_orders.csv  : {len(po_df):>7,} rows")
    print(f"  sales.csv            : {len(sales_df):>7,} rows")
    print(f"  inventory.csv        : {len(inventory_df):>7,} rows")

    # quick sanity check of embedded patterns
    print("\nPattern group sizes:")
    print(products_export.pattern_group.value_counts())

    stockout_rate_by_pattern = (
        inventory_df.merge(products_export[["product_id", "pattern_group"]], on="product_id")
        .groupby("pattern_group")["is_stockout"].mean()
        .sort_values(ascending=False)
    )
    print("\nStockout rate by pattern group (sanity check — long_lead_time should be highest):")
    print(stockout_rate_by_pattern.round(3))


if __name__ == "__main__":
    main()

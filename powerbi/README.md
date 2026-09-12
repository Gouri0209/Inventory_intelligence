# Power BI Dashboard — Build Guide

This project doesn't ship a `.pbix` binary (it can't be generated outside Power BI
Desktop), but here's exactly how to build the 4-page dashboard from the MySQL database
or the CSVs in `data/`.

## 1. Connect

`Get Data` → `MySQL database` → point at `inventory_intelligence`
(or `Get Data` → `Text/CSV` for each file in `data/` if you're not using MySQL).

Import (not DirectQuery) is fine at this data volume (~80K rows in `sales`/`inventory`).

## 2. Data model (star-schema-ish)

- `products` (dimension) — 1-to-many → `sales`, `inventory`, `purchase_orders`
- `suppliers` (dimension) — 1-to-many → `products`, `purchase_orders`
- Build a proper **Date table** (`Modeling` → `New Table`):
  ```
  DateTable = CALENDAR(DATE(2024,1,1), DATE(2025,6,30))
  ```
  Mark it as a Date Table, then relate it to `sales[sale_date]` and
  `inventory[snapshot_date]`.

## 3. Key DAX measures

```DAX
Total Revenue = SUM(sales[revenue])

Units Lost to Stockout =
SUMX(
    FILTER(sales, RELATED(inventory[is_stockout]) = 1),
    sales[units_demanded] - sales[units_sold]
)
-- (simpler alternative: pre-join units_lost in Power Query instead of RELATED)

Estimated Revenue Lost =
SUMX(
    sales,
    (sales[units_demanded] - sales[units_sold]) * RELATED(products[unit_price])
)

Stockout Rate = AVERAGE(inventory[is_stockout])

Inventory Turnover Ratio =
DIVIDE([Total Revenue], AVERAGE(inventory[stock_on_hand]) * AVERAGE(products[unit_cost]))

Days of Inventory Remaining =
DIVIDE(
    CALCULATE(SUM(inventory[stock_on_hand]), LASTDATE(DateTable[Date])),
    [Avg Daily Demand 30d]
)

On-Time Delivery % =
DIVIDE(
    CALCULATE(COUNTROWS(purchase_orders), purchase_orders[status] = "Delivered"),
    COUNTROWS(purchase_orders)
)
```

Bring the 🔴🟠🟢🔵 status classification over from
`sql_analysis/02_reorder_point_status.sql` as a calculated column or Power Query step
(recommended: compute it in SQL/Python and import as a column, since it depends on
multiple aggregations — cleaner than replicating in DAX).

## 4. Pages

### Page 1 — Executive Inventory Overview
- KPI cards: Total Revenue, Estimated Revenue Lost to Stockouts, Overall Stockout Rate,
  Total Inventory Value, # Products by status (🔴🟠🟢🔵)
- Trend line: Monthly revenue vs. monthly estimated revenue lost
- Donut/bar: Product count by status classification

### Page 2 — Stockout Intelligence
- Bar chart: Estimated revenue lost by category (from Query 04)
- Table: Top stockout-days products per category, with drill-through to product detail
- Line chart: Stockout rate over time (monthly), sliceable by category/pattern
- Map or bar: Stockout rate by region

### Page 3 — Inventory Optimization
- Table (main visual): all products with Status, Stock on Hand, Reorder Point, Days of
  Inventory Remaining — conditional formatting on Status column using the emoji/category
- Slicer: filter by Status, Category
- Drill-down: click a product → daily stock-on-hand line vs. reorder point line
  (area/line combo chart) to visually show when it crossed the reorder threshold

### Page 4 — Supplier Performance
- Table: Supplier ranking from Query 03 (on-time %, avg lead time, stockout rate of
  supplied products)
- Scatter chart: On-Time % (x-axis) vs. Stockout Rate of Supplied Products (y-axis),
  bubble size = # products supplied — this is the chart that visually proves/disproves
  "bad suppliers cause stockouts"
- Bar chart: Delay days distribution by supplier

## 5. Tips
- Use bookmarks + a nav bar (buttons) across the top of every page for a portfolio-ready
  feel.
- Set the emoji-status column's font size up slightly and center-align — it reads much
  better in tables than as a slicer.
- Export each page as an image and drop them into your portfolio/README once built —
  recruiters skim images before they open a `.pbix`.

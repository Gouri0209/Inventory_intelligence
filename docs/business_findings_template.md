# Business Findings — Summary Template

> Auto-derived from the generated dataset (seed=42, 150 products, 2024-01-01 to
> 2025-06-30). Regenerate the data and re-run the SQL/EDA to refresh these numbers, or
> plug your own real dataset into the same schema.

## Headline numbers (this run)

- **Estimated revenue lost to stockouts: ~₹29.8 crore** over the 18-month window,
  concentrated in products from the `demand_outpace` and `seasonal_trend` pattern groups
  and in products sourced from the four "problem" suppliers (Suppliers 01–04).
- **75 of 150 products (50%)** experienced a stockout rate above 5% at some point in the
  window — a useful cut-line for "needs replenishment review."
- **16 products** are currently sitting on more than 60 days of inventory relative to
  their recent demand, tying up an estimated **~₹2.67 crore** in inventory value that
  could be redeployed.

## Narrative template (fill in with your own run's numbers)

> "**[X] products** are currently at high risk of stockout, representing **~₹[Y]** in
> potential revenue at risk — concentrated in **[category/categories]** with
> above-average supplier lead times, primarily sourced from **[supplier(s)]**."

> "**[Z] products** are significantly overstocked relative to demand, tying up
> **~₹[W]** in inventory value that could be freed up by pausing reorders or running a
> clearance."

## How each number is produced

| Number | Source |
|---|---|
| Revenue lost to stockouts | `sql_analysis/04_top_stockout_days.sql` (`estimated_revenue_lost` column), summed |
| Products at stockout risk | `sql_analysis/02_reorder_point_status.sql` — count of 🔴 Critical + 🟠 Reorder Soon |
| Overstock capital tied up | `stock_on_hand × unit_cost` for products flagged 🔵 Overstocked |
| Supplier culpability | `sql_analysis/03_supplier_on_time_ranking.sql` — cross-reference `on_time_pct` against `stockout_rate_pct_of_products_supplied` |

## Suggested next steps to include in a real write-up

1. Prioritize replenishment review for 🔴 Critical products first — check whether their
   reorder point needs recalculating (likely `demand_outpace`/`seasonal_trend` cases) vs.
   whether the supplier needs escalation (likely `long_lead_time` cases).
2. Consider renegotiating or diversifying away from consistently low `on_time_pct`
   suppliers, especially where their `stockout_rate_pct_of_products_supplied` is
   materially above the company average.
3. Run a clearance/promotion pass on the 🔵 Overstocked list to free up working capital
   before the next purchasing cycle.

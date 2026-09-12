# Limitations

Every analytics project should state its own limits. This one has three worth calling
out explicitly:

1. **Lead time is modeled as a distribution, not truly dynamic/real-time.**
   Each supplier has a fixed `avg_lead_time_days` / `lead_time_std_dev` used to sample
   lead times for every purchase order. In reality, lead time can shift due to external
   shocks (port congestion, raw material shortages, geopolitical events) that aren't
   captured by a static per-supplier distribution. The reorder-point formula also does
   not propagate lead-time variance itself (see `reorder_point_methodology.md`) — only
   demand variance.

2. **No promotional or marketing-driven demand spikes are modeled.**
   The `seasonal_trend` group includes a recurring festive-season spike and general
   seasonality, but there's no representation of one-off marketing campaigns, flash
   sales, or price-driven demand shocks that a real retailer would need to plan
   inventory around separately (and which a reorder-point model alone can't handle —
   those need manual buffer overrides).

3. **Reorder logic assumes independent demand across products.**
   Each product's demand is simulated independently. In reality, products substitute for
   one another (a stockout on Product A can spike demand for Product B) and some products
   are complements (bundle/kit demand). This project's reorder point calculations do not
   account for cross-product substitution or cannibalization effects.

### Secondary limitations (also worth noting)
- The synthetic dataset, while pattern-embedded and validated (see
  `python_eda/eda_analysis.py`, section 3), is still synthetic — real retail data would
  have messier edge cases (returns, partial shipments, SKU changes mid-lifecycle,
  multi-warehouse allocation) not modeled here.
- Currency/financial figures assume a single unit cost and price per product for the
  full window; no cost inflation or price changes over time are modeled.
- The system optimizes for service level / stockout avoidance, not full profit
  optimization (it doesn't jointly optimize holding cost vs. stockout cost — the four
  status buckets are decision-support, not a solved cost-minimization function).

# Reorder Point & Safety Stock Methodology

## Formula

```
Safety Stock  = Z × σ(demand) × √(Lead Time)
Reorder Point = (Average Daily Demand × Lead Time) + Safety Stock
```

## Why this formula

This is the standard **statistical safety stock model** used in inventory management,
appropriate when both **demand** and **lead time** carry uncertainty and we want a stock
buffer that limits the probability of a stockout during the replenishment window.

- **Average Daily Demand × Lead Time** — the stock we expect to sell during the time it
  takes a new order to arrive ("expected consumption during lead time").
- **σ(demand) × √(Lead Time)** — the *demand-side* uncertainty compounded over the lead
  time window (variance scales linearly with time, so standard deviation scales with the
  square root of time — this is why lead time appears under a square root rather than
  multiplied directly).
- **Z** — the number of standard deviations of buffer needed to hit a target **service
  level** (probability of NOT stocking out during the lead time window), assuming
  approximately normally distributed demand.

## Choosing Z

| Target service level | Z-score |
|---|---|
| 90% | 1.28 |
| 95% | **1.65** ← used in this project |
| 97.5% | 1.96 |
| 99% | 2.33 |

We use **Z = 1.65 (~95% service level)** as a deliberate middle ground: high enough to be
commercially realistic for a retail business that cares about customer experience, not so
high (99%+) that it would imply carrying unrealistic amounts of safety stock and inflating
holding costs. This is a *business trade-off*, not just a statistics choice — a 99%
service level roughly doubles the required safety stock buffer for the same demand
variability, at rapidly diminishing returns.

## Known limitation of this (simplified) formula

This formula treats **lead time as fixed** and only propagates *demand* variability
through the √(Lead Time) term. It does **not** account for variability in the lead time
itself. A more complete model would be:

```
Safety Stock = Z × √( (Lead Time × σ(demand)²) + (Average Daily Demand² × σ(Lead Time)²) )
```

This project uses the simpler formula deliberately (it's the version most commonly taught
and most commonly implemented in real SMB inventory systems), but the **`long_lead_time`
synthetic product group is specifically designed to expose this limitation**: those
products have high lead-time variability, and the EDA (`python_eda/eda_analysis.py`,
section 3) shows their achieved service level underperforming target *not* because the
demand-side formula is wrong, but because lead-time variability isn't modeled. This is
called out explicitly rather than hidden, and is referenced again in `limitations.md`.

## Validation approach

`python_eda/eda_analysis.py` computes, per product, the **achieved service level**
(`1 - stockout_rate`) over the full simulation window and compares it against the 95%
target, broken out by synthetic pattern group. Because the pattern groups are known by
construction, this lets us confirm:

- Stable-demand products (`baseline`, `overstock`) cluster near/above the 95% target →
  **formula works as intended under its assumptions**.
- Trending/seasonal and rapidly-growing demand products (`seasonal_trend`,
  `demand_outpace`) fall below target → **expected and explainable**: the reorder point is
  calculated from an early demand estimate that a static formula cannot keep updating as
  demand shifts. This is precisely the population that should be flagged 🔴 Critical /
  🟠 Reorder Soon and prioritized for a review of reorder parameters.
- High lead-time-variability products (`long_lead_time`) underperform for a supply-side
  reason, distinguishable in the data from a demand-side reason via the supplier delay
  analysis (`04_supplier_delay_distribution.png`).

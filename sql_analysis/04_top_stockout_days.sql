-- ============================================================
-- Query 04: Top stockout-days products by category
-- (window function + RANK)
--
-- Surfaces the worst offenders per category rather than a single
-- global top-N, so every category gets visibility in the dashboard
-- drill-down instead of one category dominating the list.
-- ============================================================
USE inventory_intelligence;

WITH stockout_summary AS (
    SELECT
        p.product_id,
        p.product_name,
        p.category,
        p.pattern_group,
        SUM(i.is_stockout) AS total_stockout_days,
        COUNT(*) AS days_tracked,
        ROUND(100.0 * SUM(i.is_stockout) / COUNT(*), 2) AS stockout_rate_pct,
        SUM(CASE WHEN i.is_stockout = 1 THEN (s.units_demanded - s.units_sold) ELSE 0 END) AS total_units_lost,
        ROUND(SUM(CASE WHEN i.is_stockout = 1 THEN (s.units_demanded - s.units_sold) ELSE 0 END)
              * AVG(p.unit_price), 2) AS estimated_revenue_lost
    FROM products p
    JOIN inventory i ON i.product_id = p.product_id
    JOIN sales s ON s.product_id = p.product_id AND s.sale_date = i.snapshot_date
    GROUP BY p.product_id, p.product_name, p.category, p.pattern_group
),
ranked AS (
    SELECT
        *,
        RANK() OVER (PARTITION BY category ORDER BY total_stockout_days DESC) AS rank_in_category
    FROM stockout_summary
)
SELECT *
FROM ranked
WHERE rank_in_category <= 5          -- top 5 worst-offenders per category
ORDER BY category, rank_in_category;

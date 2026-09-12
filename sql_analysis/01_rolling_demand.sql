-- ============================================================
-- Query 01: 30-day rolling demand per product (window function)
--
-- Purpose: smooth out daily noise to reveal the true demand trend per
-- product. This is the input signal that seasonal_trend and
-- demand_outpace products should visibly diverge from baseline on.
-- ============================================================
USE inventory_intelligence;

SELECT
    s.product_id,
    p.product_name,
    p.category,
    p.pattern_group,
    s.sale_date,
    s.units_sold,
    ROUND(
        AVG(s.units_sold) OVER (
            PARTITION BY s.product_id
            ORDER BY s.sale_date
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ), 2
    ) AS rolling_30d_avg_demand,
    ROUND(
        SUM(s.units_sold) OVER (
            PARTITION BY s.product_id
            ORDER BY s.sale_date
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ), 2
    ) AS rolling_30d_total_demand
FROM sales s
JOIN products p ON p.product_id = s.product_id
ORDER BY s.product_id, s.sale_date;

-- Variant: latest rolling average per product (for dashboard KPI cards)
-- SELECT product_id, rolling_30d_avg_demand
-- FROM ( <query above> ) t
-- WHERE sale_date = (SELECT MAX(sale_date) FROM sales);

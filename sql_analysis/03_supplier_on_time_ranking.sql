-- ============================================================
-- Query 03: Supplier on-time delivery ranking
-- (aggregation + join across 3 tables: suppliers, purchase_orders, products)
--
-- Ranks suppliers by on-time delivery rate and links that to the
-- stockout rate of the products they supply -- this is the query that
-- proves (or disproves) "bad suppliers cause stockouts."
-- ============================================================
USE inventory_intelligence;

WITH po_performance AS (
    SELECT
        po.supplier_id,
        COUNT(*) AS total_orders,
        SUM(CASE WHEN po.status = 'Delivered'
                  AND po.actual_delivery_date <= po.expected_delivery_date THEN 1 ELSE 0 END) AS on_time_orders,
        SUM(CASE WHEN po.status = 'Delayed' THEN 1 ELSE 0 END) AS delayed_orders,
        AVG(DATEDIFF(po.actual_delivery_date, po.order_date)) AS avg_actual_lead_time_days
    FROM purchase_orders po
    WHERE po.actual_delivery_date IS NOT NULL
    GROUP BY po.supplier_id
),
supplier_stockout_link AS (
    SELECT
        pr.supplier_id,
        AVG(inv.is_stockout) AS avg_stockout_rate_of_supplied_products
    FROM products pr
    JOIN inventory inv ON inv.product_id = pr.product_id
    GROUP BY pr.supplier_id
)
SELECT
    s.supplier_id,
    s.supplier_name,
    s.region,
    s.avg_lead_time_days AS quoted_avg_lead_time,
    ROUND(pp.avg_actual_lead_time_days, 1) AS actual_avg_lead_time,
    pp.total_orders,
    pp.on_time_orders,
    pp.delayed_orders,
    ROUND(100.0 * pp.on_time_orders / NULLIF(pp.total_orders, 0), 1) AS on_time_pct,
    ROUND(100.0 * ssl.avg_stockout_rate_of_supplied_products, 1) AS stockout_rate_pct_of_products_supplied,
    RANK() OVER (ORDER BY (100.0 * pp.on_time_orders / NULLIF(pp.total_orders, 0)) DESC) AS on_time_rank
FROM suppliers s
JOIN po_performance pp ON pp.supplier_id = s.supplier_id
JOIN supplier_stockout_link ssl ON ssl.supplier_id = s.supplier_id
ORDER BY on_time_rank;

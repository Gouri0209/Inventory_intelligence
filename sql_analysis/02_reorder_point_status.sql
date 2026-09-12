-- ============================================================
-- Query 02: Reorder point + current status classification
-- (CTE + CASE)
--
-- Classifies every product into:
--   🔴 Critical      - already at/below reorder point AND recent stockouts
--   🟠 Reorder Soon  - within 20% buffer above reorder point
--   🟢 Healthy       - comfortably above reorder point
--   🔵 Overstocked   - stock far exceeds reorder point relative to demand
-- ============================================================
USE inventory_intelligence;

WITH latest_inventory AS (
    SELECT i.product_id, i.stock_on_hand, i.reorder_point_snapshot, i.snapshot_date
    FROM inventory i
    INNER JOIN (
        SELECT product_id, MAX(snapshot_date) AS max_date
        FROM inventory
        GROUP BY product_id
    ) latest ON latest.product_id = i.product_id AND latest.max_date = i.snapshot_date
),
recent_demand AS (
    SELECT product_id, AVG(units_sold) AS avg_daily_demand_30d
    FROM sales
    WHERE sale_date >= (SELECT DATE_SUB(MAX(sale_date), INTERVAL 30 DAY) FROM sales)
    GROUP BY product_id
),
recent_stockouts AS (
    SELECT product_id, SUM(is_stockout) AS stockout_days_30d
    FROM inventory
    WHERE snapshot_date >= (SELECT DATE_SUB(MAX(snapshot_date), INTERVAL 30 DAY) FROM inventory)
    GROUP BY product_id
)
SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.pattern_group,
    li.stock_on_hand,
    ROUND(li.reorder_point_snapshot, 1) AS reorder_point,
    ROUND(rd.avg_daily_demand_30d, 2) AS avg_daily_demand_30d,
    COALESCE(rs.stockout_days_30d, 0) AS stockout_days_last_30d,
    ROUND(li.stock_on_hand / NULLIF(rd.avg_daily_demand_30d, 0), 1) AS days_of_inventory_remaining,
    CASE
        WHEN li.stock_on_hand <= li.reorder_point_snapshot
             AND COALESCE(rs.stockout_days_30d, 0) > 0
            THEN '🔴 Critical'
        WHEN li.stock_on_hand <= li.reorder_point_snapshot * 1.2
            THEN '🟠 Reorder Soon'
        WHEN li.stock_on_hand > li.reorder_point_snapshot * 3
             AND rd.avg_daily_demand_30d < (SELECT AVG(units_sold) FROM sales)
            THEN '🔵 Overstocked'
        ELSE '🟢 Healthy'
    END AS status
FROM products p
JOIN latest_inventory li ON li.product_id = p.product_id
LEFT JOIN recent_demand rd ON rd.product_id = p.product_id
LEFT JOIN recent_stockouts rs ON rs.product_id = p.product_id
ORDER BY
    FIELD(status, '🔴 Critical', '🟠 Reorder Soon', '🔵 Overstocked', '🟢 Healthy'),
    days_of_inventory_remaining ASC;

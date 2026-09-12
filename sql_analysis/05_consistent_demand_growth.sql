-- ============================================================
-- Query 05: Products with consistent multi-month demand growth
-- (LAG window function over monthly aggregates)
--
-- Flags products where demand has grown month-over-month for at
-- least 4 consecutive months -- these are the demand_outpace-pattern
-- products by construction, and are exactly the SKUs whose reorder
-- point (calculated from early, lower demand) is now too low.
-- ============================================================
USE inventory_intelligence;

WITH monthly_demand AS (
    SELECT
        product_id,
        DATE_FORMAT(sale_date, '%Y-%m-01') AS month_start,
        SUM(units_sold) AS monthly_units_sold
    FROM sales
    GROUP BY product_id, DATE_FORMAT(sale_date, '%Y-%m-01')
),
with_growth_flag AS (
    SELECT
        product_id,
        month_start,
        monthly_units_sold,
        LAG(monthly_units_sold) OVER (PARTITION BY product_id ORDER BY month_start) AS prev_month_units,
        CASE
            WHEN monthly_units_sold > LAG(monthly_units_sold) OVER (PARTITION BY product_id ORDER BY month_start)
                THEN 1 ELSE 0
        END AS grew_vs_prev_month
    FROM monthly_demand
),
-- group consecutive growth months into "streaks" using the classic
-- (row_number - row_number_within_flag_group) gaps-and-islands trick
streaks AS (
    SELECT
        product_id,
        month_start,
        monthly_units_sold,
        grew_vs_prev_month,
        ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY month_start) -
        ROW_NUMBER() OVER (PARTITION BY product_id, grew_vs_prev_month ORDER BY month_start) AS streak_group
    FROM with_growth_flag
),
streak_lengths AS (
    SELECT
        product_id,
        streak_group,
        COUNT(*) AS consecutive_growth_months,
        MIN(month_start) AS streak_start,
        MAX(month_start) AS streak_end
    FROM streaks
    WHERE grew_vs_prev_month = 1
    GROUP BY product_id, streak_group
)
SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.pattern_group,
    sl.consecutive_growth_months,
    sl.streak_start,
    sl.streak_end
FROM streak_lengths sl
JOIN products p ON p.product_id = sl.product_id
WHERE sl.consecutive_growth_months >= 4
ORDER BY sl.consecutive_growth_months DESC, p.product_id;

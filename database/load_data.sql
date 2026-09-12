-- ============================================================
-- Load generated CSVs into MySQL.
-- Run AFTER schema.sql and AFTER generate_synthetic_data.py
--
-- IMPORTANT: adjust the file paths below to the absolute path of the
-- `data/` folder on YOUR machine, and ensure your MySQL server allows
-- local_infile (client + server): SET GLOBAL local_infile = 1;
-- Then connect with: mysql --local-infile=1 -u root -p
-- ============================================================

USE inventory_intelligence;

SET FOREIGN_KEY_CHECKS = 0;

-- 1. SUPPLIERS
LOAD DATA LOCAL INFILE '/absolute/path/to/inventory-intelligence-system/data/suppliers.csv'
INTO TABLE suppliers
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(supplier_id, supplier_name, region, avg_lead_time_days, lead_time_std_dev, reliability_score);

-- 2. PRODUCTS
LOAD DATA LOCAL INFILE '/absolute/path/to/inventory-intelligence-system/data/products.csv'
INTO TABLE products
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(product_id, sku, product_name, category, unit_cost, unit_price, supplier_id, pattern_group);

-- 3. PURCHASE ORDERS
LOAD DATA LOCAL INFILE '/absolute/path/to/inventory-intelligence-system/data/purchase_orders.csv'
INTO TABLE purchase_orders
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(po_id, product_id, supplier_id, order_date, expected_delivery_date, @actual,
 quantity_ordered, unit_cost, status)
SET actual_delivery_date = NULLIF(@actual, '');

-- 4. SALES
LOAD DATA LOCAL INFILE '/absolute/path/to/inventory-intelligence-system/data/sales.csv'
INTO TABLE sales
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(product_id, sale_date, region, units_sold, units_demanded, revenue);

-- 5. INVENTORY
LOAD DATA LOCAL INFILE '/absolute/path/to/inventory-intelligence-system/data/inventory.csv'
INTO TABLE inventory
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(product_id, snapshot_date, stock_on_hand, is_stockout, reorder_point_snapshot);

SET FOREIGN_KEY_CHECKS = 1;

-- Quick sanity checks after load
SELECT 'suppliers' AS tbl, COUNT(*) FROM suppliers
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'purchase_orders', COUNT(*) FROM purchase_orders
UNION ALL SELECT 'sales', COUNT(*) FROM sales
UNION ALL SELECT 'inventory', COUNT(*) FROM inventory;

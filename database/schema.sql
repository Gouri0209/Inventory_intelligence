-- ============================================================
-- Inventory Intelligence & Stockout Optimization System
-- Database Schema (MySQL 8.0+)
-- ============================================================

DROP DATABASE IF EXISTS inventory_intelligence;
CREATE DATABASE inventory_intelligence CHARACTER SET utf8mb4;
USE inventory_intelligence;

-- ------------------------------------------------------------
-- 1. SUPPLIERS
-- ------------------------------------------------------------
CREATE TABLE suppliers (
    supplier_id         INT PRIMARY KEY AUTO_INCREMENT,
    supplier_name       VARCHAR(120) NOT NULL,
    region              VARCHAR(60)  NOT NULL,
    avg_lead_time_days  DECIMAL(5,2) NOT NULL,      -- mean quoted lead time
    lead_time_std_dev   DECIMAL(5,2) NOT NULL,      -- variability of lead time
    reliability_score   DECIMAL(4,2) NOT NULL,      -- 0-1, derived later from PO history
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 2. PRODUCTS
-- ------------------------------------------------------------
CREATE TABLE products (
    product_id          INT PRIMARY KEY AUTO_INCREMENT,
    sku                 VARCHAR(20) UNIQUE NOT NULL,
    product_name        VARCHAR(150) NOT NULL,
    category            VARCHAR(60)  NOT NULL,
    unit_cost           DECIMAL(10,2) NOT NULL,
    unit_price          DECIMAL(10,2) NOT NULL,
    supplier_id         INT NOT NULL,
    pattern_group       VARCHAR(30)  NOT NULL,      -- which synthetic pattern this SKU belongs to (audit trail)
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_products_supplier
        FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 3. PURCHASE_ORDERS  (supplier replenishment history)
-- ------------------------------------------------------------
CREATE TABLE purchase_orders (
    po_id               INT PRIMARY KEY AUTO_INCREMENT,
    product_id          INT NOT NULL,
    supplier_id         INT NOT NULL,
    order_date          DATE NOT NULL,
    expected_delivery_date DATE NOT NULL,
    actual_delivery_date   DATE,                    -- NULL if still in transit
    quantity_ordered    INT NOT NULL,
    unit_cost           DECIMAL(10,2) NOT NULL,
    status              ENUM('Delivered','Delayed','In Transit','Cancelled') NOT NULL,
    CONSTRAINT fk_po_product  FOREIGN KEY (product_id)  REFERENCES products(product_id),
    CONSTRAINT fk_po_supplier FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 4. SALES  (daily demand at the product level)
-- ------------------------------------------------------------
CREATE TABLE sales (
    sale_id             BIGINT PRIMARY KEY AUTO_INCREMENT,
    product_id          INT NOT NULL,
    sale_date           DATE NOT NULL,
    region              VARCHAR(60) NOT NULL,
    units_sold          INT NOT NULL,
    units_demanded      INT NOT NULL,                -- what customers WANTED (>= units_sold; gap = lost sale)
    revenue             DECIMAL(12,2) NOT NULL,
    CONSTRAINT fk_sales_product FOREIGN KEY (product_id) REFERENCES products(product_id)
) ENGINE=InnoDB;

CREATE INDEX idx_sales_product_date ON sales(product_id, sale_date);

-- ------------------------------------------------------------
-- 5. INVENTORY  (daily stock snapshot)
-- ------------------------------------------------------------
CREATE TABLE inventory (
    inventory_id        BIGINT PRIMARY KEY AUTO_INCREMENT,
    product_id          INT NOT NULL,
    snapshot_date        DATE NOT NULL,
    stock_on_hand        INT NOT NULL,
    is_stockout           TINYINT(1) NOT NULL DEFAULT 0,
    reorder_point_snapshot DECIMAL(10,2),            -- reorder point calculated as of this date
    CONSTRAINT fk_inventory_product FOREIGN KEY (product_id) REFERENCES products(product_id)
) ENGINE=InnoDB;

CREATE INDEX idx_inventory_product_date ON inventory(product_id, snapshot_date);

-- ------------------------------------------------------------
-- Notes
-- ------------------------------------------------------------
-- * pattern_group on products is NOT a "real world" column — it's an audit trail so
--   the write-up can prove downstream findings match the embedded synthetic pattern.
--   Values: 'long_lead_time', 'seasonal_trend', 'demand_outpace', 'overstock', 'baseline'
-- * units_demanded - units_sold on days with is_stockout = 1 is the basis for the
--   lost-revenue calculation in the SQL analysis layer.

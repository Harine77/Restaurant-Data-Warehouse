-- ================================================================
--  03_setup_warehouse.sql
--  STEP 3 — Run in MySQL Workbench or terminal:
--      mysql -u root -p < 03_setup_warehouse.sql
--
--  STAR SCHEMA — 1 fact, 4 dims
--
--              dim_customer
--                   |
--  dim_staff ── fact_order_items ── dim_menu_item
--                   |
--               dim_date
-- ================================================================

CREATE DATABASE IF NOT EXISTS restaurant_dw;
USE restaurant_dw;

-- ────────────────────────────────────────────────────────────
--  DROP: fact first (child), then dims (parents)
-- ────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS fact_order_items;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_menu_item;
DROP TABLE IF EXISTS dim_staff;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS etl_control;


-- ════════════════════════════════════════════════════════════
--  DIM_DATE
--  No SCD — dates are immutable
--  date_key format: YYYYMMDD  (e.g. 20240115)
-- ════════════════════════════════════════════════════════════
CREATE TABLE dim_date (
    date_key        INT          PRIMARY KEY,
    full_date       DATE         NOT NULL,
    day_of_month    TINYINT      NOT NULL,
    month_num       TINYINT      NOT NULL,
    month_name      VARCHAR(15)  NOT NULL,
    quarter         TINYINT      NOT NULL,
    year            SMALLINT     NOT NULL,
    week_number     TINYINT      NOT NULL,
    day_name        VARCHAR(10)  NOT NULL,
    is_weekend      TINYINT(1)   NOT NULL DEFAULT 0
);


-- ════════════════════════════════════════════════════════════
--  DIM_CUSTOMER
--  SCD1 : phone, email          (overwrite in place)
--  SCD2 : city, loyalty_tier    (new versioned row)
-- ════════════════════════════════════════════════════════════
CREATE TABLE dim_customer (
    customer_key         INT          AUTO_INCREMENT PRIMARY KEY,
    customer_id          VARCHAR(20)  NOT NULL,
    customer_name        VARCHAR(100) NOT NULL,
    phone                VARCHAR(20),
    email                VARCHAR(150),
    city                 VARCHAR(80),
    area                 VARCHAR(80),
    loyalty_tier         VARCHAR(20),
    member_since         DATE,
    effective_start_date DATE         NOT NULL,
    effective_end_date   DATE         NULL,
    is_current           TINYINT(1)   NOT NULL DEFAULT 1,

    INDEX idx_customer_id (customer_id),
    INDEX idx_is_current  (is_current)
);


-- ════════════════════════════════════════════════════════════
--  DIM_MENU_ITEM
--  SCD1 : price                 (overwrite in place)
--  SCD2 : category              (new versioned row)
-- ════════════════════════════════════════════════════════════
CREATE TABLE dim_menu_item (
    item_key             INT          AUTO_INCREMENT PRIMARY KEY,
    item_id              VARCHAR(20)  NOT NULL,
    item_name            VARCHAR(150) NOT NULL,
    category             VARCHAR(80),
    sub_category         VARCHAR(80),
    price                DECIMAL(10,2),
    is_veg               TINYINT(1)   NOT NULL DEFAULT 1,
    is_available         TINYINT(1)   NOT NULL DEFAULT 1,
    calories             INT,
    prep_time_min        INT,
    effective_start_date DATE         NOT NULL,
    effective_end_date   DATE         NULL,
    is_current           TINYINT(1)   NOT NULL DEFAULT 1,

    INDEX idx_item_id    (item_id),
    INDEX idx_is_current (is_current)
);


-- ════════════════════════════════════════════════════════════
--  DIM_STAFF
--  SCD1 : phone, salary         (overwrite in place)
--  SCD2 : role                  (new versioned row)
-- ════════════════════════════════════════════════════════════
CREATE TABLE dim_staff (
    staff_key            INT          AUTO_INCREMENT PRIMARY KEY,
    staff_id             VARCHAR(20)  NOT NULL,
    staff_name           VARCHAR(100) NOT NULL,
    phone                VARCHAR(20),
    email                VARCHAR(100),
    role                 VARCHAR(50),
    department           VARCHAR(50),
    salary               DECIMAL(10,2),
    join_date            DATE,
    shift                VARCHAR(20),
    status               VARCHAR(20),
    effective_start_date DATE         NOT NULL,
    effective_end_date   DATE         NULL,
    is_current           TINYINT(1)   NOT NULL DEFAULT 1,

    INDEX idx_staff_id   (staff_id),
    INDEX idx_is_current (is_current)
);


-- ════════════════════════════════════════════════════════════
--  FACT_ORDER_ITEMS  ← ONE AND ONLY FACT TABLE
--  Grain  : one row per menu item sold in one order
--  Measures : quantity, unit_price, discount, line_total
--
--  Removed from original:
--    ✗ table_no       — not useful for revenue analytics
--    ✗ payment_status — always "Paid", zero variance
--    ✗ num_items      — derivable: SUM(quantity) per order
--    ✗ total_amount   — derivable: SUM(line_total) per order
--    ✗ net_amount     — derivable: SUM(line_total - discount)
--    ✗ dim_order      — collapsed; order_id kept as degenerate dim
-- ════════════════════════════════════════════════════════════
CREATE TABLE fact_order_items (
    order_item_id   VARCHAR(20)    PRIMARY KEY,

    -- Degenerate dimension (order context, no separate dim table needed)
    order_id        VARCHAR(20)    NOT NULL,
    order_type      VARCHAR(20),                    -- Dine-In / Takeaway
    payment_mode    VARCHAR(30),                    -- Cash / UPI / Card

    -- Foreign keys to dimensions
    customer_key    INT            NOT NULL,
    staff_key       INT            NOT NULL,
    item_key        INT            NOT NULL,
    date_key        INT            NOT NULL,

    -- Measures
    quantity        INT            NOT NULL DEFAULT 1,
    unit_price      DECIMAL(10,2)  NOT NULL,
    discount        DECIMAL(10,2)  NOT NULL DEFAULT 0,
    line_total      DECIMAL(10,2)  NOT NULL,

    loaded_at       TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_foi_customer FOREIGN KEY (customer_key) REFERENCES dim_customer(customer_key),
    CONSTRAINT fk_foi_staff    FOREIGN KEY (staff_key)    REFERENCES dim_staff(staff_key),
    CONSTRAINT fk_foi_item     FOREIGN KEY (item_key)     REFERENCES dim_menu_item(item_key),
    CONSTRAINT fk_foi_date     FOREIGN KEY (date_key)     REFERENCES dim_date(date_key),

    INDEX idx_order_id     (order_id),
    INDEX idx_customer_key (customer_key),
    INDEX idx_staff_key    (staff_key),
    INDEX idx_item_key     (item_key),
    INDEX idx_date_key     (date_key)
);


-- ════════════════════════════════════════════════════════════
--  ETL_CONTROL
--  Watermark per source — incremental loads use last_loaded_date
-- ════════════════════════════════════════════════════════════
CREATE TABLE etl_control (
    source_name       VARCHAR(50)  PRIMARY KEY,
    last_loaded_date  DATE         NOT NULL,
    last_run_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                                   ON UPDATE CURRENT_TIMESTAMP
);

INSERT INTO etl_control (source_name, last_loaded_date) VALUES
    ('customers',   '1900-01-01'),
    ('menu_items',  '1900-01-01'),
    ('staff',       '1900-01-01'),
    ('order_items', '1900-01-01');


-- ════════════════════════════════════════════════════════════
--  VERIFY
-- ════════════════════════════════════════════════════════════
SELECT
    TABLE_NAME                        AS `table`,
    TABLE_ROWS                        AS `rows`,
    ROUND(DATA_LENGTH  / 1024, 1)     AS `data_kb`,
    ROUND(INDEX_LENGTH / 1024, 1)     AS `index_kb`
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'restaurant_dw'
ORDER BY TABLE_NAME;

SELECT '03_setup_warehouse.sql executed successfully' AS status;
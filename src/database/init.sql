-- ==============================================================================
-- Kafka Food Processing Pipeline - Database Initialization
-- ==============================================================================
--
-- This script initializes the PostgreSQL database for order storage.
-- It runs automatically when the PostgreSQL Docker container first starts.
--
-- WHY BOTH KAFKA AND DATABASE?
-- - Kafka: Immutable event log (source of truth for "what happened")
-- - Database: Current state (optimized for queries)
-- - Pattern: Event Sourcing + CQRS (Command Query Responsibility Segregation)
--

-- ==============================================================================
-- ORDERS TABLE
-- ==============================================================================
--
-- DESIGN DECISIONS:
--
-- 1. PRIMARY KEY: order_id (VARCHAR)
--    - Natural key from business domain (e.g., "ORD-20250110-00001")
--    - Better than surrogate UUID for debugging/support
--    - Ensures idempotency (duplicate messages don't create duplicate rows)
--
-- 2. JSONB COLUMN: items
--    - PostgreSQL's JSONB (binary JSON) is indexed and queryable
--    - Flexible schema for variable order items
--    - Can query inside JSON: SELECT * WHERE items @> '[{"name": "Burger"}]'
--    - Better than separate order_items table for this use case
--
-- 3. TIMESTAMPS:
--    - created_at: When order was created (from Kafka message)
--    - processed_at: When consumer wrote to database (auto-set by DB)
--    - Helps track processing latency (processed_at - created_at)
--

CREATE TABLE IF NOT EXISTS orders (
    -- Primary key: Natural business identifier from Kafka message
    -- Format: ORD-YYYYMMDD-NNNNN (e.g., ORD-20250110-00001)
    order_id VARCHAR(50) PRIMARY KEY,

    -- Customer identifier (used as Kafka partition key)
    -- All orders from same customer go to same partition (maintains ordering)
    customer_id VARCHAR(50) NOT NULL,

    -- Order items stored as JSONB array
    -- Example: [{"name": "Burger", "quantity": 2, "price": 8.99}, ...]
    -- JSONB allows indexing and querying (GIN index below)
    items JSONB NOT NULL,

    -- Total order amount (calculated from items)
    -- DECIMAL(10,2) stores up to $99,999,999.99 with exact precision
    -- Never use FLOAT/DOUBLE for money (rounding errors!)
    total_amount DECIMAL(10, 2) NOT NULL CHECK (total_amount > 0),

    -- Order status (pending, processing, completed, failed, etc.)
    -- Could be ENUM in production for type safety
    status VARCHAR(20) NOT NULL,

    -- When the order was created (from Kafka message timestamp)
    created_at TIMESTAMP NOT NULL,

    -- When the order was written to database (auto-set by PostgreSQL)
    -- Used to measure consumer processing latency
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- INDEXES
-- ==============================================================================
--
-- INDEXING STRATEGY:
--
-- 1. PRIMARY KEY INDEX (order_id):
--    - Automatically created by PostgreSQL for PRIMARY KEY
--    - Used for idempotency checks (INSERT ... ON CONFLICT)
--
-- 2. INDEX ON created_at:
--    - Queries like "orders from last hour" need this
--    - Time-based queries are common (analytics, monitoring)
--    - B-tree index (default) works well for range queries
--
-- 3. INDEX ON customer_id:
--    - Queries like "all orders for customer X"
--    - Matches Kafka partition key (natural query pattern)
--
-- 4. GIN INDEX ON items (JSONB):
--    - Allows fast queries inside JSON structure
--    - Example: Find all orders containing "Burger"
--    - GIN = Generalized Inverted Index (for composite values like JSON, arrays)
--

-- Index for time-based queries (e.g., "orders in last 24 hours")
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);

-- Index for customer-based queries (e.g., "all orders for CUST-001")
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);

-- GIN index for querying inside JSONB items column
-- Enables queries like: WHERE items @> '[{"name": "Burger"}]'
CREATE INDEX IF NOT EXISTS idx_orders_items_gin ON orders USING GIN(items);

-- Composite index for common query pattern: customer + time range
-- Example: "Customer X's orders from last month"
CREATE INDEX IF NOT EXISTS idx_orders_customer_created ON orders(customer_id, created_at);

-- ==============================================================================
-- COMMENTS (PostgreSQL Documentation)
-- ==============================================================================
-- Add metadata to database objects for documentation

COMMENT ON TABLE orders IS
'Order records consumed from Kafka food-orders topic. Represents current state of orders.';

COMMENT ON COLUMN orders.order_id IS
'Unique order identifier from Kafka message. Format: ORD-YYYYMMDD-NNNNN. Used for idempotency.';

COMMENT ON COLUMN orders.customer_id IS
'Customer identifier. Used as Kafka partition key to maintain ordering per customer.';

COMMENT ON COLUMN orders.items IS
'Order items as JSONB array. Example: [{"name": "Burger", "quantity": 2, "price": 8.99}]';

COMMENT ON COLUMN orders.total_amount IS
'Total order amount in dollars. Calculated from sum of items. Must be > 0.';

COMMENT ON COLUMN orders.status IS
'Order status: pending, processing, completed, failed, etc.';

COMMENT ON COLUMN orders.created_at IS
'Timestamp when order was created (from Kafka message). Used for time-based queries.';

COMMENT ON COLUMN orders.processed_at IS
'Timestamp when order was written to database by consumer. Auto-set. Used for latency tracking.';

-- ==============================================================================
-- GRANT PERMISSIONS (if needed)
-- ==============================================================================
-- In production, use principle of least privilege
-- Consumer service only needs INSERT, SELECT (not DELETE, UPDATE)

-- Already granted via POSTGRES_USER in Docker Compose, but good practice to be explicit:
-- GRANT SELECT, INSERT ON orders TO kafka_user;

-- ==============================================================================
-- SAMPLE QUERIES FOR TESTING
-- ==============================================================================
--
-- List all orders:
--   SELECT * FROM orders ORDER BY created_at DESC;
--
-- Count orders per customer:
--   SELECT customer_id, COUNT(*) FROM orders GROUP BY customer_id;
--
-- Find orders containing specific item:
--   SELECT * FROM orders WHERE items @> '[{"name": "Burger"}]';
--
-- Calculate processing latency:
--   SELECT order_id,
--          created_at,
--          processed_at,
--          EXTRACT(EPOCH FROM (processed_at - created_at)) AS latency_seconds
--   FROM orders
--   ORDER BY latency_seconds DESC;
--
-- Orders from last hour:
--   SELECT * FROM orders
--   WHERE created_at > NOW() - INTERVAL '1 hour'
--   ORDER BY created_at DESC;
--
-- Total revenue per customer:
--   SELECT customer_id, SUM(total_amount) as total_spent
--   FROM orders
--   GROUP BY customer_id
--   ORDER BY total_spent DESC;
--
-- ==============================================================================

-- Verify table creation
\echo '✅ Orders table created successfully!'
\echo ''
\echo 'Table schema:'
\d orders

\echo ''
\echo 'Indexes created:'
\di

\echo ''
\echo '======================================================================'
\echo 'Database initialization complete!'
\echo '======================================================================'

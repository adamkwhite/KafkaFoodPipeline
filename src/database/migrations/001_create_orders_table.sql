-- ==============================================================================
-- MIGRATION 001: Create Orders Table
-- ==============================================================================
--
-- Migration: 001_create_orders_table
-- Description: Initial schema for order storage from Kafka stream
-- Author: Kafka Food Pipeline
-- Date: 2025-01-10
--
-- MIGRATION STRATEGY:
-- - This migration creates the core orders table
-- - Idempotent: Safe to run multiple times (IF NOT EXISTS)
-- - Rollback: See rollback section at bottom
--
-- ==============================================================================

-- ==============================================================================
-- FORWARD MIGRATION (Apply Changes)
-- ==============================================================================

BEGIN;

-- Create orders table
CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    items JSONB NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL CHECK (total_amount > 0),
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_items_gin ON orders USING GIN(items);
CREATE INDEX IF NOT EXISTS idx_orders_customer_created ON orders(customer_id, created_at);

-- Add comments
COMMENT ON TABLE orders IS
'Order records consumed from Kafka food-orders topic. Migration 001.';

COMMENT ON COLUMN orders.order_id IS
'Unique order identifier. Format: ORD-YYYYMMDD-NNNNN.';

COMMENT ON COLUMN orders.customer_id IS
'Customer identifier. Used as Kafka partition key.';

COMMENT ON COLUMN orders.items IS
'Order items as JSONB array. Indexed with GIN for fast queries.';

COMMENT ON COLUMN orders.total_amount IS
'Total order amount. Must be positive.';

COMMENT ON COLUMN orders.status IS
'Order status: pending, processing, completed, failed.';

COMMENT ON COLUMN orders.created_at IS
'Order creation timestamp from Kafka message.';

COMMENT ON COLUMN orders.processed_at IS
'Database write timestamp. Used for latency tracking.';

COMMIT;

\echo '✅ Migration 001: Orders table created successfully!'

-- ==============================================================================
-- ROLLBACK MIGRATION (Revert Changes)
-- ==============================================================================
--
-- To rollback this migration, run:
--
-- BEGIN;
-- DROP INDEX IF EXISTS idx_orders_customer_created;
-- DROP INDEX IF EXISTS idx_orders_items_gin;
-- DROP INDEX IF EXISTS idx_orders_customer_id;
-- DROP INDEX IF EXISTS idx_orders_created_at;
-- DROP TABLE IF EXISTS orders;
-- COMMIT;
--
-- ==============================================================================

"""
SQLAlchemy ORM Models for Order Storage

This module defines the database models used by the Kafka consumer to persist
orders from the Kafka stream into PostgreSQL.

WHAT IS AN ORM?
- Object-Relational Mapping: Maps database tables to Python classes
- Rows become objects, columns become attributes
- Abstracts SQL - write Python code instead of raw SQL queries
- SQLAlchemy is the most popular Python ORM

WHY USE ORM?
- Type safety: Python type hints + Pydantic validation
- Database abstraction: Switch databases easier
- Relationship handling: Foreign keys, joins managed automatically
- Migration support: Alembic (SQLAlchemy's migration tool)
- Connection pooling: Built-in connection management

PATTERN: DECLARATIVE BASE
- SQLAlchemy 2.0+ uses declarative mapping
- Base class provides ORM functionality
- Inherit from Base to create models
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DECIMAL,
    TIMESTAMP,
    CheckConstraint,
    Index,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# ==============================================================================
# DECLARATIVE BASE
# ==============================================================================
# All models inherit from this base class
# Provides SQLAlchemy ORM functionality


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


# ==============================================================================
# ORDER MODEL
# ==============================================================================
#
# SQLALCHEMY 2.0+ FEATURES:
# - Mapped[]: Type annotations for columns (Python 3.9+)
# - mapped_column(): Defines column with type inference
# - Relationship(): Would define foreign keys (not used here)
#
# MAPPING TO DATABASE:
# - Python class -> SQL table
# - Class attributes -> SQL columns
# - Object instance -> SQL row
#
# EXAMPLE:
#   order = Order(order_id="ORD-001", customer_id="CUST-001", ...)
#   session.add(order)       # Add to session
#   session.commit()         # INSERT INTO orders ...
#


class Order(Base):
    """
    Order model representing a food order from Kafka stream.

    This model maps to the 'orders' table in PostgreSQL.
    Each instance represents one order consumed from Kafka and persisted to DB.

    Attributes:
        order_id: Unique order identifier (PRIMARY KEY)
        customer_id: Customer who placed the order (Kafka partition key)
        items: Order items as JSON array
        total_amount: Total order cost
        status: Order status (pending, completed, etc.)
        created_at: When order was created (from Kafka message)
        processed_at: When order was written to database
    """

    __tablename__ = "orders"

    # ==========================================================================
    # PRIMARY KEY
    # ==========================================================================
    # order_id is the natural business key from Kafka message
    # Format: ORD-YYYYMMDD-NNNNN
    # primary_key=True automatically creates index

    order_id: Mapped[str] = mapped_column(
        String(50), primary_key=True, comment="Unique order identifier from Kafka message"
    )

    # ==========================================================================
    # CUSTOMER REFERENCE
    # ==========================================================================
    # customer_id is used as Kafka partition key
    # All orders from same customer go to same partition (ordering guarantee)
    # nullable=False means NOT NULL constraint in SQL

    customer_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,  # Creates idx_orders_customer_id index
        comment="Customer identifier, used as Kafka partition key",
    )

    # ==========================================================================
    # ORDER ITEMS (JSONB)
    # ==========================================================================
    # PostgreSQL-specific JSONB type (binary JSON)
    # Stores array of items: [{"name": "Burger", "quantity": 2, "price": 8.99}, ...]
    #
    # JSONB vs JSON:
    # - JSONB: Binary format, indexed, slightly slower writes, faster reads
    # - JSON: Text format, not indexed, faster writes, slower reads
    # - Use JSONB for querying, JSON for pure storage
    #
    # GIN INDEX (created in SQL):
    # - Allows queries like: WHERE items @> '[{"name": "Burger"}]'
    # - Full-text search inside JSON

    items: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Order items as JSONB array. Indexed with GIN for fast queries.",
    )

    # ==========================================================================
    # TOTAL AMOUNT (DECIMAL)
    # ==========================================================================
    # DECIMAL(10, 2) for money (exact precision)
    # - 10 total digits, 2 after decimal point
    # - Max value: 99,999,999.99
    # - Never use FLOAT for money (rounding errors!)
    #
    # CheckConstraint ensures positive amounts

    total_amount: Mapped[float] = mapped_column(
        DECIMAL(10, 2),
        CheckConstraint("total_amount > 0", name="check_positive_amount"),
        nullable=False,
        comment="Total order amount. Must be positive.",
    )

    # ==========================================================================
    # ORDER STATUS
    # ==========================================================================
    # Status field (pending, processing, completed, failed, etc.)
    # Could use ENUM for type safety in production:
    #   status_enum = Enum('pending', 'completed', 'failed', name='order_status')
    #   status: Mapped[str] = mapped_column(status_enum, ...)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Order status: pending, processing, completed, failed"
    )

    # ==========================================================================
    # TIMESTAMPS
    # ==========================================================================
    # Two timestamps for latency tracking:
    # 1. created_at: When order was created (from Kafka message)
    # 2. processed_at: When consumer wrote to database (auto-set)
    #
    # Latency = processed_at - created_at (shows consumer lag)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        index=True,  # For time-based queries
        comment="Order creation timestamp from Kafka message",
    )

    processed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),  # Database sets this
        comment="Database write timestamp, used for latency tracking",
    )

    # ==========================================================================
    # TABLE-LEVEL CONFIGURATION
    # ==========================================================================
    # Additional indexes defined at table level (beyond column-level indexes)

    __table_args__ = (
        # GIN index for JSONB queries (full-text search in items)
        Index("idx_orders_items_gin", "items", postgresql_using="gin"),
        # Composite index for common query: customer + time range
        # Example: "Get customer X's orders from last month"
        # First column (customer_id) for filtering, second (created_at) for sorting
        Index("idx_orders_customer_created", "customer_id", "created_at"),
        # Table comment
        {"comment": "Order records consumed from Kafka food-orders topic"},
    )

    # ==========================================================================
    # STRING REPRESENTATION
    # ==========================================================================
    # Useful for debugging and logging

    def __repr__(self) -> str:
        """String representation of Order instance."""
        return (
            f"<Order(order_id={self.order_id}, "
            f"customer_id={self.customer_id}, "
            f"total_amount={self.total_amount}, "
            f"status={self.status})>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"Order {self.order_id} - {self.customer_id} - ${self.total_amount}"


# ==============================================================================
# USAGE EXAMPLES
# ==============================================================================
"""
# Create database engine and session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine('postgresql://user:pass@localhost/dbname')
Session = sessionmaker(bind=engine)
session = Session()

# Create new order
new_order = Order(
    order_id="ORD-20250110-00001",
    customer_id="CUST-00001",
    items=[
        {"name": "Burger", "quantity": 2, "price": 8.99},
        {"name": "Fries", "quantity": 1, "price": 3.49}
    ],
    total_amount=21.47,
    status="pending",
    created_at=datetime.utcnow()
)

# Insert to database
session.add(new_order)
session.commit()

# Query orders
orders = session.query(Order).filter(Order.customer_id == "CUST-00001").all()

# Query with JSONB (find orders with Burger)
burger_orders = session.query(Order).filter(
    Order.items.contains([{"name": "Burger"}])
).all()

# Time-based query (last 24 hours)
from datetime import timedelta
yesterday = datetime.utcnow() - timedelta(days=1)
recent_orders = session.query(Order).filter(
    Order.created_at > yesterday
).all()

# Update order status
order = session.query(Order).filter(Order.order_id == "ORD-20250110-00001").first()
order.status = "completed"
session.commit()

# Handle duplicates (idempotency)
from sqlalchemy.exc import IntegrityError
try:
    session.add(duplicate_order)
    session.commit()
except IntegrityError:
    session.rollback()
    print("Order already exists!")

# Close session
session.close()
"""

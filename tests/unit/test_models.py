"""
Unit Tests for Order Model

Tests the SQLAlchemy ORM Order model used for database persistence.
These are unit tests that don't require a database connection.

TEST STRATEGY:
- Test model creation from Kafka messages
- Test data conversion methods (to_dict, from_kafka_message)
- Test field validation and constraints
- Test timestamp parsing
- Test string representations
"""

from datetime import datetime
from decimal import Decimal

import pytest

from src.consumer.models import Order

# ==============================================================================
# MODEL CREATION TESTS
# ==============================================================================


@pytest.mark.unit
def test_order_from_kafka_message(sample_order_data):
    """Test creating Order from Kafka message data."""
    order = Order.from_kafka_message(sample_order_data)

    assert order.order_id == sample_order_data["order_id"]
    assert order.customer_id == sample_order_data["customer_id"]
    assert order.customer_name == sample_order_data["customer_name"]
    assert order.customer_email == sample_order_data["customer_email"]
    assert order.items == sample_order_data["items"]
    assert float(order.total_amount) == sample_order_data["total_amount"]
    assert order.status == sample_order_data["status"]
    assert isinstance(order.created_at, datetime)


@pytest.mark.unit
def test_order_timestamp_parsing_with_z_suffix():
    """Test timestamp parsing with Z suffix (UTC)."""
    data = {
        "order_id": "ORD-20250110-00001",
        "customer_id": "CUST-00001",
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "items": [{"name": "Test", "quantity": 1, "price": 10.0, "subtotal": 10.0}],
        "total_amount": 10.0,
        "status": "pending",
        "created_at": "2025-01-10T14:30:00.000Z",  # Z suffix
    }

    order = Order.from_kafka_message(data)
    assert isinstance(order.created_at, datetime)


@pytest.mark.unit
def test_order_timestamp_parsing_with_offset():
    """Test timestamp parsing with timezone offset."""
    data = {
        "order_id": "ORD-20250110-00001",
        "customer_id": "CUST-00001",
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "items": [{"name": "Test", "quantity": 1, "price": 10.0, "subtotal": 10.0}],
        "total_amount": 10.0,
        "status": "pending",
        "created_at": "2025-01-10T14:30:00+00:00",  # Offset format
    }

    order = Order.from_kafka_message(data)
    assert isinstance(order.created_at, datetime)


@pytest.mark.unit
def test_order_total_amount_decimal_conversion():
    """Test that total_amount is converted to Decimal correctly."""
    data = {
        "order_id": "ORD-20250110-00001",
        "customer_id": "CUST-00001",
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "items": [{"name": "Test", "quantity": 1, "price": 10.99, "subtotal": 10.99}],
        "total_amount": 10.99,
        "status": "pending",
        "created_at": "2025-01-10T14:30:00+00:00",
    }

    order = Order.from_kafka_message(data)
    assert isinstance(order.total_amount, Decimal)
    assert float(order.total_amount) == 10.99


# ==============================================================================
# TO_DICT CONVERSION TESTS
# ==============================================================================


@pytest.mark.unit
def test_order_to_dict(sample_order_data):
    """Test converting Order to dictionary."""
    order = Order.from_kafka_message(sample_order_data)
    order_dict = order.to_dict()

    # Check all fields present
    assert "order_id" in order_dict
    assert "customer_id" in order_dict
    assert "customer_name" in order_dict
    assert "customer_email" in order_dict
    assert "items" in order_dict
    assert "total_amount" in order_dict
    assert "status" in order_dict
    assert "created_at" in order_dict
    assert "processed_at" in order_dict

    # Check values
    assert order_dict["order_id"] == sample_order_data["order_id"]
    assert order_dict["customer_id"] == sample_order_data["customer_id"]


@pytest.mark.unit
def test_order_to_dict_types():
    """Test that to_dict returns correct types."""
    data = {
        "order_id": "ORD-20250110-00001",
        "customer_id": "CUST-00001",
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "items": [{"name": "Test", "quantity": 1, "price": 10.0, "subtotal": 10.0}],
        "total_amount": 10.0,
        "status": "pending",
        "created_at": "2025-01-10T14:30:00+00:00",
    }

    order = Order.from_kafka_message(data)
    order_dict = order.to_dict()

    # Check types
    assert isinstance(order_dict["order_id"], str)
    assert isinstance(order_dict["customer_id"], str)
    assert isinstance(order_dict["total_amount"], float)
    assert isinstance(order_dict["items"], dict) or isinstance(order_dict["items"], list)
    assert isinstance(order_dict["created_at"], str)  # Should be ISO format string


# ==============================================================================
# STRING REPRESENTATION TESTS
# ==============================================================================


@pytest.mark.unit
def test_order_repr(sample_order_data):
    """Test Order __repr__ method."""
    order = Order.from_kafka_message(sample_order_data)
    repr_str = repr(order)

    # Should contain key information
    assert "Order" in repr_str
    assert sample_order_data["order_id"] in repr_str
    assert sample_order_data["customer_id"] in repr_str


@pytest.mark.unit
def test_order_str(sample_order_data):
    """Test Order __str__ method."""
    order = Order.from_kafka_message(sample_order_data)
    str_repr = str(order)

    # Should be human-readable
    assert sample_order_data["order_id"] in str_repr
    assert sample_order_data["customer_id"] in str_repr
    assert "$" in str_repr  # Should show price


# ==============================================================================
# FIELD VALIDATION TESTS
# ==============================================================================


@pytest.mark.unit
def test_order_items_as_dict():
    """Test that items can be stored as dict (JSONB)."""
    data = {
        "order_id": "ORD-20250110-00001",
        "customer_id": "CUST-00001",
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "items": {"item1": "value1", "item2": "value2"},  # Dict instead of list
        "total_amount": 10.0,
        "status": "pending",
        "created_at": "2025-01-10T14:30:00+00:00",
    }

    order = Order.from_kafka_message(data)
    assert isinstance(order.items, dict)


@pytest.mark.unit
def test_order_items_as_list():
    """Test that items can be stored as list (JSONB)."""
    data = {
        "order_id": "ORD-20250110-00001",
        "customer_id": "CUST-00001",
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "items": [{"name": "Item 1"}, {"name": "Item 2"}],
        "total_amount": 10.0,
        "status": "pending",
        "created_at": "2025-01-10T14:30:00+00:00",
    }

    order = Order.from_kafka_message(data)
    # items field is dict type in mapping, but JSONB can store list
    assert isinstance(order.items, (dict, list))


@pytest.mark.unit
def test_order_default_status():
    """Test that status can be provided or use default."""
    data = {
        "order_id": "ORD-20250110-00001",
        "customer_id": "CUST-00001",
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "items": [],
        "total_amount": 10.0,
        # No status provided
        "created_at": "2025-01-10T14:30:00+00:00",
    }

    order = Order.from_kafka_message(data)
    assert order.status == "pending"  # Should use default


# ==============================================================================
# EDGE CASE TESTS
# ==============================================================================


@pytest.mark.unit
def test_order_with_empty_items():
    """Test creating order with empty items list."""
    data = {
        "order_id": "ORD-20250110-00001",
        "customer_id": "CUST-00001",
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "items": [],  # Empty
        "total_amount": 0.01,  # Minimum amount
        "status": "pending",
        "created_at": "2025-01-10T14:30:00+00:00",
    }

    order = Order.from_kafka_message(data)
    assert order.items == []


@pytest.mark.unit
def test_order_with_large_total():
    """Test order with large total amount."""
    data = {
        "order_id": "ORD-20250110-00001",
        "customer_id": "CUST-00001",
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "items": [{"name": "Expensive", "quantity": 1, "price": 99999.99, "subtotal": 99999.99}],
        "total_amount": 99999.99,
        "status": "pending",
        "created_at": "2025-01-10T14:30:00+00:00",
    }

    order = Order.from_kafka_message(data)
    assert float(order.total_amount) == 99999.99


@pytest.mark.unit
def test_order_with_many_items():
    """Test order with many items."""
    items = [
        {"name": f"Item {i}", "quantity": 1, "price": 1.0, "subtotal": 1.0} for i in range(100)
    ]

    data = {
        "order_id": "ORD-20250110-00001",
        "customer_id": "CUST-00001",
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "items": items,
        "total_amount": 100.0,
        "status": "pending",
        "created_at": "2025-01-10T14:30:00+00:00",
    }

    order = Order.from_kafka_message(data)
    assert len(order.items) == 100


@pytest.mark.unit
def test_order_with_special_characters():
    """Test order with special characters in fields."""
    data = {
        "order_id": "ORD-20250110-00001",
        "customer_id": "CUST-00001",
        "customer_name": "José María O'Brien-Smith",
        "customer_email": "josé.maría@example.com",
        "items": [{"name": "Café & Crêpe", "quantity": 1, "price": 10.0, "subtotal": 10.0}],
        "total_amount": 10.0,
        "status": "pending",
        "created_at": "2025-01-10T14:30:00+00:00",
    }

    order = Order.from_kafka_message(data)
    assert order.customer_name == "José María O'Brien-Smith"
    assert "Café" in order.items[0]["name"]


# ==============================================================================
# DECIMAL PRECISION TESTS
# ==============================================================================


@pytest.mark.unit
def test_order_decimal_precision():
    """Test that Decimal maintains precision for monetary values."""
    data = {
        "order_id": "ORD-20250110-00001",
        "customer_id": "CUST-00001",
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "items": [{"name": "Test", "quantity": 1, "price": 10.99, "subtotal": 10.99}],
        "total_amount": 10.99,
        "status": "pending",
        "created_at": "2025-01-10T14:30:00+00:00",
    }

    order = Order.from_kafka_message(data)

    # Decimal should maintain exact precision
    assert str(order.total_amount) == "10.99"
    # Not "10.989999..." like float would


@pytest.mark.unit
def test_order_decimal_arithmetic():
    """Test that Decimal handles arithmetic correctly."""
    data = {
        "order_id": "ORD-20250110-00001",
        "customer_id": "CUST-00001",
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "items": [{"name": "Item 1", "quantity": 3, "price": 0.10, "subtotal": 0.30}],
        "total_amount": 0.30,
        "status": "pending",
        "created_at": "2025-01-10T14:30:00+00:00",
    }

    order = Order.from_kafka_message(data)

    # Should be exactly 0.30, not 0.30000000000000004
    assert str(order.total_amount) == "0.30"

"""
Unit Tests for MockDataGenerator

Tests the mock data generation logic used by the producer service.
These are pure unit tests with no external dependencies.

TEST STRATEGY:
- Test reproducibility (same seed → same data)
- Test data validity (correct formats, ranges)
- Test constraints (positive prices, non-empty lists)
- Test edge cases (min/max quantities, unique IDs)
"""

from datetime import datetime

import pytest

from src.producer.mock_data import MockDataGenerator

# ==============================================================================
# INITIALIZATION TESTS
# ==============================================================================


@pytest.mark.unit
def test_mock_data_generator_initialization():
    """Test that MockDataGenerator initializes correctly."""
    generator = MockDataGenerator(seed=42)

    assert generator is not None
    assert len(generator.customers) > 0
    assert len(generator.menu_items) > 0


@pytest.mark.unit
def test_seed_reproducibility():
    """Test that same seed produces same data."""
    gen1 = MockDataGenerator(seed=42)
    gen2 = MockDataGenerator(seed=42)

    # Generate customers
    customers1 = gen1.customers
    customers2 = gen2.customers

    # Should be identical
    assert len(customers1) == len(customers2)
    assert customers1[0]["customer_id"] == customers2[0]["customer_id"]
    assert customers1[0]["name"] == customers2[0]["name"]
    assert customers1[0]["email"] == customers2[0]["email"]


@pytest.mark.unit
def test_different_seeds_produce_different_data():
    """Test that different seeds produce different data."""
    gen1 = MockDataGenerator(seed=42)
    gen2 = MockDataGenerator(seed=100)

    customers1 = gen1.customers
    customers2 = gen2.customers

    # Should be different (highly unlikely to match)
    assert customers1[0]["name"] != customers2[0]["name"]


# ==============================================================================
# CUSTOMER GENERATION TESTS
# ==============================================================================


@pytest.mark.unit
def test_generate_customers_count():
    """Test that correct number of customers are generated."""
    num_customers = 50
    generator = MockDataGenerator(seed=42, num_customers=num_customers)

    assert len(generator.customers) == num_customers


@pytest.mark.unit
def test_customer_data_structure():
    """Test that customer data has correct structure."""
    generator = MockDataGenerator(seed=42)
    customer = generator.customers[0]

    # Check required fields
    assert "customer_id" in customer
    assert "name" in customer
    assert "email" in customer

    # Check field types
    assert isinstance(customer["customer_id"], str)
    assert isinstance(customer["name"], str)
    assert isinstance(customer["email"], str)

    # Check formats
    assert customer["customer_id"].startswith("CUST-")
    assert "@" in customer["email"]


@pytest.mark.unit
def test_customer_ids_unique():
    """Test that all customer IDs are unique."""
    generator = MockDataGenerator(seed=42, num_customers=100)
    customer_ids = [c["customer_id"] for c in generator.customers]

    assert len(customer_ids) == len(set(customer_ids))  # No duplicates


# ==============================================================================
# MENU ITEM GENERATION TESTS
# ==============================================================================


@pytest.mark.unit
def test_generate_menu_items_count():
    """Test that correct number of menu items are generated."""
    num_items = 30
    generator = MockDataGenerator(seed=42, num_menu_items=num_items)

    assert len(generator.menu_items) == num_items


@pytest.mark.unit
def test_menu_item_data_structure():
    """Test that menu item data has correct structure."""
    generator = MockDataGenerator(seed=42)
    item = generator.menu_items[0]

    # Check required fields
    assert "item_id" in item
    assert "name" in item
    assert "category" in item
    assert "price" in item

    # Check field types
    assert isinstance(item["item_id"], str)
    assert isinstance(item["name"], str)
    assert isinstance(item["category"], str)
    assert isinstance(item["price"], float)

    # Check formats and constraints
    assert item["item_id"].startswith("ITEM-")
    assert item["price"] > 0
    assert item["price"] < 100  # Reasonable max price


@pytest.mark.unit
def test_menu_item_ids_unique():
    """Test that all menu item IDs are unique."""
    generator = MockDataGenerator(seed=42, num_menu_items=50)
    item_ids = [i["item_id"] for i in generator.menu_items]

    assert len(item_ids) == len(set(item_ids))  # No duplicates


@pytest.mark.unit
def test_menu_item_categories_valid():
    """Test that menu items have valid categories."""
    generator = MockDataGenerator(seed=42)
    valid_categories = ["Appetizer", "Main Course", "Side", "Dessert", "Beverage"]

    for item in generator.menu_items:
        assert item["category"] in valid_categories


# ==============================================================================
# ORDER GENERATION TESTS
# ==============================================================================


@pytest.mark.unit
def test_generate_order_structure():
    """Test that generated order has correct structure."""
    generator = MockDataGenerator(seed=42)
    order = generator.generate_order()

    # Check required fields
    required_fields = [
        "order_id",
        "customer_id",
        "customer_name",
        "customer_email",
        "items",
        "total_amount",
        "status",
        "created_at",
    ]

    for field in required_fields:
        assert field in order, f"Missing required field: {field}"


@pytest.mark.unit
def test_order_id_format():
    """Test that order ID follows correct format."""
    generator = MockDataGenerator(seed=42)
    order = generator.generate_order()

    order_id = order["order_id"]
    assert order_id.startswith("ORD-")

    # Check date format in ID (ORD-YYYYMMDD-NNNNN)
    parts = order_id.split("-")
    assert len(parts) == 3
    assert len(parts[1]) == 8  # YYYYMMDD
    assert parts[1].isdigit()
    assert len(parts[2]) == 5  # NNNNN
    assert parts[2].isdigit()


@pytest.mark.unit
def test_order_customer_exists():
    """Test that order references existing customer."""
    generator = MockDataGenerator(seed=42)
    order = generator.generate_order()

    customer_ids = [c["customer_id"] for c in generator.customers]
    assert order["customer_id"] in customer_ids


@pytest.mark.unit
def test_order_items_not_empty():
    """Test that order has at least one item."""
    generator = MockDataGenerator(seed=42)

    # Generate multiple orders to test
    for _ in range(10):
        order = generator.generate_order()
        assert len(order["items"]) > 0
        assert len(order["items"]) <= 5  # Max 5 items per order


@pytest.mark.unit
def test_order_item_structure():
    """Test that order items have correct structure."""
    generator = MockDataGenerator(seed=42)
    order = generator.generate_order()

    for item in order["items"]:
        assert "item_id" in item
        assert "name" in item
        assert "quantity" in item
        assert "price" in item
        assert "subtotal" in item

        # Check types
        assert isinstance(item["item_id"], str)
        assert isinstance(item["name"], str)
        assert isinstance(item["quantity"], int)
        assert isinstance(item["price"], float)
        assert isinstance(item["subtotal"], float)

        # Check constraints
        assert item["quantity"] > 0
        assert item["price"] > 0
        assert item["subtotal"] == round(item["quantity"] * item["price"], 2)


@pytest.mark.unit
def test_order_total_amount_calculation():
    """Test that order total is correctly calculated."""
    generator = MockDataGenerator(seed=42)
    order = generator.generate_order()

    # Calculate expected total
    expected_total = sum(item["subtotal"] for item in order["items"])
    expected_total = round(expected_total, 2)

    assert order["total_amount"] == expected_total


@pytest.mark.unit
def test_order_total_amount_positive():
    """Test that order total is always positive."""
    generator = MockDataGenerator(seed=42)

    for _ in range(20):
        order = generator.generate_order()
        assert order["total_amount"] > 0


@pytest.mark.unit
def test_order_status_valid():
    """Test that order has valid status."""
    generator = MockDataGenerator(seed=42)
    order = generator.generate_order()

    # For now, all generated orders are "pending"
    assert order["status"] == "pending"


@pytest.mark.unit
def test_order_timestamp_format():
    """Test that order timestamp is valid ISO 8601 format."""
    generator = MockDataGenerator(seed=42)
    order = generator.generate_order()

    # Should be parseable as datetime
    timestamp_str = order["created_at"]
    try:
        # Try parsing with Z suffix
        if timestamp_str.endswith("Z"):
            timestamp_str = timestamp_str[:-1] + "+00:00"
        datetime.fromisoformat(timestamp_str)
    except ValueError:
        pytest.fail(f"Invalid timestamp format: {order['created_at']}")


# ==============================================================================
# EDGE CASES AND CONSTRAINTS
# ==============================================================================


@pytest.mark.unit
def test_order_generation_consistency():
    """Test that multiple orders can be generated consistently."""
    generator = MockDataGenerator(seed=42)

    orders = [generator.generate_order() for _ in range(100)]

    # All orders should be valid
    assert len(orders) == 100

    # All order IDs should be unique
    order_ids = [o["order_id"] for o in orders]
    assert len(order_ids) == len(set(order_ids))


@pytest.mark.unit
def test_minimum_configuration():
    """Test generator with minimum configuration."""
    generator = MockDataGenerator(seed=42, num_customers=1, num_menu_items=1)

    assert len(generator.customers) == 1
    assert len(generator.menu_items) == 1

    # Should still generate valid orders
    order = generator.generate_order()
    assert order is not None
    assert len(order["items"]) > 0


@pytest.mark.unit
def test_large_configuration():
    """Test generator with large configuration."""
    generator = MockDataGenerator(seed=42, num_customers=1000, num_menu_items=100)

    assert len(generator.customers) == 1000
    assert len(generator.menu_items) == 100

    # Should still generate valid orders
    order = generator.generate_order()
    assert order is not None


@pytest.mark.unit
def test_order_sequence_counter():
    """Test that order sequence counter increments."""
    generator = MockDataGenerator(seed=42)

    order1 = generator.generate_order()
    order2 = generator.generate_order()

    # Extract sequence numbers from order IDs
    seq1 = int(order1["order_id"].split("-")[2])
    seq2 = int(order2["order_id"].split("-")[2])

    # Should increment (unless date changed, but unlikely in test)
    assert seq2 > seq1 or seq1 == 99999  # Handle rollover


# ==============================================================================
# DATA QUALITY TESTS
# ==============================================================================


@pytest.mark.unit
def test_customer_names_realistic():
    """Test that customer names look realistic."""
    generator = MockDataGenerator(seed=42)

    for customer in generator.customers[:10]:
        name = customer["name"]
        # Should have at least first and last name
        assert len(name.split()) >= 2
        # Should be title case
        assert name == name.title() or " " in name


@pytest.mark.unit
def test_emails_valid_format():
    """Test that generated emails have valid format."""
    generator = MockDataGenerator(seed=42)

    for customer in generator.customers:
        email = customer["email"]
        # Basic email validation
        assert "@" in email
        assert "." in email.split("@")[1]  # Domain has extension


@pytest.mark.unit
def test_menu_prices_realistic():
    """Test that menu item prices are realistic."""
    generator = MockDataGenerator(seed=42)

    for item in generator.menu_items:
        price = item["price"]
        # Reasonable price range for food
        assert 0.99 <= price <= 50.00


@pytest.mark.unit
def test_order_quantities_reasonable():
    """Test that order quantities are reasonable."""
    generator = MockDataGenerator(seed=42)

    for _ in range(50):
        order = generator.generate_order()
        for item in order["items"]:
            # Typically order 1-5 of each item
            assert 1 <= item["quantity"] <= 5

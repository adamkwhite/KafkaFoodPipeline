"""
Mock Data Generator for Kafka Food Orders

This module generates realistic mock data for testing the Kafka order processing pipeline.

WHY MOCK DATA?
- Learning: Focus on Kafka concepts without building real UI/API
- Testing: Generate high-volume realistic data for load testing
- Reproducibility: Seed-based generation for consistent test scenarios
- Flexibility: Easy to adjust order rates, customer counts, menu items

DATA GENERATION STRATEGY:
1. Generate fixed set of customers (100 unique)
2. Generate fixed menu items (20 food items with prices)
3. Generate random orders from these pools
4. Use customer_id as Kafka partition key (ordering per customer)

LIBRARIES USED:
- Faker: Generate realistic names, emails, phone numbers
- random: Random selection and number generation
- datetime: Timestamp generation
- uuid: Unique order ID generation (alternative to sequential)

LEARNING OBJECTIVES:
- Understand data serialization for Kafka (dict → JSON → bytes)
- Learn partition key importance (customer_id for ordering)
- See realistic data patterns (order frequency, item combinations)
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from faker import Faker

# ==============================================================================
# GLOBAL CONFIGURATION
# ==============================================================================

# Seed for reproducible random data (same seed = same data every time)
# Useful for debugging and consistent test scenarios
RANDOM_SEED = 42

# Initialize Faker with seed for reproducible fake data
fake = Faker()
Faker.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

# Number of unique customers (affects partition distribution)
NUM_CUSTOMERS = 100

# Number of menu items (affects order variety)
NUM_MENU_ITEMS = 20

# Order ID format: ORD-YYYYMMDD-NNNNN (e.g., ORD-20250110-00001)
# Includes date for easy identification and 5-digit sequence number
ORDER_ID_FORMAT = "ORD-{date}-{sequence:05d}"


# ==============================================================================
# CUSTOMER DATA GENERATOR
# ==============================================================================
#
# CUSTOMER DATA STRUCTURE:
# {
#     "customer_id": "CUST-00001",
#     "name": "John Doe",
#     "email": "john.doe@example.com",
#     "phone": "+1-555-123-4567"
# }
#
# WHY FIXED CUSTOMER SET?
# - Kafka partitioning: Same customer_id → same partition
# - Realistic pattern: Real apps have finite user base
# - Testing: Verify ordering guarantees per customer
# - Analytics: Track customer order history

class MockDataGenerator:
    """
    Generates mock data for food orders.

    This class creates realistic customer data, menu items, and orders
    for testing the Kafka pipeline.

    Attributes:
        customers: List of 100 unique customer dictionaries
        menu_items: List of 20 food item dictionaries
        order_sequence: Counter for sequential order IDs
    """

    def __init__(self, seed: int = RANDOM_SEED):
        """
        Initialize mock data generator.

        Args:
            seed: Random seed for reproducibility (default: 42)
        """
        self.seed = seed
        random.seed(seed)
        Faker.seed(seed)

        # Generate fixed customer pool (100 customers)
        self.customers = self._generate_customers(NUM_CUSTOMERS)

        # Generate fixed menu items (20 items)
        self.menu_items = self._generate_menu_items(NUM_MENU_ITEMS)

        # Order sequence counter for unique order IDs
        self.order_sequence = 0

    def _generate_customers(self, count: int) -> List[Dict[str, str]]:
        """
        Generate a fixed pool of unique customers.

        This creates a realistic customer database with unique IDs.
        In production, this would come from a user database.

        Args:
            count: Number of customers to generate (default: 100)

        Returns:
            List of customer dictionaries with id, name, email, phone

        Example:
            >>> generator = MockDataGenerator()
            >>> customers = generator._generate_customers(100)
            >>> len(customers)
            100
            >>> customers[0]
            {
                'customer_id': 'CUST-00001',
                'name': 'John Doe',
                'email': 'john.doe@example.com',
                'phone': '+1-555-123-4567'
            }
        """
        customers = []

        for i in range(1, count + 1):
            # Generate customer ID with zero-padded number
            # CUST-00001, CUST-00002, ..., CUST-00100
            customer_id = f"CUST-{i:05d}"

            # Generate realistic personal data using Faker
            name = fake.name()

            # Email derived from name for consistency
            # "John Doe" → john.doe@example.com
            email = f"{name.lower().replace(' ', '.')}.{i}@example.com"

            # Generate phone number
            phone = fake.phone_number()

            customers.append({
                "customer_id": customer_id,
                "name": name,
                "email": email,
                "phone": phone
            })

        return customers

    def _generate_menu_items(self, count: int) -> List[Dict[str, Any]]:
        """
        Generate a fixed menu of food items.

        Creates realistic menu items with names, descriptions, and prices.
        Price range: $2.00 - $15.00 (typical fast food range).

        Args:
            count: Number of menu items to generate (default: 20)

        Returns:
            List of menu item dictionaries with name, description, price

        Example:
            >>> generator = MockDataGenerator()
            >>> menu = generator._generate_menu_items(20)
            >>> len(menu)
            20
            >>> menu[0]
            {
                'item_id': 'ITEM-001',
                'name': 'Classic Burger',
                'description': 'Beef patty with lettuce, tomato, and cheese',
                'price': 8.99,
                'category': 'Burgers'
            }
        """
        # Predefined menu items for realistic variety
        # Format: (name, description, price, category)
        menu_data = [
            ("Classic Burger", "Beef patty with lettuce, tomato, and cheese", 8.99, "Burgers"),
            ("Cheeseburger", "Double cheese with beef patty", 9.99, "Burgers"),
            ("Bacon Burger", "Beef patty with crispy bacon", 10.99, "Burgers"),
            ("Veggie Burger", "Plant-based patty with vegetables", 8.49, "Burgers"),

            ("French Fries", "Crispy golden fries", 3.49, "Sides"),
            ("Onion Rings", "Beer-battered onion rings", 4.49, "Sides"),
            ("Sweet Potato Fries", "Crispy sweet potato fries", 4.99, "Sides"),
            ("Coleslaw", "Fresh cabbage slaw", 2.99, "Sides"),

            ("Caesar Salad", "Romaine with Caesar dressing", 6.99, "Salads"),
            ("Garden Salad", "Mixed greens with vegetables", 5.99, "Salads"),

            ("Coke", "Coca-Cola classic", 2.49, "Beverages"),
            ("Sprite", "Lemon-lime soda", 2.49, "Beverages"),
            ("Iced Tea", "Freshly brewed iced tea", 2.99, "Beverages"),
            ("Lemonade", "Homemade lemonade", 2.99, "Beverages"),
            ("Milkshake", "Chocolate, vanilla, or strawberry", 4.99, "Beverages"),

            ("Apple Pie", "Warm apple pie with cinnamon", 3.99, "Desserts"),
            ("Ice Cream Sundae", "Vanilla ice cream with toppings", 4.49, "Desserts"),
            ("Brownie", "Chocolate fudge brownie", 3.49, "Desserts"),

            ("Chicken Nuggets", "Crispy chicken nuggets (6 pieces)", 5.99, "Chicken"),
            ("Chicken Sandwich", "Grilled chicken with lettuce", 7.99, "Chicken"),
        ]

        menu_items = []
        for i, (name, description, price, category) in enumerate(menu_data[:count], start=1):
            menu_items.append({
                "item_id": f"ITEM-{i:03d}",
                "name": name,
                "description": description,
                "price": price,
                "category": category
            })

        return menu_items

    def get_random_customer(self) -> Dict[str, str]:
        """
        Get a random customer from the pool.

        Returns:
            Random customer dictionary

        KAFKA PARTITIONING:
        - customer_id is used as partition key
        - Same customer → same partition → ordering guaranteed
        - Different customers → different partitions → parallel processing
        """
        return random.choice(self.customers)

    def get_random_menu_items(self, min_items: int = 1, max_items: int = 5) -> List[Dict[str, Any]]:
        """
        Get random menu items for an order.

        Args:
            min_items: Minimum items in order (default: 1)
            max_items: Maximum items in order (default: 5)

        Returns:
            List of menu items with quantity

        Example:
            >>> generator = MockDataGenerator()
            >>> items = generator.get_random_menu_items(1, 3)
            >>> len(items)
            2  # Random between 1-3
            >>> items[0]
            {
                'item_id': 'ITEM-001',
                'name': 'Classic Burger',
                'quantity': 2,
                'price': 8.99,
                'subtotal': 17.98
            }
        """
        # Random number of items in order
        num_items = random.randint(min_items, max_items)

        # Randomly select items (without replacement to avoid duplicates)
        selected_items = random.sample(self.menu_items, num_items)

        # Add quantity and calculate subtotal
        order_items = []
        for item in selected_items:
            quantity = random.randint(1, 3)  # 1-3 of each item
            subtotal = round(item['price'] * quantity, 2)

            order_items.append({
                "item_id": item['item_id'],
                "name": item['name'],
                "quantity": quantity,
                "price": item['price'],
                "subtotal": subtotal
            })

        return order_items

    def generate_order_id(self) -> str:
        """
        Generate unique order ID.

        Format: ORD-YYYYMMDD-NNNNN
        Example: ORD-20250110-00001

        Returns:
            Unique order ID string

        WHY THIS FORMAT?
        - ORD prefix: Identifies as order (vs customer, item)
        - YYYYMMDD: Date for easy filtering/querying
        - NNNNN: Sequential number (5 digits, supports 99,999 orders/day)
        - Human-readable: Easy to communicate ("order 12345")
        - Sortable: Chronological ordering by ID
        """
        self.order_sequence += 1
        today = datetime.now().strftime("%Y%m%d")
        return ORDER_ID_FORMAT.format(date=today, sequence=self.order_sequence)

    def generate_order(self) -> Dict[str, Any]:
        """
        Generate a complete mock order.

        This creates a realistic order with:
        - Unique order ID
        - Random customer (from pool of 100)
        - Random menu items (1-5 items)
        - Calculated total amount
        - Timestamp
        - Initial status

        Returns:
            Complete order dictionary ready for Kafka

        ORDER STRUCTURE:
        {
            "order_id": "ORD-20250110-00001",
            "customer_id": "CUST-00042",  # Partition key!
            "customer_name": "John Doe",
            "items": [
                {
                    "item_id": "ITEM-001",
                    "name": "Classic Burger",
                    "quantity": 2,
                    "price": 8.99,
                    "subtotal": 17.98
                }
            ],
            "total_amount": 17.98,
            "status": "pending",
            "created_at": "2025-01-10T14:30:00.000Z"
        }

        KAFKA PUBLISHING:
        - Serialize to JSON: json.dumps(order)
        - Partition key: order['customer_id']
        - Value: JSON bytes

        Example:
            >>> generator = MockDataGenerator()
            >>> order = generator.generate_order()
            >>> order['customer_id']
            'CUST-00042'
            >>> len(order['items'])
            3  # Random 1-5
            >>> order['status']
            'pending'
        """
        # Get random customer (partition key for Kafka)
        customer = self.get_random_customer()

        # Generate random order items
        items = self.get_random_menu_items(min_items=1, max_items=5)

        # Calculate total amount from items
        total_amount = sum(item['subtotal'] for item in items)
        total_amount = round(total_amount, 2)

        # Generate timestamp (ISO 8601 format for consistency)
        created_at = datetime.utcnow().isoformat() + 'Z'

        # Build complete order
        order = {
            "order_id": self.generate_order_id(),
            "customer_id": customer['customer_id'],  # PARTITION KEY!
            "customer_name": customer['name'],
            "customer_email": customer['email'],
            "items": items,
            "total_amount": total_amount,
            "status": "pending",  # Initial status
            "created_at": created_at
        }

        return order


# ==============================================================================
# USAGE EXAMPLES
# ==============================================================================
"""
# Basic usage
generator = MockDataGenerator(seed=42)

# Get customer pool
customers = generator.customers
print(f"Generated {len(customers)} customers")
# Output: Generated 100 customers

# Get menu items
menu = generator.menu_items
print(f"Menu has {len(menu)} items")
# Output: Menu has 20 items

# Generate single order
order = generator.generate_order()
print(f"Order {order['order_id']} for {order['customer_name']}")
print(f"Total: ${order['total_amount']}")
print(f"Items: {len(order['items'])}")

# Generate multiple orders
orders = [generator.generate_order() for _ in range(10)]
print(f"Generated {len(orders)} orders")

# Group orders by customer (see partition distribution)
from collections import Counter
customer_counts = Counter(o['customer_id'] for o in orders)
print(f"Order distribution: {customer_counts}")

# Reproducibility test (same seed = same data)
gen1 = MockDataGenerator(seed=42)
gen2 = MockDataGenerator(seed=42)
order1 = gen1.generate_order()
order2 = gen2.generate_order()
assert order1['customer_id'] == order2['customer_id']  # Same customer!

# Integration with Kafka producer
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

generator = MockDataGenerator()
for _ in range(100):
    order = generator.generate_order()

    # Send to Kafka with customer_id as partition key
    producer.send(
        topic='food-orders',
        key=order['customer_id'].encode('utf-8'),  # Partition key
        value=order
    )

producer.flush()
"""

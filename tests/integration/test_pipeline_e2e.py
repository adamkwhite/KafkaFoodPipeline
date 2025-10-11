"""
End-to-End Pipeline Tests

Tests the complete pipeline: Producer → Kafka → Consumer → PostgreSQL
These tests verify the full data flow and system integration.

TEST STRATEGY:
- Test complete pipeline with real testcontainers
- Verify data integrity from producer to database
- Test multiple consumers (parallel processing)
- Test system resilience and recovery
- Measure end-to-end latency

DEPENDENCIES:
- All testcontainers (Kafka, PostgreSQL)
- Producer and Consumer services
- Database verification
"""

from datetime import datetime

import pytest
from confluent_kafka import Consumer as KafkaConsumer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.consumer.consumer import OrderConsumer
from src.consumer.models import Order
from src.producer.mock_data import MockDataGenerator
from src.producer.producer import OrderProducer

# ==============================================================================
# BASIC END-TO-END TESTS
# ==============================================================================


@pytest.mark.integration
@pytest.mark.slow
def test_end_to_end_single_message(
    producer_config, consumer_config, kafka_container, postgres_container
):
    """Test complete pipeline with single message: Producer → Kafka → Consumer → DB."""
    # Step 1: Create producer and generate order
    mock_generator = MockDataGenerator(seed=42)
    producer = OrderProducer(config=producer_config, mock_generator=mock_generator)

    order = mock_generator.generate_order()
    order_id = order["order_id"]
    customer_id = order["customer_id"]

    # Step 2: Produce to Kafka
    producer.produce_order(order)
    producer.producer.flush(timeout=5)

    assert producer.messages_sent == 1

    # Step 3: Consume from Kafka and persist to database
    consumer = OrderConsumer(config=consumer_config)
    consumer.process_messages(max_messages=1, timeout=10)

    # Step 4: Verify data in PostgreSQL
    db_url = consumer_config.get_database_url()
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        saved_order = session.query(Order).filter_by(order_id=order_id).first()

        assert saved_order is not None
        assert saved_order.order_id == order_id
        assert saved_order.customer_id == customer_id
        assert float(saved_order.total_amount) == order["total_amount"]
        assert saved_order.status == "pending"
        assert saved_order.processed_at is not None

    finally:
        session.close()
        engine.dispose()

    # Clean up
    consumer.close()
    producer.close()


@pytest.mark.integration
@pytest.mark.slow
def test_end_to_end_batch_processing(
    producer_config, consumer_config, kafka_container, postgres_container
):
    """Test pipeline with batch of messages."""
    num_messages = 20

    # Step 1: Produce batch of messages
    mock_generator = MockDataGenerator(seed=42, num_customers=20)
    producer = OrderProducer(config=producer_config, mock_generator=mock_generator)

    order_ids = []
    for _ in range(num_messages):
        order = mock_generator.generate_order()
        order_ids.append(order["order_id"])
        producer.produce_order(order)

    producer.producer.flush(timeout=15)
    assert producer.messages_sent == num_messages

    # Step 2: Consume all messages
    consumer = OrderConsumer(config=consumer_config)
    consumer.process_messages(max_messages=num_messages, timeout=30)

    # Step 3: Verify all messages in database
    db_url = consumer_config.get_database_url()
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        saved_count = session.query(Order).count()
        assert saved_count == num_messages

        # Verify specific orders
        for order_id in order_ids[:5]:  # Check first 5
            saved_order = session.query(Order).filter_by(order_id=order_id).first()
            assert saved_order is not None
            assert saved_order.processed_at is not None

    finally:
        session.close()
        engine.dispose()

    # Clean up
    consumer.close()
    producer.close()


# ==============================================================================
# DATA INTEGRITY TESTS
# ==============================================================================


@pytest.mark.integration
@pytest.mark.slow
def test_data_integrity_through_pipeline(
    producer_config, consumer_config, kafka_container, postgres_container
):
    """Verify data integrity from producer through to database."""
    # Create producer with known seed for reproducibility
    mock_generator = MockDataGenerator(seed=99)
    producer = OrderProducer(config=producer_config, mock_generator=mock_generator)

    # Generate order with specific values
    order = mock_generator.generate_order()
    original_order_id = order["order_id"]
    original_customer_id = order["customer_id"]
    original_customer_name = order["customer_name"]
    original_customer_email = order["customer_email"]
    original_total = order["total_amount"]
    original_items_count = len(order["items"])

    # Produce
    producer.produce_order(order)
    producer.producer.flush(timeout=5)

    # Consume
    consumer = OrderConsumer(config=consumer_config)
    consumer.process_messages(max_messages=1, timeout=10)

    # Verify exact data match in database
    db_url = consumer_config.get_database_url()
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        saved_order = session.query(Order).filter_by(order_id=original_order_id).first()

        # Verify all fields match exactly
        assert saved_order.order_id == original_order_id
        assert saved_order.customer_id == original_customer_id
        assert saved_order.customer_name == original_customer_name
        assert saved_order.customer_email == original_customer_email
        assert float(saved_order.total_amount) == original_total
        assert len(saved_order.items) == original_items_count

        # Verify items array
        for i, item in enumerate(saved_order.items):
            original_item = order["items"][i]
            assert item["item_id"] == original_item["item_id"]
            assert item["name"] == original_item["name"]
            assert item["quantity"] == original_item["quantity"]
            assert item["price"] == original_item["price"]
            assert item["subtotal"] == original_item["subtotal"]

    finally:
        session.close()
        engine.dispose()

    consumer.close()
    producer.close()


@pytest.mark.integration
@pytest.mark.slow
def test_order_sequencing_preserved(
    producer_config, consumer_config, kafka_container, postgres_container
):
    """Verify that orders from same customer maintain sequence."""
    # Create producer with few customers to ensure same-customer orders
    mock_generator = MockDataGenerator(seed=42, num_customers=5)
    producer = OrderProducer(config=producer_config, mock_generator=mock_generator)

    # Generate orders
    customer_orders = {}
    for _ in range(10):
        order = mock_generator.generate_order()
        customer_id = order["customer_id"]

        if customer_id not in customer_orders:
            customer_orders[customer_id] = []

        customer_orders[customer_id].append(
            {"order_id": order["order_id"], "created_at": order["created_at"]}
        )

        producer.produce_order(order)

    producer.producer.flush(timeout=10)

    # Consume all
    consumer = OrderConsumer(config=consumer_config)
    consumer.process_messages(max_messages=10, timeout=20)

    # Verify ordering for each customer
    db_url = consumer_config.get_database_url()
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # For customers with multiple orders, verify they're in sequence
        for customer_id, orders in customer_orders.items():
            if len(orders) < 2:
                continue  # Skip if only one order

            # Get orders from DB for this customer
            saved_orders = (
                session.query(Order)
                .filter_by(customer_id=customer_id)
                .order_by(Order.created_at)
                .all()
            )

            # Should have same count
            assert len(saved_orders) == len(orders)

            # Should be in same sequence
            for i, saved_order in enumerate(saved_orders):
                assert saved_order.order_id == orders[i]["order_id"]

    finally:
        session.close()
        engine.dispose()

    consumer.close()
    producer.close()


# ==============================================================================
# PARTITION AND CONSUMER GROUP TESTS
# ==============================================================================


@pytest.mark.integration
@pytest.mark.slow
def test_partition_distribution_end_to_end(
    producer_config, consumer_config, kafka_container, postgres_container
):
    """Test that messages are distributed across partitions and consumed correctly."""
    # Create producer with many customers (to hit multiple partitions)
    mock_generator = MockDataGenerator(seed=42, num_customers=30)
    producer = OrderProducer(config=producer_config, mock_generator=mock_generator)

    # Produce 30 orders (should spread across 3 partitions)
    num_messages = 30
    for _ in range(num_messages):
        order = mock_generator.generate_order()
        producer.produce_order(order)

    producer.producer.flush(timeout=15)

    # Verify messages went to multiple partitions
    kafka_consumer_config = {
        "bootstrap.servers": consumer_config.kafka_bootstrap_servers,
        "group.id": "partition-test-group",
        "auto.offset.reset": "earliest",
    }
    kafka_consumer = KafkaConsumer(kafka_consumer_config)
    kafka_consumer.subscribe([consumer_config.kafka_topic_orders])

    partitions_seen = set()
    messages_checked = 0
    for _ in range(50):  # Check up to 50 times
        msg = kafka_consumer.poll(timeout=1.0)
        if msg is None:
            continue
        if not msg.error():
            partitions_seen.add(msg.partition())
            messages_checked += 1

        if messages_checked >= num_messages:
            break

    kafka_consumer.close()

    # Should see multiple partitions (statistically very likely with 30 messages)
    assert len(partitions_seen) > 1, (
        f"Expected messages across multiple partitions, " f"but only saw: {partitions_seen}"
    )

    # Now consume with OrderConsumer
    consumer = OrderConsumer(config=consumer_config)
    consumer.process_messages(max_messages=num_messages, timeout=30)

    # Verify all in database
    db_url = consumer_config.get_database_url()
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        saved_count = session.query(Order).count()
        assert saved_count == num_messages
    finally:
        session.close()
        engine.dispose()

    consumer.close()
    producer.close()


# ==============================================================================
# LATENCY AND PERFORMANCE TESTS
# ==============================================================================


@pytest.mark.integration
@pytest.mark.slow
def test_end_to_end_latency(producer_config, consumer_config, kafka_container, postgres_container):
    """Measure end-to-end latency from production to database persistence."""
    mock_generator = MockDataGenerator(seed=42)
    producer = OrderProducer(config=producer_config, mock_generator=mock_generator)

    # Generate order
    order = mock_generator.generate_order()
    order_id = order["order_id"]

    # Measure production time
    produce_start = datetime.now()
    producer.produce_order(order)
    producer.producer.flush(timeout=5)
    produce_end = datetime.now()

    produce_latency = (produce_end - produce_start).total_seconds()

    # Measure consumption time
    consumer = OrderConsumer(config=consumer_config)
    consume_start = datetime.now()
    consumer.process_messages(max_messages=1, timeout=10)
    consume_end = datetime.now()

    consume_latency = (consume_end - consume_start).total_seconds()

    # Total end-to-end latency
    total_latency = (consume_end - produce_start).total_seconds()

    # Verify order is in database
    db_url = consumer_config.get_database_url()
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        saved_order = session.query(Order).filter_by(order_id=order_id).first()
        assert saved_order is not None
    finally:
        session.close()
        engine.dispose()

    consumer.close()
    producer.close()

    # Log latency metrics
    print("\nEnd-to-End Latency Metrics:")
    print(f"  Production latency: {produce_latency * 1000:.2f}ms")
    print(f"  Consumption latency: {consume_latency * 1000:.2f}ms")
    print(f"  Total E2E latency: {total_latency * 1000:.2f}ms")

    # Reasonable latency thresholds (generous for test environment)
    assert produce_latency < 2.0, f"Production too slow: {produce_latency}s"
    assert consume_latency < 5.0, f"Consumption too slow: {consume_latency}s"
    assert total_latency < 10.0, f"E2E latency too high: {total_latency}s"


@pytest.mark.integration
@pytest.mark.slow
def test_sustained_throughput(
    producer_config, consumer_config, kafka_container, postgres_container
):
    """Test sustained throughput over longer batch."""
    num_messages = 50

    mock_generator = MockDataGenerator(seed=42)
    producer = OrderProducer(config=producer_config, mock_generator=mock_generator)
    consumer = OrderConsumer(config=consumer_config)

    # Production phase
    produce_start = datetime.now()
    for _ in range(num_messages):
        order = mock_generator.generate_order()
        producer.produce_order(order)

    producer.producer.flush(timeout=20)
    produce_end = datetime.now()

    # Consumption phase
    consume_start = datetime.now()
    consumer.process_messages(max_messages=num_messages, timeout=60)
    consume_end = datetime.now()

    # Calculate throughput
    produce_time = (produce_end - produce_start).total_seconds()
    consume_time = (consume_end - consume_start).total_seconds()
    total_time = (consume_end - produce_start).total_seconds()

    produce_throughput = num_messages / produce_time
    consume_throughput = num_messages / consume_time
    e2e_throughput = num_messages / total_time

    # Verify all in database
    db_url = consumer_config.get_database_url()
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        saved_count = session.query(Order).count()
        assert saved_count == num_messages
    finally:
        session.close()
        engine.dispose()

    consumer.close()
    producer.close()

    # Log throughput metrics
    print(f"\nThroughput Metrics ({num_messages} messages):")
    print(f"  Producer: {produce_throughput:.2f} msg/s")
    print(f"  Consumer: {consume_throughput:.2f} msg/s")
    print(f"  End-to-End: {e2e_throughput:.2f} msg/s")

    # Reasonable throughput expectations
    assert produce_throughput > 5.0, f"Producer throughput too low: {produce_throughput}"
    assert consume_throughput > 3.0, f"Consumer throughput too low: {consume_throughput}"


# ==============================================================================
# RESILIENCE AND RECOVERY TESTS
# ==============================================================================


@pytest.mark.integration
@pytest.mark.slow
def test_consumer_recovery_after_restart(
    producer_config, consumer_config, kafka_container, postgres_container
):
    """Test that consumer can resume after restart without reprocessing."""
    mock_generator = MockDataGenerator(seed=42)
    producer = OrderProducer(config=producer_config, mock_generator=mock_generator)

    # Produce 10 messages
    for _ in range(10):
        order = mock_generator.generate_order()
        producer.produce_order(order)

    producer.producer.flush(timeout=10)

    # Process first 5 messages
    consumer1 = OrderConsumer(config=consumer_config)
    consumer1.process_messages(max_messages=5, timeout=15)
    consumer1.close()

    # Check database - should have 5 orders
    db_url = consumer_config.get_database_url()
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        count_after_first = session.query(Order).count()
        assert count_after_first == 5
    finally:
        session.close()
        engine.dispose()

    # Create new consumer (simulates restart)
    consumer2 = OrderConsumer(config=consumer_config)
    consumer2.process_messages(max_messages=5, timeout=15)
    consumer2.close()

    # Check database - should now have 10 orders (not 15)
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        count_after_second = session.query(Order).count()
        assert count_after_second == 10, (
            f"Expected 10 orders after resume, found {count_after_second}. "
            "Messages may have been reprocessed."
        )
    finally:
        session.close()
        engine.dispose()

    producer.close()


@pytest.mark.integration
@pytest.mark.slow
def test_idempotency_across_pipeline(
    producer_config, consumer_config, kafka_container, postgres_container
):
    """Test idempotency: duplicate messages don't create duplicate database entries."""
    mock_generator = MockDataGenerator(seed=42)
    producer = OrderProducer(config=producer_config, mock_generator=mock_generator)

    # Generate single order
    order = mock_generator.generate_order()
    order_id = order["order_id"]

    # Produce same order twice
    producer.produce_order(order)
    producer.produce_order(order)  # Duplicate
    producer.producer.flush(timeout=10)

    # Consumer processes both
    consumer = OrderConsumer(config=consumer_config)
    consumer.process_messages(max_messages=2, timeout=15)

    # Verify only ONE entry in database
    db_url = consumer_config.get_database_url()
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        count = session.query(Order).filter_by(order_id=order_id).count()
        assert count == 1, f"Expected 1 order, found {count}. Idempotency failed."
    finally:
        session.close()
        engine.dispose()

    consumer.close()
    producer.close()

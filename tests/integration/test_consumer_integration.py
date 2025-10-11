"""
Integration Tests for Order Consumer

Tests the OrderConsumer with real Kafka and PostgreSQL testcontainers.
These tests verify message consumption, database persistence, and error handling.

TEST STRATEGY:
- Use testcontainers for real Kafka broker and PostgreSQL
- Test message consumption from Kafka
- Verify database persistence
- Test idempotency (duplicate handling)
- Test error handling and retries
- Test graceful shutdown

DEPENDENCIES:
- testcontainers-python (Kafka + PostgreSQL)
- confluent-kafka (Producer to send test messages)
- SQLAlchemy (Database verification)
"""

import json
from decimal import Decimal

import pytest
from confluent_kafka import Producer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.consumer.consumer import OrderConsumer
from src.consumer.models import Order

# ==============================================================================
# CONSUMER INITIALIZATION TESTS
# ==============================================================================


@pytest.mark.integration
def test_consumer_initialization(consumer_config):
    """Test that OrderConsumer initializes correctly with test config."""
    consumer = OrderConsumer(config=consumer_config)

    assert consumer is not None
    assert consumer.config == consumer_config
    assert consumer.consumer is not None  # Kafka Consumer object
    assert consumer.db_session is not None  # Database session
    assert consumer.running is False  # Not started yet

    # Clean up
    consumer.close()


@pytest.mark.integration
def test_consumer_close(consumer_config):
    """Test that consumer closes gracefully."""
    consumer = OrderConsumer(config=consumer_config)

    # Should not raise exception
    consumer.close()


# ==============================================================================
# MESSAGE CONSUMPTION TESTS
# ==============================================================================


@pytest.mark.integration
def test_consume_single_message(consumer_config, kafka_container, sample_order_data):
    """Test consuming a single message from Kafka and saving to database."""
    # Produce a test message to Kafka
    producer_config = {
        "bootstrap.servers": consumer_config.kafka_bootstrap_servers,
        "client.id": "test-producer",
    }
    producer = Producer(producer_config)
    producer.produce(
        consumer_config.kafka_topic_orders,
        key=sample_order_data["customer_id"].encode("utf-8"),
        value=json.dumps(sample_order_data).encode("utf-8"),
    )
    producer.flush(timeout=5)

    # Create consumer
    consumer = OrderConsumer(config=consumer_config)

    # Process one message
    consumer.process_messages(max_messages=1, timeout=10)

    # Verify message was saved to database
    db_url = consumer_config.get_database_url()
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        saved_order = session.query(Order).filter_by(order_id=sample_order_data["order_id"]).first()

        assert saved_order is not None
        assert saved_order.customer_id == sample_order_data["customer_id"]
        assert saved_order.customer_name == sample_order_data["customer_name"]
        assert float(saved_order.total_amount) == sample_order_data["total_amount"]
    finally:
        session.close()
        engine.dispose()

    consumer.close()


@pytest.mark.integration
def test_consume_multiple_messages(consumer_config, kafka_container, postgres_container):
    """Test consuming multiple messages from Kafka."""
    # Create test orders
    test_orders = [
        {
            "order_id": f"ORD-20250110-{i:05d}",
            "customer_id": f"CUST-{i:05d}",
            "customer_name": f"Customer {i}",
            "customer_email": f"customer{i}@example.com",
            "items": [
                {
                    "item_id": "ITEM-001",
                    "name": "Test Item",
                    "quantity": 1,
                    "price": 10.0,
                    "subtotal": 10.0,
                }
            ],
            "total_amount": 10.0,
            "status": "pending",
            "created_at": "2025-01-10T14:30:00+00:00",
        }
        for i in range(5)
    ]

    # Produce test messages to Kafka
    producer_config = {
        "bootstrap.servers": consumer_config.kafka_bootstrap_servers,
        "client.id": "test-producer",
    }
    producer = Producer(producer_config)

    for order in test_orders:
        producer.produce(
            consumer_config.kafka_topic_orders,
            key=order["customer_id"].encode("utf-8"),
            value=json.dumps(order).encode("utf-8"),
        )

    producer.flush(timeout=10)

    # Create consumer and process messages
    consumer = OrderConsumer(config=consumer_config)
    consumer.process_messages(max_messages=5, timeout=15)

    # Verify all messages were saved
    db_url = consumer_config.get_database_url()
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        saved_count = session.query(Order).count()
        assert saved_count == 5, f"Expected 5 orders, found {saved_count}"
    finally:
        session.close()
        engine.dispose()

    consumer.close()


# ==============================================================================
# IDEMPOTENCY TESTS
# ==============================================================================


@pytest.mark.integration
def test_duplicate_message_handling(consumer_config, kafka_container, sample_order_data):
    """Test that duplicate messages are handled idempotently."""
    # Produce same message twice to Kafka
    producer_config = {
        "bootstrap.servers": consumer_config.kafka_bootstrap_servers,
        "client.id": "test-producer",
    }
    producer = Producer(producer_config)

    for _ in range(2):  # Send same message twice
        producer.produce(
            consumer_config.kafka_topic_orders,
            key=sample_order_data["customer_id"].encode("utf-8"),
            value=json.dumps(sample_order_data).encode("utf-8"),
        )

    producer.flush(timeout=10)

    # Create consumer and process both messages
    consumer = OrderConsumer(config=consumer_config)
    consumer.process_messages(max_messages=2, timeout=15)

    # Verify only one order is saved (idempotency)
    db_url = consumer_config.get_database_url()
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        order_count = session.query(Order).filter_by(order_id=sample_order_data["order_id"]).count()

        # Should be exactly 1 (second insert should fail or be ignored)
        assert order_count == 1, (
            f"Expected exactly 1 order, found {order_count}. "
            "Duplicate was not handled idempotently."
        )
    finally:
        session.close()
        engine.dispose()

    consumer.close()


# ==============================================================================
# DATABASE PERSISTENCE TESTS
# ==============================================================================


@pytest.mark.integration
def test_order_persisted_correctly(consumer_config, kafka_container, sample_order_data):
    """Test that order fields are persisted correctly to database."""
    # Produce test message
    producer_config = {
        "bootstrap.servers": consumer_config.kafka_bootstrap_servers,
        "client.id": "test-producer",
    }
    producer = Producer(producer_config)
    producer.produce(
        consumer_config.kafka_topic_orders,
        key=sample_order_data["customer_id"].encode("utf-8"),
        value=json.dumps(sample_order_data).encode("utf-8"),
    )
    producer.flush(timeout=5)

    # Consume and persist
    consumer = OrderConsumer(config=consumer_config)
    consumer.process_messages(max_messages=1, timeout=10)

    # Verify all fields persisted correctly
    db_url = consumer_config.get_database_url()
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        saved_order = session.query(Order).filter_by(order_id=sample_order_data["order_id"]).first()

        assert saved_order is not None

        # Verify all fields
        assert saved_order.order_id == sample_order_data["order_id"]
        assert saved_order.customer_id == sample_order_data["customer_id"]
        assert saved_order.customer_name == sample_order_data["customer_name"]
        assert saved_order.customer_email == sample_order_data["customer_email"]
        assert float(saved_order.total_amount) == sample_order_data["total_amount"]
        assert saved_order.status == sample_order_data["status"]

        # Verify items (JSONB field)
        assert saved_order.items == sample_order_data["items"]
        assert len(saved_order.items) == len(sample_order_data["items"])

        # Verify processed_at timestamp was set
        assert saved_order.processed_at is not None

    finally:
        session.close()
        engine.dispose()

    consumer.close()


@pytest.mark.integration
def test_decimal_precision_preserved(consumer_config, kafka_container):
    """Test that monetary Decimal precision is preserved in database."""
    # Create order with precise decimal amount
    test_order = {
        "order_id": "ORD-20250110-99999",
        "customer_id": "CUST-00001",
        "customer_name": "Test Customer",
        "customer_email": "test@example.com",
        "items": [
            {
                "item_id": "ITEM-001",
                "name": "Test Item",
                "quantity": 3,
                "price": 3.33,
                "subtotal": 9.99,
            }
        ],
        "total_amount": 9.99,
        "status": "pending",
        "created_at": "2025-01-10T14:30:00+00:00",
    }

    # Produce and consume
    producer_config = {
        "bootstrap.servers": consumer_config.kafka_bootstrap_servers,
        "client.id": "test-producer",
    }
    producer = Producer(producer_config)
    producer.produce(
        consumer_config.kafka_topic_orders,
        key=test_order["customer_id"].encode("utf-8"),
        value=json.dumps(test_order).encode("utf-8"),
    )
    producer.flush(timeout=5)

    consumer = OrderConsumer(config=consumer_config)
    consumer.process_messages(max_messages=1, timeout=10)

    # Verify decimal precision
    db_url = consumer_config.get_database_url()
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        saved_order = session.query(Order).filter_by(order_id=test_order["order_id"]).first()

        assert saved_order is not None
        # Verify exact decimal precision
        assert isinstance(saved_order.total_amount, Decimal)
        assert str(saved_order.total_amount) == "9.99"
        # Not "9.989999..." like float would give

    finally:
        session.close()
        engine.dispose()

    consumer.close()


# ==============================================================================
# ERROR HANDLING TESTS
# ==============================================================================


@pytest.mark.integration
def test_invalid_message_handling(consumer_config, kafka_container):
    """Test that consumer handles invalid messages gracefully."""
    # Produce invalid JSON message
    producer_config = {
        "bootstrap.servers": consumer_config.kafka_bootstrap_servers,
        "client.id": "test-producer",
    }
    producer = Producer(producer_config)
    producer.produce(
        consumer_config.kafka_topic_orders,
        key=b"invalid-key",
        value=b"{ invalid json }",  # Malformed JSON
    )
    producer.flush(timeout=5)

    # Consumer should handle this gracefully
    consumer = OrderConsumer(config=consumer_config)

    # Should not crash, should log error and continue
    try:
        consumer.process_messages(max_messages=1, timeout=5)
        # If we get here, consumer handled error gracefully
    except Exception as e:
        pytest.fail(f"Consumer crashed on invalid message: {e}")
    finally:
        consumer.close()


@pytest.mark.integration
def test_missing_required_fields(consumer_config, kafka_container):
    """Test handling of messages with missing required fields."""
    # Create order with missing customer_id
    invalid_order = {
        "order_id": "ORD-20250110-00001",
        # Missing customer_id (required field)
        "customer_name": "Test Customer",
        "items": [],
        "total_amount": 0.0,
        "status": "pending",
        "created_at": "2025-01-10T14:30:00+00:00",
    }

    # Produce invalid message
    producer_config = {
        "bootstrap.servers": consumer_config.kafka_bootstrap_servers,
        "client.id": "test-producer",
    }
    producer = Producer(producer_config)
    producer.produce(
        consumer_config.kafka_topic_orders,
        key=b"test-key",
        value=json.dumps(invalid_order).encode("utf-8"),
    )
    producer.flush(timeout=5)

    # Consumer should handle gracefully
    consumer = OrderConsumer(config=consumer_config)

    try:
        consumer.process_messages(max_messages=1, timeout=5)
    except Exception as e:
        pytest.fail(f"Consumer crashed on invalid message: {e}")
    finally:
        consumer.close()


# ==============================================================================
# OFFSET MANAGEMENT TESTS
# ==============================================================================


@pytest.mark.integration
def test_manual_offset_commit(consumer_config, kafka_container, sample_order_data):
    """Test that consumer commits offsets manually after successful processing."""
    # Produce test message
    producer_config = {
        "bootstrap.servers": consumer_config.kafka_bootstrap_servers,
        "client.id": "test-producer",
    }
    producer = Producer(producer_config)
    producer.produce(
        consumer_config.kafka_topic_orders,
        key=sample_order_data["customer_id"].encode("utf-8"),
        value=json.dumps(sample_order_data).encode("utf-8"),
    )
    producer.flush(timeout=5)

    # Create consumer and process message
    consumer = OrderConsumer(config=consumer_config)
    consumer.process_messages(max_messages=1, timeout=10)

    # Offset should be committed (manual commit after successful processing)
    # Verify by creating new consumer with same group ID
    consumer.close()

    # Create second consumer with same group - should not reprocess message
    consumer2 = OrderConsumer(config=consumer_config)

    # If offset was committed, poll should timeout (no messages to process)
    # If offset was NOT committed, same message would be reprocessed
    messages_processed = 0
    for _ in range(5):  # Try polling a few times
        msg = consumer2.consumer.poll(timeout=1.0)
        if msg is not None and not msg.error():
            messages_processed += 1

    consumer2.close()

    # Should be 0 because offset was committed
    assert messages_processed == 0, "Message was reprocessed. Offset was not committed correctly."


# ==============================================================================
# PERFORMANCE TESTS
# ==============================================================================


@pytest.mark.integration
@pytest.mark.slow
def test_consumer_throughput(consumer_config, kafka_container):
    """Test consumer throughput (should handle 100+ messages)."""
    # Produce 100 test messages
    num_messages = 100
    producer_config = {
        "bootstrap.servers": consumer_config.kafka_bootstrap_servers,
        "client.id": "test-producer",
    }
    producer = Producer(producer_config)

    for i in range(num_messages):
        order = {
            "order_id": f"ORD-20250110-{i:05d}",
            "customer_id": f"CUST-{i:05d}",
            "customer_name": f"Customer {i}",
            "customer_email": f"customer{i}@example.com",
            "items": [
                {
                    "item_id": "ITEM-001",
                    "name": "Test Item",
                    "quantity": 1,
                    "price": 10.0,
                    "subtotal": 10.0,
                }
            ],
            "total_amount": 10.0,
            "status": "pending",
            "created_at": "2025-01-10T14:30:00+00:00",
        }

        producer.produce(
            consumer_config.kafka_topic_orders,
            key=order["customer_id"].encode("utf-8"),
            value=json.dumps(order).encode("utf-8"),
        )

    producer.flush(timeout=15)

    # Consume all messages
    consumer = OrderConsumer(config=consumer_config)

    from datetime import datetime

    start_time = datetime.now()
    consumer.process_messages(max_messages=num_messages, timeout=60)
    end_time = datetime.now()

    elapsed = (end_time - start_time).total_seconds()

    # Verify all messages processed
    db_url = consumer_config.get_database_url()
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        saved_count = session.query(Order).count()
        assert saved_count == num_messages, f"Expected {num_messages} orders, found {saved_count}"
    finally:
        session.close()
        engine.dispose()

    consumer.close()

    # Should complete in reasonable time (< 30 seconds for 100 messages)
    assert elapsed < 30.0, f"Throughput test took {elapsed}s (expected < 30s)"

    # Calculate throughput
    throughput = num_messages / elapsed
    print(f"Consumer throughput: {throughput:.2f} messages/second")


# ==============================================================================
# GRACEFUL SHUTDOWN TESTS
# ==============================================================================


@pytest.mark.integration
def test_consumer_graceful_shutdown(consumer_config, kafka_container):
    """Test that consumer shuts down gracefully."""
    # Produce some messages
    producer_config = {
        "bootstrap.servers": consumer_config.kafka_bootstrap_servers,
        "client.id": "test-producer",
    }
    producer = Producer(producer_config)

    for i in range(5):
        order = {
            "order_id": f"ORD-20250110-{i:05d}",
            "customer_id": f"CUST-{i:05d}",
            "customer_name": f"Customer {i}",
            "customer_email": f"customer{i}@example.com",
            "items": [
                {
                    "item_id": "ITEM-001",
                    "name": "Test Item",
                    "quantity": 1,
                    "price": 10.0,
                    "subtotal": 10.0,
                }
            ],
            "total_amount": 10.0,
            "status": "pending",
            "created_at": "2025-01-10T14:30:00+00:00",
        }

        producer.produce(
            consumer_config.kafka_topic_orders,
            key=order["customer_id"].encode("utf-8"),
            value=json.dumps(order).encode("utf-8"),
        )

    producer.flush(timeout=10)

    # Create consumer
    consumer = OrderConsumer(config=consumer_config)

    # Process some messages then close
    consumer.process_messages(max_messages=3, timeout=10)

    # Should close gracefully without errors
    try:
        consumer.close()
    except Exception as e:
        pytest.fail(f"Consumer failed to close gracefully: {e}")

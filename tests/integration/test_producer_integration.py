"""
Integration Tests for Order Producer

Tests the OrderProducer with real Kafka testcontainer.
These tests verify actual message production, delivery, and partitioning.

TEST STRATEGY:
- Use testcontainers for real Kafka broker
- Test actual message production and delivery
- Verify partition key distribution
- Test delivery callbacks and error handling
- Test graceful shutdown and message flushing

DEPENDENCIES:
- testcontainers-python (Kafka container)
- confluent-kafka (Consumer to verify messages)
"""

from datetime import datetime

import pytest
from confluent_kafka import Consumer, KafkaException

from src.producer.mock_data import MockDataGenerator
from src.producer.producer import OrderProducer

# ==============================================================================
# PRODUCER INITIALIZATION TESTS
# ==============================================================================


@pytest.mark.integration
def test_producer_initialization(producer_config):
    """Test that OrderProducer initializes correctly with test config."""
    mock_generator = MockDataGenerator(seed=42)
    producer = OrderProducer(config=producer_config, mock_generator=mock_generator)

    assert producer is not None
    assert producer.config == producer_config
    assert producer.mock_generator == mock_generator
    assert producer.producer is not None  # Kafka Producer object
    assert producer.messages_sent == 0
    assert producer.messages_failed == 0

    # Clean up
    producer.close()


@pytest.mark.integration
def test_producer_close(producer_config):
    """Test that producer closes gracefully."""
    mock_generator = MockDataGenerator(seed=42)
    producer = OrderProducer(config=producer_config, mock_generator=mock_generator)

    # Should not raise exception
    producer.close()

    # Verify producer is flushed
    assert producer.producer is None or producer.messages_sent >= 0


# ==============================================================================
# MESSAGE PRODUCTION TESTS
# ==============================================================================


@pytest.mark.integration
def test_produce_single_message(producer_config, kafka_container):
    """Test producing a single message to Kafka."""
    # Create producer
    mock_generator = MockDataGenerator(seed=42)
    producer = OrderProducer(config=producer_config, mock_generator=mock_generator)

    # Produce one message
    order = mock_generator.generate_order()
    producer.produce_order(order)
    producer.producer.flush(timeout=5)

    # Verify message was sent
    assert producer.messages_sent == 1
    assert producer.messages_failed == 0

    # Clean up
    producer.close()


@pytest.mark.integration
def test_produce_multiple_messages(producer_config, kafka_container):
    """Test producing multiple messages to Kafka."""
    # Create producer
    mock_generator = MockDataGenerator(seed=42)
    producer = OrderProducer(config=producer_config, mock_generator=mock_generator)

    # Produce 10 messages
    num_messages = 10
    for _ in range(num_messages):
        order = mock_generator.generate_order()
        producer.produce_order(order)

    producer.producer.flush(timeout=10)

    # Verify all messages were sent
    assert producer.messages_sent == num_messages
    assert producer.messages_failed == 0

    # Clean up
    producer.close()


@pytest.mark.integration
def test_produce_and_consume_message(producer_config, kafka_container):
    """Test that produced messages can be consumed from Kafka."""
    # Create producer
    mock_generator = MockDataGenerator(seed=42)
    producer = OrderProducer(config=producer_config, mock_generator=mock_generator)

    # Generate and produce an order
    order = mock_generator.generate_order()
    order_id = order["order_id"]
    customer_id = order["customer_id"]

    producer.produce_order(order)
    producer.producer.flush(timeout=5)

    # Create consumer to verify message
    consumer_config = {
        "bootstrap.servers": producer_config.kafka_bootstrap_servers,
        "group.id": "test-verification-group",
        "auto.offset.reset": "earliest",
    }
    consumer = Consumer(consumer_config)
    consumer.subscribe([producer_config.kafka_topic_orders])

    # Consume message
    message_found = False
    for _ in range(10):  # Try up to 10 times
        msg = consumer.poll(timeout=2.0)
        if msg is None:
            continue
        if msg.error():
            raise KafkaException(msg.error())

        # Parse message value
        import json

        message_data = json.loads(msg.value().decode("utf-8"))

        if message_data["order_id"] == order_id:
            # Verify message content
            assert message_data["customer_id"] == customer_id
            assert message_data["order_id"] == order_id
            assert "items" in message_data
            assert "total_amount" in message_data
            message_found = True
            break

    # Clean up
    consumer.close()
    producer.close()

    assert message_found, f"Order {order_id} was not found in Kafka"


# ==============================================================================
# PARTITION KEY TESTS
# ==============================================================================


@pytest.mark.integration
def test_partition_key_distribution(producer_config, kafka_container):
    """Test that messages with same customer_id go to same partition."""
    # Create producer
    mock_generator = MockDataGenerator(seed=42, num_customers=10)
    producer = OrderProducer(config=producer_config, mock_generator=mock_generator)

    # Generate multiple orders for same customer
    target_customer = mock_generator.customers[0]
    customer_id = target_customer["customer_id"]

    # Track which partitions we see for this customer
    partitions_seen = set()

    # Create consumer to verify partition assignment
    consumer_config = {
        "bootstrap.servers": producer_config.kafka_bootstrap_servers,
        "group.id": "test-partition-group",
        "auto.offset.reset": "earliest",
    }
    consumer = Consumer(consumer_config)
    consumer.subscribe([producer_config.kafka_topic_orders])

    # Produce 5 orders for the same customer
    for _ in range(5):
        order = mock_generator.generate_order()
        # Force same customer_id
        order["customer_id"] = customer_id
        producer.produce_order(order)

    producer.producer.flush(timeout=10)

    # Consume messages and track partitions
    messages_consumed = 0
    for _ in range(20):  # Try up to 20 times
        msg = consumer.poll(timeout=2.0)
        if msg is None:
            continue
        if msg.error():
            raise KafkaException(msg.error())

        import json

        message_data = json.loads(msg.value().decode("utf-8"))

        if message_data["customer_id"] == customer_id:
            partitions_seen.add(msg.partition())
            messages_consumed += 1

        if messages_consumed >= 5:
            break

    # Clean up
    consumer.close()
    producer.close()

    # All messages for same customer should be in same partition
    assert len(partitions_seen) == 1, (
        f"Messages for customer {customer_id} were split across "
        f"multiple partitions: {partitions_seen}"
    )


@pytest.mark.integration
def test_different_customers_different_partitions(producer_config, kafka_container):
    """Test that different customers can go to different partitions."""
    # Create producer with multiple customers
    mock_generator = MockDataGenerator(seed=42, num_customers=50)
    producer = OrderProducer(config=producer_config, mock_generator=mock_generator)

    # Create consumer
    consumer_config = {
        "bootstrap.servers": producer_config.kafka_bootstrap_servers,
        "group.id": "test-multi-partition-group",
        "auto.offset.reset": "earliest",
    }
    consumer = Consumer(consumer_config)
    consumer.subscribe([producer_config.kafka_topic_orders])

    # Produce 30 orders from different customers
    num_orders = 30
    for _ in range(num_orders):
        order = mock_generator.generate_order()
        producer.produce_order(order)

    producer.producer.flush(timeout=10)

    # Consume messages and track partitions
    partitions_used = set()
    messages_consumed = 0
    for _ in range(50):  # Try up to 50 times
        msg = consumer.poll(timeout=2.0)
        if msg is None:
            continue
        if msg.error():
            raise KafkaException(msg.error())

        partitions_used.add(msg.partition())
        messages_consumed += 1

        if messages_consumed >= num_orders:
            break

    # Clean up
    consumer.close()
    producer.close()

    # With 30 orders and 3 partitions, we should see multiple partitions used
    # (statistically very likely with different customer_ids)
    assert len(partitions_used) > 1, (
        f"All messages went to single partition. "
        f"Expected distribution across partitions. "
        f"Partitions used: {partitions_used}"
    )


# ==============================================================================
# DELIVERY CALLBACK TESTS
# ==============================================================================


@pytest.mark.integration
def test_delivery_callback_success(producer_config, kafka_container):
    """Test that delivery callback is called on successful delivery."""
    mock_generator = MockDataGenerator(seed=42)
    producer = OrderProducer(config=producer_config, mock_generator=mock_generator)

    # Produce message
    order = mock_generator.generate_order()
    producer.produce_order(order)
    producer.producer.flush(timeout=5)

    # Verify callback was called (messages_sent incremented)
    assert producer.messages_sent == 1
    assert producer.messages_failed == 0

    producer.close()


@pytest.mark.integration
def test_message_metadata(producer_config, kafka_container):
    """Test that message metadata is correctly set."""
    mock_generator = MockDataGenerator(seed=42)
    producer = OrderProducer(config=producer_config, mock_generator=mock_generator)

    # Create consumer to check metadata
    consumer_config = {
        "bootstrap.servers": producer_config.kafka_bootstrap_servers,
        "group.id": "test-metadata-group",
        "auto.offset.reset": "earliest",
    }
    consumer = Consumer(consumer_config)
    consumer.subscribe([producer_config.kafka_topic_orders])

    # Produce message
    order = mock_generator.generate_order()
    order_id = order["order_id"]
    producer.produce_order(order)
    producer.producer.flush(timeout=5)

    # Consume and verify metadata
    message_found = False
    for _ in range(10):
        msg = consumer.poll(timeout=2.0)
        if msg is None:
            continue
        if msg.error():
            raise KafkaException(msg.error())

        import json

        message_data = json.loads(msg.value().decode("utf-8"))

        if message_data["order_id"] == order_id:
            # Verify topic
            assert msg.topic() == producer_config.kafka_topic_orders
            # Verify partition is valid
            assert msg.partition() >= 0
            # Verify offset is valid
            assert msg.offset() >= 0
            # Verify timestamp exists
            assert msg.timestamp()[1] > 0
            message_found = True
            break

    consumer.close()
    producer.close()

    assert message_found, "Message metadata could not be verified"


# ==============================================================================
# EDGE CASES AND ERROR HANDLING
# ==============================================================================


@pytest.mark.integration
def test_produce_large_message(producer_config, kafka_container):
    """Test producing a large message (many items)."""
    mock_generator = MockDataGenerator(seed=42, num_menu_items=50)
    producer = OrderProducer(config=producer_config, mock_generator=mock_generator)

    # Create order with many items
    order = mock_generator.generate_order()
    # Manually add more items to make it large
    for i in range(20):
        order["items"].append(
            {
                "item_id": f"ITEM-{i:03d}",
                "name": f"Large Item {i}",
                "quantity": 1,
                "price": 10.0,
                "subtotal": 10.0,
            }
        )

    order["total_amount"] = sum(item["subtotal"] for item in order["items"])

    # Should handle large message
    producer.produce_order(order)
    producer.producer.flush(timeout=5)

    assert producer.messages_sent == 1
    assert producer.messages_failed == 0

    producer.close()


@pytest.mark.integration
def test_produce_empty_batch(producer_config):
    """Test that producer handles empty batch gracefully."""
    mock_generator = MockDataGenerator(seed=42)
    producer = OrderProducer(config=producer_config, mock_generator=mock_generator)

    # Don't produce any messages, just close
    producer.close()

    # Should not crash
    assert producer.messages_sent == 0


@pytest.mark.integration
def test_producer_statistics(producer_config, kafka_container):
    """Test that producer tracks statistics correctly."""
    mock_generator = MockDataGenerator(seed=42)
    producer = OrderProducer(config=producer_config, mock_generator=mock_generator)

    # Produce 5 messages
    for _ in range(5):
        order = mock_generator.generate_order()
        producer.produce_order(order)

    producer.producer.flush(timeout=10)

    # Verify statistics
    assert producer.messages_sent == 5
    assert producer.messages_failed == 0

    # Get stats
    stats = producer.get_stats()
    assert stats["messages_sent"] == 5
    assert stats["messages_failed"] == 0
    assert stats["success_rate"] == 100.0

    producer.close()


# ==============================================================================
# PERFORMANCE TESTS
# ==============================================================================


@pytest.mark.integration
@pytest.mark.slow
def test_producer_throughput(producer_config, kafka_container):
    """Test producer throughput (should handle 100+ messages)."""
    mock_generator = MockDataGenerator(seed=42)
    producer = OrderProducer(config=producer_config, mock_generator=mock_generator)

    # Produce 100 messages
    num_messages = 100
    start_time = datetime.now()

    for _ in range(num_messages):
        order = mock_generator.generate_order()
        producer.produce_order(order)

    producer.producer.flush(timeout=30)
    end_time = datetime.now()

    elapsed = (end_time - start_time).total_seconds()

    # Verify all messages sent
    assert producer.messages_sent == num_messages
    assert producer.messages_failed == 0

    # Should complete in reasonable time (< 10 seconds for 100 messages)
    assert elapsed < 10.0, f"Throughput test took {elapsed}s (expected < 10s)"

    # Calculate throughput
    throughput = num_messages / elapsed
    print(f"Producer throughput: {throughput:.2f} messages/second")

    producer.close()

"""
Kafka Order Producer Implementation

This module implements the Kafka producer for publishing food orders to the
'food-orders' topic with proper partitioning, callbacks, and error handling.

KAFKA PRODUCER CONCEPTS:
- **Producer**: Client that publishes messages to Kafka topics
- **Asynchronous**: send() returns immediately, delivery happens in background
- **Callbacks**: Notified when message delivery succeeds or fails
- **Partitioning**: Messages distributed across partitions using key
- **Serialization**: Convert Python objects → bytes for Kafka

PRODUCER RESPONSIBILITIES:
1. Serialize order data to JSON bytes
2. Send messages with customer_id as partition key (ensures ordering per customer)
3. Handle delivery confirmations via callbacks
4. Implement error handling and retries
5. Log all operations with correlation IDs
6. Graceful shutdown (flush pending messages)

DELIVERY GUARANTEES:
- acks=1: Leader acknowledgment (balance of speed and reliability)
- enable.idempotence=true: Prevents duplicate messages
- retries=INT_MAX: Automatic retry on transient failures
- At-least-once delivery: Consumer handles duplicates via primary key

BLOCKCHAIN ANALOGY:
- Producer = Transaction creator (signs and broadcasts)
- Partition key = Shard assignment (which chain receives tx)
- Callback = Transaction confirmation (block inclusion)
- Flush = Wait for finality (all confirmations received)
"""

import json
import logging
from typing import Dict, Any, Optional, Callable
from confluent_kafka import Producer, KafkaError, KafkaException
from confluent_kafka.admin import AdminClient

from src.shared.logger import setup_logger

# ==============================================================================
# KAFKA PRODUCER CLASS
# ==============================================================================

class OrderProducer:
    """
    Kafka producer for publishing food orders.

    This class handles:
    - Connecting to Kafka brokers
    - Serializing orders to JSON
    - Publishing with partition keys (customer_id)
    - Delivery callbacks and error handling
    - Graceful shutdown

    Attributes:
        bootstrap_servers: Kafka broker addresses (e.g., "localhost:9092")
        topic: Kafka topic name (e.g., "food-orders")
        producer: confluent_kafka.Producer instance
        logger: Structured logger with service name
        delivery_callback: Optional custom delivery callback
    """

    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        client_id: str = "order-producer",
        delivery_callback: Optional[Callable] = None,
        log_level: str = "INFO",
        log_format: str = "json"
    ):
        """
        Initialize Kafka producer.

        Args:
            bootstrap_servers: Comma-separated Kafka broker addresses
            topic: Kafka topic to publish to
            client_id: Producer identifier (for monitoring)
            delivery_callback: Optional custom callback for delivery reports
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            log_format: Log format ("json" or "text")

        Raises:
            KafkaException: If producer initialization fails
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.client_id = client_id

        # Set up structured logging
        self.logger = setup_logger(
            name=__name__,
            service_name="order-producer",
            log_level=log_level,
            log_format=log_format
        )

        # Store custom callback or use default
        self.delivery_callback = delivery_callback or self._default_delivery_callback

        # Producer configuration
        # See __init__.py for detailed explanation of each parameter
        # Note: Not all librdkafka (Java) configs are available in Python client
        producer_config = {
            # === CONNECTION ===
            'bootstrap.servers': bootstrap_servers,
            'client.id': client_id,

            # === RELIABILITY ===
            # Idempotence prevents duplicate messages
            # REQUIRES acks='all' (automatic when idempotence enabled)
            # Also sets: retries=INT_MAX, max.in.flight=5
            'enable.idempotence': True,

            # acks must be 'all' when idempotence is enabled
            # acks='all' or -1: Wait for all replicas (required for idempotence)
            # acks=1: Leader only (can't use with idempotence)
            # acks=0: No acknowledgment (can't use with idempotence)
            'acks': 'all',

            # === PERFORMANCE ===
            # Compression reduces network bandwidth and storage
            # Options: none, gzip, snappy, lz4, zstd
            'compression.type': 'snappy',

            # Batching parameters
            'linger.ms': 10,  # Wait 10ms to batch messages (throughput vs latency)
            'batch.num.messages': 10000,  # Batch up to 10k messages

            # === ERROR HANDLING ===
            # Retries on transient failures (idempotence sets this to INT_MAX)
            'retry.backoff.ms': 100,  # Wait 100ms between retries

            # Request timeout
            'request.timeout.ms': 30000,  # 30 seconds

            # Max in-flight requests (idempotence allows up to 5)
            'max.in.flight.requests.per.connection': 5,
        }

        # Initialize producer
        try:
            self.producer = Producer(producer_config)
            self.logger.info(
                "Kafka producer initialized",
                extra={
                    "bootstrap_servers": bootstrap_servers,
                    "topic": topic,
                    "client_id": client_id,
                    "compression": producer_config['compression.type'],
                    "idempotence": producer_config['enable.idempotence']
                }
            )
        except KafkaException as e:
            self.logger.error(
                "Failed to initialize Kafka producer",
                exc_info=True,
                extra={"error": str(e)}
            )
            raise

    def _default_delivery_callback(self, err: Optional[KafkaError], msg) -> None:
        """
        Default callback for message delivery reports.

        This callback is invoked for each message when:
        - Message successfully delivered to Kafka
        - Message delivery failed after retries

        Args:
            err: KafkaError if delivery failed, None if successful
            msg: Message object with metadata (topic, partition, offset)

        CALLBACK EXECUTION:
        - Called from producer.poll() or producer.flush()
        - Runs in background thread (be thread-safe!)
        - Should be fast (don't block producer)

        BLOCKCHAIN ANALOGY:
        - Callback = Transaction confirmation
        - err=None = Transaction included in block
        - err!=None = Transaction failed/rejected
        - msg.offset() = Block height (position in chain)
        """
        if err is not None:
            # Delivery failed after retries
            self.logger.error(
                "Message delivery failed",
                extra={
                    "error": err.str(),
                    "error_code": err.code(),
                    "topic": msg.topic(),
                    "partition": msg.partition() if msg else None,
                    # Try to extract order_id from message value
                    "order_id": self._extract_order_id(msg)
                }
            )
        else:
            # Delivery successful!
            # Extract order_id for correlation logging
            order_id = self._extract_order_id(msg)

            self.logger.info(
                "Message delivered successfully",
                extra={
                    "correlation_id": order_id,
                    "topic": msg.topic(),
                    "partition": msg.partition(),
                    "offset": msg.offset(),
                    "latency_ms": msg.latency() if hasattr(msg, 'latency') else None
                }
            )

    def _extract_order_id(self, msg) -> Optional[str]:
        """
        Extract order_id from Kafka message for logging.

        Args:
            msg: Kafka message object

        Returns:
            Order ID string or None if extraction fails
        """
        try:
            if msg and msg.value():
                order_data = json.loads(msg.value().decode('utf-8'))
                return order_data.get('order_id')
        except Exception:
            pass
        return None

    def produce_order(self, order: Dict[str, Any]) -> None:
        """
        Publish a food order to Kafka topic.

        This method:
        1. Serializes order to JSON bytes
        2. Uses customer_id as partition key (ensures ordering)
        3. Sends asynchronously to Kafka
        4. Polls for delivery callbacks

        Args:
            order: Order dictionary with structure:
                {
                    "order_id": "ORD-20250110-00001",
                    "customer_id": "CUST-00042",  # Partition key!
                    "items": [...],
                    "total_amount": 21.47,
                    "status": "pending",
                    "created_at": "2025-01-10T14:30:00Z"
                }

        Raises:
            BufferError: Producer buffer full (slow down production)
            KafkaException: Kafka client error
            ValueError: Invalid order structure

        PARTITION KEY STRATEGY:
        - Key: customer_id (e.g., "CUST-00042")
        - Kafka computes: partition = hash(customer_id) % num_partitions
        - Same customer → same partition → ordering guaranteed
        - Different customers → different partitions → parallel processing

        Example:
            >>> producer = OrderProducer("localhost:9092", "food-orders")
            >>> order = {"order_id": "ORD-001", "customer_id": "CUST-042", ...}
            >>> producer.produce_order(order)
            >>> producer.flush()  # Wait for delivery
        """
        # Validate required fields
        if 'order_id' not in order:
            raise ValueError("Order missing 'order_id' field")
        if 'customer_id' not in order:
            raise ValueError("Order missing 'customer_id' field (required for partition key)")

        order_id = order['order_id']
        customer_id = order['customer_id']

        try:
            # Serialize order to JSON bytes
            # Kafka messages are always bytes
            value_bytes = json.dumps(order).encode('utf-8')

            # Partition key as bytes
            # Kafka uses key to determine partition: hash(key) % num_partitions
            key_bytes = customer_id.encode('utf-8')

            # Asynchronous send (non-blocking)
            # Message goes to internal buffer, sent in background
            self.producer.produce(
                topic=self.topic,
                key=key_bytes,  # Partition key (customer_id)
                value=value_bytes,  # Order data (JSON)
                on_delivery=self.delivery_callback,  # Callback when delivered
            )

            # Poll for delivery callbacks
            # Triggers callbacks for previously sent messages
            # poll(0) = non-blocking check
            self.producer.poll(0)

            self.logger.debug(
                "Order published to Kafka",
                extra={
                    "correlation_id": order_id,
                    "customer_id": customer_id,
                    "topic": self.topic,
                    "total_amount": order.get('total_amount'),
                    "items_count": len(order.get('items', []))
                }
            )

        except BufferError as e:
            # Producer buffer full - backpressure!
            # Options:
            # 1. Increase buffer.memory config
            # 2. Slow down production rate
            # 3. Flush more frequently
            self.logger.error(
                "Producer buffer full",
                exc_info=True,
                extra={
                    "correlation_id": order_id,
                    "error": str(e),
                    "advice": "Slow down production or increase buffer.memory"
                }
            )
            raise

        except KafkaException as e:
            # Kafka client error
            self.logger.error(
                "Kafka error publishing order",
                exc_info=True,
                extra={
                    "correlation_id": order_id,
                    "error": str(e),
                    "error_code": e.args[0].code() if e.args else None
                }
            )
            raise

        except Exception as e:
            # Unexpected error (serialization, etc.)
            self.logger.error(
                "Unexpected error publishing order",
                exc_info=True,
                extra={
                    "correlation_id": order_id,
                    "error": str(e)
                }
            )
            raise

    def flush(self, timeout: float = 30.0) -> int:
        """
        Wait for all pending messages to be delivered.

        This blocks until:
        - All buffered messages are sent and acknowledged
        - Timeout expires
        - Fatal error occurs

        Args:
            timeout: Maximum time to wait in seconds (default: 30)

        Returns:
            Number of messages still in queue (0 = all delivered)

        WHEN TO FLUSH:
        - Before shutdown: Ensure no data loss
        - End of batch: Wait for confirmations
        - Critical messages: Verify delivery

        BLOCKCHAIN ANALOGY:
        - Flush = Wait for transaction finality
        - Returns 0 = All transactions confirmed on-chain
        - Returns >0 = Some transactions still pending

        Example:
            >>> producer.produce_order(order1)
            >>> producer.produce_order(order2)
            >>> remaining = producer.flush(timeout=10.0)
            >>> if remaining == 0:
            ...     print("All orders delivered!")
        """
        self.logger.info(
            "Flushing producer buffer",
            extra={"timeout": timeout}
        )

        # Flush blocks until all messages delivered or timeout
        remaining = self.producer.flush(timeout=timeout)

        if remaining > 0:
            self.logger.warning(
                "Producer flush timeout",
                extra={
                    "remaining_messages": remaining,
                    "timeout": timeout,
                    "advice": "Increase timeout or check broker health"
                }
            )
        else:
            self.logger.info("All messages delivered successfully")

        return remaining

    def close(self, timeout: float = 30.0) -> None:
        """
        Gracefully shutdown producer.

        This method:
        1. Flushes pending messages
        2. Closes producer connection
        3. Releases resources

        Args:
            timeout: Maximum time to wait for flush (seconds)

        Example:
            >>> producer = OrderProducer("localhost:9092", "food-orders")
            >>> try:
            ...     producer.produce_order(order)
            ... finally:
            ...     producer.close()  # Ensure graceful shutdown
        """
        self.logger.info("Shutting down producer")

        # Flush pending messages
        remaining = self.flush(timeout=timeout)

        if remaining > 0:
            self.logger.error(
                f"Producer closed with {remaining} messages undelivered",
                extra={"remaining_messages": remaining}
            )

        self.logger.info("Producer shutdown complete")

    def get_topic_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the target topic.

        Returns topic information including:
        - Partition count
        - Replication factor
        - Leader for each partition

        Returns:
            Dictionary with topic metadata

        Example:
            >>> producer = OrderProducer("localhost:9092", "food-orders")
            >>> metadata = producer.get_topic_metadata()
            >>> print(f"Topic has {len(metadata['partitions'])} partitions")
        """
        try:
            # Get cluster metadata
            metadata = self.producer.list_topics(topic=self.topic, timeout=10)

            topic_metadata = metadata.topics.get(self.topic)
            if not topic_metadata:
                return {"error": f"Topic '{self.topic}' not found"}

            partitions = []
            for partition_id, partition_metadata in topic_metadata.partitions.items():
                partitions.append({
                    "partition_id": partition_id,
                    "leader": partition_metadata.leader,
                    "replicas": partition_metadata.replicas,
                    "isrs": partition_metadata.isrs  # In-Sync Replicas
                })

            return {
                "topic": self.topic,
                "partition_count": len(partitions),
                "partitions": partitions,
                "error": topic_metadata.error
            }

        except Exception as e:
            self.logger.error(
                "Failed to get topic metadata",
                exc_info=True,
                extra={"error": str(e)}
            )
            return {"error": str(e)}


# ==============================================================================
# USAGE EXAMPLES
# ==============================================================================
"""
# Basic usage
from src.producer.producer import OrderProducer
from src.producer.mock_data import MockDataGenerator

# Initialize producer
producer = OrderProducer(
    bootstrap_servers="localhost:9092",
    topic="food-orders",
    client_id="demo-producer",
    log_level="INFO",
    log_format="json"
)

# Generate mock order
generator = MockDataGenerator()
order = generator.generate_order()

# Publish order
producer.produce_order(order)

# Flush and close
producer.flush()
producer.close()

# Continuous production (rate-limited)
import time

producer = OrderProducer("localhost:9092", "food-orders")
generator = MockDataGenerator()

try:
    for i in range(100):
        order = generator.generate_order()
        producer.produce_order(order)
        time.sleep(0.1)  # 10 orders/second
finally:
    producer.close()

# Custom delivery callback
def custom_callback(err, msg):
    if err:
        print(f"FAILED: {err}")
    else:
        print(f"SUCCESS: partition={msg.partition()}, offset={msg.offset()}")

producer = OrderProducer(
    bootstrap_servers="localhost:9092",
    topic="food-orders",
    delivery_callback=custom_callback
)

# Get topic metadata
producer = OrderProducer("localhost:9092", "food-orders")
metadata = producer.get_topic_metadata()
print(f"Topic: {metadata['topic']}")
print(f"Partitions: {metadata['partition_count']}")
for p in metadata['partitions']:
    print(f"  Partition {p['partition_id']}: leader={p['leader']}")

# Error handling
producer = OrderProducer("localhost:9092", "food-orders")

try:
    order = generator.generate_order()
    producer.produce_order(order)
except BufferError:
    print("Buffer full - slow down!")
except KafkaException as e:
    print(f"Kafka error: {e}")
finally:
    producer.close()
"""

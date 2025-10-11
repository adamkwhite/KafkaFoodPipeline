"""
Order Producer Service - Package Initialization

This package contains the Kafka producer service that generates and publishes
mock food orders to the Kafka 'food-orders' topic.

WHY A PRODUCER SERVICE?
- Simulates real-world order creation (e.g., mobile app, web checkout)
- Generates realistic test data for learning Kafka concepts
- Demonstrates producer best practices (partitioning, error handling, callbacks)

PRODUCER RESPONSIBILITIES:
1. Generate mock orders with realistic data (customers, menu items, timestamps)
2. Serialize orders to JSON format (Kafka messages are bytes)
3. Publish messages to Kafka topic with proper partition key
4. Handle delivery confirmations and errors
5. Log all operations with correlation IDs for tracing

KAFKA PRODUCER CONCEPTS:
- **Serialization**: Convert Python dict → JSON → bytes for Kafka
- **Partition Key**: customer_id ensures all orders from same customer → same partition
- **Acks**: Acknowledgment level (0=none, 1=leader, all=replicas)
- **Retries**: Automatic retry on transient errors
- **Idempotence**: Prevents duplicate messages (enable.idempotence=true)
- **Batching**: Group messages for efficiency (linger.ms, batch.size)

PACKAGE STRUCTURE:
- mock_data.py: Generate fake customers, menu items, orders
- producer.py: Kafka producer implementation with callbacks
- config.py: Producer configuration from environment variables
- main.py: Entry point for running the producer service

BLOCKCHAIN ANALOGY:
- Producer = Transaction creator (signs and broadcasts transactions)
- Partition Key = Shard ID (determines which shard/partition receives data)
- Acks = Confirmation level (wait for 1 validator vs wait for finality)
- Message = Transaction (immutable once committed to log)

LEARNING OBJECTIVES:
- Understand producer configuration (bootstrap servers, serializers)
- Learn partitioning strategies (key-based vs round-robin)
- Handle asynchronous delivery confirmations (callbacks)
- Implement error handling and retries
- Monitor producer metrics (latency, throughput, failures)

USAGE:
    # Run producer from command line
    python -m src.producer.main --rate 10 --duration 60

    # Or import as module
    from src.producer.producer import OrderProducer
    producer = OrderProducer(bootstrap_servers="localhost:9092")
    producer.produce_order(order_data)
    producer.flush()  # Wait for all messages to be delivered

NEXT STEPS AFTER THIS MODULE:
1. Mock Data Generator (mock_data.py) - Generate realistic orders
2. Producer Implementation (producer.py) - Kafka client with callbacks
3. Configuration (config.py) - Environment-based settings
4. Main Entry Point (main.py) - CLI for running producer
"""

# Package metadata
__version__ = "1.0.0"
__author__ = "Kafka Food Pipeline"

from src.producer.config import ProducerConfig, load_config
from src.producer.mock_data import MockDataGenerator

# Package exports (available when importing: from src.producer import ...)
# Import classes for convenient access
from src.producer.producer import OrderProducer

__all__ = [
    "OrderProducer",  # Main producer class (from producer.py)
    "MockDataGenerator",  # Mock data generator (from mock_data.py)
    "ProducerConfig",  # Configuration class (from config.py)
    "load_config",  # Configuration loader function
]

# ==============================================================================
# KAFKA PRODUCER QUICK REFERENCE
# ==============================================================================
"""
KEY CONFIGURATION PARAMETERS:

bootstrap.servers: Kafka broker addresses (kafka:9092)
client.id: Unique producer identifier (for monitoring)
acks: Acknowledgment level
    - 0: No acknowledgment (fire and forget, fastest, no guarantee)
    - 1: Leader acknowledgment (wait for leader, no replica guarantee)
    - all/-1: All replicas acknowledgment (slowest, strongest guarantee)

enable.idempotence: Prevent duplicate messages (recommended: true)
    - Ensures exactly-once semantics within partition
    - Automatically sets acks=all, max.in.flight.requests=5, retries=MAX_INT

compression.type: Compress messages (none, gzip, snappy, lz4, zstd)
    - Reduces network bandwidth and storage
    - Trade-off: CPU for bandwidth

linger.ms: Wait time before sending batch (default: 0)
    - 0: Send immediately (low latency)
    - >0: Wait for batch to fill (higher throughput)

batch.size: Maximum batch size in bytes (default: 16384)
    - Larger batches = better compression and throughput
    - Smaller batches = lower latency

retries: Number of retries on transient errors (default: MAX_INT when idempotence enabled)
retry.backoff.ms: Wait between retries (default: 100ms)

max.in.flight.requests.per.connection: Number of unacknowledged requests (default: 5)
    - Higher = better throughput
    - 1 = strict ordering (but slower)
    - 5 = good balance with idempotence

PARTITIONING STRATEGIES:

1. Key-based (hash partitioning):
   - Provide partition key (e.g., customer_id)
   - Kafka uses: hash(key) % num_partitions
   - Guarantees: Same key → same partition → ordering

2. Round-robin (default when key=None):
   - Distributes evenly across partitions
   - No ordering guarantees
   - Good for load balancing

3. Custom partitioner:
   - Implement custom logic
   - Example: VIP customers → dedicated partition

DELIVERY SEMANTICS:

1. At-most-once (acks=0, retries=0):
   - Message may be lost, never duplicated
   - Fastest, least reliable

2. At-least-once (acks=1, retries>0):
   - Message guaranteed delivered, may duplicate
   - Good balance for most use cases
   - Our consumer handles duplicates via primary key

3. Exactly-once (idempotence + transactions):
   - Message delivered exactly once
   - Highest guarantee, more complexity
   - Requires enable.idempotence=true

ERROR HANDLING:

BufferError: Producer buffer full
    - Increase buffer.memory
    - Slow down production rate
    - Increase linger.ms for better batching

KafkaTimeoutError: Message not sent within timeout
    - Check network connectivity
    - Increase request.timeout.ms
    - Check broker health

SerializationError: Failed to serialize message
    - Verify message format
    - Check serializer configuration

MONITORING METRICS:

- record-send-rate: Messages sent per second
- record-error-rate: Failed messages per second
- request-latency-avg: Average request latency
- buffer-available-bytes: Available producer buffer
- batch-size-avg: Average batch size
"""

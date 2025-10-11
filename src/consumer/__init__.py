"""
Order Consumer Service Package

This package implements the Kafka consumer service that:
1. Subscribes to the 'food-orders' Kafka topic
2. Consumes order messages in real-time
3. Validates order data
4. Persists orders to PostgreSQL database
5. Implements idempotency (duplicate detection)
6. Provides at-least-once delivery guarantees

WHY EVENT SOURCING WITH KAFKA + DATABASE?
- Kafka: Source of truth (immutable event log, replay capability)
- PostgreSQL: Materialized view (current state, queryable)
- Pattern: Consumer reads from Kafka → writes to DB (dual writes)
- Benefits: Audit trail, time travel, event replay, scalability

CONSUMER ARCHITECTURE:
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│   Kafka     │────▶│   Consumer   │────▶│   PostgreSQL   │
│ food-orders │     │   Group      │     │  orders table  │
│  (3 parts)  │     │ (N instances)│     │ (materialized) │
└─────────────┘     └──────────────┘     └────────────────┘

CONSUMER GROUP BEHAVIOR:
- Consumer group: 'order-processors'
- Partition assignment: Kafka auto-assigns partitions to consumers
- 3 partitions, 1 consumer: Consumer gets all 3 partitions
- 3 partitions, 2 consumers: 2:1 partition split
- 3 partitions, 3 consumers: 1:1 partition assignment (optimal)
- 3 partitions, 4 consumers: 1 consumer idle (no partition)

OFFSET MANAGEMENT (Critical for exactly-once):
1. Consumer reads message from Kafka
2. Process message (validate + save to DB)
3. Commit offset ONLY if successful
4. On failure: Don't commit → message redelivered
5. Idempotency: Handle duplicate deliveries (order_id uniqueness)

ERROR HANDLING STRATEGY:
- Validation errors: Log and skip (can't recover)
- Transient DB errors: Retry with backoff
- Fatal errors: Log, alert, shutdown gracefully
- Dead letter queue: Future enhancement for failed messages

Package components:
- config.py: Configuration from environment variables
- consumer.py: Kafka consumer implementation
- database.py: Database connection and operations
- main.py: Entry point with CLI and shutdown handling
"""

__version__ = "1.0.0"
__author__ = "Kafka Food Pipeline"

# Package exports (available when importing: from src.consumer import ...)
from src.consumer.config import ConsumerConfig, load_config

__all__ = [
    "ConsumerConfig",
    "load_config",
]

# ==============================================================================
# KAFKA CONSUMER QUICK REFERENCE
# ==============================================================================
"""
KAFKA CONSUMER BASICS:

1. **Subscribe to Topic**
   consumer.subscribe(['food-orders'])
   - Joins consumer group
   - Kafka auto-assigns partitions
   - Rebalances on consumer add/remove

2. **Poll for Messages**
   msg = consumer.poll(timeout=1.0)
   - Blocks for up to 1 second
   - Returns None if no message
   - Returns Message object if available

3. **Process Message**
   if msg and not msg.error():
       value = json.loads(msg.value().decode('utf-8'))
       # Validate and save to DB

4. **Commit Offset (Manual)**
   consumer.commit(asynchronous=False)
   - Tells Kafka: "I've processed this message"
   - enable.auto.commit=False for manual control
   - Commit after successful DB write (at-least-once)

5. **Error Handling**
   if msg.error():
       if msg.error().code() == KafkaError._PARTITION_EOF:
           # Reached end of partition
       else:
           # Real error, handle it

6. **Graceful Shutdown**
   consumer.close()
   - Commits offsets
   - Leaves consumer group
   - Triggers rebalance for other consumers

OFFSET COMMIT PATTERNS:

Pattern 1: Auto-commit (simple, at-most-once)
- enable.auto.commit=True
- Kafka commits every auto.commit.interval.ms
- Risk: May lose messages on crash

Pattern 2: Manual commit after each message (at-least-once)
- enable.auto.commit=False
- Commit after successful processing
- May process duplicates on crash → need idempotency

Pattern 3: Batch commit (higher throughput)
- Process N messages
- Commit offset of last message
- Trade-off: More duplicates on crash

This service uses Pattern 2 (manual commit per message) with idempotency.
"""

"""
Kafka Order Consumer Implementation

This module implements the Kafka consumer that reads orders from the 'food-orders'
topic and persists them to PostgreSQL database.

KAFKA CONSUMER ARCHITECTURE:
┌─────────────────────────────────────────────────────────────────────────┐
│  Kafka Consumer Lifecycle                                               │
├─────────────────────────────────────────────────────────────────────────┤
│  1. Subscribe to topic → Join consumer group                            │
│  2. Kafka assigns partitions (rebalancing)                              │
│  3. Poll for messages (blocking with timeout)                           │
│  4. Deserialize message (JSON bytes → Python dict)                      │
│  5. Validate message data                                               │
│  6. Process message (save to database)                                  │
│  7. Commit offset (tell Kafka: message processed)                       │
│  8. Handle errors (retry transient, skip permanent)                     │
│  9. Graceful shutdown (close consumer, commit offsets)                  │
└─────────────────────────────────────────────────────────────────────────┘

AT-LEAST-ONCE DELIVERY:
- Consumer commits offset AFTER successful database write
- If crash before commit → message redelivered
- Idempotency via order_id PRIMARY KEY (duplicates cause IntegrityError)
- Trade-off: Duplicate processing vs lost messages

CONSUMER GROUP BEHAVIOR:
- Consumer group: 'order-processors'
- Multiple consumers → share partitions (horizontal scaling)
- Partition assignment: Automatic (Kafka rebalancing)
- 3 partitions, 1 consumer: 1 consumer gets all 3 partitions
- 3 partitions, 3 consumers: Each gets 1 partition (optimal)
- 3 partitions, 4 consumers: 1 consumer idle (no work)

ERROR HANDLING STRATEGY:
1. Validation errors: Log and skip (can't recover, poison message)
2. Transient DB errors: Retry with exponential backoff
3. Fatal errors: Log, alert, shutdown gracefully
4. Duplicates: Log and skip (already processed, idempotency working)
"""

import json
import logging
import time
from typing import Any, Dict

from confluent_kafka import Consumer, KafkaError, Message
from sqlalchemy.exc import IntegrityError, OperationalError

from src.consumer.config import ConsumerConfig
from src.consumer.database import DatabaseManager
from src.consumer.models import Order
from src.shared.logger import CorrelationAdapter

# ==============================================================================
# KAFKA CONSUMER
# ==============================================================================


class OrderConsumer:
    """
    Kafka consumer for processing food orders.

    This class implements the complete consumer lifecycle:
    - Subscribe to Kafka topic
    - Poll for messages
    - Deserialize and validate
    - Save to PostgreSQL
    - Commit offsets
    - Handle errors and retries

    Attributes:
        config: Consumer configuration
        consumer: Confluent Kafka consumer instance
        db_manager: Database connection manager
        logger: Structured logger
        running: Flag for graceful shutdown
        messages_processed: Counter for metrics
        messages_failed: Counter for errors
    """

    def __init__(self, config: ConsumerConfig, db_manager: DatabaseManager):
        """
        Initialize Kafka consumer.

        Args:
            config: Consumer configuration
            db_manager: Database manager for persistence

        CONSUMER INITIALIZATION:
        1. Create Kafka consumer with config
        2. Subscribe to topic
        3. Initialize metrics counters
        4. Set up logging
        """
        self.config = config
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)

        # Metrics counters
        self.messages_processed = 0
        self.messages_failed = 0
        self.messages_skipped = 0  # Duplicates
        self.running = True

        # Create Kafka consumer
        self.consumer = self._create_consumer()

        # Subscribe to topic
        self.consumer.subscribe([config.kafka_topic_orders])

        self.logger.info(
            "Order consumer initialized",
            extra={
                "topic": config.kafka_topic_orders,
                "group_id": config.consumer_group_id,
                "bootstrap_servers": config.kafka_bootstrap_servers,
            },
        )

    def _create_consumer(self) -> Consumer:
        """
        Create Confluent Kafka consumer with configuration.

        Returns:
            Configured Kafka Consumer instance

        CONSUMER CONFIGURATION:
        - bootstrap.servers: Kafka broker addresses
        - group.id: Consumer group (for partition assignment)
        - client.id: Consumer identifier (for debugging)
        - auto.offset.reset: Where to start (earliest/latest)
        - enable.auto.commit: False (manual commit for at-least-once)
        """
        kafka_config = self.config.get_kafka_config()

        self.logger.debug(
            "Creating Kafka consumer",
            extra={"config": {k: v for k, v in kafka_config.items() if k != "password"}},
        )

        return Consumer(kafka_config)

    def start(self) -> None:
        """
        Start consuming messages from Kafka.

        This is the main consumer loop:
        1. Poll for message
        2. Process message
        3. Commit offset
        4. Repeat until shutdown

        CONSUMER LOOP:
        - Runs continuously until self.running = False
        - Polls with 1-second timeout (non-blocking)
        - Handles errors without crashing
        - Logs metrics periodically
        """
        self.logger.info("Starting consumer loop...")

        try:
            while self.running:
                # Poll for message (1-second timeout)
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    # No message available, continue polling
                    continue

                if msg.error():
                    # Handle Kafka errors
                    self._handle_kafka_error(msg.error())
                    continue

                # Process message
                self._process_message(msg)

        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt, shutting down...")
        except Exception:
            self.logger.error("Fatal error in consumer loop", exc_info=True)
            raise
        finally:
            self._shutdown()

    def _process_message(self, msg: Message) -> None:
        """
        Process a single Kafka message.

        Args:
            msg: Kafka message

        PROCESSING FLOW:
        1. Deserialize JSON
        2. Extract order_id for correlation
        3. Validate data structure
        4. Create Order instance
        5. Save to database (with retry)
        6. Commit offset
        7. Log success

        ERROR HANDLING:
        - JSON decode error → skip (poison message)
        - Validation error → skip (bad data)
        - Integrity error → skip (duplicate)
        - Operational error → retry (transient)
        - Unknown error → log and skip
        """
        start_time = time.time()
        order_id = None

        try:
            # 1. Deserialize message
            message_data = self._deserialize_message(msg)
            order_id = message_data.get("order_id", "unknown")

            # Set up correlation logger for this order
            order_logger = CorrelationAdapter(self.logger, {"correlation_id": order_id})

            order_logger.debug(
                "Processing message",
                extra={
                    "partition": msg.partition(),
                    "offset": msg.offset(),
                    "customer_id": message_data.get("customer_id"),
                },
            )

            # 2. Validate message structure
            self._validate_message(message_data)

            # 3. Create Order instance from message
            order = Order.from_kafka_message(message_data)

            # Extract data for logging before session closes
            customer_id = message_data["customer_id"]
            total_amount = message_data["total_amount"]

            # 4. Save to database with retry
            self._save_order_with_retry(order, order_logger)

            # 5. Commit offset (message successfully processed)
            self.consumer.commit(asynchronous=False)

            # 6. Update metrics
            self.messages_processed += 1
            processing_time = (time.time() - start_time) * 1000  # milliseconds

            order_logger.info(
                "Order processed successfully",
                extra={
                    "customer_id": customer_id,
                    "total_amount": total_amount,
                    "processing_time_ms": round(processing_time, 2),
                    "messages_processed": self.messages_processed,
                },
            )

        except json.JSONDecodeError:
            # Permanent error: Can't decode JSON
            self.messages_failed += 1
            self.logger.error(
                "Failed to decode JSON message",
                exc_info=True,
                extra={
                    "correlation_id": order_id,
                    "offset": msg.offset(),
                    "partition": msg.partition(),
                },
            )
            # Skip this message (don't commit offset in this case? No, commit to move on)
            self.consumer.commit(asynchronous=False)

        except ValueError as e:
            # Permanent error: Invalid data structure
            self.messages_failed += 1
            self.logger.error(
                "Message validation failed",
                exc_info=True,
                extra={"correlation_id": order_id, "error": str(e)},
            )
            # Skip this message
            self.consumer.commit(asynchronous=False)

        except IntegrityError:
            # Duplicate order (idempotency working as expected)
            self.messages_skipped += 1
            self.logger.warning(
                "Duplicate order detected, skipping",
                extra={
                    "correlation_id": order_id,
                    "messages_skipped": self.messages_skipped,
                },
            )
            # Commit offset (already processed)
            self.consumer.commit(asynchronous=False)

        except Exception:
            # Unknown error
            self.messages_failed += 1
            self.logger.error(
                "Unexpected error processing message",
                exc_info=True,
                extra={"correlation_id": order_id},
            )
            # Commit offset to skip this message and move on
            # (otherwise consumer gets stuck retrying bad message forever)
            try:
                self.consumer.commit(asynchronous=False)
            except Exception:
                self.logger.error(
                    "Failed to commit offset after error",
                    exc_info=True,
                    extra={"correlation_id": order_id},
                )

    def _deserialize_message(self, msg: Message) -> Dict[str, Any]:
        """
        Deserialize Kafka message from bytes to Python dict.

        Args:
            msg: Kafka message

        Returns:
            Deserialized message data

        Raises:
            json.JSONDecodeError: If message is not valid JSON

        MESSAGE FORMAT:
        - Key: customer_id (UTF-8 string)
        - Value: JSON order data (UTF-8 encoded)
        """
        # Decode bytes to string, then parse JSON
        message_bytes = msg.value()
        message_str = message_bytes.decode("utf-8")
        message_data = json.loads(message_str)

        return message_data

    def _validate_message(self, message_data: Dict[str, Any]) -> None:
        """
        Validate message structure.

        Args:
            message_data: Deserialized message data

        Raises:
            ValueError: If message structure is invalid

        REQUIRED FIELDS:
        - order_id: str
        - customer_id: str
        - customer_name: str
        - customer_email: str
        - items: list
        - total_amount: float
        - status: str
        - created_at: str (ISO 8601)
        """
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

        missing_fields = [field for field in required_fields if field not in message_data]

        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")

        # Validate items is a non-empty list
        if not isinstance(message_data["items"], list) or len(message_data["items"]) == 0:
            raise ValueError("Items must be a non-empty list")

        # Validate total_amount is positive
        if (
            not isinstance(message_data["total_amount"], (int, float))
            or message_data["total_amount"] <= 0
        ):
            raise ValueError("Total amount must be a positive number")

    def _save_order_with_retry(self, order: Order, logger: CorrelationAdapter) -> None:
        """
        Save order to database with retry logic.

        Args:
            order: Order instance to save
            logger: Correlation logger for this order

        Raises:
            OperationalError: If all retries exhausted
            IntegrityError: If duplicate order (idempotency)

        RETRY STRATEGY:
        - Retry only transient errors (OperationalError)
        - Don't retry permanent errors (IntegrityError, ValueError)
        - Exponential backoff: 1s, 2s, 4s, ...
        - Max retries from config
        """
        for attempt in range(self.config.max_retries):
            try:
                # Attempt to save order
                with self.db_manager.get_session() as session:
                    session.add(order)
                    # Commit happens automatically on context exit

                # Success!
                return

            except IntegrityError:
                # Duplicate order (primary key violation)
                # This is expected (idempotency), re-raise to handle at higher level
                raise

            except OperationalError as e:
                # Transient database error (connection lost, timeout, etc.)
                if attempt < self.config.max_retries - 1:
                    # Calculate backoff time (exponential)
                    backoff_ms = self.config.retry_backoff_ms * (2**attempt)
                    backoff_s = backoff_ms / 1000

                    logger.warning(
                        f"Database error, retrying in {backoff_s}s",
                        extra={
                            "attempt": attempt + 1,
                            "max_retries": self.config.max_retries,
                            "error": str(e),
                        },
                    )

                    time.sleep(backoff_s)
                else:
                    # Max retries exhausted
                    logger.error(
                        "Max retries exhausted, giving up",
                        extra={"attempts": self.config.max_retries},
                    )
                    raise

    def _handle_kafka_error(self, error: KafkaError) -> None:
        """
        Handle Kafka-specific errors.

        Args:
            error: Kafka error

        KAFKA ERROR TYPES:
        - _PARTITION_EOF: Reached end of partition (normal, not an error)
        - _ALL_BROKERS_DOWN: No brokers available (fatal)
        - _AUTHENTICATION: Authentication failed (fatal)
        - _TOPIC_AUTHORIZATION: Not authorized for topic (fatal)
        """
        if error.code() == KafkaError._PARTITION_EOF:
            # Reached end of partition (not an error, just info)
            self.logger.debug(
                "Reached end of partition",
                extra={
                    "partition": error.partition() if hasattr(error, "partition") else "unknown"
                },
            )
        else:
            # Real error
            self.logger.error(
                f"Kafka error: {error.str()}",
                extra={
                    "error_code": error.code(),
                    "error_name": error.name(),
                },
            )

            # If fatal error, stop consumer
            if error.code() in [
                KafkaError._ALL_BROKERS_DOWN,
                KafkaError._AUTHENTICATION,
                KafkaError._TOPIC_AUTHORIZATION_FAILED,
            ]:
                self.logger.critical("Fatal Kafka error, shutting down")
                self.stop()

    def stop(self) -> None:
        """
        Signal consumer to stop gracefully.

        Sets self.running = False to break the consumer loop.
        The loop will finish processing the current message, then exit.
        """
        self.logger.info("Stopping consumer...")
        self.running = False

    def _shutdown(self) -> None:
        """
        Clean shutdown: close Kafka consumer and database connections.

        SHUTDOWN SEQUENCE:
        1. Close Kafka consumer (commits final offsets)
        2. Close database connections
        3. Log final metrics
        """
        self.logger.info(
            "Consumer shutting down",
            extra={
                "messages_processed": self.messages_processed,
                "messages_failed": self.messages_failed,
                "messages_skipped": self.messages_skipped,
            },
        )

        # Close Kafka consumer
        try:
            self.consumer.close()
            self.logger.info("Kafka consumer closed")
        except Exception:
            self.logger.error("Error closing Kafka consumer", exc_info=True)

        # Close database connections
        try:
            self.db_manager.close()
            self.logger.info("Database connections closed")
        except Exception:
            self.logger.error("Error closing database", exc_info=True)

        self.logger.info("Consumer shutdown complete")


# ==============================================================================
# USAGE EXAMPLE
# ==============================================================================
"""
from src.consumer.config import load_config
from src.consumer.database import init_database
from src.consumer.consumer import OrderConsumer
from src.shared.logger import setup_logger

# Load configuration
config = load_config()

# Set up logging
logger = setup_logger(
    name=__name__,
    service_name="order-consumer",
    log_level=config.log_level,
    log_format=config.log_format
)

# Initialize database
db_manager = init_database(config)

# Create consumer
consumer = OrderConsumer(config, db_manager)

# Start consuming (blocking)
try:
    consumer.start()
except KeyboardInterrupt:
    logger.info("Shutting down...")
finally:
    consumer.stop()
"""

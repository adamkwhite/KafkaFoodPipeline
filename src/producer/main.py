"""
Order Producer Service - Main Entry Point

This module provides the main entry point for running the Kafka order producer.

WHAT THIS SERVICE DOES:
1. Generates mock food orders at configurable rate
2. Publishes orders to Kafka 'food-orders' topic
3. Uses customer_id as partition key (ordering per customer)
4. Handles graceful shutdown (flush pending messages)
5. Logs all operations with correlation IDs

RUN MODES:
- Batch: Generate N orders then stop (PRODUCER_DURATION > 0)
- Continuous: Generate orders until stopped (PRODUCER_DURATION = 0)
- Rate-limited: Control orders/second (PRODUCER_RATE)

USAGE:
    # Using environment variables (from .env)
    python -m src.producer.main

    # Command-line overrides
    python -m src.producer.main --rate 20 --duration 120
    python -m src.producer.main --bootstrap-servers kafka:9092
    python -m src.producer.main --log-level DEBUG --log-format text

    # Continuous production (Ctrl+C to stop)
    python -m src.producer.main --duration 0

LEARNING OBJECTIVES:
- Understand producer lifecycle (init → produce → flush → close)
- See rate limiting for controlled load
- Learn graceful shutdown patterns (signal handling)
- Monitor producer metrics (throughput, latency, errors)
"""

import argparse
import signal
import sys
import time

from src.producer.config import ProducerConfig, load_config, validate_kafka_connection
from src.producer.mock_data import MockDataGenerator
from src.producer.producer import OrderProducer
from src.shared.logger import setup_logger

# ==============================================================================
# GLOBAL STATE FOR SIGNAL HANDLING
# ==============================================================================
# Used for graceful shutdown on Ctrl+C (SIGINT) or SIGTERM

shutdown_requested = False


def signal_handler(signum, frame):
    """
    Handle shutdown signals gracefully.

    This function is called when:
    - User presses Ctrl+C (SIGINT)
    - System sends SIGTERM (e.g., Docker stop)

    It sets a flag to exit the production loop gracefully.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    global shutdown_requested
    print(f"\n\n⚠️  Shutdown signal received (signal {signum})")
    print("🔄 Gracefully shutting down producer...")
    print("   - Stopping order generation")
    print("   - Flushing pending messages to Kafka")
    print("   - Please wait...\n")
    shutdown_requested = True


# ==============================================================================
# MAIN PRODUCER FUNCTION
# ==============================================================================


def run_producer(config: ProducerConfig) -> int:
    """
    Run the order producer service.

    This function:
    1. Validates Kafka connection
    2. Initializes mock data generator
    3. Creates Kafka producer
    4. Runs production loop (rate-limited)
    5. Handles errors and shutdown gracefully

    Args:
        config: Producer configuration

    Returns:
        Exit code (0 = success, 1 = error)

    PRODUCTION LOOP:
    - Generate order
    - Publish to Kafka
    - Sleep to maintain rate
    - Check shutdown flag
    - Repeat until duration or shutdown
    """
    global shutdown_requested  # noqa: F824

    # Set up logger
    logger = setup_logger(
        name=__name__,
        service_name="order-producer",
        log_level=config.log_level,
        log_format=config.log_format,
    )

    logger.info(
        "Order producer starting",
        extra={
            "bootstrap_servers": config.kafka_bootstrap_servers,
            "topic": config.kafka_topic_orders,
            "rate": config.producer_rate,
            "duration": config.producer_duration if config.producer_duration > 0 else "infinite",
            "compression": config.producer_compression,
            "idempotence": config.enable_idempotence,
        },
    )

    # Validate Kafka connection before starting
    logger.info("Validating Kafka connection...")
    if not validate_kafka_connection(config):
        logger.error(
            "Cannot connect to Kafka brokers",
            extra={"bootstrap_servers": config.kafka_bootstrap_servers},
        )
        return 1

    logger.info("✅ Kafka connection validated")

    # Initialize mock data generator
    logger.info(
        "Initializing mock data generator",
        extra={
            "seed": config.mock_seed,
            "num_customers": 100,
            "num_menu_items": 20,
            "reproducible": config.mock_seed > 0,
        },
    )
    generator = MockDataGenerator(seed=config.mock_seed)

    # Initialize Kafka producer
    try:
        producer = OrderProducer(
            bootstrap_servers=config.kafka_bootstrap_servers,
            topic=config.kafka_topic_orders,
            client_id=config.producer_client_id,
            log_level=config.log_level,
            log_format=config.log_format,
        )
        logger.info("✅ Kafka producer initialized")
    except Exception as e:
        logger.error("Failed to initialize Kafka producer", exc_info=True, extra={"error": str(e)})
        return 1

    # Get topic metadata for informational purposes
    metadata = producer.get_topic_metadata()
    if "error" not in metadata:
        logger.info(
            "Topic metadata",
            extra={
                "topic": metadata["topic"],
                "partition_count": metadata["partition_count"],
                "partitions": metadata["partitions"],
            },
        )

    # Calculate sleep interval for rate limiting
    # Example: 10 orders/sec → sleep 0.1 sec between orders
    sleep_interval = 1.0 / config.producer_rate

    logger.info(
        "Starting order production",
        extra={
            "rate": config.producer_rate,
            "sleep_interval_ms": sleep_interval * 1000,
            "duration": config.producer_duration if config.producer_duration > 0 else "infinite",
        },
    )

    # Production loop
    orders_produced = 0
    start_time = time.time()
    errors = 0

    try:
        while not shutdown_requested:
            # Check duration limit (if set)
            if config.producer_duration > 0:
                elapsed = time.time() - start_time
                if elapsed >= config.producer_duration:
                    logger.info(
                        "Duration limit reached, stopping production",
                        extra={
                            "duration": config.producer_duration,
                            "elapsed": elapsed,
                            "orders_produced": orders_produced,
                        },
                    )
                    break

            # Generate mock order
            try:
                order = generator.generate_order()
            except Exception as e:
                logger.error("Failed to generate order", exc_info=True, extra={"error": str(e)})
                errors += 1
                continue

            # Publish to Kafka
            try:
                producer.produce_order(order)
                orders_produced += 1

                # Log periodic progress (every 100 orders)
                if orders_produced % 100 == 0:
                    elapsed = time.time() - start_time
                    actual_rate = orders_produced / elapsed if elapsed > 0 else 0
                    logger.info(
                        "Production progress",
                        extra={
                            "orders_produced": orders_produced,
                            "elapsed_seconds": round(elapsed, 2),
                            "target_rate": config.producer_rate,
                            "actual_rate": round(actual_rate, 2),
                            "errors": errors,
                        },
                    )

            except Exception as e:
                logger.error(
                    "Failed to publish order",
                    exc_info=True,
                    extra={"correlation_id": order.get("order_id"), "error": str(e)},
                )
                errors += 1
                continue

            # Rate limiting: sleep to maintain target rate
            time.sleep(sleep_interval)

    except KeyboardInterrupt:
        # Ctrl+C pressed (already handled by signal handler)
        pass

    except Exception as e:
        logger.error("Unexpected error in production loop", exc_info=True, extra={"error": str(e)})
        return 1

    finally:
        # Graceful shutdown
        elapsed = time.time() - start_time
        actual_rate = orders_produced / elapsed if elapsed > 0 else 0

        logger.info(
            "Shutting down producer",
            extra={
                "orders_produced": orders_produced,
                "errors": errors,
                "elapsed_seconds": round(elapsed, 2),
                "actual_rate": round(actual_rate, 2),
            },
        )

        # Flush pending messages
        logger.info("Flushing pending messages to Kafka...")
        try:
            remaining = producer.flush(timeout=30.0)
            if remaining == 0:
                logger.info("✅ All messages delivered successfully")
            else:
                logger.warning(
                    f"⚠️  {remaining} messages not delivered", extra={"remaining": remaining}
                )
        except Exception as e:
            logger.error("Error flushing producer", exc_info=True, extra={"error": str(e)})

        # Close producer
        try:
            producer.close(timeout=10.0)
            logger.info("✅ Producer closed successfully")
        except Exception as e:
            logger.error("Error closing producer", exc_info=True, extra={"error": str(e)})

        # Final statistics
        logger.info(
            "Producer shutdown complete",
            extra={
                "total_orders": orders_produced,
                "total_errors": errors,
                "total_duration_seconds": round(elapsed, 2),
                "average_rate": round(actual_rate, 2),
                "success_rate": (
                    round((orders_produced - errors) / orders_produced * 100, 2)
                    if orders_produced > 0
                    else 0
                ),
            },
        )

    return 0 if errors == 0 else 1


# ==============================================================================
# CLI ARGUMENT PARSING
# ==============================================================================


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Command-line args override environment variables.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Kafka Order Producer - Generate and publish food orders to Kafka",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use environment variables (from .env)
  python -m src.producer.main

  # Override rate and duration
  python -m src.producer.main --rate 20 --duration 120

  # Run indefinitely with debug logging
  python -m src.producer.main --duration 0 --log-level DEBUG

  # Custom Kafka broker and topic
  python -m src.producer.main --bootstrap-servers kafka:9092 --topic orders

  # Text logs for local development
  python -m src.producer.main --log-format text
        """,
    )

    # Kafka configuration
    parser.add_argument(
        "--bootstrap-servers", type=str, help="Kafka bootstrap servers (default: from config)"
    )

    parser.add_argument("--topic", type=str, help="Kafka topic name (default: from config)")

    # Producer settings
    parser.add_argument("--rate", type=int, help="Orders per second (1-1000, default: from config)")

    parser.add_argument(
        "--duration", type=int, help="Run duration in seconds (0=infinite, default: from config)"
    )

    parser.add_argument("--client-id", type=str, help="Producer client ID (default: from config)")

    # Mock data
    parser.add_argument(
        "--seed", type=int, help="Random seed for reproducible data (default: from config)"
    )

    # Logging
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: from config)",
    )

    parser.add_argument(
        "--log-format",
        type=str,
        choices=["json", "text"],
        help="Log output format (default: from config)",
    )

    return parser.parse_args()


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================


def main() -> int:
    """
    Main entry point for producer service.

    Returns:
        Exit code (0 = success, 1 = error)
    """
    # Parse CLI arguments
    args = parse_args()

    # Load configuration from environment
    config = load_config()

    # Override config with CLI arguments (if provided)
    if args.bootstrap_servers:
        config.kafka_bootstrap_servers = args.bootstrap_servers
    if args.topic:
        config.kafka_topic_orders = args.topic
    if args.rate:
        config.producer_rate = args.rate
    if args.duration is not None:  # Allow 0
        config.producer_duration = args.duration
    if args.client_id:
        config.producer_client_id = args.client_id
    if args.seed is not None:  # Allow 0
        config.mock_seed = args.seed
    if args.log_level:
        config.log_level = args.log_level
    if args.log_format:
        config.log_format = args.log_format

    # Display configuration
    print(config.display_config())
    print("=" * 70)
    print()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Docker stop

    # Run producer
    return run_producer(config)


if __name__ == "__main__":
    sys.exit(main())


# ==============================================================================
# USAGE EXAMPLES
# ==============================================================================
"""
# Basic usage (environment variables from .env)
python -m src.producer.main

# Override rate to 20 orders/second for 2 minutes
python -m src.producer.main --rate 20 --duration 120

# Run indefinitely until Ctrl+C
python -m src.producer.main --duration 0

# Debug mode with text logs
python -m src.producer.main --log-level DEBUG --log-format text

# Connect to custom Kafka broker
python -m src.producer.main --bootstrap-servers kafka-prod:9092

# Reproducible test run (same seed = same orders)
python -m src.producer.main --seed 12345 --duration 60

# Quick test: 5 orders/sec for 10 seconds
python -m src.producer.main --rate 5 --duration 10

# Load test: 100 orders/sec for 5 minutes
python -m src.producer.main --rate 100 --duration 300

# Docker run
docker run order-producer \
  -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
  -e PRODUCER_RATE=10 \
  python -m src.producer.main

# Kubernetes run
kubectl run order-producer \
  --image=order-producer:latest \
  --env="KAFKA_BOOTSTRAP_SERVERS=kafka-service:9092" \
  --env="PRODUCER_RATE=50"
"""

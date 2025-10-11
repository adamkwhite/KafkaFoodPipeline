"""
Order Consumer Service - Main Entry Point

This module provides the command-line interface and main entry point for the
Kafka order consumer service.

USAGE:
    python -m src.consumer.main [options]

OPTIONS:
    --log-level    Logging level (DEBUG, INFO, WARNING, ERROR)
    --log-format   Log format (json or text)
    --help         Show help message

ENVIRONMENT VARIABLES:
    See src/consumer/config.py for full list of configuration options:
    - KAFKA_BOOTSTRAP_SERVERS: Kafka broker addresses
    - KAFKA_TOPIC_ORDERS: Topic to consume from
    - CONSUMER_GROUP_ID: Consumer group identifier
    - POSTGRES_HOST: PostgreSQL host
    - POSTGRES_PORT: PostgreSQL port
    - POSTGRES_DB: Database name
    - LOG_LEVEL: Logging level
    - LOG_FORMAT: Log format

GRACEFUL SHUTDOWN:
- Handles SIGINT (Ctrl+C) and SIGTERM (Docker stop)
- Finishes processing current message
- Commits final offsets
- Closes database connections
- Logs shutdown metrics

DOCKER DEPLOYMENT:
    docker build -f Dockerfile.consumer -t order-consumer .
    docker run --env-file .env order-consumer

MONITORING:
- Structured JSON logs to stdout
- Correlation IDs (order_id) for tracing
- Metrics: messages processed, failed, skipped
- Health checks via database connectivity
"""

import argparse
import logging
import signal
import sys
from typing import Optional

from src.consumer.config import load_config
from src.consumer.consumer import OrderConsumer
from src.consumer.database import init_database
from src.shared.logger import setup_logger

# ==============================================================================
# GLOBAL STATE
# ==============================================================================
# Global consumer instance for signal handlers
# Must be global so signal handlers can access it

consumer_instance: Optional[OrderConsumer] = None

# ==============================================================================
# SIGNAL HANDLERS
# ==============================================================================
# Handle SIGINT (Ctrl+C) and SIGTERM (Docker stop) for graceful shutdown


def signal_handler(signum: int, frame) -> None:
    """
    Handle shutdown signals (SIGINT, SIGTERM).

    Args:
        signum: Signal number
        frame: Current stack frame

    SIGNAL HANDLING:
    - SIGINT: Sent by Ctrl+C in terminal
    - SIGTERM: Sent by Docker stop, Kubernetes, systemd
    - Both trigger graceful shutdown (finish current message, then exit)

    GRACEFUL SHUTDOWN STEPS:
    1. Set consumer.running = False (breaks poll loop)
    2. Finish processing current message
    3. Commit final offset
    4. Close Kafka consumer
    5. Close database connections
    6. Exit with code 0
    """
    signal_name = signal.Signals(signum).name

    logger = logging.getLogger(__name__)
    logger.info(f"Received {signal_name}, initiating graceful shutdown...")

    # Stop consumer gracefully
    if consumer_instance:
        consumer_instance.stop()


# ==============================================================================
# CLI ARGUMENT PARSING
# ==============================================================================


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments

    ARGUMENTS:
    - --log-level: Override LOG_LEVEL env var
    - --log-format: Override LOG_FORMAT env var
    - --help: Show help and exit
    """
    parser = argparse.ArgumentParser(
        description="Kafka Order Consumer Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start consumer with default settings
  python -m src.consumer.main

  # Start with debug logging
  python -m src.consumer.main --log-level DEBUG

  # Start with plain text logs (for development)
  python -m src.consumer.main --log-format text

  # Docker deployment
  docker run --env-file .env order-consumer

Environment Variables:
  KAFKA_BOOTSTRAP_SERVERS    Kafka broker addresses (default: localhost:9092)
  KAFKA_TOPIC_ORDERS         Topic to consume (default: food-orders)
  CONSUMER_GROUP_ID          Consumer group (default: order-processors)
  POSTGRES_HOST              Database host (default: localhost)
  POSTGRES_PORT              Database port (default: 5432)
  POSTGRES_DB                Database name (default: food_orders)
  POSTGRES_USER              Database user (default: postgres)
  POSTGRES_PASSWORD          Database password (default: postgres)
  LOG_LEVEL                  Logging level (default: INFO)
  LOG_FORMAT                 Log format: json or text (default: json)

Signals:
  SIGINT (Ctrl+C)            Graceful shutdown
  SIGTERM (Docker stop)      Graceful shutdown
        """,
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (overrides LOG_LEVEL env var)",
    )

    parser.add_argument(
        "--log-format",
        type=str,
        choices=["json", "text"],
        help="Log output format (overrides LOG_FORMAT env var)",
    )

    return parser.parse_args()


# ==============================================================================
# MAIN FUNCTION
# ==============================================================================


def main() -> int:
    """
    Main entry point for order consumer service.

    Returns:
        Exit code (0 = success, 1 = error)

    STARTUP SEQUENCE:
    1. Parse CLI arguments
    2. Load configuration from environment
    3. Set up structured logging
    4. Initialize database connection
    5. Create Kafka consumer
    6. Register signal handlers
    7. Start consuming messages
    8. Handle graceful shutdown

    ERROR HANDLING:
    - Configuration errors: Exit code 1
    - Database connection errors: Exit code 1
    - Kafka errors: Logged, consumer retries
    - Fatal errors: Exit code 1 after logging
    """
    global consumer_instance

    # Parse command-line arguments
    args = parse_args()

    # Load configuration
    try:
        config = load_config()
    except Exception as e:
        print(f"ERROR: Failed to load configuration: {e}", file=sys.stderr)
        return 1

    # Override config with CLI arguments if provided
    if args.log_level:
        config.log_level = args.log_level
    if args.log_format:
        config.log_format = args.log_format

    # Set up logging
    logger = setup_logger(
        name=__name__,
        service_name="order-consumer",
        log_level=config.log_level,
        log_format=config.log_format,
    )

    logger.info(
        "Starting Order Consumer Service",
        extra={
            "version": "3.0",
            "kafka_bootstrap_servers": config.kafka_bootstrap_servers,
            "kafka_topic": config.kafka_topic_orders,
            "consumer_group": config.consumer_group_id,
            "database_host": config.postgres_host,
            "database_name": config.postgres_db,
            "log_level": config.log_level,
            "log_format": config.log_format,
        },
    )

    # Initialize database
    try:
        db_manager = init_database(config)
        logger.info("Database connection established")
    except Exception:
        logger.error("Failed to initialize database", exc_info=True)
        return 1

    # Create consumer
    try:
        consumer_instance = OrderConsumer(config, db_manager)
        logger.info("Kafka consumer created successfully")
    except Exception:
        logger.error("Failed to create Kafka consumer", exc_info=True)
        db_manager.close()
        return 1

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    logger.info("Signal handlers registered (SIGINT, SIGTERM)")

    # Start consuming messages (blocking until shutdown)
    try:
        logger.info("Consumer starting, press Ctrl+C to stop...")
        consumer_instance.start()
        logger.info("Consumer stopped")
        return 0

    except KeyboardInterrupt:
        # Should be handled by signal handler, but just in case
        logger.info("Keyboard interrupt received")
        return 0

    except Exception:
        logger.error("Fatal error in consumer", exc_info=True)
        return 1


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    sys.exit(main())

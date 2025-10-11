"""
Structured JSON Logging Configuration

This module provides structured logging for Kafka producer and consumer services.

WHY STRUCTURED LOGGING?
- Plain text logs are hard to parse/search (e.g., "Order ORD-001 processed successfully")
- JSON logs are machine-readable (e.g., {"order_id": "ORD-001", "status": "processed"})
- Enable powerful querying in log aggregation tools (ELK, Splunk, CloudWatch)
- Better for distributed systems (microservices, Kafka pipelines)

STRUCTURED LOGGING BENEFITS:
1. Easy parsing: Parse JSON instead of regex on text
2. Consistent format: Same structure across all services
3. Correlation: Track requests across services (correlation_id)
4. Filtering: Query specific fields (e.g., "all ERROR logs for customer_id=X")
5. Metrics: Extract metrics from logs (latency, throughput, errors)

EXAMPLE OUTPUT:
{
  "timestamp": "2025-01-10T14:30:00.123Z",
  "level": "INFO",
  "service": "order-consumer",
  "correlation_id": "ORD-20250110-00001",
  "message": "Order processed successfully",
  "customer_id": "CUST-00001",
  "total_amount": 21.47,
  "processing_time_ms": 45
}
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional


# ==============================================================================
# JSON FORMATTER
# ==============================================================================
# Custom formatter that outputs logs as JSON instead of plain text

class JSONFormatter(logging.Formatter):
    """
    Custom log formatter that outputs JSON structured logs.

    Converts Python logging.LogRecord to JSON format with:
    - timestamp: ISO 8601 format
    - level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - service: Service name (producer or consumer)
    - message: Log message
    - correlation_id: Order ID for tracing (if provided)
    - extra fields: Any additional context passed to logger
    """

    def __init__(
        self,
        service_name: str = "kafka-pipeline",
        include_extra: bool = True
    ):
        """
        Initialize JSON formatter.

        Args:
            service_name: Name of the service (e.g., "order-producer")
            include_extra: Whether to include extra fields from log record
        """
        super().__init__()
        self.service_name = service_name
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON string.

        Args:
            record: Python logging.LogRecord object

        Returns:
            JSON string representation of log record
        """
        # Base log structure
        log_data: Dict[str, Any] = {
            "timestamp": self._format_timestamp(record.created),
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add correlation ID if present (order_id for tracing)
        if hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add extra fields (customer_id, latency, etc.)
        if self.include_extra:
            # Get all extra attributes not in standard LogRecord
            standard_attrs = {
                'name', 'msg', 'args', 'created', 'filename', 'funcName',
                'levelname', 'levelno', 'lineno', 'module', 'msecs',
                'message', 'pathname', 'process', 'processName', 'relativeCreated',
                'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info',
                'correlation_id'  # Already handled above
            }

            extra_fields = {
                k: v for k, v in record.__dict__.items()
                if k not in standard_attrs and not k.startswith('_')
            }

            if extra_fields:
                log_data['extra'] = extra_fields

        # Return JSON string (one line for easy parsing)
        return json.dumps(log_data, default=str)

    @staticmethod
    def _format_timestamp(created: float) -> str:
        """
        Format timestamp as ISO 8601 string.

        Args:
            created: Unix timestamp from log record

        Returns:
            ISO 8601 formatted timestamp (e.g., "2025-01-10T14:30:00.123Z")
        """
        dt = datetime.utcfromtimestamp(created)
        return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


# ==============================================================================
# PLAIN TEXT FORMATTER (for development)
# ==============================================================================
# Human-readable format for local development

class PlainTextFormatter(logging.Formatter):
    """
    Human-readable log formatter for local development.

    Format: [2025-01-10 14:30:00] INFO [order-consumer] Order processed successfully
    """

    def __init__(self, service_name: str = "kafka-pipeline"):
        """Initialize plain text formatter."""
        super().__init__(
            fmt=f'[%(asctime)s] %(levelname)s [{service_name}] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


# ==============================================================================
# LOGGER SETUP
# ==============================================================================

def setup_logger(
    name: str,
    service_name: str,
    log_level: str = "INFO",
    log_format: str = "json"
) -> logging.Logger:
    """
    Set up structured logger for Kafka services.

    This function creates a logger with:
    - Structured JSON output (or plain text for development)
    - Configurable log level
    - Console output (stdout)
    - Correlation ID support for request tracing

    Args:
        name: Logger name (usually __name__ of module)
        service_name: Service identifier (e.g., "order-producer", "order-consumer")
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ("json" or "text")

    Returns:
        Configured logging.Logger instance

    Example:
        >>> logger = setup_logger(
        ...     name=__name__,
        ...     service_name="order-producer",
        ...     log_level="INFO",
        ...     log_format="json"
        ... )
        >>> logger.info("Starting producer", extra={"order_rate": 10})
        {"timestamp": "2025-01-10T14:30:00Z", "level": "INFO", ...}

        >>> # With correlation ID (order tracking)
        >>> logger.info(
        ...     "Order published",
        ...     extra={
        ...         "correlation_id": "ORD-001",
        ...         "customer_id": "CUST-001",
        ...         "total": 21.47
        ...     }
        ... )
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Prevent duplicate handlers if logger already configured
    if logger.handlers:
        return logger

    # Create console handler (output to stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logger.level)

    # Choose formatter based on log_format
    if log_format.lower() == "json":
        formatter = JSONFormatter(service_name=service_name)
    else:
        formatter = PlainTextFormatter(service_name=service_name)

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# ==============================================================================
# CORRELATION ID ADAPTER
# ==============================================================================
# Helper to automatically include correlation_id in all log messages

class CorrelationAdapter(logging.LoggerAdapter):
    """
    Logger adapter that automatically adds correlation_id to all logs.

    Useful for tracking a specific order/request through the entire pipeline.

    Example:
        >>> base_logger = setup_logger(__name__, "order-consumer")
        >>> logger = CorrelationAdapter(base_logger, {"correlation_id": "ORD-001"})
        >>> logger.info("Processing order")  # correlation_id automatically included
    """

    def process(self, msg: str, kwargs: dict) -> tuple:
        """
        Add correlation_id to log record.

        Args:
            msg: Log message
            kwargs: Additional keyword arguments

        Returns:
            Tuple of (message, updated_kwargs)
        """
        # Get extra dict or create new one
        extra = kwargs.get('extra', {})

        # Add correlation_id from adapter context
        if 'correlation_id' in self.extra:
            extra['correlation_id'] = self.extra['correlation_id']

        kwargs['extra'] = extra
        return msg, kwargs


# ==============================================================================
# USAGE EXAMPLES
# ==============================================================================
"""
# Basic usage
logger = setup_logger(
    name=__name__,
    service_name="order-producer",
    log_level="INFO",
    log_format="json"
)

logger.info("Producer started", extra={"order_rate": 10})
# Output: {"timestamp": "2025-01-10T14:30:00Z", "level": "INFO", "service": "order-producer",
#          "message": "Producer started", "extra": {"order_rate": 10}}

# With correlation ID (for tracking specific orders)
logger.info(
    "Order published to Kafka",
    extra={
        "correlation_id": "ORD-20250110-00001",
        "customer_id": "CUST-00001",
        "partition": 2,
        "total_amount": 21.47
    }
)
# Output: {"timestamp": "...", "correlation_id": "ORD-20250110-00001",
#          "message": "Order published to Kafka", "extra": {"customer_id": "CUST-00001", ...}}

# Using CorrelationAdapter (automatically includes correlation_id)
base_logger = setup_logger(__name__, "order-consumer")
order_logger = CorrelationAdapter(base_logger, {"correlation_id": "ORD-001"})

order_logger.info("Validating order")  # correlation_id auto-included
order_logger.info("Writing to database")  # correlation_id auto-included

# Error logging with exception
try:
    process_order()
except Exception as e:
    logger.error("Order processing failed", exc_info=True, extra={"correlation_id": "ORD-001"})
    # Output includes full exception traceback in JSON

# Different log levels
logger.debug("Detailed debugging info", extra={"kafka_offset": 12345})
logger.info("Normal operation")
logger.warning("Potential issue detected", extra={"retry_count": 3})
logger.error("Operation failed", extra={"error_code": "DB_TIMEOUT"})
logger.critical("Service unavailable", extra={"uptime_seconds": 3600})
"""

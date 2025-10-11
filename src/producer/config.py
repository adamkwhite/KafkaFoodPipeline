"""
Producer Configuration Module

This module loads producer configuration from environment variables and provides
a structured configuration object using Pydantic for validation.

WHY ENVIRONMENT-BASED CONFIGURATION?
- Security: Keep secrets (credentials) out of code
- Flexibility: Different configs for local/dev/prod without code changes
- 12-Factor App: Configuration in environment (industry best practice)
- Docker-friendly: Easy to override via docker-compose or k8s

CONFIGURATION SOURCES (priority order):
1. Environment variables (highest priority)
2. .env file (loaded by python-dotenv)
3. Default values (fallback)

PYDANTIC VALIDATION:
- Type checking at runtime
- Automatic parsing (string → int, bool, etc.)
- Clear error messages for invalid config
- Documentation via Field descriptions
"""

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load .env file if present (local development)
# In production, use actual environment variables
load_dotenv()


class ProducerConfig(BaseSettings):
    """
    Producer service configuration with validation.

    This class loads configuration from environment variables and validates
    all settings using Pydantic. Invalid configuration will raise clear errors.

    Attributes:
        kafka_bootstrap_servers: Kafka broker addresses
        kafka_topic_orders: Topic name for orders
        producer_client_id: Producer identifier
        producer_rate: Orders per second to generate
        producer_duration: How long to run producer (seconds, 0=infinite)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_format: Log output format (json or text)

    Example:
        >>> config = ProducerConfig()
        >>> print(config.kafka_bootstrap_servers)
        'localhost:9092'
        >>> print(config.producer_rate)
        10
    """

    # === KAFKA CONNECTION ===
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Kafka broker addresses (comma-separated for multiple brokers)",
        json_schema_extra={
            "example": "kafka:9092",
            "production_example": "broker1:9092,broker2:9092,broker3:9092",
        },
    )

    kafka_topic_orders: str = Field(
        default="food-orders",
        description="Kafka topic for order messages",
        json_schema_extra={"example": "food-orders"},
    )

    # === PRODUCER SETTINGS ===
    producer_client_id: str = Field(
        default="order-producer",
        description="Producer client identifier (visible in broker logs and monitoring)",
        json_schema_extra={"example": "order-producer-instance-1"},
    )

    producer_rate: int = Field(
        default=10,
        ge=1,  # Greater than or equal to 1
        le=1000,  # Less than or equal to 1000
        description="Number of orders to generate per second (1-1000)",
        json_schema_extra={
            "example": 10,
            "note": "Start low (10) for testing, increase for load testing",
        },
    )

    producer_duration: int = Field(
        default=60,
        ge=0,
        description="Producer run duration in seconds (0 = run indefinitely)",
        json_schema_extra={"example": 60, "note": "0 for continuous production, >0 for batch runs"},
    )

    # === MOCK DATA SETTINGS ===
    mock_seed: int = Field(
        default=42,
        description="Random seed for reproducible mock data generation",
        json_schema_extra={
            "example": 42,
            "note": "Same seed = same customers and orders (useful for testing)",
        },
    )

    # === LOGGING CONFIGURATION ===
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        json_schema_extra={"example": "INFO"},
    )

    log_format: str = Field(
        default="json",
        description="Log output format (json for production, text for development)",
        json_schema_extra={"example": "json", "alternatives": ["json", "text"]},
    )

    # === PERFORMANCE TUNING (Advanced) ===
    producer_compression: str = Field(
        default="snappy",
        description="Compression algorithm (none, gzip, snappy, lz4, zstd)",
        json_schema_extra={
            "example": "snappy",
            "note": "snappy = good balance of speed and compression",
        },
    )

    producer_linger_ms: int = Field(
        default=10,
        ge=0,
        le=1000,
        description="Time to wait for batching messages (milliseconds)",
        json_schema_extra={
            "example": 10,
            "note": "0=send immediately (low latency), >0=batch for throughput",
        },
    )

    producer_batch_size: int = Field(
        default=16384,
        ge=1024,
        description="Maximum batch size in bytes",
        json_schema_extra={
            "example": 16384,
            "note": "16KB default, increase for higher throughput",
        },
    )

    producer_buffer_memory: int = Field(
        default=33554432,
        ge=1048576,  # Min 1MB
        description="Total memory for buffering pending messages (bytes)",
        json_schema_extra={
            "example": 33554432,
            "note": "32MB default, increase if getting BufferError",
        },
    )

    producer_acks: int = Field(
        default=1,
        ge=0,
        le=1,
        description="Acknowledgment level (0=none, 1=leader, -1/all=all replicas)",
        json_schema_extra={"example": 1, "note": "1 = good balance, 'all' for critical data"},
    )

    enable_idempotence: bool = Field(
        default=True,
        description="Enable idempotent producer (prevents duplicates)",
        json_schema_extra={
            "example": True,
            "note": "Recommended for production (exactly-once within partition)",
        },
    )

    class Config:
        """Pydantic configuration."""

        # Allow loading from .env file
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Make config case-insensitive
        case_sensitive = False
        # Allow extra fields (ignore unknown env vars)
        extra = "ignore"

    def get_kafka_config(self) -> dict:
        """
        Get Kafka producer configuration dictionary.

        Converts Pydantic model to dict suitable for confluent_kafka.Producer.

        Returns:
            Dictionary of Kafka producer configuration

        Example:
            >>> config = ProducerConfig()
            >>> kafka_conf = config.get_kafka_config()
            >>> producer = Producer(kafka_conf)
        """
        return {
            "bootstrap.servers": self.kafka_bootstrap_servers,
            "client.id": self.producer_client_id,
            "compression.type": self.producer_compression,
            "linger.ms": self.producer_linger_ms,
            "batch.size": self.producer_batch_size,
            "buffer.memory": self.producer_buffer_memory,
            "acks": self.producer_acks,
            "enable.idempotence": self.enable_idempotence,
        }

    def display_config(self) -> str:
        """
        Get human-readable configuration summary.

        Returns:
            Formatted configuration string

        Example:
            >>> config = ProducerConfig()
            >>> print(config.display_config())
        """
        return f"""
Order Producer Configuration
=============================
Kafka:
  Bootstrap Servers: {self.kafka_bootstrap_servers}
  Topic: {self.kafka_topic_orders}
  Client ID: {self.producer_client_id}

Producer Settings:
  Rate: {self.producer_rate} orders/second
  Duration: {self.producer_duration} seconds {'(infinite)' if self.producer_duration == 0 else ''}
  Compression: {self.producer_compression}
  Batch Size: {self.producer_batch_size} bytes
  Linger: {self.producer_linger_ms}ms
  Idempotence: {self.enable_idempotence}

Logging:
  Level: {self.log_level}
  Format: {self.log_format}

Mock Data:
  Seed: {self.mock_seed} (reproducible: {'Yes' if self.mock_seed else 'No'})
"""


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================


def load_config() -> ProducerConfig:
    """
    Load and validate producer configuration.

    This function:
    1. Loads environment variables (including .env file)
    2. Creates ProducerConfig instance
    3. Validates all settings
    4. Returns validated config

    Returns:
        Validated ProducerConfig instance

    Raises:
        ValidationError: If configuration is invalid

    Example:
        >>> config = load_config()
        >>> print(config.kafka_bootstrap_servers)
    """
    return ProducerConfig()


def validate_kafka_connection(config: ProducerConfig) -> bool:
    """
    Validate Kafka connection before starting producer.

    Tests connectivity to Kafka brokers by creating admin client.

    Args:
        config: Producer configuration

    Returns:
        True if connection successful, False otherwise

    Example:
        >>> config = load_config()
        >>> if validate_kafka_connection(config):
        ...     print("Kafka is reachable!")
    """
    from confluent_kafka.admin import AdminClient

    try:
        admin_client = AdminClient({"bootstrap.servers": config.kafka_bootstrap_servers})

        # List topics as connectivity test
        metadata = admin_client.list_topics(timeout=10)

        # Check if our topic exists (validate connection works)
        _ = config.kafka_topic_orders in metadata.topics

        return True

    except Exception as e:
        print(f"Kafka connection failed: {e}")
        return False


# ==============================================================================
# USAGE EXAMPLES
# ==============================================================================
"""
# Basic usage
from src.producer.config import load_config

config = load_config()
print(config.display_config())

# Access configuration
print(f"Producing to: {config.kafka_bootstrap_servers}")
print(f"Topic: {config.kafka_topic_orders}")
print(f"Rate: {config.producer_rate} orders/sec")

# Get Kafka producer config
kafka_conf = config.get_kafka_config()
producer = Producer(kafka_conf)

# Validate connection before starting
config = load_config()
if not validate_kafka_connection(config):
    print("ERROR: Cannot connect to Kafka")
    exit(1)

# Environment variable override (command line or .env)
# export KAFKA_BOOTSTRAP_SERVERS="kafka:9092"
# export PRODUCER_RATE=100
# python -m src.producer.main

# Programmatic override
import os
os.environ['PRODUCER_RATE'] = '50'
config = load_config()
print(config.producer_rate)  # 50

# Validation example (invalid value)
try:
    os.environ['PRODUCER_RATE'] = '2000'  # > 1000 (max)
    config = load_config()
except ValidationError as e:
    print(f"Invalid config: {e}")

# Docker Compose override
# docker-compose.yml:
#   environment:
#     - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
#     - PRODUCER_RATE=20
#     - LOG_FORMAT=json
"""

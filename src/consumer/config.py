"""
Consumer Configuration Module

Consumer-specific configuration for Kafka consumer and PostgreSQL database.
Loads settings from environment variables with Pydantic validation.
"""

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load .env file if present (local development)
load_dotenv()


class ConsumerConfig(BaseSettings):
    """
    Consumer service configuration with validation.

    Includes Kafka consumer settings and PostgreSQL database configuration.
    """

    # === KAFKA CONSUMER SETTINGS ===
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Kafka broker addresses",
    )

    kafka_topic_orders: str = Field(
        default="food-orders",
        description="Kafka topic to consume from",
    )

    consumer_group_id: str = Field(
        default="order-processors",
        description="Consumer group ID for load balancing",
    )

    consumer_client_id: str = Field(
        default="order-consumer",
        description="Consumer client identifier",
    )

    consumer_auto_offset_reset: str = Field(
        default="earliest",
        description="Where to start consuming: earliest or latest",
    )

    enable_auto_commit: bool = Field(
        default=False,
        description="Auto-commit offsets (False = manual commit)",
    )

    # === DATABASE SETTINGS ===
    postgres_host: str = Field(
        default="localhost",
        description="PostgreSQL host",
    )

    postgres_port: int = Field(
        default=5432,
        description="PostgreSQL port",
    )

    postgres_db: str = Field(
        default="food_orders",
        description="PostgreSQL database name",
    )

    postgres_user: str = Field(
        default="postgres",
        description="PostgreSQL username",
    )

    postgres_password: str = Field(
        default="postgres",
        description="PostgreSQL password",
    )

    db_pool_size: int = Field(
        default=5,
        ge=1,
        le=20,
        description="SQLAlchemy connection pool size",
    )

    # === PROCESSING SETTINGS ===
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Max retries for transient failures",
    )

    retry_backoff_ms: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Retry backoff in milliseconds",
    )

    # === LOGGING ===
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )

    log_format: str = Field(
        default="json",
        description="Log output format (json or text)",
    )

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

    def get_kafka_config(self) -> dict:
        """Get Kafka consumer configuration dictionary."""
        return {
            "bootstrap.servers": self.kafka_bootstrap_servers,
            "group.id": self.consumer_group_id,
            "client.id": self.consumer_client_id,
            "auto.offset.reset": self.consumer_auto_offset_reset,
            "enable.auto.commit": self.enable_auto_commit,
        }

    def get_database_url(self) -> str:
        """Get SQLAlchemy database URL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


def load_config() -> ConsumerConfig:
    """Load and validate consumer configuration."""
    return ConsumerConfig()

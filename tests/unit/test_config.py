"""
Unit Tests for Configuration Classes

Tests Pydantic configuration validation for both Producer and Consumer configs.
Ensures proper defaults, validation, and environment variable loading.

TEST STRATEGY:
- Test default values
- Test validation rules (constraints, types)
- Test environment variable loading
- Test invalid configurations (should raise ValidationError)
- Test helper methods (get_kafka_config, get_database_url)
"""

import pytest
from pydantic import ValidationError

from src.consumer.config import ConsumerConfig
from src.consumer.config import load_config as load_consumer_config
from src.producer.config import ProducerConfig
from src.producer.config import load_config as load_producer_config

# ==============================================================================
# PRODUCER CONFIG TESTS
# ==============================================================================


@pytest.mark.unit
def test_producer_config_defaults():
    """Test ProducerConfig default values."""
    config = ProducerConfig()

    # Kafka defaults
    assert config.kafka_bootstrap_servers == "localhost:9092"
    assert config.kafka_topic_orders == "food-orders"
    assert config.producer_client_id == "order-producer"

    # Producer settings defaults
    assert config.producer_rate == 10
    assert config.producer_duration == 60
    assert config.producer_compression == "snappy"

    # Mock data defaults
    assert config.mock_seed == 42

    # Logging defaults
    assert config.log_level == "INFO"
    assert config.log_format == "json"


@pytest.mark.unit
def test_producer_config_custom_values():
    """Test ProducerConfig with custom values."""
    config = ProducerConfig(
        kafka_bootstrap_servers="kafka:29092",
        kafka_topic_orders="test-orders",
        producer_client_id="test-producer",
        producer_rate=100,
        producer_duration=30,
        mock_seed=999,
        log_level="DEBUG",
    )

    assert config.kafka_bootstrap_servers == "kafka:29092"
    assert config.kafka_topic_orders == "test-orders"
    assert config.producer_client_id == "test-producer"
    assert config.producer_rate == 100
    assert config.producer_duration == 30
    assert config.mock_seed == 999
    assert config.log_level == "DEBUG"


@pytest.mark.unit
def test_producer_config_validation_rate_positive():
    """Test that producer_rate must be positive."""
    with pytest.raises(ValidationError) as exc_info:
        ProducerConfig(producer_rate=0)

    assert "producer_rate" in str(exc_info.value)


@pytest.mark.unit
def test_producer_config_validation_rate_max():
    """Test that producer_rate has maximum limit."""
    with pytest.raises(ValidationError) as exc_info:
        ProducerConfig(producer_rate=10000)

    assert "producer_rate" in str(exc_info.value)


@pytest.mark.unit
def test_producer_config_validation_duration_non_negative():
    """Test that producer_duration can be 0 or positive."""
    # 0 should be valid (infinite)
    config = ProducerConfig(producer_duration=0)
    assert config.producer_duration == 0

    # Positive should be valid
    config = ProducerConfig(producer_duration=60)
    assert config.producer_duration == 60

    # Negative should fail
    with pytest.raises(ValidationError):
        ProducerConfig(producer_duration=-1)


@pytest.mark.unit
def test_producer_config_get_kafka_config():
    """Test get_kafka_config() helper method."""
    config = ProducerConfig(
        kafka_bootstrap_servers="localhost:9092", producer_client_id="test-producer"
    )

    kafka_config = config.get_kafka_config()

    assert "bootstrap.servers" in kafka_config
    assert kafka_config["bootstrap.servers"] == "localhost:9092"
    assert "client.id" in kafka_config
    assert kafka_config["client.id"] == "test-producer"


@pytest.mark.unit
def test_producer_config_from_env(monkeypatch):
    """Test loading ProducerConfig from environment variables."""
    # Set environment variables
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
    monkeypatch.setenv("KAFKA_TOPIC_ORDERS", "env-orders")
    monkeypatch.setenv("PRODUCER_RATE", "50")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    config = load_producer_config()

    assert config.kafka_bootstrap_servers == "kafka:29092"
    assert config.kafka_topic_orders == "env-orders"
    assert config.producer_rate == 50
    assert config.log_level == "DEBUG"


# ==============================================================================
# CONSUMER CONFIG TESTS
# ==============================================================================


@pytest.mark.unit
def test_consumer_config_defaults():
    """Test ConsumerConfig default values."""
    config = ConsumerConfig()

    # Kafka defaults
    assert config.kafka_bootstrap_servers == "localhost:9092"
    assert config.kafka_topic_orders == "food-orders"
    assert config.consumer_group_id == "order-processors"
    assert config.consumer_client_id == "order-consumer"
    assert config.consumer_auto_offset_reset == "earliest"
    assert config.enable_auto_commit is False

    # PostgreSQL defaults
    assert config.postgres_host == "localhost"
    assert config.postgres_port == 5432
    assert config.postgres_db == "food_orders"
    assert config.postgres_user == "postgres"
    # password should have default but not assert it (sensitive)

    # Processing defaults
    assert config.max_retries == 3
    assert config.retry_backoff_ms == 1000
    assert config.db_pool_size == 5

    # Logging defaults
    assert config.log_level == "INFO"
    assert config.log_format == "json"


@pytest.mark.unit
def test_consumer_config_custom_values():
    """Test ConsumerConfig with custom values."""
    config = ConsumerConfig(
        kafka_bootstrap_servers="kafka:29092",
        consumer_group_id="test-group",
        postgres_host="db.example.com",
        postgres_port=5433,
        postgres_db="test_db",
        postgres_user="test_user",
        postgres_password="test_pass",
        max_retries=5,
        db_pool_size=10,
        log_level="DEBUG",
    )

    assert config.kafka_bootstrap_servers == "kafka:29092"
    assert config.consumer_group_id == "test-group"
    assert config.postgres_host == "db.example.com"
    assert config.postgres_port == 5433
    assert config.postgres_db == "test_db"
    assert config.postgres_user == "test_user"
    assert config.postgres_password == "test_pass"
    assert config.max_retries == 5
    assert config.db_pool_size == 10
    assert config.log_level == "DEBUG"


@pytest.mark.unit
def test_consumer_config_validation_port_range():
    """Test that postgres_port must be in valid range."""
    # Valid port
    config = ConsumerConfig(postgres_port=5432)
    assert config.postgres_port == 5432

    # Invalid port (too low)
    with pytest.raises(ValidationError):
        ConsumerConfig(postgres_port=0)

    # Invalid port (too high)
    with pytest.raises(ValidationError):
        ConsumerConfig(postgres_port=70000)


@pytest.mark.unit
def test_consumer_config_validation_max_retries():
    """Test that max_retries has valid range."""
    # Valid retries
    config = ConsumerConfig(max_retries=3)
    assert config.max_retries == 3

    # Min retries
    config = ConsumerConfig(max_retries=1)
    assert config.max_retries == 1

    # Invalid (too low)
    with pytest.raises(ValidationError):
        ConsumerConfig(max_retries=0)

    # Invalid (too high)
    with pytest.raises(ValidationError):
        ConsumerConfig(max_retries=100)


@pytest.mark.unit
def test_consumer_config_validation_db_pool_size():
    """Test that db_pool_size has valid range."""
    # Valid pool size
    config = ConsumerConfig(db_pool_size=5)
    assert config.db_pool_size == 5

    # Min pool size
    config = ConsumerConfig(db_pool_size=1)
    assert config.db_pool_size == 1

    # Max pool size
    config = ConsumerConfig(db_pool_size=20)
    assert config.db_pool_size == 20

    # Invalid (too low)
    with pytest.raises(ValidationError):
        ConsumerConfig(db_pool_size=0)

    # Invalid (too high)
    with pytest.raises(ValidationError):
        ConsumerConfig(db_pool_size=100)


@pytest.mark.unit
def test_consumer_config_get_kafka_config():
    """Test get_kafka_config() helper method."""
    config = ConsumerConfig(
        kafka_bootstrap_servers="localhost:9092",
        consumer_group_id="test-group",
        consumer_client_id="test-consumer",
    )

    kafka_config = config.get_kafka_config()

    assert "bootstrap.servers" in kafka_config
    assert kafka_config["bootstrap.servers"] == "localhost:9092"
    assert "group.id" in kafka_config
    assert kafka_config["group.id"] == "test-group"
    assert "client.id" in kafka_config
    assert kafka_config["client.id"] == "test-consumer"
    assert "enable.auto.commit" in kafka_config
    assert kafka_config["enable.auto.commit"] is False


@pytest.mark.unit
def test_consumer_config_get_database_url():
    """Test get_database_url() helper method."""
    config = ConsumerConfig(
        postgres_host="db.example.com",
        postgres_port=5432,
        postgres_user="testuser",
        postgres_password="testpass",
        postgres_db="testdb",
    )

    db_url = config.get_database_url()

    # Should be valid PostgreSQL URL
    assert db_url.startswith("postgresql://")
    assert "testuser" in db_url
    assert "testpass" in db_url
    assert "db.example.com" in db_url
    assert "5432" in db_url
    assert "testdb" in db_url


@pytest.mark.unit
def test_consumer_config_from_env(monkeypatch):
    """Test loading ConsumerConfig from environment variables."""
    # Set environment variables
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
    monkeypatch.setenv("CONSUMER_GROUP_ID", "env-group")
    monkeypatch.setenv("POSTGRES_HOST", "env-db")
    monkeypatch.setenv("POSTGRES_PORT", "5433")
    monkeypatch.setenv("POSTGRES_DB", "env_db")
    monkeypatch.setenv("MAX_RETRIES", "5")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    config = load_consumer_config()

    assert config.kafka_bootstrap_servers == "kafka:29092"
    assert config.consumer_group_id == "env-group"
    assert config.postgres_host == "env-db"
    assert config.postgres_port == 5433
    assert config.postgres_db == "env_db"
    assert config.max_retries == 5
    assert config.log_level == "DEBUG"


# ==============================================================================
# LOG LEVEL VALIDATION TESTS
# ==============================================================================


@pytest.mark.unit
@pytest.mark.parametrize("log_level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
def test_valid_log_levels(log_level):
    """Test that all standard log levels are valid."""
    # Producer
    producer_config = ProducerConfig(log_level=log_level)
    assert producer_config.log_level == log_level

    # Consumer
    consumer_config = ConsumerConfig(log_level=log_level)
    assert consumer_config.log_level == log_level


@pytest.mark.unit
@pytest.mark.parametrize("log_format", ["json", "text"])
def test_valid_log_formats(log_format):
    """Test that both log formats are valid."""
    # Producer
    producer_config = ProducerConfig(log_format=log_format)
    assert producer_config.log_format == log_format

    # Consumer
    consumer_config = ConsumerConfig(log_format=log_format)
    assert consumer_config.log_format == log_format


# ==============================================================================
# AUTO OFFSET RESET VALIDATION
# ==============================================================================


@pytest.mark.unit
@pytest.mark.parametrize("offset_reset", ["earliest", "latest"])
def test_valid_offset_reset_values(offset_reset):
    """Test that valid offset reset strategies are accepted."""
    config = ConsumerConfig(consumer_auto_offset_reset=offset_reset)
    assert config.consumer_auto_offset_reset == offset_reset


# ==============================================================================
# COMPRESSION TYPE VALIDATION
# ==============================================================================


@pytest.mark.unit
@pytest.mark.parametrize("compression", ["none", "gzip", "snappy", "lz4", "zstd"])
def test_valid_compression_types(compression):
    """Test that all valid compression types are accepted."""
    config = ProducerConfig(producer_compression=compression)
    assert config.producer_compression == compression


# ==============================================================================
# CONFIG IMMUTABILITY TESTS (Pydantic frozen)
# ==============================================================================


@pytest.mark.unit
def test_producer_config_immutable():
    """Test that ProducerConfig is immutable (if frozen=True)."""
    config = ProducerConfig()

    # This test will only pass if Config.frozen = True in the model
    # For now, just test that we can't accidentally modify protected fields
    with pytest.raises((ValidationError, AttributeError)):
        config.kafka_bootstrap_servers = "modified"


@pytest.mark.unit
def test_consumer_config_immutable():
    """Test that ConsumerConfig is immutable (if frozen=True)."""
    config = ConsumerConfig()

    # This test will only pass if Config.frozen = True in the model
    with pytest.raises((ValidationError, AttributeError)):
        config.postgres_password = "modified"

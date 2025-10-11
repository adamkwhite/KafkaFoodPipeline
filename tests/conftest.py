"""
Pytest Configuration and Shared Fixtures

This module provides shared pytest fixtures for testing the Kafka Food Pipeline.
It uses testcontainers to spin up real Kafka and PostgreSQL instances for integration tests.

TESTCONTAINERS PATTERN:
- Spin up real services (Kafka, PostgreSQL) in Docker containers
- Run tests against real infrastructure (not mocks)
- Automatically clean up containers after tests
- Provides production-like test environment

FIXTURE SCOPES:
- session: Created once for entire test session (fastest, shared state)
- module: Created once per test module (shared within file)
- function: Created for each test function (slowest, isolated)
"""

import os
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.kafka import KafkaContainer
from testcontainers.postgres import PostgresContainer

from src.consumer.config import ConsumerConfig
from src.consumer.models import Base
from src.producer.config import ProducerConfig

# ==============================================================================
# POSTGRESQL FIXTURES
# ==============================================================================


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    """
    Provides PostgreSQL testcontainer for the entire test session.

    Scope: session (started once, shared across all tests)

    Yields:
        PostgresContainer instance with running PostgreSQL

    Usage:
        def test_something(postgres_container):
            db_url = postgres_container.get_connection_url()
    """
    with PostgresContainer("postgres:15") as postgres:
        # Wait for PostgreSQL to be ready
        postgres.get_connection_url()
        yield postgres


@pytest.fixture(scope="function")
def db_session(postgres_container):
    """
    Provides clean database session for each test function.

    Scope: function (fresh database for each test)

    - Creates all tables before test
    - Drops all tables after test
    - Ensures test isolation

    Yields:
        SQLAlchemy session
    """
    # Get connection URL from container
    db_url = postgres_container.get_connection_url()

    # Create engine and tables
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    # Create session
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Clean up tables for next test
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture(scope="function")
def consumer_config(postgres_container, kafka_container):
    """
    Provides ConsumerConfig pointing to test containers.

    Scope: function (new config for each test)

    Returns:
        ConsumerConfig with test container connection details
    """
    # Get Kafka bootstrap servers
    kafka_host = kafka_container.get_bootstrap_server()

    # Override environment variables for test
    os.environ["KAFKA_BOOTSTRAP_SERVERS"] = kafka_host
    os.environ["POSTGRES_HOST"] = postgres_container.get_container_host_ip()
    os.environ["POSTGRES_PORT"] = postgres_container.get_exposed_port(5432)
    os.environ["POSTGRES_USER"] = postgres_container.POSTGRES_USER
    os.environ["POSTGRES_PASSWORD"] = postgres_container.POSTGRES_PASSWORD
    os.environ["POSTGRES_DB"] = postgres_container.POSTGRES_DB

    return ConsumerConfig(
        kafka_bootstrap_servers=kafka_host,
        kafka_topic_orders="test-orders",
        consumer_group_id="test-consumer-group",
        postgres_host=postgres_container.get_container_host_ip(),
        postgres_port=int(postgres_container.get_exposed_port(5432)),
        postgres_user=postgres_container.POSTGRES_USER,
        postgres_password=postgres_container.POSTGRES_PASSWORD,
        postgres_db=postgres_container.POSTGRES_DB,
    )


# ==============================================================================
# KAFKA FIXTURES
# ==============================================================================


@pytest.fixture(scope="session")
def kafka_container() -> Generator[KafkaContainer, None, None]:
    """
    Provides Kafka testcontainer for the entire test session.

    Scope: session (started once, shared across all tests)

    Yields:
        KafkaContainer instance with running Kafka broker

    Usage:
        def test_kafka(kafka_container):
            bootstrap_servers = kafka_container.get_bootstrap_server()
    """
    with KafkaContainer() as kafka:
        # Wait for Kafka to be ready
        kafka.get_bootstrap_server()
        yield kafka


@pytest.fixture(scope="function")
def producer_config(kafka_container):
    """
    Provides ProducerConfig pointing to test Kafka container.

    Scope: function (new config for each test)

    Returns:
        ProducerConfig with test Kafka connection details
    """
    kafka_host = kafka_container.get_bootstrap_server()

    return ProducerConfig(
        kafka_bootstrap_servers=kafka_host,
        kafka_topic_orders="test-orders",
        producer_client_id="test-producer",
        producer_rate=10,
        producer_duration=5,  # Short duration for tests
        mock_seed=42,  # Reproducible test data
    )


# ==============================================================================
# MOCK DATA FIXTURES
# ==============================================================================


@pytest.fixture
def sample_order_data():
    """
    Provides sample order data for testing.

    Returns:
        Dictionary representing a valid order message
    """
    return {
        "order_id": "ORD-20250110-00001",
        "customer_id": "CUST-00001",
        "customer_name": "John Doe",
        "customer_email": "john.doe@example.com",
        "items": [
            {
                "item_id": "ITEM-001",
                "name": "Burger",
                "quantity": 2,
                "price": 8.99,
                "subtotal": 17.98,
            },
            {
                "item_id": "ITEM-002",
                "name": "Fries",
                "quantity": 1,
                "price": 3.49,
                "subtotal": 3.49,
            },
        ],
        "total_amount": 21.47,
        "status": "pending",
        "created_at": "2025-01-10T14:30:00+00:00",
    }


@pytest.fixture
def sample_invalid_order_data():
    """
    Provides invalid order data for negative testing.

    Returns:
        Dictionary with missing required fields
    """
    return {
        "order_id": "ORD-20250110-00001",
        # Missing customer_id, customer_name, customer_email
        "items": [],  # Empty items (invalid)
        "total_amount": -10.00,  # Negative amount (invalid)
        "status": "pending",
        "created_at": "2025-01-10T14:30:00+00:00",
    }


# ==============================================================================
# TEST ENVIRONMENT CONFIGURATION
# ==============================================================================


def pytest_configure(config):
    """
    Pytest hook called during test configuration.

    Sets up test environment variables and markers.
    """
    # Set test environment
    os.environ["ENVIRONMENT"] = "test"
    os.environ["LOG_LEVEL"] = "DEBUG"

    # Register custom markers
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires containers)"
    )
    config.addinivalue_line("markers", "slow: mark test as slow (takes more than 5 seconds)")
    config.addinivalue_line("markers", "unit: mark test as unit test (no external dependencies)")


# ==============================================================================
# USAGE EXAMPLES
# ==============================================================================
"""
# Unit test (no fixtures needed)
@pytest.mark.unit
def test_config_validation():
    config = ConsumerConfig(kafka_bootstrap_servers="localhost:9092")
    assert config.kafka_bootstrap_servers == "localhost:9092"

# Integration test with database
@pytest.mark.integration
def test_save_order(db_session, sample_order_data):
    from src.consumer.models import Order

    order = Order.from_kafka_message(sample_order_data)
    db_session.add(order)
    db_session.commit()

    # Verify order was saved
    saved_order = db_session.query(Order).filter_by(
        order_id=sample_order_data["order_id"]
    ).first()
    assert saved_order is not None
    assert saved_order.customer_id == sample_order_data["customer_id"]

# Integration test with Kafka
@pytest.mark.integration
def test_produce_message(producer_config, kafka_container):
    from confluent_kafka import Producer

    producer = Producer({"bootstrap.servers": producer_config.kafka_bootstrap_servers})
    producer.produce("test-topic", value=b"test message")
    producer.flush()

    # Verify message was produced (would need consumer to verify fully)

# End-to-end test with both Kafka and PostgreSQL
@pytest.mark.integration
@pytest.mark.slow
def test_full_pipeline(kafka_container, postgres_container, consumer_config):
    # This would test producer → Kafka → consumer → database
    pass
"""

"""
Database Connection and Session Management

This module provides SQLAlchemy database connection with connection pooling,
session management, and transaction handling for the order consumer service.

WHY SQLALCHEMY?
- ORM: Object-Relational Mapping (Python objects ↔ database tables)
- Type safety: Pydantic models + SQLAlchemy ORM = compile-time validation
- Connection pooling: Reuse connections instead of creating new ones
- Transaction management: ACID guarantees for data integrity
- Database agnostic: Switch PostgreSQL → MySQL with minimal changes

CONNECTION POOLING:
- Pool size: 5 connections (configurable)
- Max overflow: 10 additional connections under load
- Recycle time: 3600s (1 hour) to prevent stale connections
- Pre-ping: Test connection health before use

TRANSACTION PATTERN:
1. Get session from pool
2. Begin transaction (implicit)
3. Perform database operations
4. Commit on success
5. Rollback on error
6. Return connection to pool

WHY CONNECTION POOLING?
- Performance: Avoid connection overhead (handshake, authentication)
- Resource efficiency: Limit total database connections
- Fault tolerance: Automatic reconnection on connection loss
- Scalability: Handle concurrent requests efficiently
"""

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from src.consumer.config import ConsumerConfig

# ==============================================================================
# DATABASE ENGINE SETUP
# ==============================================================================


class DatabaseManager:
    """
    Manages SQLAlchemy database connections with pooling.

    This class provides:
    - Connection pooling for performance
    - Session management with context managers
    - Health checks for connection validation
    - Automatic reconnection on failures

    Attributes:
        engine: SQLAlchemy engine with connection pool
        SessionLocal: Session factory for creating database sessions
    """

    def __init__(self, config: ConsumerConfig):
        """
        Initialize database manager with connection pooling.

        Args:
            config: Consumer configuration with database settings

        CONNECTION POOL SETTINGS:
        - pool_size: Number of persistent connections (default: 5)
        - max_overflow: Extra connections under load (default: 10)
        - pool_recycle: Recycle connections after N seconds (default: 3600)
        - pool_pre_ping: Test connection before use (default: True)

        POOL SIZING GUIDE:
        - Small apps: pool_size=5, max_overflow=10 (our case)
        - Medium apps: pool_size=20, max_overflow=20
        - Large apps: pool_size=50, max_overflow=50
        - Formula: pool_size = (concurrent_workers * 2) + overflow_buffer
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Get database URL from config
        database_url = config.get_database_url()

        # Create SQLAlchemy engine with connection pooling
        self.engine = self._create_engine(database_url)

        # Create session factory (not a session itself!)
        # This is a factory that creates new sessions when called
        self.SessionLocal = sessionmaker(
            autocommit=False,  # Manual transaction control
            autoflush=False,  # Manual flush control
            bind=self.engine,
        )

        self.logger.info(
            "Database manager initialized",
            extra={
                "database_url": self._mask_password(database_url),
                "pool_size": config.db_pool_size,
                "pool_class": "QueuePool",
            },
        )

    def _create_engine(self, database_url: str) -> Engine:
        """
        Create SQLAlchemy engine with optimized connection pooling.

        Args:
            database_url: PostgreSQL connection string

        Returns:
            SQLAlchemy engine with connection pool

        POOL CONFIGURATION:
        - QueuePool: Default pool (best for most use cases)
        - pool_size: Persistent connections (config.db_pool_size)
        - max_overflow: Temporary connections under load
        - pool_recycle: Prevent stale connections (1 hour)
        - pool_pre_ping: Validate connection before use

        ALTERNATIVE POOLS:
        - NullPool: No pooling (testing only)
        - StaticPool: Single connection (SQLite)
        - QueuePool: Production (PostgreSQL, MySQL)
        """
        return create_engine(
            database_url,
            poolclass=QueuePool,  # Connection pool implementation
            pool_size=self.config.db_pool_size,  # Persistent connections
            max_overflow=10,  # Additional connections under load
            pool_recycle=3600,  # Recycle connections after 1 hour
            pool_pre_ping=True,  # Test connection health before use
            echo=False,  # Don't log SQL statements (use logger instead)
            future=True,  # Use SQLAlchemy 2.0 style
        )

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions with automatic cleanup.

        Yields:
            SQLAlchemy session

        Usage:
            >>> db_manager = DatabaseManager(config)
            >>> with db_manager.get_session() as session:
            ...     order = session.query(Order).filter_by(order_id="ORD-001").first()
            ...     session.commit()
            # Session automatically closed here

        TRANSACTION LIFECYCLE:
        1. Create session from pool
        2. Begin transaction (implicit)
        3. Yield session to caller
        4. Commit on success
        5. Rollback on exception
        6. Close session (return to pool)

        ERROR HANDLING:
        - Database errors → rollback transaction
        - Connection errors → session closed, connection returned to pool
        - Validation errors → rollback transaction
        """
        session = self.SessionLocal()
        try:
            yield session
            # If we get here without exception, commit the transaction
            session.commit()
        except SQLAlchemyError as e:
            # Database error (integrity constraint, connection lost, etc.)
            session.rollback()
            self.logger.error(
                "Database error, transaction rolled back",
                exc_info=True,
                extra={"error_type": type(e).__name__},
            )
            raise
        except Exception as e:
            # Application error (validation, business logic, etc.)
            session.rollback()
            self.logger.error(
                "Application error, transaction rolled back",
                exc_info=True,
                extra={"error_type": type(e).__name__},
            )
            raise
        finally:
            # Always close session (returns connection to pool)
            session.close()

    def check_health(self) -> bool:
        """
        Check database connection health.

        Returns:
            True if database is accessible, False otherwise

        Usage:
            >>> db_manager = DatabaseManager(config)
            >>> if db_manager.check_health():
            ...     print("Database healthy")
            ... else:
            ...     print("Database unavailable")

        HEALTH CHECK QUERY:
        - Simple SELECT 1 query
        - Fast (no table access)
        - Tests connection + authentication
        """
        try:
            with self.engine.connect() as conn:
                # Simple query to test connection
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
                self.logger.debug("Database health check passed")
                return True
        except OperationalError as e:
            self.logger.error(
                "Database health check failed",
                exc_info=True,
                extra={"error": str(e)},
            )
            return False

    def close(self) -> None:
        """
        Close all database connections in pool.

        Call this on application shutdown to gracefully close connections.

        Usage:
            >>> db_manager = DatabaseManager(config)
            >>> # ... use database ...
            >>> db_manager.close()  # Shutdown cleanup
        """
        self.logger.info("Closing database connection pool")
        self.engine.dispose()

    @staticmethod
    def _mask_password(database_url: str) -> str:
        """
        Mask password in database URL for logging.

        Args:
            database_url: Full database URL with password

        Returns:
            URL with password replaced by asterisks

        Example:
            >>> url = "postgresql://user:secret@localhost:5432/db"
            >>> DatabaseManager._mask_password(url)
            'postgresql://user:***@localhost:5432/db'
        """
        if "@" not in database_url:
            return database_url

        try:
            # Split on @ to separate credentials from host
            credentials, host_part = database_url.rsplit("@", 1)

            # Split credentials on : to separate user from password
            if ":" in credentials:
                protocol_user, _ = credentials.rsplit(":", 1)
                return f"{protocol_user}:***@{host_part}"

            return database_url
        except ValueError:
            # Couldn't parse URL, return as-is (better than crashing)
            return database_url


# ==============================================================================
# DATABASE INITIALIZATION
# ==============================================================================


def init_database(config: ConsumerConfig) -> DatabaseManager:
    """
    Initialize database manager and verify connection.

    Args:
        config: Consumer configuration

    Returns:
        DatabaseManager instance

    Raises:
        RuntimeError: If database connection fails

    Usage:
        >>> config = load_config()
        >>> db_manager = init_database(config)
        >>> with db_manager.get_session() as session:
        ...     # Use session...
    """
    logger = logging.getLogger(__name__)

    logger.info("Initializing database connection...")

    # Create database manager
    db_manager = DatabaseManager(config)

    # Verify connection health
    if not db_manager.check_health():
        raise RuntimeError(
            f"Failed to connect to database at {config.postgres_host}:{config.postgres_port}"
        )

    logger.info(
        "Database connection successful",
        extra={
            "host": config.postgres_host,
            "port": config.postgres_port,
            "database": config.postgres_db,
        },
    )

    return db_manager


# ==============================================================================
# SQLALCHEMY EVENT LISTENERS (for debugging/monitoring)
# ==============================================================================


@event.listens_for(Engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """
    Event listener for new database connections.

    This is called whenever SQLAlchemy creates a new connection to the database.
    Useful for:
    - Logging connection events
    - Setting connection-level parameters
    - Monitoring connection pool usage

    Args:
        dbapi_conn: DBAPI connection object
        connection_record: Connection record from pool
    """
    logger = logging.getLogger(__name__)
    logger.debug("New database connection established")


@event.listens_for(Engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """
    Event listener for connection checkout from pool.

    This is called whenever a connection is retrieved from the pool.
    Useful for:
    - Monitoring pool utilization
    - Detecting pool exhaustion
    - Performance profiling

    Args:
        dbapi_conn: DBAPI connection object
        connection_record: Connection record from pool
        connection_proxy: Connection proxy
    """
    logger = logging.getLogger(__name__)
    logger.debug("Connection checked out from pool")


@event.listens_for(Engine, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """
    Event listener for connection return to pool.

    This is called whenever a connection is returned to the pool.
    Useful for:
    - Verifying connection cleanup
    - Monitoring connection lifecycle
    - Detecting connection leaks

    Args:
        dbapi_conn: DBAPI connection object
        connection_record: Connection record from pool
    """
    logger = logging.getLogger(__name__)
    logger.debug("Connection returned to pool")


# ==============================================================================
# USAGE EXAMPLES
# ==============================================================================
"""
# Basic usage
from src.consumer.config import load_config
from src.consumer.database import init_database

config = load_config()
db_manager = init_database(config)

# Using context manager (recommended)
with db_manager.get_session() as session:
    # Query orders
    orders = session.query(Order).filter_by(status="pending").all()

    # Insert new order
    new_order = Order(
        order_id="ORD-001",
        customer_id="CUST-001",
        items=[...],
        total_amount=21.47,
        status="pending"
    )
    session.add(new_order)
    # Automatically committed on exit

# Health check
if db_manager.check_health():
    print("Database healthy")

# Shutdown
db_manager.close()

# Manual transaction control
session = db_manager.SessionLocal()
try:
    # Multiple operations in single transaction
    order1 = session.query(Order).get("ORD-001")
    order1.status = "processing"

    order2 = session.query(Order).get("ORD-002")
    order2.status = "processing"

    session.commit()
except Exception as e:
    session.rollback()
    raise
finally:
    session.close()

# Error handling with retry
from time import sleep

def save_order_with_retry(order_data, max_retries=3):
    for attempt in range(max_retries):
        try:
            with db_manager.get_session() as session:
                order = Order(**order_data)
                session.add(order)
                # Auto-commit on exit
                return True
        except OperationalError as e:
            # Transient database error (connection lost, etc.)
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"Database error, retrying in {wait_time}s...")
                sleep(wait_time)
            else:
                logger.error("Max retries reached, giving up")
                raise
        except IntegrityError as e:
            # Permanent error (duplicate key, constraint violation)
            logger.error("Integrity error, cannot retry")
            raise

# Connection pool monitoring
pool = db_manager.engine.pool
logger.info(f"Pool size: {pool.size()}")
logger.info(f"Checked out: {pool.checkedout()}")
logger.info(f"Overflow: {pool.overflow()}")
"""

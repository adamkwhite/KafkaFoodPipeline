# Kafka Food Processing Pipeline - Implementation Tasks

**PRD:** [prd.md](prd.md)
**Status:** PLANNED - Ready for implementation

## Relevant Files

### Infrastructure & Configuration
- `docker-compose.yml` - ✅ Docker Compose configuration with extensive Kafka learning notes (Zookeeper, Kafka broker, PostgreSQL)
- `docker-compose.aws.yml` - AWS-optimized Docker Compose with memory limits for t2.small
- `.env.example` - ✅ Environment variable template with Kafka/DB configuration and learning notes
- `.env` - ✅ Local environment config (copied from .env.example, excluded from git)
- `.gitignore` - ✅ Comprehensive Python/Docker/Kafka ignore rules (secrets, venv, cache, logs)
- `requirements.txt` - ✅ Production dependencies with educational comments (confluent-kafka, sqlalchemy, psycopg2-binary, pydantic, python-dotenv)
- `requirements-dev.txt` - ✅ Development dependencies with explanations (pytest, testcontainers, pytest-cov, black, ruff, mypy)
- `kafka-venv/` - ✅ Python virtual environment (excluded from git)

### Shared Utilities
- `src/shared/__init__.py` - ✅ Shared utilities package
- `src/shared/logger.py` - ✅ Structured JSON logging (JSONFormatter, CorrelationAdapter, setup_logger)

### Source Code - Producer
- `src/producer/main.py` - Entry point for producer service
- `src/producer/kafka_producer.py` - Kafka producer implementation with error handling
- `src/producer/data_generator.py` - Mock data generation (customers, menu items, orders)
- `src/producer/models.py` - Pydantic models for order validation
- `src/producer/config.py` - Configuration loading from environment variables
- `src/producer/Dockerfile` - Container image for producer service

### Source Code - Consumer
- `src/consumer/main.py` - Entry point for consumer service
- `src/consumer/kafka_consumer.py` - Kafka consumer implementation with consumer group
- `src/consumer/order_processor.py` - Order validation and processing logic
- `src/consumer/database.py` - SQLAlchemy database connection and operations
- `src/consumer/models.py` - ✅ SQLAlchemy ORM model with educational comments (Order class, JSONB support, indexes)
- `src/consumer/config.py` - Configuration loading from environment variables
- `src/consumer/Dockerfile` - Container image for consumer service

### Database
- `src/database/init.sql` - ✅ Database initialization script with extensive comments (orders table, indexes, sample queries)
- `src/database/migrations/001_create_orders_table.sql` - ✅ Migration file for orders table creation (forward + rollback)

### Tests - Unit
- `tests/unit/test_producer_data_generator.py` - Unit tests for mock data generation
- `tests/unit/test_producer_kafka.py` - Unit tests for producer logic
- `tests/unit/test_consumer_validation.py` - Unit tests for order validation
- `tests/unit/test_consumer_processor.py` - Unit tests for order processing
- `tests/unit/test_models.py` - Unit tests for Pydantic and SQLAlchemy models

### Tests - Integration
- `tests/integration/test_kafka_integration.py` - Kafka producer/consumer integration tests with testcontainers
- `tests/integration/test_database_integration.py` - PostgreSQL integration tests with testcontainers
- `tests/integration/test_e2e.py` - End-to-end test (produce → consume → verify in DB)
- `tests/conftest.py` - Pytest fixtures for test containers and shared setup

### Tests - Configuration
- `pytest.ini` - Pytest configuration (test discovery, coverage settings)
- `.coveragerc` - Coverage configuration (minimum 80%)

### Deployment & Scripts
- `scripts/init-kafka-topics.sh` - ✅ Initialize Kafka topics with partition and retention configuration
- `scripts/setup_local.sh` - Local development setup script
- `scripts/deploy_aws.sh` - AWS deployment helper script
- `scripts/healthcheck.sh` - Health check script for services
- `docs/deployment/aws-setup.md` - AWS deployment guide
- `docs/deployment/troubleshooting.md` - Common issues and solutions

### Learning Documentation
- `docs/KeyPoints/README.md` - ✅ Index of all learning documentation
- `docs/KeyPoints/infrastructure.md` - ✅ Kafka infrastructure concepts (Zookeeper, brokers, topics, partitions, offsets, retention, bootstrap servers)

### Notes
- Unit tests should be placed in `tests/unit/` directory, separate from code
- Integration tests in `tests/integration/` use testcontainers
- Run tests with `pytest` (all tests) or `pytest tests/unit/` (unit only)
- Check coverage with `pytest --cov=src --cov-report=term-missing`
- Python virtual environment recommended: `python3 -m venv kafka-venv`

## Tasks

- [x] 1.0 **Project Infrastructure Setup**
  - [x] 1.1 Create project directory structure (`src/`, `tests/`, `scripts/`, `docs/deployment/`)
  - [x] 1.2 Initialize Python virtual environment and create `requirements.txt` with all dependencies
  - [x] 1.3 Create `.env.example` with all required environment variables (Kafka brokers, DB credentials, topic names, log level)
  - [x] 1.4 Create `docker-compose.yml` with Zookeeper, Kafka broker, PostgreSQL services
  - [x] 1.5 Configure Kafka topic `food-orders` with 3 partitions and 7-day retention
  - [x] 1.6 Create database initialization script (`src/database/init.sql`) and migration for orders table
  - [x] 1.7 Create SQLAlchemy models for orders table (order_id PK, customer_id, items JSONB, total_amount, status, created_at, processed_at)
  - [x] 1.8 Add indexes on order_id and created_at columns
  - [x] 1.9 Set up structured JSON logging configuration (shared logger module)
  - [x] 1.10 Create `.gitignore` for Python project (.env, __pycache__, .pytest_cache, venv)
  - [x] 1.11 Test infrastructure: `docker-compose up` should start all services successfully

- [ ] 2.0 **Order Producer Service**
  - [ ] 2.1 Create `src/producer/` directory structure and `__init__.py`
  - [ ] 2.2 Implement mock data generator with 100 unique customers (customer_id format: CUST-XXXXX)
  - [ ] 2.3 Implement mock menu items generator with 20 food items (name, price range $2-$15)
  - [ ] 2.4 Create Pydantic models for OrderItem and Order validation
  - [ ] 2.5 Implement order generator that combines random customers and menu items
  - [ ] 2.6 Generate order_id with format: ORD-YYYYMMDD-NNNNN
  - [ ] 2.7 Implement Kafka producer using confluent-kafka-python
  - [ ] 2.8 Add JSON serialization for order messages
  - [ ] 2.9 Implement partition key using customer_id for consistent routing
  - [ ] 2.10 Add configurable order generation rate (default: 10 orders/second, env var: ORDER_RATE)
  - [ ] 2.11 Implement error handling with retry logic (3 retries, exponential backoff)
  - [ ] 2.12 Add delivery callback to confirm message publication
  - [ ] 2.13 Implement structured logging with correlation IDs (order_id in all logs)
  - [ ] 2.14 Create main.py entry point with graceful shutdown (SIGTERM handler)
  - [ ] 2.15 Create Dockerfile with Python 3.11+ base image
  - [ ] 2.16 Add producer service to docker-compose.yml with memory limit (128MB)

- [ ] 3.0 **Order Consumer Service**
  - [ ] 3.1 Create `src/consumer/` directory structure and `__init__.py`
  - [ ] 3.2 Implement configuration loader for database and Kafka settings
  - [ ] 3.3 Create SQLAlchemy database connection with connection pooling (pool_size=5)
  - [ ] 3.4 Implement Kafka consumer subscribing to `food-orders` topic
  - [ ] 3.5 Configure consumer group `order-processors` with auto.offset.reset=earliest
  - [ ] 3.6 Implement JSON deserialization for incoming messages
  - [ ] 3.7 Create order validation logic (required fields, total_amount > 0, item quantities > 0)
  - [ ] 3.8 Implement duplicate detection using order_id uniqueness (handle IntegrityError)
  - [ ] 3.9 Create database insert logic using SQLAlchemy sessions with transaction support
  - [ ] 3.10 Implement "process then commit" pattern (commit offset only after successful DB write)
  - [ ] 3.11 Add retry logic for transient database failures (max 3 retries with exponential backoff)
  - [ ] 3.12 Implement error handling for validation failures (log and skip invalid messages)
  - [ ] 3.13 Add processing metrics logging (orders processed, failures, latency per order)
  - [ ] 3.14 Implement graceful shutdown (commit offsets, close DB connections on SIGTERM)
  - [ ] 3.15 Create Dockerfile with Python 3.11+ base image
  - [ ] 3.16 Add consumer service to docker-compose.yml with memory limit (128MB)
  - [ ] 3.17 Test with 2 consumer instances to verify consumer group load balancing

- [ ] 4.0 **Testing Infrastructure**
  - [ ] 4.1 Create `tests/unit/` and `tests/integration/` directory structure
  - [ ] 4.2 Create `pytest.ini` with test discovery settings and coverage configuration
  - [ ] 4.3 Install pytest, testcontainers, pytest-cov in `requirements-dev.txt`
  - [ ] 4.4 Create unit tests for mock data generator (validate customer/item generation, uniqueness)
  - [ ] 4.5 Create unit tests for order_id generation (format validation, uniqueness)
  - [ ] 4.6 Create unit tests for Pydantic order validation (valid orders, invalid amounts, missing fields)
  - [ ] 4.7 Create unit tests for consumer validation logic (all validation rules)
  - [ ] 4.8 Create unit tests for duplicate detection logic
  - [ ] 4.9 Create `tests/conftest.py` with pytest fixtures for Kafka and PostgreSQL testcontainers
  - [ ] 4.10 Create Kafka integration test: produce 10 messages, consume and verify all received
  - [ ] 4.11 Create database integration test: insert orders, verify with queries, test duplicate handling
  - [ ] 4.12 Create consumer group integration test: verify partition assignment with 2 consumers
  - [ ] 4.13 Create end-to-end test: produce 50 orders → wait for processing → query database and verify count/data
  - [ ] 4.14 Configure coverage reporting with minimum 80% threshold
  - [ ] 4.15 Run full test suite and verify all tests pass: `pytest --cov=src`
  - [ ] 4.16 Document how to run tests in README (unit only, integration only, with coverage)

- [ ] 5.0 **Documentation & Deployment**
  - [ ] 5.1 Update README.md with complete setup instructions (prerequisites, local development)
  - [ ] 5.2 Add "Quick Start" section with `docker-compose up` commands
  - [ ] 5.3 Document how to view logs from each service
  - [ ] 5.4 Add architecture diagram (already in README, verify accuracy)
  - [ ] 5.5 Document Kafka concepts in code comments (partitions, consumer groups, offsets, replication)
  - [ ] 5.6 Create `docker-compose.aws.yml` with optimized memory limits for t2.small
  - [ ] 5.7 Document AWS-specific configuration (Kafka 512MB heap, PostgreSQL 256MB shared buffers)
  - [ ] 5.8 Create `docs/deployment/aws-setup.md` with step-by-step AWS deployment guide
  - [ ] 5.9 Document how to monitor services on AWS (Docker logs, disk usage, memory)
  - [ ] 5.10 Create `docs/deployment/troubleshooting.md` with common issues and solutions
  - [ ] 5.11 Add environment variable documentation in README
  - [ ] 5.12 Document how to scale consumers (add more instances to consumer group)
  - [ ] 5.13 Create `scripts/healthcheck.sh` to verify all services are healthy
  - [ ] 5.14 Add section on "Scalability Discussion Points" referencing PRD
  - [ ] 5.15 Test complete local setup on fresh clone: clone → setup → docker-compose up → verify 100 orders processed
  - [ ] 5.16 Test AWS deployment on t2.small instance and document any resource adjustments needed

---

**Next Steps:**
1. Review task list for completeness
2. Begin implementation starting with Task 1.0
3. Follow tasks sequentially for best results
4. Update status.md as tasks are completed

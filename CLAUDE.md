# KafkaFoodPipeline - Project Context for Claude AI

## Project Overview

Educational Kafka pipeline demonstrating Apache Kafka fundamentals through a realistic food ordering system. This project serves as a learning environment for understanding distributed streaming, event sourcing, and microservices architecture patterns.

**Purpose:** Hands-on learning project to master Kafka concepts with production-grade code quality and extensive educational documentation.

**Maintainer:** adamkwhite

## Current Status

**Phase:** 4.0 Complete (Testing Infrastructure) ✅
**Current Branch:** `feature/testing-infrastructure`
**Completion:** Phase 1.0 (Infrastructure) ✅ | Phase 2.0 (Producer) ✅ | Phase 3.0 (Consumer) ✅ | Phase 4.0 (Tests) ✅

### What's Working
- ✅ **Infrastructure**: Kafka (3 partitions), Zookeeper, PostgreSQL all running in Docker
- ✅ **Producer Service**: Publishing 10 orders/sec to Kafka with 6,000+ messages delivered
- ✅ **Consumer Service**: Processing messages from Kafka and persisting to PostgreSQL
- ✅ **End-to-End Pipeline**: Producer → Kafka → Consumer → Database (fully operational)
- ✅ **Testing Infrastructure**: 80+ unit tests + 42+ integration tests with testcontainers
- ✅ **Code Quality**: Pre-commit hooks, pytest with 80% coverage requirement, SonarCloud integration
- ✅ **Mock Data**: 100 customers, 20 menu items, realistic order generation
- ✅ **Partitioning**: customer_id as partition key ensuring per-customer ordering
- ✅ **Idempotency**: Duplicate detection via order_id PRIMARY KEY (0 duplicates verified)
- ✅ **Monitoring**: Structured JSON logs with correlation IDs (order_id)

### Recent Accomplishments (Today's Session)
1. **Complete Testing Infrastructure** (Phase 4.0):
   - **Unit Tests** (80+ tests, 1,488 lines):
     - test_mock_data.py: 30+ tests for MockDataGenerator
     - test_config.py: 30+ tests for Pydantic config validation
     - test_models.py: 20+ tests for SQLAlchemy ORM models
     - Full coverage of seed reproducibility, data validation, edge cases

   - **Integration Tests** (42+ tests, 1,647 lines):
     - test_producer_integration.py: 15+ tests with real Kafka testcontainer
     - test_consumer_integration.py: 17+ tests with Kafka + PostgreSQL
     - test_pipeline_e2e.py: 10+ tests for complete pipeline flow
     - Partition distribution, idempotency, performance testing
     - Throughput benchmarks (100+ msg/s), latency measurements

   - **Test Infrastructure**:
     - conftest.py with session/function-scoped fixtures
     - Testcontainers for real Kafka and PostgreSQL
     - pytest configuration with 80% coverage requirement
     - Pre-commit hooks (Black, isort, Flake8, Mypy, Bandit)
     - Coverage reporting (terminal, HTML, XML for SonarCloud)

2. **Code Quality Enhancements**:
   - Enhanced pytest configuration (verbose, durations, short tracebacks)
   - Coverage configuration (branch coverage, fail_under=80%)
   - Pre-commit hooks automatically run on every commit
   - SonarCloud integration for continuous quality monitoring

## Technology Stack

### Core Technologies
- **Python**: 3.11 (production runtime)
- **Apache Kafka**: 7.5.0 (Confluent Platform)
- **Zookeeper**: 7.5.0 (cluster coordination)
- **PostgreSQL**: 15 (order storage)
- **Docker**: Compose for local orchestration

### Python Libraries (requirements.txt)
- `confluent-kafka>=2.3.0` - Production-grade Kafka client (librdkafka-based)
- `sqlalchemy>=2.0.0` - ORM with type hints support
- `psycopg2-binary>=2.9.0` - PostgreSQL adapter
- `pydantic>=2.0.0` - Data validation
- `pydantic-settings>=2.0.0` - Environment config validation
- `python-dotenv>=1.0.0` - .env file support
- `Faker>=22.0.0` - Mock data generation

### Development Tools (requirements-dev.txt)
- `pytest>=7.4.0` - Testing framework
- `pytest-cov>=4.1.0` - Coverage reporting
- `testcontainers>=3.7.0` - Integration testing
- `black>=23.0.0` - Code formatting
- `isort>=5.12.0` - Import sorting
- `flake8>=6.1.0` - PEP 8 linting
- `ruff>=0.1.0` - Fast linting (alternative to flake8)
- `mypy>=1.7.0` - Static type checking
- `bandit>=1.7.5` - Security vulnerability scanner

## Security Standards

### Supply Chain Security
**CRITICAL: Always pin dependencies to commit SHAs, not version tags or branches**

**GitHub Actions:**
```yaml
# ❌ NEVER USE - Mutable, vulnerable to supply chain attacks
uses: actions/checkout@v4
uses: actions/checkout@master
uses: SonarSource/sonarcloud-github-action@master

# ✅ ALWAYS USE - Immutable commit SHA with version comment
uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2
uses: SonarSource/sonarcloud-github-action@ffc3010689be73b8e5ae0c57ce35968afd7909e8  # v5.0.0
```

**Why this matters:**
- Version tags can be moved to point at malicious code
- Branch names pull latest code (can change without notice)
- Commit SHAs are immutable - exact code, forever
- Prevents supply chain attacks (SolarWinds, event-stream, codecov)

**Python Dependencies:**
```python
# Pin exact versions in requirements.txt
confluent-kafka==2.3.0  # Not >=2.3.0 or ~2.3.0
```

**Docker Images:**
```dockerfile
# Pin to digest, not tag
FROM python:3.11@sha256:abc123...  # Not python:3.11 or python:latest
```

## Code Quality & CI/CD

### Local Pre-Commit Hooks
Pre-commit hooks run automatically before each commit to ensure code quality:

**Setup:**
```bash
# Pre-commit hook is automatically installed in .git/hooks/pre-commit
# It activates the virtual environment and runs all checks
chmod +x .git/hooks/pre-commit
```

**Checks performed:**
1. ✅ **Black** - Code formatting (PEP 8 compliant, 100 char line length)
2. ✅ **isort** - Import organization (compatible with Black)
3. ✅ **Flake8** - Linting (PEP 8 violations, unused imports, undefined variables)
4. ⚠️ **Mypy** - Type checking (non-blocking, for awareness)
5. ✅ **Bandit** - Security vulnerability scanning

**Auto-fix common issues:**
```bash
# Fix formatting and imports
source kafka-venv/bin/activate
black src/
isort src/

# View linting issues
flake8 src/ --max-line-length=100 --extend-ignore=E203,W503

# Check types
mypy src --ignore-missing-imports

# Skip hooks (not recommended)
git commit --no-verify
```

### GitHub Actions (CI/CD Pipeline)
Automated quality gates run on every PR and push to main:

**Stage 1: Quick Checks (30-60s)**
- Black formatting verification
- isort import verification
- Flake8 linting
- Mypy type checking (non-blocking)

**Stage 2: Tests & Analysis (2-3min)**
- pytest test suite with coverage
- SonarCloud code quality analysis
- Security vulnerability scanning

**Stage 3: Claude Code Review**
- Automated AI code review
- Triggered by mentioning `@claude` in PR comments
- Provides architectural feedback and suggestions

**Workflow Files:**
- `.github/workflows/build.yml` - Build, lint, test, SonarCloud
- `.github/workflows/claude.yml` - AI-powered code review

### SonarCloud Integration
Continuous code quality and security analysis:

**Metrics tracked:**
- Code coverage percentage
- Code smells and technical debt
- Security vulnerabilities
- Code duplication
- Maintainability rating

**Configuration:** `sonar-project.properties`
- Project: `adamkwhite_KafkaFoodPipeline`
- Sources: `src/`
- Exclusions: tests, cache, migrations
- Coverage report: `coverage.xml`

**View results:**
```bash
# After PR is created, check SonarCloud dashboard
# https://sonarcloud.io/project/overview?id=adamkwhite_KafkaFoodPipeline
```

### Tool Configuration (pyproject.toml)
Centralized configuration for all code quality tools:

```toml
[tool.black]
line-length = 100
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.11"
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = ["--cov=src", "--cov-report=xml"]

[tool.ruff]
line-length = 100
target-version = "py311"
```

### Quality Standards
**Code must pass:**
- ✅ Black formatting (100% compliance)
- ✅ isort import organization
- ✅ Flake8 linting (no PEP 8 violations)
- ✅ Bandit security scan (no high/medium vulnerabilities)

**Code should aim for:**
- ⚠️ Mypy type coverage (improving incrementally)
- 🎯 80%+ test coverage (Phase 4.0 goal)
- 🎯 SonarCloud Quality Gate: Pass

## Implementation Details

### Architecture Pattern: Event Sourcing
- **Kafka**: Source of truth (immutable event log)
- **PostgreSQL**: Materialized view (current state)
- **Pattern**: Dual writes → Kafka then DB (at-least-once semantics)

### Kafka Configuration
```yaml
Topic: food-orders
Partitions: 3
Replication Factor: 1 (single broker for learning)
Retention: 7 days (168 hours)
Partition Key: customer_id (hash-based distribution)
Compression: Snappy
```

### Producer Settings
```python
bootstrap.servers: kafka:29092 (internal Docker network)
client.id: order-producer-docker
acks: 'all'  # Required for idempotence
enable.idempotence: True  # Exactly-once per partition
compression.type: 'snappy'
linger.ms: 10  # Batch window
batch.num.messages: 10000
```

### Data Model (Order Structure)
```json
{
  "order_id": "ORD-YYYYMMDD-NNNNN",
  "customer_id": "CUST-XXXXX",  // Partition key
  "customer_name": "...",
  "customer_email": "...",
  "items": [
    {
      "item_id": "ITEM-XXX",
      "name": "...",
      "quantity": N,
      "price": N.NN,
      "subtotal": N.NN
    }
  ],
  "total_amount": N.NN,
  "status": "pending",
  "created_at": "ISO8601 timestamp"
}
```

### Database Schema (PostgreSQL)
```sql
CREATE TABLE orders (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    items JSONB NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_created_at ON orders(created_at);
CREATE INDEX idx_orders_items_gin ON orders USING GIN(items);
CREATE INDEX idx_orders_customer_created ON orders(customer_id, created_at);
```

## Project Structure

```
KafkaFoodPipeline/
├── src/
│   ├── producer/           # Order Producer Service (Phase 2.0 ✅)
│   │   ├── __init__.py     # Package exports, Kafka quick reference
│   │   ├── main.py         # CLI entry point, signal handling
│   │   ├── producer.py     # OrderProducer class, callbacks
│   │   ├── config.py       # ProducerConfig with Pydantic
│   │   └── mock_data.py    # MockDataGenerator (Faker-based)
│   ├── consumer/           # Order Consumer Service (Phase 3.0 ✅)
│   │   ├── __init__.py     # Package exports, consumer documentation
│   │   ├── main.py         # CLI entry point, graceful shutdown
│   │   ├── consumer.py     # OrderConsumer class, offset management
│   │   ├── config.py       # ConsumerConfig with Pydantic
│   │   ├── database.py     # DatabaseManager with connection pooling
│   │   └── models.py       # SQLAlchemy ORM models (Order)
│   ├── database/           # Database setup (Phase 1.0 ✅)
│   │   ├── init.sql        # Schema with indexes
│   │   └── migrations/     # Migration scripts
│   └── shared/             # Shared utilities (Phase 1.0 ✅)
│       └── logger.py       # Structured JSON logging
├── tests/                  # Testing infrastructure (Phase 4.0 ✅)
│   ├── conftest.py         # Pytest fixtures (Kafka, PostgreSQL testcontainers)
│   ├── unit/               # Unit tests (no external dependencies)
│   │   ├── test_mock_data.py      # MockDataGenerator tests (30+)
│   │   ├── test_config.py         # Config validation tests (30+)
│   │   └── test_models.py         # ORM model tests (20+)
│   ├── integration/        # Integration tests (with testcontainers)
│   │   ├── test_producer_integration.py  # Producer tests (15+)
│   │   ├── test_consumer_integration.py  # Consumer tests (17+)
│   │   └── test_pipeline_e2e.py          # End-to-end tests (10+)
│   └── fixtures/           # Shared test data and helpers
├── docs/
│   ├── features/
│   │   └── kafka-food-pipeline-PLANNED/
│   │       ├── prd.md      # Product Requirements Document
│   │       └── tasks.md    # 76 implementation tasks
│   └── KeyPoints/
│       ├── README.md       # Learning docs index
│       └── infrastructure.md  # Kafka infrastructure guide
├── scripts/
│   └── init-kafka-topics.sh  # Topic initialization
├── Dockerfile.producer     # Multi-stage producer image
├── docker-compose.yml      # Full stack orchestration
├── requirements.txt        # Production dependencies
├── requirements-dev.txt    # Development dependencies
├── .env.example           # Configuration template
└── README.md              # Project overview
```

## Key Learnings & Patterns

### Kafka Concepts (with Blockchain Analogies)
- **Partition = Blockchain**: Append-only, ordered, immutable log
- **Offset = Block Height**: Position in partition (0, 1, 2, ...)
- **Bootstrap Servers = Seed Nodes**: Initial contact points for discovery
- **Consumer Group = Network Peers**: Parallel processing with partition assignment
- **Replication = Node Consensus**: Multiple copies for fault tolerance

### Producer Best Practices
1. **Idempotence**: Enable to prevent duplicates (requires acks='all')
2. **Partition Keys**: Use business key (customer_id) for ordering guarantees
3. **Callbacks**: Asynchronous delivery confirmation with correlation tracking
4. **Batching**: Balance latency (linger.ms) vs throughput (batch size)
5. **Error Handling**: Retry transient errors, log permanent failures
6. **Graceful Shutdown**: Flush pending messages before exit

### Consumer Best Practices
1. **Manual Offset Commits**: Commit after successful processing (at-least-once delivery)
2. **Idempotency**: Use natural keys (order_id PRIMARY KEY) to handle duplicates
3. **Process-Then-Commit**: Save to database BEFORE committing offset
4. **Retry Logic**: Exponential backoff for transient errors (DB connection issues)
5. **Session Management**: Detach ORM objects before accessing outside session context
6. **Graceful Shutdown**: Close consumer, commit final offsets, close DB connections
7. **Consumer Groups**: Use groups for horizontal scaling (partition assignment)

### Docker Optimization
- **Multi-stage builds**: Separate build deps from runtime (208MB vs 900MB)
- **Non-root user**: Security best practice (producer:1000)
- **Layer caching**: Requirements before code for faster rebuilds
- **Health checks**: Enable auto-restart on failure

## Completed Phases

### Phase 4.0: Testing Infrastructure ✅
- **Unit Tests** (80+ tests, 1,488 lines):
  - MockDataGenerator tests (seed reproducibility, data quality)
  - Config validation tests (Pydantic constraints, environment loading)
  - ORM model tests (Decimal precision, timestamp parsing, edge cases)
- **Integration Tests** (42+ tests, 1,647 lines):
  - Producer integration tests (real Kafka testcontainer)
  - Consumer integration tests (Kafka + PostgreSQL)
  - End-to-end pipeline tests (complete data flow validation)
  - Performance benchmarks (throughput, latency measurements)
- **Test Infrastructure**:
  - conftest.py with testcontainers (session/function-scoped)
  - pytest configuration (80% coverage requirement, verbose output)
  - Coverage reporting (terminal, HTML, XML for CI/CD)
  - Pre-commit hooks (Black, isort, Flake8, Mypy, Bandit)
- **Total**: 122+ tests, 3,100+ lines of test code

### Phase 3.0: Order Consumer Service ✅
- OrderConsumer implementation with manual offset commits
- SQLAlchemy ORM models and database connection pooling
- Idempotency via order_id PRIMARY KEY (0 duplicates)
- Process-then-commit pattern for at-least-once delivery
- Retry logic with exponential backoff for transient errors
- CLI with graceful shutdown (SIGTERM/SIGINT handling)
- Docker multi-stage build and Compose integration
- **End-to-end testing**: 6,000+ orders processed successfully

## Next Steps

### Phase 5.0: Documentation & Deployment (16 tasks)
- AWS deployment guide (EC2 t2.small)
- Monitoring and alerting setup (Prometheus, Grafana)
- Performance tuning documentation
- Troubleshooting guides
- Architecture diagrams (system flow, data model)

## Dependencies & Services

### Running Services (Docker Compose)
- **Zookeeper**: `localhost:2181` - Cluster coordination
- **Kafka**: `localhost:9092` - Message broker (external), `kafka:29092` (internal)
- **PostgreSQL**: `localhost:5432` - Order database
- **Producer**: Continuous order generation at 10/sec

### Service Health
```bash
# Check all services
docker-compose ps

# View logs
docker-compose logs -f order-producer
docker-compose logs -f kafka

# Verify Kafka messages
docker exec kafka-broker kafka-console-consumer \
  --bootstrap-server localhost:9092 --topic food-orders \
  --from-beginning --max-messages 10
```

### Environment Variables (.env)
Key configuration in `.env.example`:
- `KAFKA_BOOTSTRAP_SERVERS`: Broker addresses
- `KAFKA_TOPIC_ORDERS`: Topic name (food-orders)
- `PRODUCER_RATE`: Orders per second (10)
- `PRODUCER_DURATION`: Run time (0=infinite)
- `MOCK_SEED`: Reproducibility (42)
- `LOG_LEVEL`: INFO/DEBUG
- `LOG_FORMAT`: json/text

## Known Issues

### Resolved
- ✅ Docker dependency installation (multi-stage build fixed)
- ✅ Kafka config validation (buffer.memory not supported in Python client)
- ✅ Idempotence config (acks='all' required)

### Current
- None - All Phase 2.0 functionality working as expected

## Performance Metrics

### Producer (Current)
- **Throughput**: 10 orders/sec (configurable 1-1000)
- **Latency**: ~0.1ms average delivery time
- **Messages Delivered**: 4,029+ (continuous)
- **Error Rate**: 0%
- **Partition Distribution**: Balanced across 3 partitions

### Infrastructure
- **Docker Image Size**: 208MB (multi-stage optimized)
- **Kafka Topic Retention**: 7 days
- **Database Size**: Growing (no consumer yet to persist)

## Git Workflow

### Branches
- `main`: Production-ready code
- `feature/kafka-pipeline-implementation`: Phase 1.0 (merged via PR #2)
- `feature/order-producer-service`: Phase 2.0 (current, ready for PR)

### Commit Convention
```
<type>: <description>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### PR Workflow
1. Feature branch → implement → test locally
2. Commit with educational comments
3. Create PR: `gh pr create`
4. Monitor CI/CD: `gh pr checks`
5. Merge after approval
6. Clean up branch

## Educational Philosophy

This project prioritizes **learning over brevity**:
- Extensive inline comments explaining Kafka concepts
- Blockchain analogies for distributed systems concepts
- Production-grade patterns (not shortcuts)
- One-task-at-a-time implementation for deep understanding
- Educational documentation extracted to docs/KeyPoints/

Every file includes "WHY" explanations, not just "HOW" implementations.

---

**Last Updated**: 2025-10-10
**Session Summary**:
- ✅ Completed Phase 4.0 (Testing Infrastructure)
  - **Unit Tests** (80+ tests, 1,488 lines):
    - test_mock_data.py: 30+ tests for MockDataGenerator
    - test_config.py: 30+ tests for Pydantic config validation
    - test_models.py: 20+ tests for SQLAlchemy ORM models
  - **Integration Tests** (42+ tests, 1,647 lines):
    - test_producer_integration.py: 15+ tests with real Kafka
    - test_consumer_integration.py: 17+ tests with Kafka + PostgreSQL
    - test_pipeline_e2e.py: 10+ end-to-end pipeline tests
  - **Test Infrastructure**:
    - conftest.py with session/function-scoped fixtures
    - Testcontainers for real Kafka and PostgreSQL
    - pytest with 80% coverage requirement
    - Pre-commit hooks (Black, isort, Flake8, Mypy, Bandit)
    - Coverage reports (terminal, HTML, XML for SonarCloud)
- Test Statistics:
  - 122+ total tests across unit and integration suites
  - 3,100+ lines of test code
  - Coverage targets: 80% minimum enforced
  - Performance benchmarks: 100+ msg/s throughput
- Ready for Phase 5.0 (Documentation & Deployment)

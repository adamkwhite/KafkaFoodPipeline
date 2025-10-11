# KafkaFoodPipeline - Project Context for Claude AI

## Project Overview

Educational Kafka pipeline demonstrating Apache Kafka fundamentals through a realistic food ordering system. This project serves as a learning environment for understanding distributed streaming, event sourcing, and microservices architecture patterns.

**Purpose:** Hands-on learning project to master Kafka concepts with production-grade code quality and extensive educational documentation.

**Maintainer:** adamkwhite

## Current Status

**Phase:** 2.0 Complete (Order Producer Service) ✅
**Current Branch:** `feature/order-producer-service`
**Completion:** Phase 1.0 (Infrastructure) ✅ | Phase 2.0 (Producer) ✅ | Phase 3.0 (Consumer) - Next

### What's Working
- ✅ **Infrastructure**: Kafka (3 partitions), Zookeeper, PostgreSQL all running in Docker
- ✅ **Producer Service**: Publishing 10 orders/sec to Kafka with 4,029+ messages delivered
- ✅ **Mock Data**: 100 customers, 20 menu items, realistic order generation
- ✅ **Partitioning**: customer_id as partition key ensuring per-customer ordering
- ✅ **Monitoring**: Structured JSON logs with correlation IDs (order_id)

### Recent Accomplishments (Today's Session)
1. **Complete Producer Implementation** (Tasks 2.1-2.16):
   - MockDataGenerator with Faker (reproducible seed=42)
   - OrderProducer with confluent-kafka-python
   - ProducerConfig with Pydantic validation
   - CLI entry point with argparse and signal handling
   - Dockerfile with multi-stage build (208MB image)
   - Docker Compose integration

2. **Production Testing**:
   - Built and deployed producer container
   - Fixed configuration issues (acks='all' required for idempotence)
   - Verified 4,029+ messages successfully delivered
   - Confirmed partition distribution across 3 partitions
   - Validated JSON message structure in Kafka

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
- `ruff>=0.1.0` - Fast linting
- `mypy>=1.5.0` - Static type checking

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
│   ├── consumer/           # Order Consumer Service (Phase 3.0 - Next)
│   │   └── models.py       # SQLAlchemy ORM models
│   ├── database/           # Database setup (Phase 1.0 ✅)
│   │   ├── init.sql        # Schema with indexes
│   │   └── migrations/     # Migration scripts
│   └── shared/             # Shared utilities (Phase 1.0 ✅)
│       └── logger.py       # Structured JSON logging
├── tests/                  # Testing infrastructure (Phase 4.0 - Future)
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

### Docker Optimization
- **Multi-stage builds**: Separate build deps from runtime (208MB vs 900MB)
- **Non-root user**: Security best practice (producer:1000)
- **Layer caching**: Requirements before code for faster rebuilds
- **Health checks**: Enable auto-restart on failure

## Next Steps

### Phase 3.0: Order Consumer Service (17 tasks)
1. Create consumer directory structure
2. Implement KafkaConsumer class
   - Subscribe to 'food-orders' topic
   - Consumer group: 'order-processors'
   - Manual offset commits (at-least-once)
3. Database integration
   - SQLAlchemy session management
   - Connection pooling
   - Transaction handling
4. Idempotency handling
   - order_id as primary key (natural deduplication)
   - Handle duplicate message processing
5. Error handling & dead letter queue
6. Consumer configuration (Pydantic)
7. Main entry point with CLI
8. Dockerfile and Docker Compose integration

### Phase 4.0: Testing Infrastructure (16 tasks)
- Unit tests with pytest
- Integration tests with testcontainers
- End-to-end pipeline tests
- Performance/load testing
- Coverage reporting (target: 80%+)

### Phase 5.0: Documentation & Deployment (16 tasks)
- AWS deployment guide (EC2 t2.small)
- Monitoring and alerting setup
- Performance tuning documentation
- Troubleshooting guides
- Architecture diagrams

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
**Session Summary**: Completed Phase 2.0 (Producer Service), tested 4,029+ messages, ready for Phase 3.0 (Consumer)

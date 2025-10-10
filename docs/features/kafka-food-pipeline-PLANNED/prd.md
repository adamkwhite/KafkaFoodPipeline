# Product Requirements Document: Kafka Food Processing Pipeline

## Introduction/Overview

The Kafka Food Processing Pipeline is an educational project designed to demonstrate Apache Kafka fundamentals, stream processing patterns, and microservices architecture. The system simulates a food order processing workflow where orders are produced, streamed through Kafka, processed by consumers, and persisted to a database.

This project serves as a portfolio piece to showcase understanding of:
- Apache Kafka core concepts (topics, partitions, consumer groups)
- Event-driven architecture and stream processing
- Microservices communication patterns
- Python-based distributed systems

**Problem Solved**: Provides a practical, working example of how modern food delivery platforms handle high-volume order processing using event streaming architecture.

## Goals

1. **Primary Goal**: Build a functional end-to-end Kafka-based order processing system that demonstrates core streaming concepts
2. **Learning Goal**: Gain hands-on experience with Kafka topics, producers, consumers, partitioning, and consumer groups
3. **Deployment Goal**: Create a system that runs locally (Docker Compose) and can be deployed to AWS with future Kubernetes migration path
4. **Portfolio Goal**: Develop a demonstrable project that can be shared with potential employers/collaborators
5. **Scalability Awareness**: Design single-instance system with architectural considerations for horizontal scaling discussion

## User Stories

**As a developer learning Kafka**, I want to:
- Run the entire pipeline locally with a single Docker Compose command
- See orders flow from producer → Kafka → consumer → database in real-time
- Understand how partitioning affects message distribution
- Experiment with multiple consumers to see consumer group behavior

**As a technical interviewer**, I want to:
- See clean, well-documented code demonstrating Kafka best practices
- Understand the architectural decisions and trade-offs
- See evidence of proper error handling and testing

**As a future contributor**, I want to:
- Easily set up the development environment
- Understand the system components and their interactions
- Have clear documentation for extending functionality

## Functional Requirements

### Phase 1: Core Order Processing Flow

#### 1. Order Producer Service
**FR-1.1**: The system must include a Python-based order producer that generates synthetic food orders
- **FR-1.1.1**: Generate orders with realistic data: order_id, customer_id, items (name, quantity, price), total_amount, timestamp, status
  - Mock data pool: 100 unique customers, 20 menu items
- **FR-1.1.2**: Support configurable order generation rate (default: 10 orders per second)
- **FR-1.1.3**: Publish orders to Kafka topic `food-orders` with JSON serialization
- **FR-1.1.4**: Implement proper error handling for Kafka connection failures
- **FR-1.1.5**: Log all produced messages with order ID and timestamp

#### 2. Kafka Infrastructure
**FR-2.1**: The system must configure Apache Kafka cluster with:
- **FR-2.1.1**: Single Kafka broker for v1 (with multi-broker design notes for scaling discussion)
- **FR-2.1.2**: Zookeeper instance for Kafka coordination
- **FR-2.1.3**: Topic `food-orders` with 3 partitions for load distribution demonstration
- **FR-2.1.4**: Retention policy of 7 days for message history
- **FR-2.1.5**: Replication factor of 1 for single-broker setup (document how to increase for production)

#### 3. Order Processing Consumer Service
**FR-3.1**: The system must include a Python-based consumer that processes orders from Kafka
- **FR-3.1.1**: Subscribe to `food-orders` topic using consumer group `order-processors`
- **FR-3.1.2**: Deserialize JSON order messages
- **FR-3.1.3**: Validate order data (required fields, valid amounts, item quantities > 0)
- **FR-3.1.4**: Transform order data for database storage
- **FR-3.1.5**: Handle duplicate order detection using order_id uniqueness
- **FR-3.1.6**: Commit offsets only after successful database write
- **FR-3.1.7**: Implement retry logic for transient database failures (max 3 retries)
- **FR-3.1.8**: Log processing metrics (orders processed, failures, latency)

#### 4. Database Storage
**FR-4.1**: The system must persist processed orders to PostgreSQL
- **FR-4.1.1**: Create `orders` table with schema: order_id (PK), customer_id, items (JSONB), total_amount, status, created_at, processed_at
- **FR-4.1.2**: Implement database connection pooling for efficiency
- **FR-4.1.3**: Use transactions to ensure atomicity of order writes
- **FR-4.1.4**: Create indexes on order_id and created_at for query performance
- **FR-4.1.5**: Support database migration scripts for schema management

#### 5. Configuration & Environment
**FR-5.1**: The system must support environment-based configuration
- **FR-5.1.1**: Use environment variables for Kafka broker URLs, database credentials, topic names
- **FR-5.1.2**: Provide `.env.example` template with all required variables
- **FR-5.1.3**: Support different configs for local (Docker) and AWS deployments
- **FR-5.1.4**: Never commit secrets to version control

#### 6. Deployment
**FR-6.1**: The system must support multiple deployment targets
- **FR-6.1.1**: Local deployment using Docker Compose (all services containerized)
- **FR-6.1.2**: AWS deployment scripts/documentation for EC2 instance
- **FR-6.1.3**: Include Dockerfiles for producer and consumer services
- **FR-6.1.4**: Document Kubernetes deployment approach for future implementation

#### 7. Monitoring & Observability
**FR-7.1**: The system must provide basic observability through logging
- **FR-7.1.1**: Structured logging in JSON format for all services
- **FR-7.1.2**: Log levels: DEBUG (development), INFO (production)
- **FR-7.1.3**: Include correlation IDs (order_id) in all logs for tracing
- **FR-7.1.4**: Document metrics worth tracking (throughput, latency, error rate)

#### 8. Testing
**FR-8.1**: The system must include comprehensive test coverage
- **FR-8.1.1**: Unit tests for producer logic, consumer logic, data validation
- **FR-8.1.2**: Integration tests using test Kafka containers (testcontainers-python)
- **FR-8.1.3**: Database integration tests with test PostgreSQL container
- **FR-8.1.4**: End-to-end test: produce order → verify in database
- **FR-8.1.5**: Test coverage minimum 80%

## Non-Goals (Out of Scope)

The following are explicitly **not** included in Phase 1:

1. **Real-time Notifications**: Email/SMS notifications for order updates (logging only)
2. **Analytics Service**: Real-time analytics dashboard or aggregation service
3. **Authentication/Authorization**: No user authentication or API security
4. **Frontend UI**: No web interface or dashboard (command-line/logs only)
5. **Payment Processing**: No payment gateway integration
6. **Advanced Monitoring**: No Prometheus, Grafana, or APM tools (future enhancement)
7. **Multi-region Deployment**: Single AWS region only
8. **Schema Registry**: No Avro/Protobuf schemas (JSON only for simplicity)
9. **Kafka Streams**: No Kafka Streams API (basic consumer/producer only)
10. **Restaurant Management**: No restaurant entity or multi-tenant support

## Design Considerations

### Architecture
```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│ Order Producer  │────────▶│  Kafka Broker   │────────▶│ Order Consumer  │
│   (Python)      │         │                 │         │    (Python)     │
└─────────────────┘         │  Topic:         │         └─────────────────┘
                            │  food-orders    │                  │
                            │  (3 partitions) │                  │
                            └─────────────────┘                  ▼
                                                        ┌─────────────────┐
                                                        │   PostgreSQL    │
                                                        │   (Orders DB)   │
                                                        └─────────────────┘
```

### Technology Stack
- **Language**: Python 3.11+
- **Kafka Client**: confluent-kafka-python (robust, production-grade)
- **Database**: PostgreSQL 15+
- **ORM**: SQLAlchemy for database interactions
- **Containerization**: Docker & Docker Compose
- **Testing**: pytest, testcontainers
- **Deployment**: Docker Compose (local), AWS EC2 (cloud), future Kubernetes

### Data Model

**Order Message Schema (JSON)**:
```json
{
  "order_id": "ORD-20250110-001",
  "customer_id": "CUST-12345",
  "items": [
    {
      "name": "Burger",
      "quantity": 2,
      "price": 8.99
    },
    {
      "name": "Fries",
      "quantity": 1,
      "price": 3.49
    }
  ],
  "total_amount": 21.47,
  "status": "pending",
  "created_at": "2025-01-10T14:30:00Z"
}
```

**PostgreSQL Orders Table**:
```sql
CREATE TABLE orders (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    items JSONB NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_created_at (created_at),
    INDEX idx_customer_id (customer_id)
);
```

### Partitioning Strategy
- Use `customer_id` as partition key to ensure orders from same customer go to same partition
- Maintains ordering guarantee for individual customers
- Enables parallel processing across different customers

### Error Handling
- **Producer**: Retry failed publishes up to 3 times with exponential backoff
- **Consumer**: Dead Letter Queue (DLQ) topic for messages that fail validation after retries
- **Database**: Connection retry with circuit breaker pattern
- **Graceful Shutdown**: Handle SIGTERM to commit offsets before shutdown

## Technical Considerations

### Dependencies
```
confluent-kafka>=2.3.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
pydantic>=2.0.0  # Data validation
python-dotenv>=1.0.0
pytest>=7.4.0
testcontainers>=3.7.0
```

### Scalability Discussion Points
While Phase 1 is single-instance, the architecture supports:
- **Horizontal Scaling**: Add more consumer instances to same consumer group
- **Partitioning**: Increase partitions to distribute load
- **Kafka Cluster**: Add brokers with replication for fault tolerance
- **Database**: Read replicas for query scaling, sharding by customer_id

### AWS Deployment Approach
- **Target Instance**: t2.small EC2 (2 vCPU, 2GB RAM) - shared with SonarQube
- **Resource Constraints**: Optimize container memory limits for shared environment
  - Kafka: 512MB heap
  - PostgreSQL: 256MB shared buffers
  - Producer/Consumer: 128MB each
- EC2 instance with Docker Compose
- Consider RDS PostgreSQL for production (currently containerized for cost)
- MSK (Managed Streaming for Kafka) as future option
- CloudWatch for log aggregation
- Security groups for network isolation

### Future Kubernetes Migration
- Helm charts for service deployment
- StatefulSets for Kafka brokers
- ConfigMaps for environment configuration
- Persistent Volume Claims for Kafka data
- Horizontal Pod Autoscaler for consumers

## Success Metrics

The project is considered successful when:

1. **Functional Success**:
   - ✅ System produces and consumes 100 orders end-to-end without errors
   - ✅ All orders appear correctly in PostgreSQL database
   - ✅ Consumer group demonstrates parallel processing with 2+ consumers

2. **Code Quality**:
   - ✅ Test coverage ≥ 80%
   - ✅ All tests pass (unit + integration)
   - ✅ Code follows PEP 8 style guidelines
   - ✅ Comprehensive README documentation

3. **Deployment Success**:
   - ✅ One-command local setup: `docker-compose up`
   - ✅ Successfully deployed and running on AWS instance
   - ✅ Services remain stable for 1+ hour continuous operation

4. **Learning Objectives**:
   - ✅ Can explain Kafka topics, partitions, consumer groups, offsets
   - ✅ Can discuss scaling strategies and architectural trade-offs
   - ✅ Can demonstrate system to others (portfolio piece)

5. **Documentation**:
   - ✅ README with quickstart, architecture diagram, deployment instructions
   - ✅ Code comments explaining key Kafka concepts
   - ✅ Environment setup guide

## Future Enhancements (Post Phase 1)

1. **Failure Scenario Testing** (Fast Follow):
   - Simulate network partitions and Kafka broker failures
   - Test database connection loss and recovery
   - Chaos engineering for resilience validation
   - Load testing beyond 10 ops/sec to identify bottlenecks

2. **Phase 2 Features** (Future Decision):
   - Real-time notification service
   - Analytics and metrics dashboard
   - Advanced monitoring (Prometheus/Grafana)
   - Schema Registry integration

## Related Work

This PRD will be linked to GitHub issues for implementation tracking once approved.

---

**Document Status**: PLANNED
**Created**: 2025-01-10
**Last Updated**: 2025-01-10
**Version**: 1.1 (Clarifications incorporated)

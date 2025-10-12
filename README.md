# Kafka Food Processing Pipeline - Learning Project

## Overview

An educational project demonstrating Apache Kafka fundamentals, stream processing patterns, and microservices architecture through a food order processing simulation. This project simulates how modern food delivery platforms handle high-volume order processing using event streaming.

**Learning Objectives:**
- Kafka core concepts (topics, partitions, consumer groups, offsets)
- Event-driven architecture and stream processing
- Microservices communication patterns
- Python-based distributed systems

**Status:** PLANNED - See [PRD](docs/features/kafka-food-pipeline-PLANNED/prd.md) for detailed requirements

## Architecture

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

## Technology Stack

**Core Technologies:**
- Python 3.11+ (backend services)
- Apache Kafka (message streaming, 3 partitions)
- PostgreSQL 15+ (persistent storage)
- Docker & Docker Compose (containerization)

**Key Libraries:**
- `confluent-kafka-python` - Production-grade Kafka client
- `SQLAlchemy` - ORM with type hints
- `Pydantic` - Data validation and settings
- `pytest` + `testcontainers` - Testing (80% coverage target)

**Infrastructure:**
- Local: Docker Compose
- Cloud: AWS EC2 (t2.small) with future Kubernetes support

## Quick Start

> **Note:** Implementation not yet started. See [PRD](docs/features/kafka-food-pipeline-PLANNED/prd.md) for planned features.

### Prerequisites (Planned)
- Python 3.11+
- Docker & Docker Compose
- Git

### Local Development (Planned)
```bash
# Clone repository
git clone <repo-url>
cd KafkaFoodPipeline

# Start all services
docker-compose up

# View order processing logs
docker-compose logs -f consumer
```

### AWS Deployment (Planned)
- Target: t2.small EC2 instance (2GB RAM)
- Shared with SonarQube - optimized memory limits
- See [PRD](docs/features/kafka-food-pipeline-PLANNED/prd.md#aws-deployment-approach) for details

## Project Structure

```
KafkaFoodPipeline/
├── src/                    # Application source code (TBD)
├── tests/                  # Unit and integration tests (TBD)
├── docs/                   # Documentation
│   └── features/
│       └── kafka-food-pipeline-PLANNED/
│           └── prd.md      # Product Requirements Document
├── scripts/                # Build and deployment scripts (TBD)
├── docker-compose.yml      # Local development setup (TBD)
├── README.md               # This file
└── CLAUDE.md               # Project context for Claude AI
```

## Documentation

- **[Product Requirements Document (PRD)](docs/features/kafka-food-pipeline-PLANNED/prd.md)** - Detailed feature requirements and technical specifications
- **Implementation Tasks** - Coming soon

## Success Criteria

The project is considered successful when:

✅ System produces and consumes 100 orders end-to-end without errors
✅ All orders appear correctly in PostgreSQL database
✅ Consumer group demonstrates parallel processing with 2+ consumers
✅ Test coverage ≥ 80%
✅ One-command local setup: `docker-compose up`
✅ Successfully deployed and running on AWS instance
✅ Services remain stable for 1+ hour continuous operation

## Future Enhancements

### Fast Follow
- Failure scenario testing (network partitions, broker failures)
- Chaos engineering for resilience validation
- Load testing beyond 10 ops/sec

### Phase 2 (Future)
- Real-time notification service
- Analytics and metrics dashboard
- Advanced monitoring (Prometheus/Grafana)
- Schema Registry integration

## Contributing

This is a personal learning project. Feedback and suggestions welcome via issues.

## License

MIT License (or specify your preferred license)

---

**Maintainer:** adamkwhite
**Created:** 2025-01-10
**Status:** Planning Phase

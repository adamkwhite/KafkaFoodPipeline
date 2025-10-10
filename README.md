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

## Technology Stack Comparison

This learning project's tech stack is intentionally aligned with a production medical application to maximize real-world applicability.

| **Component** | **Kafka Food Pipeline PRD** | **Production Medical App** | **Status** |
|---------------|----------------------------|---------------------------|------------|
| **Backend Language** | Python 3.11+ | Python | ✅ **MATCH** |
| **Database** | PostgreSQL 15+ | PostgreSQL | ✅ **MATCH** |
| **Message Streaming** | Kafka (core focus, 3 partitions) | Kafka (in migration, agent/model orchestration) | ✅ **MATCH** |
| **Kafka Client** | confluent-kafka-python | Not specified | ➕ **PRD SPECIFIC** |
| **ORM** | SQLAlchemy | Not specified | ➕ **PRD SPECIFIC** |
| **Data Validation** | Pydantic | Not specified | ➕ **PRD SPECIFIC** |
| **Containerization** | Docker & Docker Compose | Not specified (likely in PaaS) | ⚠️ **DIVERGENT** |
| **Infrastructure** | AWS EC2 (t2.small), future K8s | Medical-grade PaaS (HIPAA/PHIPA compliant) | ⚠️ **DIVERGENT** |
| **Testing** | pytest, testcontainers (80% coverage) | Not specified | ➕ **PRD SPECIFIC** |
| **Frontend** | None (CLI/logs only) | React (web), React Native (mobile) | ➖ **PRODUCTION ONLY** |
| **AI/ML** | None | CNN for food image recognition, CV models | ➖ **PRODUCTION ONLY** |
| **MLOps** | None | Model deployment, offline testing, validation | ➖ **PRODUCTION ONLY** |
| **Data Integration** | Mock data generator (100 customers, 20 items) | DexCom CGM, photo/voice/text/barcode | ⚠️ **DIVERGENT** |
| **Monitoring** | Structured logging only (no Prometheus/Grafana) | Gap acknowledged ("a little bit blind"), being addressed | ⚠️ **BOTH LACKING** |
| **Compliance** | None | HIPAA/PHIPA required | ➖ **PRODUCTION ONLY** |
| **Scale** | Demo app (10 ops/sec), single instance | Hundreds of thousands → millions of users | ⚠️ **DIVERGENT** |
| **Use Case** | Order processing simulation (food orders) | Patient health data, food logging, CGM integration | ⚠️ **DIVERGENT** |
| **Team Size** | 1 (learning project) | 5-6 engineers | ⚠️ **DIVERGENT** |
| **Deployment Pattern** | Local Docker Compose + AWS EC2 + future K8s | Medical PaaS (infrastructure abstracted) | ⚠️ **DIVERGENT** |
| **Notifications** | Logging only (no email/SMS) | Not specified | ➕ **PRD SPECIFIC** |
| **Analytics** | Out of scope (Phase 2) | Longitudinal analysis, reporting | ➖ **PRODUCTION ONLY** |

### Key Insights

#### ✅ Strong Alignment (Kafka Learning Applicable to Production)
1. **Python + PostgreSQL + Kafka** - Core stack matches perfectly
2. **Food domain** - Both deal with food data (orders vs. nutrition/health)
3. **Streaming architecture** - Production migrating to Kafka for orchestration, PRD focuses on Kafka patterns
4. **Monitoring gaps** - Both acknowledge observability challenges

#### ⚠️ Strategic Divergences
1. **Scale**: PRD is learning-focused (10 ops/sec) vs. production (millions of users)
2. **Infrastructure**: PRD uses raw Docker/AWS vs. managed PaaS
3. **Data sources**: PRD uses mocks vs. production has real integrations (CGM, images)
4. **Compliance**: PRD has none, production requires HIPAA/PHIPA

#### 🎯 Learning Opportunity Alignment
This Kafka pipeline project directly teaches concepts relevant to production migration:
- **Kafka fundamentals** → Applies to agent/model orchestration
- **Producer/consumer patterns** → Relevant for Gen AI features (patient/clinic memory)
- **Partitioning strategy** → Scalable message distribution for millions of users
- **Error handling & retries** → Critical for medical-grade reliability
- **Monitoring approach** → Addresses acknowledged production gap

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

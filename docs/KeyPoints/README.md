# Kafka Learning - Key Points Documentation

This directory contains educational documentation explaining Apache Kafka concepts for experienced developers new to Kafka.

## Available Topics

### ✅ [Infrastructure](infrastructure.md)
Core Kafka infrastructure components and concepts:
- Zookeeper coordination layer
- Kafka brokers, topics, partitions, and offsets
- Consumer groups and load balancing
- Listeners and networking
- Persistence and retention policies
- Database integration patterns
- Bootstrap servers (with blockchain analogy)

### 🚧 Coming Soon

- **Producer Concepts** - Publishing messages, partition keys, delivery guarantees
- **Consumer Concepts** - Reading messages, offset management, rebalancing
- **Data Modeling** - Schema design, serialization, Pydantic validation
- **Testing Strategies** - Unit tests, integration tests with testcontainers
- **Deployment Patterns** - Docker Compose, AWS, Kubernetes considerations

## Learning Approach

Each document is written with:
- **Blockchain analogies** where relevant (partitions = blockchains, offsets = block height, etc.)
- **Practical examples** from this food ordering system
- **Key configurations** with explanations
- **Common gotchas** and best practices

## Quick Navigation

**Just starting?** Begin with [Infrastructure](infrastructure.md) to understand the foundation.

**Ready to write code?** Check Producer Concepts (coming soon) after infrastructure.

**Testing?** See Testing Strategies (coming soon) for unit and integration test patterns.

---

**Related Resources:**
- [Project README](../../README.md) - Project overview and tech stack comparison
- [PRD](../features/kafka-food-pipeline-PLANNED/prd.md) - Full requirements and specifications
- [Implementation Tasks](../features/kafka-food-pipeline-PLANNED/tasks.md) - Step-by-step implementation guide

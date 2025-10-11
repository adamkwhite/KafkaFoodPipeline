# Kafka Infrastructure - Key Learning Points

This document explains the foundational infrastructure components for Apache Kafka, written for experienced developers new to Kafka.

## Table of Contents
- [Zookeeper - Coordination Layer](#zookeeper---coordination-layer)
- [Kafka Broker - Core Concepts](#kafka-broker---core-concepts)
- [Listeners and Networking](#listeners-and-networking)
- [Persistence and Retention](#persistence-and-retention)
- [Database Integration Pattern](#database-integration-pattern)
- [Bootstrap Servers](#bootstrap-servers)

---

## Zookeeper - Coordination Layer

### What is Zookeeper?
Zookeeper is a distributed coordination service that manages Kafka cluster metadata. Think of it as the cluster's "brain" that keeps everything organized.

### Key Responsibilities:
1. **Metadata Management**
   - Tracks which brokers are alive (via heartbeats)
   - Stores topic configurations (partitions, replication factors)
   - Maintains partition assignments to brokers

2. **Controller Election**
   - Elects one broker as the "controller"
   - Controller coordinates partition leadership across cluster
   - If controller fails, Zookeeper elects a new one

3. **Consensus and Coordination**
   - Ensures all brokers agree on cluster state
   - Provides distributed locking mechanisms
   - Handles configuration changes atomically

### Blockchain Analogy
- Like a distributed ledger for **cluster state** (not message data)
- Ensures consensus on cluster configuration across all brokers
- Similar to how blockchain nodes maintain consensus on chain state
- Coordination layer for the Kafka network

### The Future: KRaft Mode
- **Kafka Raft (KRaft):** Kafka is moving away from Zookeeper dependency
- Uses **Raft consensus protocol** (similar to blockchain consensus algorithms)
- Simplifies deployment (one less system to manage)
- Better scalability for massive clusters
- **For learning:** Zookeeper is still standard and easier to understand

### Key Configuration
```yaml
ZOOKEEPER_CLIENT_PORT: 2181          # Client port - Kafka brokers connect here
ZOOKEEPER_TICK_TIME: 2000            # Heartbeat interval in milliseconds
```

---

## Kafka Broker - Core Concepts

### What is a Kafka Broker?
A Kafka broker is a server that stores and serves messages. In production, you have multiple brokers for redundancy and scale. For learning, one broker is sufficient.

### 1. Topics

**What are topics?**
- Named message streams (e.g., `food-orders`)
- Like a database table, but **append-only** and **distributed**
- Messages within a topic are categorized by subject

**Key Characteristics:**
- Durable: Messages persist to disk (not just in memory)
- Distributed: Partitions can be spread across brokers
- Ordered: Within each partition (not across partitions)
- Multi-subscriber: Many consumers can read same topic independently

**Example:**
```
Topic: food-orders
├── Partition 0: [order1, order4, order7, ...]
├── Partition 1: [order2, order5, order8, ...]
└── Partition 2: [order3, order6, order9, ...]
```

### 2. Partitions

**Why partitions?**
- Enable **parallel processing** (multiple consumers reading different partitions)
- Provide **scalability** (distribute load across brokers)
- Maintain **ordering guarantees** within each partition

**How partitioning works:**
- Messages with same key go to same partition (e.g., all orders from customer_id "CUST-001" → partition 2)
- Partition assignment: `hash(key) % number_of_partitions`
- No key? Round-robin distribution

**Blockchain Analogy:**
- **Partition = Blockchain:** Both are append-only, ordered, immutable logs
- **Offset = Block Height:** Position in the log (0, 1, 2, 3, ...)
- **Replication = Multiple Nodes:** Copies of partition across brokers (like blockchain nodes maintaining same chain)

**Key Insight:**
- Ordering guaranteed **within partition**, not across partitions
- Choose partition key carefully based on ordering requirements

### 3. Offsets

**What are offsets?**
- Position in a partition (like array index: 0, 1, 2, 3, ...)
- Each consumer tracks its own offset per partition
- **Committed offset** = "I've successfully processed up to here"

**Offset Management:**
```
Partition: [msg0, msg1, msg2, msg3, msg4, msg5, ...]
            ↑                    ↑
         offset=0            offset=4 (consumer position)
```

**Types of offsets:**
- **Current offset:** Next message to read
- **Committed offset:** Last successfully processed message (saved to Kafka)
- **Auto-commit:** Automatic periodic commits (risky - may lose messages)
- **Manual commit:** Commit after processing (safer - "at least once" delivery)

**Our approach:** Manual commit after database write (ensures no data loss)

### 4. Consumer Groups

**What are consumer groups?**
- Multiple consumers working together to process a topic
- Kafka automatically **load balances** partitions across group members
- Each partition assigned to **exactly one consumer** in a group

**Example with 3 partitions, 2 consumers:**
```
Consumer Group: order-processors
├── Consumer 1: Partitions 0, 1
└── Consumer 2: Partition 2
```

**Key Rules:**
1. Each partition → one consumer in group (ensures ordering)
2. Multiple groups can read same topic independently
3. Add consumer → Kafka rebalances partition assignments
4. Remove consumer → Kafka redistributes partitions to remaining consumers

**Blockchain Analogy:**
Like validator pools where work is distributed among validators, but each validator processes specific shards/partitions.

---

## Listeners and Networking

### Why Multiple Listeners?

Kafka needs to be accessible from **different network contexts**:
1. **Docker containers** (producer/consumer services) - use internal Docker network
2. **Host machine** (your laptop) - use localhost

### Listener Configuration

```yaml
KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
```

**Two listeners:**
1. **Internal:** `kafka:29092` - Used by services inside Docker network
   - Other containers use hostname `kafka` (Docker DNS resolution)
   - Port 29092 internal to Docker network

2. **External:** `localhost:9092` - Used from host machine
   - Your laptop connects to `localhost:9092`
   - Useful for CLI tools: `kafka-console-producer`, `kafka-console-consumer`

### Advertised Listeners

**Why "advertised"?**
- Broker tells clients: "Here's how to reach me"
- Clients discover topology, then connect using advertised addresses
- Critical for multi-broker clusters where clients need to find all brokers

**Common Gotcha:**
If advertised listeners are wrong, clients can connect initially (bootstrap) but fail when trying to produce/consume messages.

---

## Persistence and Retention

### Kafka is NOT a Traditional Message Queue

**Traditional Queue (RabbitMQ, SQS):**
- Message consumed → message deleted
- Message available to one consumer
- No replay capability

**Kafka:**
- Message consumed → **message stays** (for retention period)
- Message available to multiple consumers independently
- **Full replay capability** (consumers can re-read from offset 0)

### Retention Settings

```yaml
KAFKA_LOG_RETENTION_HOURS: 168    # 7 days (7 × 24 hours)
KAFKA_LOG_SEGMENT_BYTES: 1073741824  # 1GB segments
```

**Retention by time:**
- Messages kept for configured duration (default: 7 days in our setup)
- After retention period, messages deleted (oldest first)
- Consumers can read any message within retention window

**Retention by size:**
- Can also configure max topic size
- Oldest messages deleted when limit reached

**Compaction (Advanced):**
- Alternative retention mode: keep only latest value per key
- Useful for state snapshots (e.g., "current user profile")

### Use Cases Enabled by Retention

1. **Replay/Reprocessing:** Fix bug in consumer, replay messages to recompute
2. **New Consumers:** Add new analytics service that reads historical data
3. **Debugging:** Examine actual messages that caused issues
4. **Audit Trail:** Keep immutable log of all events

---

## Database Integration Pattern

### Why Both Kafka and Database?

They serve different purposes:

**Kafka (Event Stream):**
- **What happened, when, in what order**
- Immutable event log
- Source of truth for all state changes
- Example: "Order created", "Order paid", "Order shipped", "Order delivered"

**Database (Current State):**
- **What's true right now**
- Mutable state
- Optimized for queries
- Example: `order.status = "delivered"`

### Event Sourcing Pattern

```
Kafka Log (Source of Truth):
  t=0: {"event": "OrderCreated", "order_id": "ORD-001", "status": "pending"}
  t=1: {"event": "OrderPaid", "order_id": "ORD-001", "status": "paid"}
  t=2: {"event": "OrderShipped", "order_id": "ORD-001", "status": "shipped"}
  t=3: {"event": "OrderDelivered", "order_id": "ORD-001", "status": "delivered"}

Database (Materialized View):
  orders table:
  | order_id  | status    | last_updated |
  |-----------|-----------|--------------|
  | ORD-001   | delivered | t=3          |
```

### Key Benefits

1. **Rebuild Database:** Can regenerate DB by replaying Kafka log
2. **Multiple Views:** Build different databases/caches from same Kafka stream
3. **Time Travel:** Query "what did database look like at time T?"
4. **Audit Trail:** Every change captured in Kafka forever (within retention)

### Our Implementation

- **Producer** writes orders to Kafka topic `food-orders`
- **Consumer** reads from Kafka, writes to PostgreSQL
- **Pattern:** "Process then Commit" - only commit offset after successful DB write
- Ensures **at-least-once** processing (better than losing data)

---

## Bootstrap Servers

### What are Bootstrap Servers?

**Bootstrap servers** are the initial contact points for Kafka clients to discover the cluster.

### How It Works

1. **Client connects** to bootstrap server(s): `localhost:9092`
2. **Broker responds** with cluster metadata:
   - List of all brokers in cluster
   - Topic metadata (partitions, leaders)
   - Where to send/receive messages
3. **Client discovers** full cluster topology
4. **Client connects** directly to appropriate brokers for produce/consume

### Blockchain Analogy

**Very similar to blockchain peer discovery:**
- **Bootstrap nodes = Seed nodes** in blockchain
- Connect to one known peer, discover entire network
- After initial connection, learn about all other nodes/brokers
- Don't need to hardcode every peer/broker address

### Configuration

```python
# Only need one bootstrap server to start
# (In production, provide multiple for redundancy)
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

**Production Best Practice:**
```python
# List multiple brokers in case one is down
KAFKA_BOOTSTRAP_SERVERS=broker1:9092,broker2:9092,broker3:9092
```

### Key Points

- You only need **one working broker** from bootstrap list to connect
- Client automatically discovers all other brokers
- Bootstrap servers don't need to include every broker (just enough to start)
- After connection, clients get full cluster topology

---

## Quick Reference

### Start Infrastructure
```bash
docker-compose up -d
```

### View Logs
```bash
docker-compose logs -f kafka        # Kafka broker logs
docker-compose logs -f zookeeper    # Zookeeper logs
docker-compose logs -f postgres     # PostgreSQL logs
```

### Kafka CLI Tools (from host)
```bash
# Produce messages
kafka-console-producer --bootstrap-server localhost:9092 --topic food-orders

# Consume messages from beginning
kafka-console-consumer --bootstrap-server localhost:9092 --topic food-orders --from-beginning

# List topics
kafka-topics --bootstrap-server localhost:9092 --list

# Describe topic
kafka-topics --bootstrap-server localhost:9092 --describe --topic food-orders
```

### PostgreSQL Access
```bash
docker exec -it kafka-postgres psql -U kafka_user -d food_orders
```

### Check Service Health
```bash
docker-compose ps
```

---

## Summary

**Zookeeper:** Cluster coordination and metadata management (moving to KRaft)

**Kafka Broker:** Core message streaming platform
- **Topics:** Named message streams
- **Partitions:** Parallel processing units (like blockchains - append-only logs)
- **Offsets:** Position tracking (like block height)
- **Consumer Groups:** Load balancing and parallel consumption

**Persistence:** Messages stay for retention period (not deleted after consumption)

**Pattern:** Kafka = event stream (source of truth), Database = current state (materialized view)

**Bootstrap:** Initial connection points for cluster discovery (like blockchain seed nodes)

---

## Related Documentation
- [Environment Variables](../features/kafka-food-pipeline-PLANNED/prd.md#technical-considerations)
- [PRD - Technical Specifications](../features/kafka-food-pipeline-PLANNED/prd.md)
- [Docker Compose Configuration](../../docker-compose.yml)

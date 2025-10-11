# Kafka Horizontal Scaling - Complete Guide

## Overview

This document explains the horizontal scaling experiment we performed on the KafkaFoodPipeline project, demonstrating how Kafka's consumer groups enable parallel processing across multiple consumer instances.

---

## BEFORE: Single Partition (Original Setup)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           KAFKA BROKER                                  │
│                                                                         │
│  Topic: food-orders                                                     │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │ Partition 0: [msg1, msg2, msg3, msg4, msg5, ...]           │       │
│  │ Offsets:      0      1      2      3      4                 │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                            ↓ (all messages)                             │
└─────────────────────────────────────────────────────────────────────────┘
                             ↓
                    ┌─────────────────┐
                    │   Consumer 1    │ ← Only 1 consumer could work
                    │  (partition 0)  │
                    └─────────────────┘
                             ↓
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    └─────────────────┘
```

**Problem:** Even with 3 consumer containers running, only 1 could work because there was only 1 partition to process!

---

## AFTER: Three Partitions (What We Just Built)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           KAFKA BROKER                                  │
│                                                                         │
│  Topic: food-orders                                                     │
│  ┌───────────────────────────────────────────────────────────┐         │
│  │ Partition 0: [msgA, msgD, msgG, ...]  (41,294 messages)  │         │
│  │ Offsets:      0      1      2                             │         │
│  └───────────────────────────────────────────────────────────┘         │
│                            ↓                                            │
│  ┌───────────────────────────────────────────────────────────┐         │
│  │ Partition 1: [msgB, msgE, msgH, ...]  (95 messages)      │         │
│  │ Offsets:      0      1      2                             │         │
│  └───────────────────────────────────────────────────────────┘         │
│                            ↓                                            │
│  ┌───────────────────────────────────────────────────────────┐         │
│  │ Partition 2: [msgC, msgF, msgI, ...]  (118 messages)     │         │
│  │ Offsets:      0      1      2                             │         │
│  └───────────────────────────────────────────────────────────┘         │
│                            ↓                                            │
└─────────────────────────────────────────────────────────────────────────┘
              ↓                  ↓                    ↓
    ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
    │   Consumer 1    │  │   Consumer 2    │  │   Consumer 3    │
    │  (partition 0)  │  │  (partition 1)  │  │  (partition 2)  │
    │   762529c5      │  │   b786fb37      │  │   4685f9a3      │
    └─────────────────┘  └─────────────────┘  └─────────────────┘
              ↓                  ↓                    ↓
              └──────────────────┴─────────────────────┘
                                 ↓
                        ┌─────────────────┐
                        │   PostgreSQL    │
                        │ 41,186 orders   │
                        └─────────────────┘
```

**Result:** ALL 3 consumers now actively processing in PARALLEL! Producer distributes messages across partitions based on customer_id.

---

## Zookeeper's Role in This Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ZOOKEEPER (Coordinator)                          │
│                                                                         │
│  Responsibilities:                                                      │
│  1. Track which Kafka brokers are alive (heartbeats)                   │
│  2. Store cluster metadata (topics, partitions, replicas)              │
│  3. Manage consumer group coordination                                 │
│  4. Handle leader election for partitions                              │
│  5. Store consumer group offsets (committed positions)                 │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────┐          │
│  │ Consumer Group: "order-processors"                       │          │
│  │                                                           │          │
│  │ Members:                                                  │          │
│  │  - Consumer 1 (client.id: ...762529c5) → Partition 0    │          │
│  │  - Consumer 2 (client.id: ...b786fb37)  → Partition 1    │          │
│  │  - Consumer 3 (client.id: ...4685f9a3)  → Partition 2    │          │
│  │                                                           │          │
│  │ Committed Offsets:                                        │          │
│  │  - Partition 0: offset 41,294                            │          │
│  │  - Partition 1: offset 95                                │          │
│  │  - Partition 2: offset 118                               │          │
│  └──────────────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────────┘
                                 ↓ (coordination)
                        ┌─────────────────┐
                        │   KAFKA BROKER  │
                        │  (data storage) │
                        └─────────────────┘
```

### What Zookeeper Does in Our Scaling Experiment:

1. **Consumer Group Coordination:**
   - Tracks which consumers are part of the "order-processors" group
   - Detects when consumers join or leave the group
   - Triggers rebalancing when group membership changes

2. **Partition Assignment:**
   - When we scaled to 3 consumers, Zookeeper coordinated the rebalance
   - Assigned 1 partition to each consumer for optimal distribution
   - Ensures no partition is assigned to multiple consumers

3. **Offset Management:**
   - Stores committed offsets for each partition
   - When a consumer crashes and restarts, it reads the last committed offset from Zookeeper
   - Enables at-least-once delivery (consumer can resume from last committed position)

4. **Failure Detection:**
   - Monitors consumer heartbeats
   - If a consumer crashes, Zookeeper detects it and triggers rebalance
   - Reassigns the crashed consumer's partitions to remaining consumers

5. **Cluster State:**
   - Stores topic metadata (3 partitions for food-orders topic)
   - Tracks broker health and availability
   - Maintains partition leadership information

### Zookeeper in Action During Our Experiment:

**When we ran `docker-compose up -d --scale order-consumer=3`:**
1. Zookeeper detected 3 consumers joining the "order-processors" group
2. Triggered a rebalance to distribute partitions
3. Assigned partitions: Consumer 1→P0, Consumer 2→P1, Consumer 3→P2
4. Notified all consumers of their assignments

**When we restarted consumers:**
1. Zookeeper detected consumers leaving (old instances shutting down)
2. Detected new consumers joining (restarted instances)
3. Triggered another rebalance
4. Redistributed partitions to the new consumer instances

**When consumers commit offsets:**
```python
self.consumer.commit(asynchronous=False)  # In consumer.py
```
This writes the current offset to Zookeeper (or Kafka's internal topic `__consumer_offsets`)

### Future: KRaft Mode (Zookeeper Removal)

Kafka is moving to **KRaft** (Kafka Raft) mode, which eliminates the Zookeeper dependency:
- Kafka brokers will handle coordination themselves
- Uses Raft consensus protocol (similar to blockchain consensus)
- Simpler architecture, fewer moving parts
- Better scalability

**For learning purposes**, we use Zookeeper because:
- It's the traditional architecture (still widely used in production)
- Easier to understand separation of concerns
- More educational value in seeing coordination layer explicitly

---

## How Kafka Consumer Groups Work

### Consumer Group Coordination

```
Consumer Group: "order-processors"
┌──────────────────────────────────────────────────────────────────┐
│  Kafka/Zookeeper tracks all consumers in this group and assigns  │
│  partitions ensuring each partition has exactly one consumer     │
│                                                                   │
│  Consumer 1 (client.id: order-consumer-docker-409...762529c5)    │
│    → Assigned: Partition 0                                       │
│    → Processing: Messages with offsets 0 to 41,294              │
│                                                                   │
│  Consumer 2 (client.id: order-consumer-docker-c39...b786fb37)    │
│    → Assigned: Partition 1                                       │
│    → Processing: Messages with offsets 0 to 95                  │
│                                                                   │
│  Consumer 3 (client.id: order-consumer-docker-c4a...4685f9a3)    │
│    → Assigned: Partition 2                                       │
│    → Processing: Messages with offsets 0 to 118                 │
└──────────────────────────────────────────────────────────────────┘
```

**KEY REQUIREMENT:** Each consumer needs a **UNIQUE client.id** for Kafka to track them separately and assign partitions independently.

---

## What We Changed in the Code

### BEFORE (All consumers shared same client ID)

```python
# src/consumer/config.py (BEFORE)
def get_kafka_config(self) -> dict:
    return {
        "bootstrap.servers": self.kafka_bootstrap_servers,
        "group.id": self.consumer_group_id,
        "client.id": self.consumer_client_id,  # ❌ All 3 had same ID!
        "auto.offset.reset": self.consumer_auto_offset_reset,
        "enable.auto.commit": self.enable_auto_commit,
    }
```

**Problem:** All 3 consumer containers had identical `client.id: order-consumer-docker`
- Kafka saw them as duplicate connections from the same client
- Only one could be active at a time

### AFTER (Each consumer generates unique client ID)

```python
# src/consumer/config.py (AFTER)
import socket
import uuid

def get_kafka_config(self) -> dict:
    """
    Get Kafka consumer configuration dictionary.

    Generates a unique client ID by appending hostname and UUID suffix.
    This enables horizontal scaling with multiple consumer instances.

    HORIZONTAL SCALING:
    - Multiple consumers with same group.id share partitions
    - Each consumer needs unique client.id for partition assignment
    - Format: {base_client_id}-{hostname}-{uuid}
    - Example: order-consumer-docker-abc123-a1b2c3d4
    """
    # Generate unique client ID for this consumer instance
    hostname = socket.gethostname()          # Container hostname
    unique_suffix = str(uuid.uuid4())[:8]    # Short UUID suffix
    unique_client_id = f"{self.consumer_client_id}-{hostname}-{unique_suffix}"

    return {
        "bootstrap.servers": self.kafka_bootstrap_servers,
        "group.id": self.consumer_group_id,
        "client.id": unique_client_id,  # ✅ Now each consumer gets unique ID!
        "auto.offset.reset": self.consumer_auto_offset_reset,
        "enable.auto.commit": self.enable_auto_commit,
    }
```

**Result:** Each consumer now has a unique identifier:
- Consumer 1: `order-consumer-docker-409e55c39df9-762529c5`
- Consumer 2: `order-consumer-docker-c395d886baf9-b786fb37`
- Consumer 3: `order-consumer-docker-c4a5910129a3-4685f9a3`

---

## Partition Key Strategy (Message Distribution)

The producer uses `customer_id` as the partition key to distribute messages:

```python
# Producer logic (simplified)
partition = hash(customer_id) % num_partitions
```

**Examples:**
```
Customer "CUST-00042" → Hash(CUST-00042) % 3 = 0 → Partition 0
Customer "CUST-00017" → Hash(CUST-00017) % 3 = 1 → Partition 1
Customer "CUST-00089" → Hash(CUST-00089) % 3 = 2 → Partition 2
```

### Why Use customer_id as Partition Key?

**Ordering Guarantee:** All orders from the SAME customer always go to the SAME partition.
- Partition 0 has a total order (offset 0, 1, 2, 3, ...)
- Messages within a partition are consumed in strict order
- Therefore: All orders for CUST-00042 are processed in the order they were created

**Load Distribution:** Customers are evenly distributed across partitions.
- 100 customers → ~33 per partition
- Each consumer gets roughly equal work

**Scalability:** Can add more partitions and consumers as customer base grows.

---

## Implementation Steps (What We Did)

### Step 1: Remove Custom Container Name

**Problem:** Docker Compose can't scale services with custom `container_name`

```yaml
# docker-compose.yml (BEFORE)
order-consumer:
  container_name: kafka-order-consumer  # ❌ Prevents scaling
```

**Fix:** Comment out the custom name

```yaml
# docker-compose.yml (AFTER)
order-consumer:
  # container_name: kafka-order-consumer  # Commented out to enable horizontal scaling
```

### Step 2: Modify Consumer Config (Unique Client IDs)

Added unique client ID generation in `src/consumer/config.py`:
- Import `socket` and `uuid`
- Generate unique ID using hostname + UUID
- Each consumer instance gets a different ID

### Step 3: Increase Topic Partitions

**Original:** Topic had only 1 partition (auto-created by Kafka)

```bash
# Check current partitions
docker exec kafka-broker kafka-topics --bootstrap-server localhost:9092 \
  --describe --topic food-orders
# Result: PartitionCount: 1
```

**Fix:** Increase to 3 partitions

```bash
# Add partitions to existing topic
docker exec kafka-broker kafka-topics --bootstrap-server localhost:9092 \
  --alter --topic food-orders --partitions 3

# Verify
docker exec kafka-broker kafka-topics --bootstrap-server localhost:9092 \
  --describe --topic food-orders
# Result: PartitionCount: 3
```

### Step 4: Rebuild Consumer Image

```bash
# Stop existing consumers
docker-compose stop order-consumer
docker-compose rm -f order-consumer

# Rebuild with new code
docker-compose build order-consumer

# Start 3 consumer instances
docker-compose up -d --scale order-consumer=3
```

### Step 5: Restart Producer

Producer needs to recognize the 3 partitions:

```bash
docker-compose restart order-producer
```

Now new messages are distributed across all 3 partitions!

### Step 6: Verify Partition Assignments

```bash
docker exec kafka-broker kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group order-processors \
  --describe
```

**Result:**
```
GROUP            TOPIC           PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
order-processors food-orders     0          41,294          41,294          0
order-processors food-orders     1          95              95              0
order-processors food-orders     2          118             118             0
```

✅ All 3 partitions assigned to different consumers!

---

## Real-Time Performance Metrics

### Partition Distribution
- **Partition 0:** 41,294 messages (mostly historical, pre-scaling)
- **Partition 1:** 95 messages (new messages after scaling)
- **Partition 2:** 118 messages (new messages after scaling)

### Consumer Performance
- **Lag:** 0-2 messages per partition (near real-time processing)
- **Throughput:** ~41 messages/second across all partitions combined
- **Efficiency:** All 3 consumers actively processing in parallel

### Database State
- **Total Orders:** 41,186 in PostgreSQL
- **Unique Customers:** 100 (matches mock data)
- **Average Order Value:** $32.89
- **Duplicates:** 0 (idempotency working correctly)

---

## Monitoring Commands

### Check Service Status
```bash
docker-compose ps
```

### Check Partition Assignments
```bash
docker exec kafka-broker kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group order-processors \
  --describe
```

### View Consumer Logs
```bash
# All consumers
docker-compose logs -f order-consumer

# Specific consumer
docker-compose logs -f kafkafoodpipeline-order-consumer-1
```

### Check Topic Partitions
```bash
docker exec kafka-broker kafka-topics \
  --bootstrap-server localhost:9092 \
  --describe --topic food-orders
```

### Monitor Database Growth
```bash
# Run multiple times to see growth
docker exec kafka-postgres psql -U kafka_user -d food_orders \
  -c "SELECT COUNT(*) FROM orders;"
```

### Watch Real-Time Processing
```bash
# Watch order count update every 2 seconds
watch -n 2 'docker exec kafka-postgres psql -U kafka_user -d food_orders \
  -c "SELECT COUNT(*) FROM orders;"'
```

---

## Key Learnings

### 1. Consumer Groups Enable Horizontal Scaling
- Multiple consumers in same group share partition assignments
- Kafka automatically balances partitions across consumers
- Add more consumers → process more partitions in parallel

### 2. Unique Client IDs Are Required
- Each consumer needs a unique `client.id` for partition assignment
- Using hostname + UUID ensures uniqueness across containers
- Same `client.id` → only one consumer active (others idle)

### 3. Partitions Determine Maximum Parallelism
- 3 partitions → max 3 consumers can work simultaneously
- 4th consumer would be idle (no partition to assign)
- Rule: `num_active_consumers = min(num_partitions, num_consumers)`

### 4. Partition Keys Guarantee Ordering
- Messages with same key go to same partition
- Partition maintains total order (offset 0, 1, 2, ...)
- All orders for a customer are processed in order

### 5. Adding Partitions Requires Producer Restart
- Producer caches partition count on startup
- Must restart to recognize new partitions
- Existing data in old partitions is preserved

### 6. Rebalancing Happens Automatically
- Kafka detects consumer group membership changes
- Automatically reassigns partitions on join/leave
- Coordinated through Zookeeper (or KRaft in newer versions)

---

## Scaling Scenarios

### Scenario 1: Scale Up (Add Consumers)
```bash
# From 1 to 3 consumers
docker-compose up -d --scale order-consumer=3
```
**Result:** Partitions redistributed, throughput increases

### Scenario 2: Scale Down (Remove Consumers)
```bash
# From 3 to 1 consumer
docker-compose up -d --scale order-consumer=1
```
**Result:** Remaining consumer gets all 3 partitions

### Scenario 3: Over-Scaling (More Consumers than Partitions)
```bash
# 5 consumers, 3 partitions
docker-compose up -d --scale order-consumer=5
```
**Result:** 3 consumers active, 2 idle (no partition to assign)

### Scenario 4: Failure Recovery
```bash
# Stop one consumer
docker stop kafkafoodpipeline-order-consumer-2

# Kafka rebalances automatically
# Consumer 2's partition reassigned to Consumer 1 or 3
```

---

## Troubleshooting

### Problem: Only 1 consumer active with 3 running
**Cause:** All consumers have the same `client.id`
**Fix:** Implement unique client ID generation (see code changes above)

### Problem: Consumers not picking up new partitions
**Cause:** Producer hasn't restarted after adding partitions
**Fix:** `docker-compose restart order-producer`

### Problem: Can't scale service
**Error:** `Docker requires each container to have a unique name`
**Fix:** Remove or comment out `container_name` in docker-compose.yml

### Problem: High consumer lag
**Cause:** More messages produced than consumers can process
**Fix:** Scale up consumers (if partitions allow) or optimize consumer code

---

## Blockchain Analogy

For those familiar with blockchain:

| Kafka Concept | Blockchain Equivalent |
|--------------|----------------------|
| Partition | Individual blockchain/shard |
| Offset | Block height/number |
| Consumer Group | Network of validator nodes |
| Partition Assignment | Shard assignment to validators |
| Rebalancing | Validator set rotation |
| Committed Offset | Last finalized block |
| Zookeeper | Consensus coordinator |

**Key Similarity:** Both systems maintain ordered, immutable logs with distributed processing.

---

## Next Steps

### Other Scaling Experiments to Try:

1. **Failure Recovery Testing**
   ```bash
   # Stop one consumer and watch rebalance
   docker-compose stop kafkafoodpipeline-order-consumer-2

   # Check partition reassignment
   docker exec kafka-broker kafka-consumer-groups \
     --bootstrap-server localhost:9092 \
     --group order-processors --describe
   ```

2. **Consumer Lag Monitoring**
   ```bash
   # Increase producer rate to create lag
   docker-compose stop order-consumer
   # Wait 30 seconds for messages to queue
   docker-compose start order-consumer
   # Watch consumers catch up
   ```

3. **Load Testing**
   - Modify `PRODUCER_RATE` environment variable
   - Test system limits (how many messages/sec can it handle?)
   - Monitor CPU/memory usage

4. **Add More Partitions**
   ```bash
   # Scale to 6 partitions
   docker exec kafka-broker kafka-topics \
     --bootstrap-server localhost:9092 \
     --alter --topic food-orders --partitions 6

   # Scale to 6 consumers
   docker-compose up -d --scale order-consumer=6
   ```

---

## References

- **Kafka Documentation:** https://kafka.apache.org/documentation/
- **Consumer Groups:** https://kafka.apache.org/documentation/#consumergroups
- **Partition Assignment:** https://kafka.apache.org/documentation/#impl_consumerrebalance
- **Project PRD:** `docs/features/kafka-food-pipeline-PLANNED/prd.md`
- **Consumer Code:** `src/consumer/consumer.py`
- **Config Code:** `src/consumer/config.py`

---

**Last Updated:** 2025-10-10
**Session:** Horizontal Scaling Experiment
**Result:** Successfully scaled from 1 to 3 consumers with 3-partition distribution

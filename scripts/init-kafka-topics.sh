#!/bin/bash
# ==============================================================================
# Kafka Topic Initialization Script
# ==============================================================================
#
# This script creates the 'food-orders' topic with specific configuration.
#
# WHY CREATE TOPICS EXPLICITLY?
# - Control partition count (affects parallelism and ordering)
# - Set retention policies (how long messages are kept)
# - Configure replication factor (fault tolerance)
# - Better than auto-creation for production-like setup
#
# LEARNING OBJECTIVES:
# - Understand kafka-topics command
# - Learn about partition configuration
# - See retention policy settings
#

set -e  # Exit on any error

echo "======================================================================"
echo "Kafka Topic Initialization"
echo "======================================================================"

# Configuration
KAFKA_BROKER="localhost:9092"
TOPIC_NAME="food-orders"
PARTITIONS=3
RETENTION_MS=604800000  # 7 days in milliseconds (7 * 24 * 60 * 60 * 1000)

echo ""
echo "Waiting for Kafka broker to be ready..."
echo "  Broker: $KAFKA_BROKER"
echo ""

# Wait for Kafka to be ready (max 60 seconds)
RETRIES=60
COUNT=0
until kafka-topics --bootstrap-server $KAFKA_BROKER --list > /dev/null 2>&1; do
    COUNT=$((COUNT+1))
    if [ $COUNT -ge $RETRIES ]; then
        echo "❌ ERROR: Kafka broker not ready after ${RETRIES} seconds"
        exit 1
    fi
    echo "  Waiting for Kafka... (attempt $COUNT/$RETRIES)"
    sleep 1
done

echo "✅ Kafka broker is ready!"
echo ""

# Check if topic already exists
if kafka-topics --bootstrap-server $KAFKA_BROKER --list | grep -q "^${TOPIC_NAME}$"; then
    echo "ℹ️  Topic '$TOPIC_NAME' already exists. Describing current configuration..."
    echo ""
    kafka-topics --bootstrap-server $KAFKA_BROKER --describe --topic $TOPIC_NAME
    echo ""
    echo "To delete and recreate: kafka-topics --bootstrap-server $KAFKA_BROKER --delete --topic $TOPIC_NAME"
    exit 0
fi

echo "Creating topic: $TOPIC_NAME"
echo "  Partitions: $PARTITIONS"
echo "  Retention: 7 days (${RETENTION_MS}ms)"
echo ""

# ==============================================================================
# CREATE TOPIC
# ==============================================================================
#
# KAFKA-TOPICS COMMAND EXPLAINED:
#
# --bootstrap-server: Kafka broker address (uses bootstrap server to discover cluster)
# --create: Create a new topic
# --topic: Name of the topic
# --partitions: Number of partitions (enables parallel processing)
# --replication-factor: Number of copies (1 for single broker, 3+ for production)
# --config: Additional topic-level configuration
#
# PARTITION COUNT (3):
# - Allows up to 3 consumers in consumer group to process in parallel
# - Each partition maintains message ordering
# - More partitions = more parallelism (but more overhead)
# - Rule of thumb: partitions >= expected max consumers
#
# RETENTION POLICY:
# - retention.ms: How long to keep messages (milliseconds)
# - 7 days = 604,800,000 ms
# - After 7 days, oldest messages deleted
# - Consumers can replay any message within this window
#
# REPLICATION FACTOR (1):
# - Only 1 copy (we have 1 broker)
# - Production: 3+ for fault tolerance
# - If broker fails, messages with replication=1 are lost
#

kafka-topics --bootstrap-server $KAFKA_BROKER \
    --create \
    --topic $TOPIC_NAME \
    --partitions $PARTITIONS \
    --replication-factor 1 \
    --config retention.ms=$RETENTION_MS

echo ""
echo "✅ Topic created successfully!"
echo ""

# ==============================================================================
# DESCRIBE TOPIC
# ==============================================================================
# Show detailed information about the created topic

echo "Topic details:"
echo ""
kafka-topics --bootstrap-server $KAFKA_BROKER --describe --topic $TOPIC_NAME

echo ""
echo "======================================================================"
echo "Topic initialization complete!"
echo "======================================================================"
echo ""
echo "NEXT STEPS:"
echo "  • Verify topic: kafka-topics --bootstrap-server $KAFKA_BROKER --list"
echo "  • Test produce: kafka-console-producer --bootstrap-server $KAFKA_BROKER --topic $TOPIC_NAME"
echo "  • Test consume: kafka-console-consumer --bootstrap-server $KAFKA_BROKER --topic $TOPIC_NAME --from-beginning"
echo ""
echo "PARTITION DETAILS:"
echo "  • Partition 0: Will receive ~33% of messages"
echo "  • Partition 1: Will receive ~33% of messages"
echo "  • Partition 2: Will receive ~33% of messages"
echo "  • Distribution based on hash(customer_id) % 3"
echo ""
echo "CONSUMER GROUP BEHAVIOR:"
echo "  • 1 consumer: Reads all 3 partitions"
echo "  • 2 consumers: One gets 2 partitions, one gets 1 partition"
echo "  • 3 consumers: Each gets exactly 1 partition (perfect balance)"
echo "  • 4+ consumers: Some consumers idle (more consumers than partitions)"
echo ""

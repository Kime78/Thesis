import logging
from kafka import KafkaConsumer

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set logging level to INFO
    format='%(asctime)s - %(levelname)s - %(message)s'  # Log format
)
logger = logging.getLogger(__name__)

# Kafka Consumer Configuration
consumer = KafkaConsumer(
    'file-chunks',  # Topic name
    bootstrap_servers=['kafka:29092'],  # Kafka broker address
    auto_offset_reset='earliest',  # Start reading from the earliest message
    value_deserializer=lambda x: x  # Deserialize messages as raw bytes
)

logger.info("Starting consumer...")
chunk_count = 0  # Counter for the number of chunks received

try:
    for message in consumer:
        chunk_count += 1  # Increment the counter for each message
        logger.info(f"Received chunk {chunk_count}")

    logger.info(f"Total chunks received: {chunk_count}")
except Exception as e:
    logger.error(f"Error in consumer: {e}")
finally:
    chunk_count = 0
    consumer.close()
    logger.info("Consumer closed.")
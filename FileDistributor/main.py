import base64
import json
import logging
from kafka import KafkaConsumer
from peewee import *
from peewee import IntegrityError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database setup
db = PostgresqlDatabase(
    'file_metadata',
    host='postgres',
    port=5432,
    user='postgres',
    password='postgres',
    autoconnect=False
)

class FileMetadata(Model):
    file_uuid = TextField()
    file_name = TextField()
    file_size = IntegerField()
    content_type = TextField()
    chunk_uuid = TextField()
    chunk_index = IntegerField()
    chunk_size = IntegerField()
    stored_at = IntegerField(null=True)  # Allow NULL values

    class Meta:
        database = db
        db_table = 'file_metadata'

def initialize_db():
    """Initialize database connection and create tables"""
    try:
        db.connect()
        db.create_tables([FileMetadata], safe=True)
        logger.info("Database connection established and tables verified")
    except OperationalError as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

def save_metadata_to_db(metadata):
    """Save metadata to database with conflict handling"""
    try:
        FileMetadata.create(
            file_uuid=metadata["file_uuid"],
            file_name=metadata["file_name"],
            file_size=metadata["file_size"],
            content_type=metadata["content_type"],
            chunk_uuid=metadata["chunk_uuid"],
            chunk_index=metadata["chunk_index"],
            chunk_size=metadata["chunk_size"],
            stored_at=None  # Will be set to NULL (ensure your DB schema allows this)
        )
        logger.debug(f"Inserted metadata for chunk {metadata['chunk_uuid']}")
    except IntegrityError as e:
        logger.warning(f"Duplicate chunk {metadata['chunk_uuid']} {e}- skipping")
    except Exception as e:
        logger.error(f"Failed to save metadata: {e}", exc_info=True)
        raise

def parse_received_data(received_data: bytes):
    """Parse Kafka message into metadata and chunk"""
    try:
        metadata_encoded, chunk = received_data.split(b"\n\n----METADATA----\n\n", 1)
        metadata_json = base64.b64decode(metadata_encoded).decode('utf-8')
        return json.loads(metadata_json), chunk
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error("Failed to parse message data")
        raise

def start_consumer():
    """Start Kafka consumer and process messages"""
    consumer = KafkaConsumer(
        'file-chunks',
        bootstrap_servers=['kafka:29092'],
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        value_deserializer=lambda x: x
    )

    logger.info("Consumer started. Waiting for messages...")
    processed_count = 0

    try:
        for message in consumer:
            logger.info(f"Received message at offset {message.offset}")
            try:
                metadata, chunk = parse_received_data(message.value)
                logger.info(f"Processing chunk {metadata['chunk_uuid']} "
                           f"(index {metadata['chunk_index']})")
                
                save_metadata_to_db(metadata)
                processed_count += 1
                
                logger.debug(f"Successfully processed chunk {metadata['chunk_uuid']}")
            except Exception as e:
                logger.error(f"Failed to process message: {e}", exc_info=True)
                
    except KeyboardInterrupt:
        logger.info("Consumer shutdown requested")
    finally:
        consumer.close()
        db.close()
        logger.info(f"Consumer stopped. Total chunks processed: {processed_count}")

if __name__ == "__main__":
    initialize_db()
    start_consumer()
import asyncio
import base64
from datetime import datetime
import json
from aiokafka import AIOKafkaConsumer
import grpc
from grpc import aio as aiogrpc
import chunk_pb2
import chunk_pb2_grpc
import logging
from database import create_tables, file_metadata, database
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

nodes = [
    "storage-node1:50051",
    "storage-node2:50051",
    "storage-node3:50051",
    "storage-node4:50051"
]

rr = 0

logger.info(f"GOT REPLICATION FACTOR = {os.getenv("REPLICATION_FACTOR", "3")}")

def parse_received_data(received_data: bytes):
        """Parse Kafka message into metadata and chunk"""
        try:
            metadata_encoded, chunk = received_data.split(b"\n\n----METADATA----\n\n", 1)
            metadata_json = base64.b64decode(metadata_encoded).decode('utf-8')
            return json.loads(metadata_json), chunk
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error("Failed to parse message data")
            raise

async def send_to_storage_node(message: bytes) -> str:
    """Send chunk to storage node via gRPC"""
    metadata, chunk_data = parse_received_data(message)

    logger.info(f"Attempting to send chunk {metadata}")
    async with aiogrpc.insecure_channel(metadata["storage_node"]) as channel:
        stub = chunk_pb2_grpc.ChunkServiceStub(channel)
        response = await stub.StoreChunk(
            chunk_pb2.Chunk(id=metadata["chunk_uuid"], data=message)
        )
        return response.message

async def process_message(message, db):
    
    metadata, chunk = parse_received_data(message.value)
    global rr
    global nodes
    for replica in range(0, int(os.getenv("REPLICATION_FACTOR", "3"))):
        metadata["storage_node"] = nodes[rr] 
        rr = (rr + 1) % len(nodes)
        logger.info(f"Chosen storage node: {metadata["storage_node"]}")
        # Save initial metadata with "pending" status
        metadata["status"] = "pending"
        metadata["stored_at"] = None

        query = file_metadata.insert().values(**metadata)
        await db.execute(query)
        
        try:
            # Send to storage node
            m = base64.b64encode(json.dumps(metadata).encode()).decode()
            chunk_with_metadata = f"{m}\n\n----METADATA----\n\n".encode() + chunk
            await send_to_storage_node(chunk_with_metadata)
            logger.info("Am ajuns aici 1")
            # Update status to "stored"
            query = file_metadata.update() \
                .where(file_metadata.c.chunk_uuid == metadata["chunk_uuid"]) \
                .values(status="stored", stored_at=datetime.now())
            await db.execute(query)
            
        except Exception as e:
            # Update status to "failed"
            query = file_metadata.update() \
                .where(file_metadata.c.chunk_uuid == metadata["chunk_uuid"]) \
                .values(status=f"failed: {str(e)}")
            await db.execute(query)
            raise

async def main():
    await database.connect()
    await create_tables()
    # file_metadata.create()
    consumer = AIOKafkaConsumer(
        'file-chunks',
        bootstrap_servers='kafka:29092',
        group_id="dfs-consumers"
    )
    await consumer.start()
    
    try:
        async for msg in consumer:
            await process_message(msg, database)
    finally:
        await consumer.stop()
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
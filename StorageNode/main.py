import base64
from concurrent import futures
import json
import logging
import os
import threading

import grpc
import psutil
import uvicorn
from fastapi import FastAPI

import chunk_pb2
import chunk_pb2_grpc

# ---------------- Logging Setup ----------------
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

chunk_dir = '/home/ubuntu/app/chunks'

# ---------------- FastAPI App ----------------
app = FastAPI()

@app.get("/system-status")
def get_system_status():
    cpu_percent = psutil.cpu_percent(interval=1)
    virtual_mem = psutil.virtual_memory()
    disk_usage = psutil.disk_usage('/')

    return {
        "cpu": {
            "usage_percent": cpu_percent
        },
        "ram": {
            "total": virtual_mem.total,
            "used": virtual_mem.used,
            "available": virtual_mem.available,
            "usage_percent": virtual_mem.percent
        },
        "disk": {
            "total": disk_usage.total,
            "used": disk_usage.used,
            "free": disk_usage.free,
            "usage_percent": disk_usage.percent
        }
    }

def start_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


# ---------------- gRPC Code ----------------
def parse_received_data(received_data: bytes):
    """Parse Kafka message into metadata and chunk"""
    try:
        logger.info("Parsing chunk..")
        metadata_encoded, chunk = received_data.split(b"\n\n----METADATA----\n\n", 1)
        metadata_json = base64.b64decode(metadata_encoded).decode("utf-8")
        logger.info("Parsed chunk")
        return json.loads(metadata_json), chunk
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error("Failed to parse message data")
        raise

class StorageService(chunk_pb2_grpc.ChunkServiceServicer):
    def StoreChunk(self, request, context):
        metadata, chunk = parse_received_data(request.data)
        logger.info('=====================')
        logger.info(chunk_dir)
        logger.info(f"Stored chunk {metadata} ({len(chunk)} bytes)")
        if not os.path.exists(f"{chunk_dir}"):
            logger.info("folder does not exist, creating...")
            os.makedirs(f"{chunk_dir}")
        logger.info(f"{chunk_dir}/" + metadata["chunk_uuid"])
        with open(f"{chunk_dir}/" + metadata["chunk_uuid"], "wb") as chunk_file:
            chunk_file.write(chunk)
        return chunk_pb2.StoreResponse(success=True)
    
    def GetChunk(self, request, context):
        chunk_path = f"{chunk_dir}/{request.chunk_uuid}"
        if not os.path.exists(chunk_path):
            logger.warning(f"Chunk not found: {request.chunk_uuid}")
            return chunk_pb2.ChunkResponse(data=b"", success=False)

        with open(chunk_path, "rb") as f:
            data = f.read()
        return chunk_pb2.ChunkResponse(data=data, success=True)

    

def serve_grpc():
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ("grpc.max_receive_message_length", 15 * 1024 * 1024),
            ("grpc.max_send_message_length", 15 * 1024 * 1024),
        ],
    )
    chunk_pb2_grpc.add_ChunkServiceServicer_to_server(StorageService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    logger.info("Storage node ready on port 50051")
    server.wait_for_termination()


# ---------------- Entry Point ----------------
if __name__ == "__main__":
    # Start FastAPI in a separate thread
    threading.Thread(target=start_fastapi, daemon=True).start()
    # Start gRPC server
    serve_grpc()

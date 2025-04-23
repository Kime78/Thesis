import base64
from concurrent import futures
import json
import logging
import os
import grpc
import chunk_pb2
import chunk_pb2_grpc

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_received_data(received_data: bytes):
    """Parse Kafka message into metadata and chunk"""
    try:
        metadata_encoded, chunk = received_data.split(b"\n\n----METADATA----\n\n", 1)
        metadata_json = base64.b64decode(metadata_encoded).decode("utf-8")
        return json.loads(metadata_json), chunk
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error("Failed to parse message data")
        raise


class StorageService(chunk_pb2_grpc.ChunkServiceServicer):
    def StoreChunk(self, request, context):
        metadata, chunk = parse_received_data(request.data)
        logger.info(f"Stored chunk {metadata} ({len(chunk)} bytes)")
        if not os.path.exists("/chunks"):
            os.makedirs("/chunks")
        with open("/chunks/" + metadata["chunk_uuid"], "wb") as chunk_file:
            chunk_file.write(chunk)
        return chunk_pb2.StoreResponse(success=True)


def serve():
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ("grpc.max_receive_message_length", 15 * 1024 * 1024),  # 15 MB
            (
                "grpc.max_send_message_length",
                15 * 1024 * 1024,
            ),  # 15 MB (optional for symmetry)
        ],
    )
    chunk_pb2_grpc.add_ChunkServiceServicer_to_server(StorageService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    logger.info("Storage node ready on port 50051")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

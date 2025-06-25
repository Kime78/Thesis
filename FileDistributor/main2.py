import asyncio
import base64
from datetime import datetime
import json
import random
from typing import List
from aiokafka import AIOKafkaConsumer
import grpc
from grpc import aio as aiogrpc
from pydantic import BaseModel, Field
import chunk_pb2
import chunk_pb2_grpc
import logging
from database import create_tables, file_metadata, database
import os
import requests
import abc

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

nodes = [
    "storage-node1:50051",
    "storage-node2:50051",
    "storage-node3:50051",
    "storage-node4:50051",
]

rr = 0

logger.info(f"GOT REPLICATION FACTOR = {os.getenv('REPLICATION_FACTOR', '3')}")


def parse_received_data(received_data: bytes):
    try:
        metadata_encoded, chunk = received_data.split(b"\n\n----METADATA----\n\n", 1)
        metadata_json = base64.b64decode(metadata_encoded).decode("utf-8")
        return json.loads(metadata_json), chunk
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error("Failed to parse message data")
        raise


class ReplicationAlgorithm:
    def __init__(self) -> None:
        self.nodes = [
            "storage-node1:50051",
            "storage-node2:50051",
            "storage-node3:50051",
            "storage-node4:50051",
        ]

    @abc.abstractmethod
    def choose_node(self) -> str:
        pass


class RandomReplicationAlgorithm(ReplicationAlgorithm):
    def choose_node(self) -> str:
        return random.choice(self.nodes)


class RoundRobinReplicationAlgorithm(ReplicationAlgorithm):
    def __init__(self) -> None:
        super().__init__()
        self.round_robin = 0

    def choose_node(self) -> str:
        result = self.nodes[self.round_robin]
        self.round_robin = (self.round_robin + 1) % len(self.nodes)
        return result


class CPUInfo(BaseModel):
    usage_percent: float = Field(..., description="CPU usage percentage (0.0 to 1.0)")


class RAMInfo(BaseModel):
    total: int = Field(..., description="Total RAM in bytes")
    used: int = Field(..., description="Used RAM in bytes")
    available: int = Field(..., description="Available RAM in bytes")
    usage_percent: float = Field(..., description="RAM usage percentage (0.0 to 1.0)")


class DiskInfo(BaseModel):
    total: int = Field(..., description="Total disk space in bytes")
    used: int = Field(..., description="Used disk space in bytes")
    free: int = Field(..., description="Free disk space in bytes")
    usage_percent: float = Field(..., description="Disk usage percentage (0.0 to 1.0)")


class NodeResources(BaseModel):
    cpu: CPUInfo
    ram: RAMInfo
    disk: DiskInfo


class ResourceBasedReplicationAlgorithm(ReplicationAlgorithm):
    def __init__(self) -> None:
        super().__init__()
        self.node_apis = [
            "storage-node1:8000",
            "storage-node2:8000",
            "storage-node3:8000",
            "storage-node4:8000",
        ]
        self.node_resources: List[NodeResources] = []
        for node in self.node_apis:
            logger.info(f"http://{node}/system-status")
            node_resource_json = requests.get(f"http://{node}/system-status").json()
            self.node_resources.append(NodeResources(**node_resource_json))


class CPUBasedReplicationAlgorithm(ResourceBasedReplicationAlgorithm):
    def choose_node(self) -> str:
        min_cpu_node_resource = min(
            self.node_resources, key=lambda x: x.cpu.usage_percent
        )

        min_cpu_node_index = self.node_resources.index(min_cpu_node_resource)

        chosen_grpc_address = self.nodes[min_cpu_node_index]
        logger.info(f"Chosen node based on minimum CPU: {chosen_grpc_address}")
        return chosen_grpc_address


class RAMBasedReplicationAlgorithm(ResourceBasedReplicationAlgorithm):
    def choose_node(self) -> str:
        min_cpu_node_resource = min(self.node_resources, key=lambda x: x.ram.available)

        min_cpu_node_index = self.node_resources.index(min_cpu_node_resource)

        chosen_grpc_address = self.nodes[min_cpu_node_index]
        logger.info(f"Chosen node based on minimum CPU: {chosen_grpc_address}")
        return chosen_grpc_address


class DiskBasedReplicationAlgorithm(ResourceBasedReplicationAlgorithm):
    def choose_node(self) -> str:
        min_cpu_node_resource = min(self.node_resources, key=lambda x: x.disk.free)

        min_cpu_node_index = self.node_resources.index(min_cpu_node_resource)

        chosen_grpc_address = self.nodes[min_cpu_node_index]
        logger.info(f"Chosen node based on minimum CPU: {chosen_grpc_address}")
        return chosen_grpc_address


class CombinedResourceReplicationAlgorithm(ResourceBasedReplicationAlgorithm):
    def __init__(
        self, cpu_weight: float = 0.4, ram_weight: float = 0.3, disk_weight: float = 0.3
    ) -> None:
        super().__init__()
        total_weight = cpu_weight + ram_weight + disk_weight
        if not (0.99 <= total_weight <= 1.01):
            logger.warning(f"Weights do not sum to 1.0. Normalizing: {total_weight}")
            cpu_weight /= total_weight
            ram_weight /= total_weight
            disk_weight /= total_weight

        self.cpu_weight = cpu_weight
        self.ram_weight = ram_weight
        self.disk_weight = disk_weight
        logger.info(
            f"CombinedResourceAlgorithm initialized with weights: CPU={cpu_weight}, RAM={ram_weight}, Disk={disk_weight}"
        )

    def choose_node(self) -> str:
        if not self.node_resources:
            logger.warning(
                "No node resources available for combined-based selection. Choosing randomly."
            )
            return random.choice(self.nodes)

        available_resources_with_indices = []
        for i, nr in enumerate(self.node_resources):
            if nr:
                available_resources_with_indices.append((i, nr))

        if not available_resources_with_indices:
            logger.warning(
                "No valid node resources found for combined selection. Choosing randomly."
            )
            return random.choice(self.nodes)

        best_score = float("-inf")
        best_node_index = -1

        for index, node_resource in available_resources_with_indices:
            normalized_cpu = 1.0 - node_resource.cpu.usage_percent

            normalized_ram = (
                node_resource.ram.available / node_resource.ram.total
                if node_resource.ram.total > 0
                else 0.0
            )

            normalized_disk = (
                node_resource.disk.free / node_resource.disk.total
                if node_resource.disk.total > 0
                else 0.0
            )

            current_score = (
                self.cpu_weight * normalized_cpu
                + self.ram_weight * normalized_ram
                + self.disk_weight * normalized_disk
            )

            logger.debug(
                f"Node {self.nodes[index]} (CPU: {node_resource.cpu.usage_percent:.2f}, "
                f"RAM Free: {node_resource.ram.available / (1024**3):.2f} GB, "
                f"Disk Free: {node_resource.disk.free / (1024**3):.2f} GB) "
                f"-> Normalized (CPU: {normalized_cpu:.2f}, RAM: {normalized_ram:.2f}, Disk: {normalized_disk:.2f}) "
                f"-> Score: {current_score:.4f}"
            )

            if current_score > best_score:
                best_score = current_score
                best_node_index = index

        if best_node_index != -1:
            chosen_grpc_address = self.nodes[best_node_index]
            logger.info(
                f"Chosen node {chosen_grpc_address} based on combined resources with score: {best_score:.4f}"
            )
            return chosen_grpc_address
        else:
            logger.error(
                "Failed to choose a node with combined resources. Falling back to random."
            )
            return random.choice(self.nodes)


async def send_to_storage_node(message: bytes) -> str:
    metadata, chunk_data = parse_received_data(message)

    logger.info(f"Attempting to send chunk {metadata}")
    async with aiogrpc.insecure_channel(
        metadata["storage_node"],
        options=[
            ("grpc.max_receive_message_length", 15 * 1024 * 1024),
            ("grpc.max_send_message_length", 15 * 1024 * 1024),
        ],
    ) as channel:
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
        replcation_algorithm: ReplicationAlgorithm = RoundRobinReplicationAlgorithm()
        logger.info("pula")
        metadata["storage_node"] = replcation_algorithm.choose_node()
        rr = (rr + 1) % len(nodes)
        logger.info(f"Chosen storage node: {metadata['storage_node']}")
        metadata["status"] = "pending"
        metadata["stored_at"] = None

        query = file_metadata.insert().values(**metadata)
        await db.execute(query)

        try:
            m = base64.b64encode(json.dumps(metadata).encode()).decode()
            chunk_with_metadata = f"{m}\n\n----METADATA----\n\n".encode() + chunk
            await send_to_storage_node(chunk_with_metadata)
            query = (
                file_metadata.update()
                .where(file_metadata.c.chunk_uuid == metadata["chunk_uuid"])
                .values(status="stored", stored_at=datetime.now())
            )
            await db.execute(query)

        except Exception as e:
            query = (
                file_metadata.update()
                .where(file_metadata.c.chunk_uuid == metadata["chunk_uuid"])
                .values(status=f"failed: {str(e)}")
            )
            await db.execute(query)
            raise


async def main():
    await database.connect()
    await create_tables()
    consumer = AIOKafkaConsumer(
        "file-chunks",
        bootstrap_servers="kafka:9092",
        group_id="dfs-consumers",
        max_partition_fetch_bytes=15 * 1024 * 1024,
        fetch_max_bytes=10486275,
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

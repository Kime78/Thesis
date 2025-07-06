import asyncio
import base64
from datetime import datetime
import json
import random
from typing import Dict, List
from aiokafka import AIOKafkaConsumer
import grpc
from grpc import aio as aiogrpc
from pydantic import BaseModel, Field
import chunk_pb2
import chunk_pb2_grpc
import logging
from database import create_tables, file_metadata, database
import os
import aiohttp
import abc

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

NODE_APIS = [
    "storage-node1:8000",
    "storage-node2:8000",
    "storage-node3:8000",
    "storage-node4:8000",
]
REPLICATION_FACTOR = int(os.getenv("REPLICATION_FACTOR", "3"))

logger.info(f"GOT REPLICATION FACTOR = {REPLICATION_FACTOR}")


def parse_received_data(received_data: bytes):
    try:
        metadata_encoded, chunk = received_data.split(b"\n\n----METADATA----\n\n", 1)
        metadata_json = base64.b64decode(metadata_encoded).decode("utf-8")
        return json.loads(metadata_json), chunk
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error("Failed to parse message data")
        raise


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


class ReplicationAlgorithm(abc.ABC):
    def __init__(self, node_apis: List[str]) -> None:
        self.node_apis = node_apis
        self.grpc_nodes = [api.replace(":8000", ":50051") for api in self.node_apis]
        self.available_nodes: List[str] = []
        self.lock = asyncio.Lock()

    async def update_available_nodes(self):
        while True:
            logger.info("Checking for available storage nodes...")
            available_apis = []
            async with aiohttp.ClientSession() as session:
                tasks = []
                for node_api in self.node_apis:
                    task = asyncio.create_task(
                        session.get(f"http://{node_api}/system-status", timeout=2)
                    )
                    tasks.append((node_api, task))

                for node_api, task in tasks:
                    try:
                        response = await task
                        if response.status == 200:
                            available_apis.append(node_api)
                        else:
                            logger.warning(
                                f"Node {node_api} is unavailable, status code: {response.status}"
                            )
                    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                        logger.error(f"Failed to connect to node {node_api}: {e}")

            async with self.lock:
                self.available_nodes = [
                    api.replace(":8000", ":50051") for api in available_apis
                ]
                logger.info(f"Updated available nodes: {self.available_nodes}")

            await asyncio.sleep(10)

    def start_node_availability_check(self):
        asyncio.create_task(self.update_available_nodes())

    @abc.abstractmethod
    async def choose_node(self) -> str:
        pass


class RandomReplicationAlgorithm(ReplicationAlgorithm):
    async def choose_node(self) -> str:
        async with self.lock:
            if not self.available_nodes:
                raise Exception("No available storage nodes to choose from")
            chosen_node = random.choice(self.available_nodes)
            logger.info(f"Randomly chosen node: {chosen_node}")
            return chosen_node


class RoundRobinReplicationAlgorithm(ReplicationAlgorithm):
    def __init__(self, node_apis: List[str]) -> None:
        super().__init__(node_apis)
        self.rr_index = 0

    async def choose_node(self) -> str:
        async with self.lock:
            if not self.available_nodes:
                raise Exception("No available storage nodes for Round Robin")
            if self.rr_index >= len(self.available_nodes):
                self.rr_index = 0

            chosen_node = self.available_nodes[self.rr_index]
            self.rr_index = (self.rr_index + 1) % len(self.available_nodes)
            logger.info(f"Round Robin chosen node: {chosen_node}")
            return chosen_node


class ResourceBasedReplicationAlgorithm(ReplicationAlgorithm):
    def __init__(self, node_apis: List[str]) -> None:
        super().__init__(node_apis)
        self.node_resources: Dict[str, NodeResources] = {}

    async def update_available_nodes(self):
        while True:
            logger.info("Checking for available storage nodes and their resources...")
            current_resources = {}
            available_grpc_nodes = []

            async with aiohttp.ClientSession() as session:
                tasks = {}
                for node_api in self.node_apis:
                    tasks[node_api] = asyncio.create_task(
                        session.get(f"http://{node_api}/system-status", timeout=2)
                    )

                for node_api, task in tasks.items():
                    try:
                        response = await task
                        if response.status == 200:
                            data = await response.json()
                            grpc_node = node_api.replace(":8000", ":50051")
                            current_resources[grpc_node] = NodeResources(**data)
                            available_grpc_nodes.append(grpc_node)
                        else:
                            logger.warning(
                                f"Node {node_api} unavailable, status: {response.status}"
                            )
                    except (
                        aiohttp.ClientError,
                        asyncio.TimeoutError,
                        json.JSONDecodeError,
                    ) as e:
                        logger.error(f"Failed to get resources from {node_api}: {e}")

            async with self.lock:
                self.available_nodes = available_grpc_nodes
                self.node_resources = current_resources
                logger.info(f"Updated available nodes: {self.available_nodes}")
                logger.info(f"Updated resources for {len(self.node_resources)} nodes.")

            await asyncio.sleep(10)


class CPUBasedReplicationAlgorithm(ResourceBasedReplicationAlgorithm):
    async def choose_node(self) -> str:
        async with self.lock:
            if not self.node_resources:
                raise Exception("No available nodes with resource information")

            chosen_node = min(
                self.node_resources,
                key=lambda node: self.node_resources[node].cpu.usage_percent,
            )
            logger.info(f"Chosen node based on minimum CPU: {chosen_node}")
            return chosen_node


class RAMBasedReplicationAlgorithm(ResourceBasedReplicationAlgorithm):
    async def choose_node(self) -> str:
        async with self.lock:
            if not self.node_resources:
                raise Exception("No available nodes with resource information")

            chosen_node = max(
                self.node_resources,
                key=lambda node: self.node_resources[node].ram.available,
            )
            logger.info(f"Chosen node based on maximum available RAM: {chosen_node}")
            return chosen_node


class DiskBasedReplicationAlgorithm(ResourceBasedReplicationAlgorithm):
    async def choose_node(self) -> str:
        async with self.lock:
            if not self.node_resources:
                raise Exception("No available nodes with resource information")

            chosen_node = max(
                self.node_resources,
                key=lambda node: self.node_resources[node].disk.free,
            )
            logger.info(f"Chosen node based on maximum free disk space: {chosen_node}")
            return chosen_node


class CombinedResourceReplicationAlgorithm(ResourceBasedReplicationAlgorithm):
    def __init__(
        self,
        node_apis: List[str],
        cpu_weight: float = 0.4,
        ram_weight: float = 0.3,
        disk_weight: float = 0.3,
    ) -> None:
        super().__init__(node_apis)
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
            f"CombinedAlgorithm weights: CPU={cpu_weight}, RAM={ram_weight}, Disk={disk_weight}"
        )

    async def choose_node(self) -> str:
        async with self.lock:
            if not self.node_resources:
                raise Exception(
                    "No node resources available for combined-based selection."
                )

            best_score = -1
            best_node = None

            for node, resources in self.node_resources.items():
                norm_cpu = 1.0 - resources.cpu.usage_percent
                norm_ram = (
                    resources.ram.available / resources.ram.total
                    if resources.ram.total > 0
                    else 0
                )
                norm_disk = (
                    resources.disk.free / resources.disk.total
                    if resources.disk.total > 0
                    else 0
                )

                score = (
                    (self.cpu_weight * norm_cpu)
                    + (self.ram_weight * norm_ram)
                    + (self.disk_weight * norm_disk)
                )

                if score > best_score:
                    best_score = score
                    best_node = node

            if best_node is None:
                raise Exception("Failed to choose a node with combined resources.")

            logger.info(
                f"Chosen node {best_node} based on combined score: {best_score:.4f}"
            )
            return best_node


async def send_to_storage_node(message: bytes) -> str:
    metadata, _ = parse_received_data(message)
    logger.info(f"Attempting to send chunk to {metadata['storage_node']}")
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


async def process_message(message, db, replication_algorithm: ReplicationAlgorithm):
    original_metadata, chunk = parse_received_data(message.value)

    for i in range(REPLICATION_FACTOR):
        replica_metadata = original_metadata.copy()
        record_id = None

        try:
            chosen_node = await replication_algorithm.choose_node()
            replica_metadata["storage_node"] = chosen_node
            replica_metadata["status"] = "pending"
            replica_metadata["stored_at"] = None

            insert_query = file_metadata.insert().values(**replica_metadata)
            record_id = await db.execute(insert_query)

            m = base64.b64encode(json.dumps(replica_metadata).encode()).decode()
            chunk_with_metadata = f"{m}\n\n----METADATA----\n\n".encode() + chunk
            await send_to_storage_node(chunk_with_metadata)

            update_query = (
                file_metadata.update()
                .where(file_metadata.c.id == record_id)
                .values(status="stored", stored_at=datetime.now())
            )
            await db.execute(update_query)
            logger.info(
                f"Successfully stored replica {i + 1}/{REPLICATION_FACTOR} for chunk {replica_metadata['chunk_uuid']} on {chosen_node}"
            )

        except Exception as e:
            logger.error(
                f"Failed to process replica for chunk {replica_metadata['chunk_uuid']}: {e}"
            )
            if record_id:
                fail_query = (
                    file_metadata.update()
                    .where(file_metadata.c.id == record_id)
                    .values(status=f"failed: {str(e)}")
                )
                await db.execute(fail_query)


async def main():
    await database.connect()
    await create_tables()

    replication_algorithm = RoundRobinReplicationAlgorithm(node_apis=NODE_APIS)
    availability_task = asyncio.create_task(
        replication_algorithm.update_available_nodes()
    )

    consumer = AIOKafkaConsumer(
        "file-chunks",
        bootstrap_servers="kafka:9092",
        group_id="dfs-consumers",
        max_partition_fetch_bytes=15 * 1024 * 1024,
        fetch_max_bytes=10486275,
        auto_offset_reset="earliest",
    )

    await consumer.start()

    try:
        await asyncio.sleep(10)  # Wait for the first node availability check
        async for msg in consumer:
            await process_message(msg, database, replication_algorithm)
    except asyncio.CancelledError:
        logger.info("Main task cancelled.")
    finally:
        availability_task.cancel()
        await consumer.stop()
        await database.disconnect()
        logger.info("Graceful shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user.")

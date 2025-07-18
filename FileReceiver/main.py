import asyncio
import base64
import json
import logging
import os
import random
from typing import List
from uuid import uuid4
import hashlib

import aiofiles
from aiokafka import AIOKafkaProducer
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

topic_name = "file-chunks"
CHUNK_SIZE = 10 * 1024 * 1024  # 10 MiB

app = FastAPI()
producer: AIOKafkaProducer = None

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


@app.on_event("startup")
async def startup_event():
    global producer
    producer = AIOKafkaProducer(
        bootstrap_servers="kafka:9092",
        value_serializer=lambda x: x,
        max_request_size=15 * 1024 * 1024,
    )
    await producer.start()
    logger.info("AIOKafkaProducer started successfully.")


@app.on_event("shutdown")
async def shutdown_event():
    global producer
    if producer:
        await producer.stop()
        logger.info("AIOKafkaProducer stopped.")


def create_metadata(
    file_name: str,
    content_type: str,
    file_size: int,
    chunk: bytes,
    chunk_index: int,
    chunk_uuid: str,
    file_uuid: str,
    file_hash: str,
    chunk_hash: str,
) -> str:
    metadata = {
        "file_size": file_size,
        "file_name": file_name,
        "content_type": content_type,
        "chunk_size": len(chunk),
        "chunk_index": chunk_index,
        "chunk_uuid": chunk_uuid,
        "file_uuid": file_uuid,
        "file_hash": file_hash,
        "chunk_hash": chunk_hash,
    }
    return base64.b64encode(json.dumps(metadata).encode()).decode()

@app.post("/upload")
async def upload_files(uploaded_files: List[UploadFile] = File(...)):
    async def process_file(uploaded_file: UploadFile):
        file_uuid = str(uuid4())
        temp_file_path = None

        try:
            content_type = uploaded_file.content_type
            file_name = uploaded_file.filename or "unknown_file"
            file_hasher = hashlib.sha256()
            async with aiofiles.tempfile.NamedTemporaryFile(
                "wb", delete=False
            ) as temp_file:
                temp_file_path = temp_file.name
                while True:
                    piece = await uploaded_file.read(CHUNK_SIZE)
                    if not piece:
                        break
                    file_hasher.update(piece) 
                    await temp_file.write(piece)

            file_hash_hex = file_hasher.hexdigest()
            file_size = os.path.getsize(temp_file_path)

            chunk_index = 0
            async with aiofiles.open(temp_file_path, "rb") as file:
                while True:
                    chunk = await file.read(CHUNK_SIZE)
                    if not chunk:
                        break

                    metadata_str = create_metadata(
                        file_name=file_name,
                        content_type=content_type,
                        file_size=file_size,
                        chunk=chunk,
                        chunk_index=chunk_index,
                        chunk_uuid=str(uuid4()),
                        file_uuid=file_uuid,
                        file_hash=file_hash_hex,
                        chunk_hash=hashlib.sha256(chunk).hexdigest(),
                    )
                    chunk_with_metadata = (
                        f"{metadata_str}\n\n----METADATA----\n\n".encode() + chunk
                    )

                    await producer.send_and_wait(topic_name, value=chunk_with_metadata)
                    chunk_index += 1

            return {
                "filename": file_name,
                "chunks_sent": chunk_index,
                "file_uuid": file_uuid,
                "file_hash": file_hash_hex,
                "message": "File processed successfully",
            }

        except Exception as e:
            logger.error(
                f"Failed to process {uploaded_file.filename}: {e}", exc_info=True
            )
            return {"filename": uploaded_file.filename, "error": str(e)}

        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except OSError as e:
                    logger.warning(f"Error removing temp file {temp_file_path}: {e}")

    results = await asyncio.gather(*(process_file(f) for f in uploaded_files))
    return results

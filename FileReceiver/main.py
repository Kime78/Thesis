import asyncio
import base64
import json
import os
from typing import Annotated, List
from uuid import uuid4
import aiofiles
from fastapi import FastAPI, UploadFile, HTTPException, File
from fastapi.responses import FileResponse
from aiokafka import AIOKafkaProducer
import logging
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

topic_name = 'file-chunks'
CHUNK_SIZE = 10 * 1024 * 1024  # 10 MiB

app = FastAPI()
producer: AIOKafkaProducer = None  # type: ignore

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your frontend origin
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    global producer
    producer = AIOKafkaProducer(
        bootstrap_servers='kafka:29092',
        value_serializer=lambda x: x,
        max_request_size=15 * 1024 * 1024
    )
    await producer.start()
    logger.info("AIOKafkaProducer started")

@app.on_event("shutdown")
async def shutdown_event():
    global producer
    if producer:
        await producer.stop()
        logger.info("AIOKafkaProducer stopped")

def create_metadata(file_name: str, content_type: str, file_size: int, 
                    chunk: bytes, chunk_index: int, chunk_uuid: str, file_uuid: str) -> str:
    metadata = {
        "file_size": file_size,
        "file_name": file_name,
        "content_type": content_type,
        "chunk_size": len(chunk),
        "chunk_index": chunk_index,
        "chunk_uuid": chunk_uuid,
        "file_uuid": file_uuid,
    }
    return base64.b64encode(json.dumps(metadata).encode()).decode()

@app.post("/download")
async def download_files():
    return FileResponse("test.pdf")

@app.post("/upload")
async def upload_files(uploaded_files: List[UploadFile] = File(...)):
    async def process_file(uploaded_file: UploadFile):
        file_uuid = str(uuid4())
        temp_file_path = None

        try:
            content_type = uploaded_file.content_type
            file_name = uploaded_file.filename or "unknown_file"

            async with aiofiles.tempfile.NamedTemporaryFile("wb", delete=False) as temp_file:
                temp_file_path = temp_file.name
                while True:
                    chunk = await uploaded_file.read(8192)
                    if not chunk:
                        break
                    await temp_file.write(chunk)

            file_size = os.path.getsize(temp_file_path)

            chunk_index = 0
            async with aiofiles.open(temp_file_path, "rb") as file:
                while True:
                    chunk = await file.read(CHUNK_SIZE)
                    if not chunk:
                        break

                    metadata = create_metadata(
                        file_name=file_name,
                        content_type=content_type,
                        file_size=file_size,
                        chunk=chunk,
                        chunk_index=chunk_index,
                        chunk_uuid=str(uuid4()),
                        file_uuid=file_uuid
                    )

                    chunk_with_metadata = f"{metadata}\n\n----METADATA----\n\n".encode() + chunk

                    await producer.send_and_wait(topic_name, value=chunk_with_metadata)
                    chunk_index += 1

            return {
                "filename": file_name,
                "chunks_sent": chunk_index,
                "file_uuid": file_uuid,
                "message": "Processed in parallel"
            }

        except Exception as e:
            return {"filename": uploaded_file.filename, "error": str(e)}

        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    logger.warning(f"Error deleting temp file: {e}")

    # Run all file handlers concurrently
    results = await asyncio.gather(*(process_file(f) for f in uploaded_files))
    return results
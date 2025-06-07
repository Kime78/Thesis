import asyncio
import base64
import hashlib
import io
import logging
import random
from typing import List
from fastapi import FastAPI, UploadFile, File, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlmodel import select
from urllib.parse import quote

from db import async_session, engine
from model import FileMetadata

import chunk_pb2
import chunk_pb2_grpc
import grpc

app = FastAPI()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

def choose_node(nodes: List[FileMetadata]) -> FileMetadata: 
    return random.choice(nodes)

MAX_GRPC_MESSAGE_LENGTH = 16 * 1024 * 1024
async def fetch_chunk(chunk_uuid: str, node_address: str, chunk_hash: str) -> bytes:
    channel_options = [
        ('grpc.max_receive_message_length', MAX_GRPC_MESSAGE_LENGTH),
        ('grpc.max_send_message_length', MAX_GRPC_MESSAGE_LENGTH),
    ]
    async with grpc.aio.insecure_channel(f"{node_address}", options=channel_options) as channel:
        stub = chunk_pb2_grpc.ChunkServiceStub(channel)
        response = await stub.GetChunk(chunk_pb2.ChunkRequest(chunk_uuid=chunk_uuid))
        logger.info(f"Downloaded chunk {chunk_uuid} from {node_address}")
        downloaded_hash = hashlib.sha256(response.data).hexdigest()
        if downloaded_hash != chunk_hash:
            raise Exception(f"Failed to download chunk {chunk_uuid} from {node_address}, hashes dont match downloaded{downloaded_hash} uploaded{chunk_hash}")
        if not response.success:
            raise Exception(f"Failed to download chunk {chunk_uuid} from {node_address}")
        return response.data

from fastapi.responses import StreamingResponse
from fastapi import HTTPException
import io
import base64

@app.post("/download")
async def download_files(file_uuid: str):
    async with async_session() as session:
        stmt = select(FileMetadata).where(FileMetadata.file_uuid == file_uuid).order_by(
            FileMetadata.chunk_index, FileMetadata.storage_node
        )
        result = await session.exec(stmt)
        files = list(result.all())

    if not files:
        raise HTTPException(status_code=404, detail="File not found")

    grouped_files = [files[i:i + 4] for i in range(0, len(files), 4)]
    chosen_files = [choose_node(group) for group in grouped_files]

    try:
        tasks = [fetch_chunk(chunk.chunk_uuid, chunk.storage_node, chunk.chunk_hash) for chunk in chosen_files]
        logger.info("Starting download tasks")
        chunks = await asyncio.gather(*tasks)
        logger.info("Joining data")
        combined_data = b"".join(chunks)
        downloaded_hash = hashlib.sha256(combined_data).hexdigest()
        logger.info(files[0])
        if downloaded_hash != chosen_files[0].file_hash:
            raise Exception(f"Failed to download file {files[0].file_uuid}, hashes dont match downloaded {downloaded_hash} uploaded {chosen_files[0].file_hash}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch chunks: {str(e)}")

    file_like = io.BytesIO(combined_data)
    
    # Ensure a fallback filename if it's somehow None or empty
    filename = files[0].file_name or "downloaded_file"
    
    # URL-encode the filename to handle special characters safely
    encoded_filename = quote(filename)

    # Use the RFC 5987 compliant format for the Content-Disposition header
    # This provides the best cross-browser compatibility for non-ASCII filenames.
    content_disposition_header = f"attachment; filename*=UTF-8''{encoded_filename}"
    logger.info("Sending response")
    return StreamingResponse(
        file_like,
        media_type="application/octet-stream",
        headers={"Content-Disposition": content_disposition_header}
    )

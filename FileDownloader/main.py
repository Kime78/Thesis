import asyncio
import base64
import hashlib
import io
import logging
import math
import random
from typing import List
from fastapi import FastAPI, UploadFile, File, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlmodel import select
from urllib.parse import quote

from db import async_session, engine
from model import FileMetadata

import chunk_pb2
import chunk_pb2_grpc
import grpc

app = FastAPI()


class DownloadRequest(BaseModel):
    file_uuid: str


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
        ("grpc.max_receive_message_length", MAX_GRPC_MESSAGE_LENGTH),
        ("grpc.max_send_message_length", MAX_GRPC_MESSAGE_LENGTH),
    ]
    async with grpc.aio.insecure_channel(
        f"{node_address}", options=channel_options
    ) as channel:
        stub = chunk_pb2_grpc.ChunkServiceStub(channel)
        response = await stub.GetChunk(chunk_pb2.ChunkRequest(chunk_uuid=chunk_uuid))
        logger.info(f"Downloaded chunk {chunk_uuid} from {node_address}")
        downloaded_hash = hashlib.sha256(response.data).hexdigest()
        if downloaded_hash != chunk_hash:
            raise Exception(
                f"Failed to download chunk {chunk_uuid} from {node_address}, hashes dont match downloaded{downloaded_hash} uploaded{chunk_hash}"
            )
        if not response.success:
            raise Exception(
                f"Failed to download chunk {chunk_uuid} from {node_address}"
            )
        return response.data


from fastapi.responses import StreamingResponse
from fastapi import HTTPException
import io
import base64


@app.get("/files")
async def show_files():
    async with async_session() as session:
        stmt = select(FileMetadata).distinct(FileMetadata.file_uuid)
        result = await session.exec(stmt)
        files = list(result.all())
    return files


@app.get("/status/{file_uuid}")
async def get_file_upload_status(file_uuid: str):
    """
    Retrieves the upload status of a file.

    Args:
        file_uuid: The UUID of the file to check.

    Returns:
        A JSON response indicating the file status.
    """
    async with async_session() as session:
        stmt = (
            select(FileMetadata)
            .where(FileMetadata.file_uuid == file_uuid)
            .order_by(FileMetadata.chunk_index, FileMetadata.storage_node)
        )
        result = await session.exec(stmt)
        files: List[FileMetadata] = list(result.all())

        if not files:
            raise HTTPException(
                status_code=404,
                detail={
                    "status": "not_found",
                    "message": f"File with UUID '{file_uuid}' not found.",
                },
            )

        file = files[0]
        # Ensure floating point division for accuracy
        supposed_nr_chunks = (math.ceil(file.file_size / float(file.chunk_size))) * 3

        if supposed_nr_chunks != len(files):
            return JSONResponse(
                status_code=200,
                content={
                    "status": "uploading",
                    "message": "File upload is still in progress.",
                    "current_chunks": len(files),
                    "expected_chunks": int(supposed_nr_chunks),
                },
            )

        return JSONResponse(
            status_code=200,
            content={
                "status": "complete",
                "message": "File upload is complete.",
            },
        )


@app.post("/download")
async def download_files(req: DownloadRequest):
    file_uuid = req.file_uuid
    async with async_session() as session:
        stmt = (
            select(FileMetadata)
            .where(FileMetadata.file_uuid == file_uuid)
            .order_by(FileMetadata.chunk_index, FileMetadata.storage_node)
        )
        result = await session.exec(stmt)
        files = list(result.all())

    if not files:
        raise HTTPException(status_code=404, detail="File not found")

    grouped_files = [files[i : i + 3] for i in range(0, len(files), 3)]
    chosen_files = [choose_node(group) for group in grouped_files]
    logger.info(len(chosen_files))
    try:
        tasks = [
            fetch_chunk(chunk.chunk_uuid, chunk.storage_node, chunk.chunk_hash)
            for chunk in chosen_files
        ]
        logger.info("Starting download tasks")
        chunks = await asyncio.gather(*tasks)
        logger.info("Joining data")
        combined_data = b"".join(chunks)
        downloaded_hash = hashlib.sha256(combined_data).hexdigest()
        logger.info(files[0])
        if downloaded_hash != chosen_files[0].file_hash:
            raise Exception(
                f"Failed to download file {files[0].file_uuid}, hashes dont match downloaded {downloaded_hash} uploaded {chosen_files[0].file_hash}"
            )
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
        headers={"Content-Disposition": content_disposition_header},
    )

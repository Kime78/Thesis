import asyncio
import base64
import hashlib
import io
import logging
import math
import random
from typing import List
from urllib.parse import quote

import chunk_pb2
import chunk_pb2_grpc
import grpc
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlmodel import delete, select

from db import async_session
from model import FileMetadata

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

async def fetch_chunk_with_retries(chunk_replicas: List[FileMetadata]) -> bytes:
    logger.info(f"[POST /download] Replicas:{chunk_replicas}")
    chunk_uuid = chunk_replicas[0].chunk_uuid
    for replica in chunk_replicas:
        try:
            data = await fetch_chunk(
                replica.chunk_uuid, replica.storage_node, replica.chunk_hash
            )
            return data
        except Exception as e:
            logger.warning(
                f"[POST /download] Failed to fetch chunk {replica.chunk_uuid} from {replica.storage_node}: {e}. Trying next replica."
            )
    raise Exception(f"Failed to download chunk {chunk_uuid} from all available nodes.")

async def delete_chunk(chunk_uuid: str, node_address: str) -> bool:
    async with grpc.aio.insecure_channel(f"{node_address}") as channel:
        stub = chunk_pb2_grpc.ChunkServiceStub(channel)
        try:
            response = await stub.DeleteChunk(
                chunk_pb2.ChunkRequest(chunk_uuid=chunk_uuid)
            )
            if response.success:
                logger.info(
                    f"Successfully deleted chunk {chunk_uuid} from {node_address}"
                )
                return True
            else:
                logger.warning(
                    f"Failed to delete chunk {chunk_uuid} from {node_address}: {response.message}"
                )
                return False
        except grpc.aio.AioRpcError as e:
            logger.error(
                f"RPC error deleting chunk {chunk_uuid} from {node_address}: {e}"
            )
            return False

@app.get("/files")
async def show_files():
    async with async_session() as session:
        stmt = select(FileMetadata).distinct(FileMetadata.file_uuid)
        result = await session.exec(stmt)
        files = list(result.all())
    return files

@app.get("/status/{file_uuid}")
async def get_file_upload_status(file_uuid: str):
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

    try:
        tasks = [fetch_chunk_with_retries(group) for group in grouped_files]
        logger.info("[POST /download] Starting download tasks")
        chunks = await asyncio.gather(*tasks)
        logger.info("[POST /download] Joining data")
        combined_data = b"".join(chunks)
        downloaded_hash = hashlib.sha256(combined_data).hexdigest()

        if downloaded_hash != files[0].file_hash:
            raise Exception(
                f"Failed to download file {files[0].file_uuid}, hashes dont match downloaded {downloaded_hash} uploaded {files[0].file_hash}"
            )
    except Exception as e:
        logger.error(f"[POST /download] An error occurred during file download: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch chunks: {str(e)}")

    file_like = io.BytesIO(combined_data)
    filename = files[0].file_name or "downloaded_file"
    encoded_filename = quote(filename)
    content_disposition_header = f"attachment; filename*=UTF-8''{encoded_filename}"
    logger.info(f"[POST /download] Sending response for file {filename}")
    return StreamingResponse(
        file_like,
        media_type="application/octet-stream",
        headers={"Content-Disposition": content_disposition_header},
    )

@app.delete("/files/{file_uuid}")
async def delete_single_file(file_uuid: str):
    async with async_session() as session:
        stmt = select(FileMetadata).where(FileMetadata.file_uuid == file_uuid)
        result = await session.exec(stmt)
        file_metadatas = list(result.all())

        if not file_metadatas:
            raise HTTPException(
                status_code=404, detail=f"File with UUID '{file_uuid}' not found."
            )
        
        logger.info(f"[DELETE /files/{file_uuid}] Deleting {len(file_metadatas)} chunks.")
        delete_tasks = [
            delete_chunk(meta.chunk_uuid, meta.storage_node) for meta in file_metadatas
        ]
        results = await asyncio.gather(*delete_tasks)

        if not all(results):
            logger.warning(
                f"[DELETE /files/{file_uuid}] Failed to delete some chunks for file {file_uuid}. Proceeding to delete metadata anyway."
            )

        delete_stmt = delete(FileMetadata).where(FileMetadata.file_uuid == file_uuid)
        await session.exec(delete_stmt)
        await session.commit()
        logger.info(f"[DELETE /files/{file_uuid}] Successfully deleted file metadata.")

    return JSONResponse(
        status_code=200,
        content={"message": f"File {file_uuid} and its chunks have been deleted."},
    )

@app.delete("/files")
async def delete_all_files():
    async with async_session() as session:
        stmt = select(FileMetadata)
        result = await session.exec(stmt)
        all_metadatas = list(result.all())

        if not all_metadatas:
            return JSONResponse(
                status_code=200,
                content={"message": "No files found to delete."},
            )

        logger.info(f"[DELETE /files] Deleting all {len(all_metadatas)} chunks from the system.")
        delete_tasks = [
            delete_chunk(meta.chunk_uuid, meta.storage_node) for meta in all_metadatas
        ]
        await asyncio.gather(*delete_tasks)
        logger.info("[DELETE /files] All chunk deletion tasks completed. Now clearing database.")

        delete_stmt = delete(FileMetadata)
        await session.exec(delete_stmt)
        await session.commit()
        logger.info("[DELETE /files] Successfully deleted all file metadata.")

    return JSONResponse(
        status_code=200,
        content={"message": "All files and chunks have been deleted from the system."},
    )
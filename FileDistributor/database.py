# Remove peewee, use async database library
from datetime import datetime
from databases import Database
from sqlalchemy import MetaData, Table, Column, Integer, String, DateTime
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@postgres:5432/file_metadata"
database = Database(DATABASE_URL)
metadata = MetaData()

engine = create_async_engine(DATABASE_URL)


async def create_tables():
    """Create tables if they don't exist"""
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)


file_metadata = Table(
    "file_metadata",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("file_uuid", String),
    Column("file_name", String),
    Column("file_size", Integer),
    Column("content_type", String),
    Column("chunk_uuid", String),
    Column("chunk_index", Integer),
    Column("chunk_size", Integer),
    Column("storage_node", String),  # e.g., "http://storage-node:50051"
    Column("stored_at", DateTime),
    Column("status", String),
    Column("file_hash", String),
    Column("chunk_hash", String), 
)

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class FileMetadata(SQLModel, table=True):
    __tablename__ = "file_metadata"

    id: Optional[int] = Field(default=None, primary_key=True)
    file_uuid: str = Field(index=True)
    file_name: str
    file_size: int
    content_type: str
    chunk_uuid: str
    chunk_index: int
    chunk_size: int
    storage_node: str
    stored_at: datetime
    status: str  # "pending", "stored", "failed"
    file_hash: str 
    chunk_hash: str 

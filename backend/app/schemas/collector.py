"""
Collector Schemas
"""
from pydantic import BaseModel
from typing import Optional


class CollectionJob(BaseModel):
    """Collection job"""
    job_id: str
    job_type: str
    status: str
    created_at: str


class CollectionStatus(BaseModel):
    """Job status"""
    job_id: str
    status: str
    progress: int
    message: Optional[str] = None
    result: Optional[dict] = None

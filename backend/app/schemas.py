from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.models import JobStatus


class DocumentOut(BaseModel):
    id: int
    original_filename: str
    mime_type: Optional[str]
    file_size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}


class JobSummary(BaseModel):
    id: int
    document_id: int
    status: JobStatus
    progress_percent: int
    current_stage: Optional[str]
    error_message: Optional[str]
    finalized_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    document: DocumentOut

    model_config = {"from_attributes": True}


class JobDetail(JobSummary):
    celery_task_id: Optional[str]
    result_json: Optional[Dict[str, Any]]
    reviewed_result_json: Optional[Dict[str, Any]]
    finalized_result_json: Optional[Dict[str, Any]]
    retry_count: int


class ProgressEvent(BaseModel):
    event: str
    progress_percent: int = 0
    stage: Optional[str] = None
    message: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


class UploadResponse(BaseModel):
    jobs: List[Dict[str, Any]]


class JobListQuery(BaseModel):
    search: Optional[str] = None
    status: Optional[JobStatus] = None
    sort: Literal["created_at", "-created_at", "updated_at", "-updated_at", "filename", "-filename"] = (
        "-created_at"
    )


class UpdateReviewBody(BaseModel):
    reviewed_result: Dict[str, Any] = Field(..., description="Edited structured output before finalize")

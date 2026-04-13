from __future__ import annotations

from typing import Annotated, List, Optional, Tuple

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import JobStatus
from app.schemas import JobDetail, JobListQuery, JobSummary, UpdateReviewBody
from app.services.job_service import (
    BrokerUnavailableError,
    create_jobs_from_uploads,
    export_finalized,
    finalize_job,
    get_job,
    list_jobs,
    retry_job,
    update_reviewed_result,
)
from app.storage import get_storage

router = APIRouter(prefix="/api/v1", tags=["jobs"])


@router.post("/documents/upload", status_code=201)
async def upload_documents(
    session: Annotated[AsyncSession, Depends(get_db)],
    files: List[UploadFile] = File(...),
) -> dict:
    if not files:
        raise HTTPException(400, "At least one file is required")
    storage = get_storage()
    tuples: List[Tuple[str, Optional[str], bytes]] = []
    for uf in files:
        raw = await uf.read()
        tuples.append((uf.filename or "unnamed", uf.content_type, raw))
    try:
        print("[upload_documents] received files:", [{"name": n, "mime": m, "bytes": len(b)} for (n, m, b) in tuples])
        jobs = await create_jobs_from_uploads(session, storage, tuples)
    except BrokerUnavailableError as e:
        print("[upload_documents] BrokerUnavailableError:", str(e))
        raise HTTPException(503, detail=str(e)) from e
    return {"jobs": jobs}


@router.get("/jobs", response_model=List[JobSummary])
async def get_jobs(
    session: Annotated[AsyncSession, Depends(get_db)],
    search: Optional[str] = None,
    status: Optional[JobStatus] = None,
    sort: str = "-created_at",
) -> list:
    allowed = {"created_at", "-created_at", "updated_at", "-updated_at", "filename", "-filename"}
    if sort not in allowed:
        sort = "-created_at"
    q = JobListQuery(search=search, status=status, sort=sort)  # type: ignore[arg-type]
    rows = await list_jobs(session, q)
    return list(rows)


@router.get("/jobs/{job_id}", response_model=JobDetail)
async def job_detail(job_id: int, session: Annotated[AsyncSession, Depends(get_db)]) -> JobDetail:
    job = await get_job(session, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return JobDetail.model_validate(job)


@router.get("/jobs/{job_id}/progress")
async def job_progress_snapshot(job_id: int, session: Annotated[AsyncSession, Depends(get_db)]) -> dict:
    import json

    import redis.asyncio as aioredis

    from app.config import settings
    from app.redis_progress import progress_channel

    job = await get_job(session, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        raw = await r.get(f"job:{job_id}:progress:last")
        last = json.loads(raw) if raw else None
    finally:
        await r.aclose()
    return {
        "job_id": job_id,
        "db_status": job.status.value,
        "progress_percent": job.progress_percent,
        "current_stage": job.current_stage,
        "last_event": last,
    }


@router.post("/jobs/{job_id}/retry")
async def retry(job_id: int, session: Annotated[AsyncSession, Depends(get_db)]) -> dict:
    try:
        job, err = await retry_job(session, job_id)
    except BrokerUnavailableError as e:
        raise HTTPException(503, detail=str(e)) from e
    if err == "not_found":
        raise HTTPException(404, "Job not found")
    if err == "finalized":
        raise HTTPException(409, "Cannot retry a finalized job")
    if err == "already_running":
        raise HTTPException(409, "Job is already queued or processing")
    return {"ok": True, "job_id": job.id, "status": job.status.value}


@router.patch("/jobs/{job_id}/result")
async def patch_result(job_id: int, body: UpdateReviewBody, session: Annotated[AsyncSession, Depends(get_db)]) -> dict:
    job, err = await update_reviewed_result(session, job_id, body.reviewed_result)
    if err == "not_found":
        raise HTTPException(404, "Job not found")
    if err == "finalized":
        raise HTTPException(409, "Job is finalized; edits are locked")
    if err == "not_completed":
        raise HTTPException(409, "Job is not completed yet")
    return {"ok": True, "job_id": job.id}


@router.post("/jobs/{job_id}/finalize")
async def finalize(job_id: int, session: Annotated[AsyncSession, Depends(get_db)]) -> dict:
    job, err = await finalize_job(session, job_id)
    if err == "not_found":
        raise HTTPException(404, "Job not found")
    if err == "not_completed":
        raise HTTPException(409, "Job must complete before finalize")
    if err == "already_finalized":
        raise HTTPException(409, "Already finalized")
    if err == "no_result":
        raise HTTPException(400, "No extracted result to finalize")
    return {"ok": True, "job_id": job.id, "finalized_at": job.finalized_at.isoformat() if job.finalized_at else None}


@router.get("/export/finalized")
async def export_finalized_route(
    session: Annotated[AsyncSession, Depends(get_db)],
    format: str = Query("json", alias="format"),
) -> Response:
    if format not in ("json", "csv"):
        raise HTTPException(400, "format must be json or csv")
    media, filename, body = await export_finalized(session, format)
    return Response(
        content=body,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

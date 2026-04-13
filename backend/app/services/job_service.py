from __future__ import annotations

import csv
import io
import json
from typing import Any, List, Optional, Sequence, Tuple

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import Document, JobStatus, ProcessingJob
from app.redis_progress import progress_channel, publish_progress
from app.schemas import JobListQuery
from app.storage import LocalFileStorage
from app.tasks import process_document_job


class BrokerUnavailableError(Exception):
    """Raised when Celery cannot enqueue (Redis broker usually not running)."""

    pass


def enqueue_document_job(job_id: int) -> None:
    try:
        process_document_job.delay(job_id)
    except Exception as e:
        # Print extra context to make local debugging obvious in terminals/logs.
        import traceback

        print("[enqueue_document_job] Failed to enqueue job:", job_id)
        print("[enqueue_document_job] Exception:", f"{type(e).__name__}: {e}")
        print("[enqueue_document_job] Traceback:\n" + traceback.format_exc())
        raise BrokerUnavailableError(
            "Task queue unavailable: start Redis on port 6379, then run "
            "`cd backend && PYTHONPATH=. celery -A app.celery_app worker -l info`"
        ) from e


async def create_jobs_from_uploads(
    session: AsyncSession,
    storage: LocalFileStorage,
    files: List[Tuple[str, Optional[str], bytes]],
) -> List[dict[str, Any]]:
    jobs: List[ProcessingJob] = []
    summaries: List[dict[str, Any]] = []
    for original_name, mime, data in files:
        path = storage.save_upload(original_name, data)
        doc = Document(
            original_filename=original_name,
            stored_path=path,
            mime_type=mime,
            file_size_bytes=len(data),
        )
        session.add(doc)
        await session.flush()
        job = ProcessingJob(document_id=doc.id, status=JobStatus.QUEUED, progress_percent=0, current_stage="job_queued")
        session.add(job)
        await session.flush()
        publish_progress(job.id, "job_queued", progress_percent=0, stage="job_queued", filename=original_name)
        jobs.append(job)
        summaries.append(
            {
                "job_id": job.id,
                "document_id": doc.id,
                "status": job.status.value,
                "filename": original_name,
            }
        )
    await session.commit()
    # Small delay to ensure async session changes are visible to sync workers
    import asyncio
    await asyncio.sleep(0.5)
    for job in jobs:
        enqueue_document_job(job.id)
    return summaries


def _base_job_query() -> Select[Any]:
    return (
        select(ProcessingJob)
        .options(joinedload(ProcessingJob.document))
        .join(Document, ProcessingJob.document_id == Document.id)
    )


async def list_jobs(session: AsyncSession, q: JobListQuery) -> Sequence[ProcessingJob]:
    stmt = _base_job_query()

    if q.status:
        stmt = stmt.where(ProcessingJob.status == q.status)
    if q.search:
        term = f"%{q.search.strip()}%"
        stmt = stmt.where(Document.original_filename.ilike(term))

    sort = q.sort
    if sort == "created_at":
        stmt = stmt.order_by(ProcessingJob.created_at.asc())
    elif sort == "-created_at":
        stmt = stmt.order_by(ProcessingJob.created_at.desc())
    elif sort == "updated_at":
        stmt = stmt.order_by(ProcessingJob.updated_at.asc())
    elif sort == "-updated_at":
        stmt = stmt.order_by(ProcessingJob.updated_at.desc())
    elif sort == "filename":
        stmt = stmt.order_by(Document.original_filename.asc())
    elif sort == "-filename":
        stmt = stmt.order_by(Document.original_filename.desc())
    else:
        stmt = stmt.order_by(ProcessingJob.created_at.desc())

    result = await session.execute(stmt)
    return result.unique().scalars().all()


async def get_job(session: AsyncSession, job_id: int) -> Optional[ProcessingJob]:
    stmt = _base_job_query().where(ProcessingJob.id == job_id)
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()


async def retry_job(session: AsyncSession, job_id: int) -> Tuple[Optional[ProcessingJob], Optional[str]]:
    job = await get_job(session, job_id)
    if not job:
        return None, "not_found"
    if job.finalized_at is not None:
        return job, "finalized"
    if job.status in (JobStatus.QUEUED, JobStatus.PROCESSING):
        return job, "already_running"
    job.status = JobStatus.QUEUED
    job.progress_percent = 0
    job.current_stage = "job_queued"
    job.error_message = None
    job.celery_task_id = None
    job.retry_count = job.retry_count + 1
    publish_progress(job.id, "job_queued", progress_percent=0, stage="job_queued", retry=True)
    await session.flush()
    await session.commit()
    enqueue_document_job(job.id)
    return job, None


async def update_reviewed_result(
    session: AsyncSession, job_id: int, payload: dict[str, Any]
) -> Tuple[Optional[ProcessingJob], Optional[str]]:
    job = await get_job(session, job_id)
    if not job:
        return None, "not_found"
    if job.finalized_at is not None:
        return job, "finalized"
    if job.status != JobStatus.COMPLETED:
        return job, "not_completed"
    job.reviewed_result_json = payload
    await session.commit()
    return job, None


async def finalize_job(session: AsyncSession, job_id: int) -> Tuple[Optional[ProcessingJob], Optional[str]]:
    job = await get_job(session, job_id)
    if not job:
        return None, "not_found"
    if job.status != JobStatus.COMPLETED:
        return job, "not_completed"
    if job.finalized_at is not None:
        return job, "already_finalized"
    from datetime import datetime, timezone

    source = job.reviewed_result_json or job.result_json
    if not source:
        return job, "no_result"
    job.finalized_result_json = dict(source)
    job.finalized_at = datetime.now(timezone.utc)
    await session.commit()
    return job, None


async def export_finalized(session: AsyncSession, fmt: str) -> Tuple[str, str, bytes]:
    stmt = (
        select(ProcessingJob)
        .options(joinedload(ProcessingJob.document))
        .where(ProcessingJob.finalized_at.is_not(None))
        .order_by(ProcessingJob.finalized_at.desc())
    )
    result = await session.execute(stmt)
    rows = result.unique().scalars().all()
    if fmt == "json":
        data = []
        for j in rows:
            data.append(
                {
                    "job_id": j.id,
                    "document_id": j.document_id,
                    "filename": j.document.original_filename,
                    "finalized_at": j.finalized_at.isoformat() if j.finalized_at else None,
                    "result": j.finalized_result_json,
                }
            )
        raw = json.dumps(data, indent=2).encode("utf-8")
        return "application/json", "export_finalized.json", raw
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["job_id", "document_id", "filename", "title", "category", "status", "finalized_at"])
    for j in rows:
        r = j.finalized_result_json or {}
        writer.writerow(
            [
                j.id,
                j.document_id,
                j.document.original_filename,
                r.get("title", ""),
                r.get("category", ""),
                r.get("status", ""),
                j.finalized_at.isoformat() if j.finalized_at else "",
            ]
        )
    return "text/csv", "export_finalized.csv", buf.getvalue().encode("utf-8")

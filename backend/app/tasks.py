from __future__ import annotations

import time
from typing import Optional
import traceback

from app.celery_app import celery_app
from app.models import Document, JobStatus, ProcessingJob
from app.processing_logic import build_structured_result
from app.redis_progress import cache_latest_progress, publish_progress


def _emit(job_id: int, event: str, progress: int, stage: Optional[str] = None, **kw: object) -> None:
    extra = {k: v for k, v in kw.items() if v is not None}
    publish_progress(job_id, event, progress_percent=progress, stage=stage, **extra)
    cache_latest_progress(job_id, {"event": event, "progress_percent": progress, "stage": stage, **extra})


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 5}, default_retry_delay=2)
def process_document_job(self, job_id: int) -> dict[str, object]:
    from app.worker_db import sync_session

    with sync_session() as session:
        job = session.get(ProcessingJob, job_id)
        if not job:
            print("[process_document_job] job_not_found:", job_id)
            # Retry if job not found (race condition with async/sync DB)
            raise self.retry(countdown=2, exc=Exception(f"Job {job_id} not found in database"))
        doc = session.get(Document, job.document_id)
        if not doc:
            job.status = JobStatus.FAILED
            job.error_message = "Document record missing"
            _emit(job_id, "job_failed", 0, stage="error", message="document_missing")
            print("[process_document_job] document_missing for job:", job_id, "document_id:", job.document_id)
            return {"ok": False}

        try:
            print(
                "[process_document_job] start",
                {"job_id": job_id, "document_id": doc.id, "filename": doc.original_filename, "stored_path": doc.stored_path},
            )
            job.status = JobStatus.PROCESSING
            job.celery_task_id = self.request.id
            job.progress_percent = 0
            job.current_stage = "job_started"
            job.error_message = None
            session.flush()

            _emit(job_id, "job_started", 5, stage="job_started")
            time.sleep(0.3)

            _emit(job_id, "document_received", 15, stage="document_received", filename=doc.original_filename)
            time.sleep(0.2)

            _emit(job_id, "document_parsing_started", 25, stage="document_parsing_started")
            time.sleep(0.5)
            _emit(job_id, "document_parsing_completed", 45, stage="document_parsing_completed")
            time.sleep(0.2)

            _emit(job_id, "field_extraction_started", 55, stage="field_extraction_started")
            time.sleep(0.4)
            result = build_structured_result(
                original_filename=doc.original_filename,
                stored_path=doc.stored_path,
                mime_type=doc.mime_type,
                file_size_bytes=doc.file_size_bytes,
            )
            print("[process_document_job] build_structured_result ok", {"job_id": job_id, "keys": list(result.keys())})
            _emit(job_id, "field_extraction_completed", 80, stage="field_extraction_completed")
            time.sleep(0.2)

            job.result_json = result
            job.reviewed_result_json = result.copy()
            job.progress_percent = 90
            job.current_stage = "final_result_stored"
            session.flush()
            _emit(job_id, "final_result_stored", 95, stage="final_result_stored")

            job.status = JobStatus.COMPLETED
            job.progress_percent = 100
            job.current_stage = "job_completed"
            session.flush()

            _emit(job_id, "job_completed", 100, stage="job_completed")
            print("[process_document_job] completed", {"job_id": job_id})
            return {"ok": True, "job_id": job_id}

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)[:2000]
            job.progress_percent = min(job.progress_percent, 99)
            session.flush()
            tb = traceback.format_exc()
            print("[process_document_job] FAILED", {"job_id": job_id, "error": f"{type(e).__name__}: {e}"})
            print("[process_document_job] Traceback:\n" + tb)
            _emit(job_id, "job_failed", job.progress_percent, stage="job_failed", message=str(e), traceback=tb[-4000:])
            return {"ok": False, "error": str(e)}

from __future__ import annotations

import asyncio
import json
from typing import Annotated, AsyncIterator

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.redis_progress import progress_channel
from app.services.job_service import get_job

router = APIRouter(prefix="/api/v1", tags=["progress"])


async def _sse_stream(job_id: int, request: Request) -> AsyncIterator[bytes]:
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = r.pubsub()
    channel = progress_channel(job_id)
    await pubsub.subscribe(channel)
    try:
        last = await r.get(f"job:{job_id}:progress:last")
        if last:
            yield f"data: {last}\n\n".encode()
        while True:
            if await request.is_disconnected():
                break
            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True),
                    timeout=30.0,
                )
            except asyncio.TimeoutError:
                yield b": keepalive\n\n"
                continue
            if message and message["type"] == "message" and message.get("data"):
                data = message["data"]
                yield f"data: {data}\n\n".encode()
                try:
                    payload = json.loads(data)
                    if payload.get("event") in ("job_completed", "job_failed"):
                        break
                except json.JSONDecodeError:
                    pass
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        await r.aclose()


@router.get("/jobs/{job_id}/events")
async def job_events(
    job_id: int,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    job = await get_job(session, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return StreamingResponse(
        _sse_stream(job_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import redis

from app.config import settings

logger = logging.getLogger(__name__)


def progress_channel(job_id: int) -> str:
    return f"job:{job_id}:progress"


def get_sync_redis() -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


def publish_progress(job_id: int, event: str, progress_percent: int = 0, stage: Optional[str] = None, **extra: Any) -> None:
    """Publish to Redis Pub/Sub. Does not raise — Redis may be down during local dev."""
    payload = {
        "event": event,
        "progress_percent": progress_percent,
        "stage": stage,
        **{k: v for k, v in extra.items() if v is not None},
    }
    try:
        r = get_sync_redis()
        r.publish(progress_channel(job_id), json.dumps(payload))
    except (redis.ConnectionError, redis.RedisError, TimeoutError, OSError) as e:
        logger.warning("redis progress publish skipped (job_id=%s): %s", job_id, e)


def cache_latest_progress(job_id: int, payload: dict[str, Any], ttl_seconds: int = 3600) -> None:
    """Allow polling clients to read last known state without SSE."""
    try:
        r = get_sync_redis()
        key = f"job:{job_id}:progress:last"
        r.setex(key, ttl_seconds, json.dumps(payload))
    except (redis.ConnectionError, redis.RedisError, TimeoutError, OSError) as e:
        logger.warning("redis cache_latest_progress skipped (job_id=%s): %s", job_id, e)

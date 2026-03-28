import json
import uuid
import uuid as uuid_lib
import os

import redis.asyncio as aioredis
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.gaps.citation import detect_citation_gaps
from app.redis_client import get_redis

router = APIRouter(prefix="/gaps", tags=["gaps"])

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CACHE_TTL_SECONDS = 3600


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── US 3.7 + US 3.9 ────────────────────────────────────────────────────────
@router.get("/{workspace_id}")
async def get_gaps(
    workspace_id: str,
    redis: aioredis.Redis = Depends(get_redis),
    db: Session = Depends(get_db),
):
    try:
        uuid_lib.UUID(workspace_id)
    except ValueError:
        return {"citation_gaps": [], "semantic_gaps": []}

    cached_citation = await redis.get(f"gaps:{workspace_id}:citation")
    cached_semantic = await redis.get(f"gaps:{workspace_id}:semantic")

    if cached_citation is not None:
        return {
            "citation_gaps": json.loads(cached_citation),
            "semantic_gaps": json.loads(cached_semantic) if cached_semantic else [],
        }

    citation_gaps = detect_citation_gaps(workspace_id, db)

    await redis.setex(
        f"gaps:{workspace_id}:citation",
        CACHE_TTL_SECONDS,
        json.dumps(citation_gaps),
    )

    semantic_gaps = json.loads(cached_semantic) if cached_semantic else []

    return {"citation_gaps": citation_gaps, "semantic_gaps": semantic_gaps}


# ── US 3.4 ─────────────────────────────────────────────────────────────────
@router.post("/{workspace_id}/detect")
async def trigger_gap_detection(workspace_id):
    job_id = str(uuid.uuid4())
    pool = await create_pool(RedisSettings.from_dsn(REDIS_URL))

    await pool.enqueue_job(
        "detect_gaps",
        workspace_id,
        _job_id=job_id,
    )
    await pool.aclose()

    return {"job_id": job_id}


# ── US 3.9 cache invalidation ───────────────────────────────────────────────
@router.delete("/{workspace_id}/cache")
async def invalidate_gaps_cache(
    workspace_id: str,
    redis: aioredis.Redis = Depends(get_redis),
):
    try:
        uuid_lib.UUID(workspace_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workspace ID")

    await redis.delete(f"gaps:{workspace_id}:citation")
    await redis.delete(f"gaps:{workspace_id}:semantic")
    return {"invalidated": True}

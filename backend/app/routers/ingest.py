import os
import uuid

import redis.asyncio as aioredis
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.redis_client import get_redis

router = APIRouter(prefix="/ingest", tags=["ingest"])

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


# ── US 2.6 ─────────────────────────────────────────────────────────────────
@router.get("/status/{job_id}")
async def get_job_status(
    job_id: str,
    redis: aioredis.Redis = Depends(get_redis),
):
    """Poll the status of a background ingestion job."""
    status = await redis.get(f"job:{job_id}:status")
    if status is None:
        raise HTTPException(status_code=404, detail="Job not found")

    progress = await redis.get(f"job:{job_id}:progress") or "0"
    paper_id = await redis.get(f"job:{job_id}:paper_id")  # None until job completes

    return {
        "job_id": job_id,
        "status": status,        # "pending" | "running" | "done" | "failed"
        "progress": int(progress),
        "paper_id": paper_id,    # UUID string, or null while in progress
    }


# ── US 2.7 ─────────────────────────────────────────────────────────────────
class IngestDOIRequest(BaseModel):
    doi: str
    workspace_id: str


@router.post("/doi")
async def ingest_doi(
    request: IngestDOIRequest,
    redis: aioredis.Redis = Depends(get_redis),
):
    """Enqueue a background ingestion job from a DOI."""
    doi = request.doi.strip()

    # Normalize — accept bare DOI or doi: prefix
    if doi.lower().startswith("doi:"):
        doi = doi[4:]
    if not doi.startswith("10."):
        raise HTTPException(
            status_code=400,
            detail="Invalid DOI. Must start with '10.' (e.g. 10.1145/3442188.3445922)",
        )

    job_id = str(uuid.uuid4())

    # Write initial status so E1's status endpoint can find it immediately
    await redis.set(f"job:{job_id}:status", "pending")
    await redis.set(f"job:{job_id}:progress", "0")

    # Enqueue into the arq job queue — E1's worker picks this up
    pool = await create_pool(RedisSettings.from_dsn(REDIS_URL))
    await pool.enqueue_job(
        "ingest_paper",           # ← must match the function name in E1's worker
        f"doi:{doi}",             # the url/identifier argument
        request.workspace_id,
        _job_id=job_id,           # tell arq to use our job_id as the queue key
    )
    await pool.aclose()

    return {"job_id": job_id, "status": "pending"}
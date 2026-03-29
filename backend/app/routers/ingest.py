import os
import uuid

import redis.asyncio as aioredis
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.redis_client import get_redis, check_rate_limit
from app.dependencies import get_current_user
from app.analytics import track_event

router = APIRouter(prefix="/ingest", tags=["ingest"], dependencies=[Depends(get_current_user)])

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


# ── US 2.1 ─────────────────────────────────────────────────────────────────
class IngestURLRequest(BaseModel):
    url: str
    workspace_id: str


@router.post("/url")
async def ingest_url(body: IngestURLRequest, current_user=Depends(get_current_user), redis=Depends(get_redis),):
    await check_rate_limit(redis, current_user["id"], "ingest_url", 100)
    job_id = str(uuid.uuid4())
    await redis.set(f"job:{job_id}:status", "pending")
    await redis.set(f"job:{job_id}:progress", "0")

    pool = await create_pool(RedisSettings.from_dsn(REDIS_URL))

    await pool.enqueue_job(
        "ingest_paper",
        url=body.url,
        workspace_id=body.workspace_id,
        _job_id=job_id,
    )
    await pool.aclose()

    await track_event(current_user["id"], "paper_ingested", {"workspace_id": body.workspace_id, "url": body.url})
    return {"job_id": job_id}


# ── US 2.6 ─────────────────────────────────────────────────────────────────
@router.get("/status/{job_id}")
async def get_job_status(
    job_id: str,
    redis: aioredis.Redis = Depends(get_redis),
):
    status = await redis.get(f"job:{job_id}:status")
    if status is None:
        raise HTTPException(status_code=404, detail="Job not found")

    progress = await redis.get(f"job:{job_id}:progress") or "0"
    paper_id = await redis.get(f"job:{job_id}:paper_id")
    if isinstance(status, bytes):
        status = status.decode()
    if isinstance(progress, bytes):
        progress = progress.decode()
    if isinstance(paper_id, bytes):
        paper_id = paper_id.decode()

    return {
        "job_id": job_id,
        "status": status,
        "progress": int(progress),
        "paper_id": paper_id,
    }


# ── US 2.7 ─────────────────────────────────────────────────────────────────
class IngestDOIRequest(BaseModel):
    doi: str
    workspace_id: str


@router.post("/doi")
async def ingest_doi(
    request: IngestDOIRequest,
    current_user=Depends(get_current_user),
    redis=Depends(get_redis),
):
    await check_rate_limit(redis, str(current_user["id"]), "ingest_doi", 100)
    doi = request.doi.strip()

    if doi.lower().startswith("doi:"):
        doi = doi[4:].strip()
    if not doi.startswith("10."):
        raise HTTPException(
            status_code=400,
            detail="Invalid DOI. Must start with '10.' (e.g. 10.1145/3442188.3445922)",
        )
    if "/" not in doi:
        raise HTTPException(
            status_code=400,
            detail="Incomplete DOI — include the suffix, e.g. 10.48550/arXiv.1706.03762 or 10.1145/3442188.3445922",
        )

    job_id = str(uuid.uuid4())

    await redis.set(f"job:{job_id}:status", "pending")
    await redis.set(f"job:{job_id}:progress", "0")

    pool = await create_pool(RedisSettings.from_dsn(REDIS_URL))
    await pool.enqueue_job(
        "ingest_paper",
        f"doi:{doi}",
        request.workspace_id,
        _job_id=job_id,
    )
    await pool.aclose()

    await track_event(str(current_user["id"]), "paper_ingested", {"workspace_id": request.workspace_id, "doi": doi})
    return {"job_id": job_id, "status": "pending"}

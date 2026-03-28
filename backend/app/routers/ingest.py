import uuid
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os

router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestURLRequest(BaseModel):
    url: str
    workspace_id: str


@router.post("/url")
async def ingest_url(body: IngestURLRequest):
    redis = await create_pool(RedisSettings.from_dsn(os.getenv("REDIS_URL", "redis://localhost:6379")))
    job_id = str(uuid.uuid4())

    await redis.enqueue_job(
        "ingest_paper",
        url=body.url,
        workspace_id=body.workspace_id,
        _job_id=job_id,
    )

    return {"job_id": job_id}

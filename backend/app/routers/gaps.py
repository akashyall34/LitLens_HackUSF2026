import uuid
import os
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter

router = APIRouter(prefix="/gaps", tags=["gaps"])

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


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

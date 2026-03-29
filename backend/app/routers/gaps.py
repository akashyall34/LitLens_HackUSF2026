import json
import uuid
import uuid as uuid_lib
import os

import redis.asyncio as aioredis
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.dependencies import get_current_user
from app.gaps.citation import detect_citation_gaps
from app.redis_client import get_redis
from app.analytics import track_event

router = APIRouter(prefix="/gaps", tags=["gaps"], dependencies=[Depends(get_current_user)])

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
    current_user=Depends(get_current_user),
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
        citation_gaps = json.loads(cached_citation)
        semantic_gaps = json.loads(cached_semantic) if cached_semantic else []
    else:
        citation_gaps = detect_citation_gaps(workspace_id, db)

        await redis.setex(
            f"gaps:{workspace_id}:citation",
            CACHE_TTL_SECONDS,
            json.dumps(citation_gaps),
        )

        semantic_gaps = json.loads(cached_semantic) if cached_semantic else []

    # ── US 5.9: Team coverage — papers per member (always fetched, not cached) ──
    team_rows = db.execute(
        text("""
            SELECT u.email, COUNT(wp.paper_id) AS paper_count
            FROM workspace_members wm
            JOIN users u ON u.id = wm.user_id
            LEFT JOIN workspace_papers wp ON wp.workspace_id = wm.workspace_id
                                        AND wp.added_by = wm.user_id
            WHERE wm.workspace_id = :wid
            GROUP BY u.email
        """),
        {"wid": workspace_id},
    ).fetchall()

    team_coverage = [
        {"member_email": row.email, "papers_added": int(row.paper_count)}
        for row in team_rows
    ]

    total_gaps = len(citation_gaps) + len(semantic_gaps)
    if total_gaps > 0:
        await track_event(
            current_user["id"],
            "blind_spot_surfaced",
            {"workspace_id": workspace_id, "citation_gaps": len(citation_gaps), "semantic_gaps": len(semantic_gaps)},
        )

    return {
        "citation_gaps": citation_gaps,
        "semantic_gaps": semantic_gaps,
        "team_coverage": team_coverage,
    }


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

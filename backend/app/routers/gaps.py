import json
import uuid as uuid_lib

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.gaps.citation import detect_citation_gaps
from app.redis_client import get_redis

router = APIRouter(prefix="/gaps", tags=["gaps"])

CACHE_TTL_SECONDS = 3600  # 1 hour — US 3.9


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
    """
    Return citation gaps and semantic gaps for a workspace.
    Citation gaps are computed by Layer 1 (E2).
    Semantic gaps are written to cache by E1's GapDetectionAgent.
    Results are cached in Redis for 1 hour (US 3.9).
    """
    try:
        uuid_lib.UUID(workspace_id)
    except ValueError:
        return {"citation_gaps": [], "semantic_gaps": []}

    # ── Check cache first (US 3.9) ─────────────────────────────────────
    cached_citation = await redis.get(f"gaps:{workspace_id}:citation")
    cached_semantic = await redis.get(f"gaps:{workspace_id}:semantic")

    if cached_citation is not None:
        return {
            "citation_gaps": json.loads(cached_citation),
            "semantic_gaps": json.loads(cached_semantic) if cached_semantic else [],
        }

    # ── Run Layer 1 citation gap detection (US 3.6) ────────────────────
    citation_gaps = detect_citation_gaps(workspace_id, db)

    # ── Cache results for 1 hour (US 3.9) ─────────────────────────────
    await redis.setex(
        f"gaps:{workspace_id}:citation",
        CACHE_TTL_SECONDS,
        json.dumps(citation_gaps),
    )

    # Semantic gaps: E1's agent writes to gaps:{workspace_id}:semantic
    semantic_gaps = json.loads(cached_semantic) if cached_semantic else []

    return {"citation_gaps": citation_gaps, "semantic_gaps": semantic_gaps}


@router.delete("/{workspace_id}/cache")
async def invalidate_gaps_cache(
    workspace_id: str,
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Clear the gaps cache for a workspace.
    Call this after new papers are ingested so the next GET recomputes.
    """
    try:
        uuid_lib.UUID(workspace_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workspace ID")

    await redis.delete(f"gaps:{workspace_id}:citation")
    await redis.delete(f"gaps:{workspace_id}:semantic")
    return {"invalidated": True}
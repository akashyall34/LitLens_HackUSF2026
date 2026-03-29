import json
import os

from arq.connections import RedisSettings

from app.db import SessionLocal
from app.agents.tools.gap_tools import detect_semantic_gaps

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


async def detect_gaps(ctx, workspace_id):
    job_id = ctx["job_id"]
    r = ctx["redis"]

    await r.set(f"job:{job_id}:status", "running")
    await r.set(f"job:{job_id}:progress", 10)

    db = SessionLocal()
    try:
        semantic_gaps = detect_semantic_gaps(workspace_id, db)
        await r.set(f"job:{job_id}:progress", 80)

        cache_payload = json.dumps([
            {
                "label": g["label"],
                "coverage_score": g["coverage_score"],
                "why_matters": g["why_matters"],
                "top_papers": [
                    {"id": str(p.id), "title": p.title} for p in g["top_papers"]
                ],
            }
            for g in semantic_gaps
        ])
        await r.set(f"gaps:{workspace_id}:semantic", cache_payload, ex=3600)

        await r.set(f"job:{job_id}:progress", 100)
        await r.set(f"job:{job_id}:status", "done")

    except Exception:
        db.rollback()
        await r.set(f"job:{job_id}:status", "failed")
        raise
    finally:
        db.close()

    return {"workspace_id": workspace_id, "semantic_gaps": len(semantic_gaps)}


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
    functions = [detect_gaps]

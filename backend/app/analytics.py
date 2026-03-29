"""
US 7.2 — fire-and-forget usage event tracking.
Never raises — analytics must not block or fail requests.
"""
import json
import logging

from sqlalchemy import text

from app.db import SessionLocal

logger = logging.getLogger(__name__)

VALID_EVENTS = {
    "paper_ingested",
    "blind_spot_surfaced",
    "rag_query",
    "gap_added_to_workspace",
}


async def track_event(user_id: str, event: str, metadata: dict | None = None) -> None:
    """Write a usage event row. Silently swallows all errors."""
    if event not in VALID_EVENTS:
        return
    db = SessionLocal()
    try:
        db.execute(
            text(
                "INSERT INTO usage_events (user_id, event, metadata) "
                "VALUES (CAST(:uid AS UUID), :event, CAST(:meta AS jsonb))"
            ),
            {
                "uid": str(user_id),
                "event": event,
                "meta": json.dumps(metadata or {}),
            },
        )
        db.commit()
    except Exception:
        logger.exception("track_event failed silently")
        db.rollback()
    finally:
        db.close()

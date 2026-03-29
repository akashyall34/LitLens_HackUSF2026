"""Keeps the hardcoded frontend workspace in sync with Postgres (no manual SQL)."""

from sqlalchemy import text
from sqlalchemy.orm import Session

# Must match frontend WORKSPACE_ID (App.tsx, BlindSpotPanel, etc.)
DEMO_WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"


def ensure_demo_workspace_for_user(db: Session, user_id: str) -> None:
    """
    Ensure the demo workspace row exists and this user is in workspace_members.
    First member becomes owner; later users become members. Safe under concurrent signups.
    """
    wid = DEMO_WORKSPACE_ID
    db.execute(
        text("""
            INSERT INTO workspaces (id, name, owner_id)
            VALUES (CAST(:wid AS UUID), :name, CAST(:uid AS UUID))
            ON CONFLICT (id) DO NOTHING
        """),
        {"wid": wid, "name": "Demo", "uid": user_id},
    )
    db.execute(
        text("""
            INSERT INTO workspace_members (workspace_id, user_id, role)
            SELECT CAST(:wid AS UUID), CAST(:uid AS UUID),
                   CASE
                       WHEN EXISTS (
                           SELECT 1 FROM workspace_members m
                           WHERE m.workspace_id = CAST(:wid AS UUID)
                       ) THEN 'member'
                       ELSE 'owner'
                   END
            ON CONFLICT (workspace_id, user_id) DO NOTHING
        """),
        {"wid": wid, "uid": user_id},
    )

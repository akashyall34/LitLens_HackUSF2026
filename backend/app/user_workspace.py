"""Each user gets their own workspace on register; invitees join the inviter's workspace."""

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

# Old builds auto-added everyone as a *member* of this workspace. Do not treat it as the user's
# primary "invited" team — otherwise new accounts still see the shared QA graph.
LEGACY_DEMO_WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"


def _insert_workspace(db: Session, workspace_id: str, owner_user_id: str, name: str = "My workspace") -> None:
    db.execute(
        text("""
            INSERT INTO workspaces (id, name, owner_id)
            VALUES (CAST(:wid AS UUID), :name, CAST(:uid AS UUID))
        """),
        {"wid": workspace_id, "name": name, "uid": owner_user_id},
    )
    db.execute(
        text("""
            INSERT INTO workspace_members (workspace_id, user_id, role)
            VALUES (CAST(:wid AS UUID), CAST(:uid AS UUID), 'owner')
        """),
        {"wid": workspace_id, "uid": owner_user_id},
    )


def create_personal_workspace(db: Session, user_id: str) -> str:
    """Create a new workspace owned by this user. Does not commit."""
    wid = str(uuid.uuid4())
    _insert_workspace(db, wid, user_id)
    return wid


def primary_workspace_id_for_user(db: Session, user_id: str) -> str | None:
    """Prefer invited (non-owned) workspaces so join flows show the team graph; else own workspace."""
    invited = db.execute(
        text("""
            SELECT w.id::text
            FROM workspace_members wm
            JOIN workspaces w ON w.id = wm.workspace_id
            WHERE wm.user_id = CAST(:u AS UUID)
              AND w.owner_id != CAST(:u AS UUID)
              AND w.id != CAST(:legacy AS UUID)
            ORDER BY wm.joined_at DESC
            LIMIT 1
        """),
        {"u": user_id, "legacy": LEGACY_DEMO_WORKSPACE_ID},
    ).fetchone()
    if invited:
        return invited[0]

    owned = db.execute(
        text("""
            SELECT id::text FROM workspaces
            WHERE owner_id = CAST(:u AS UUID)
            ORDER BY created_at ASC
            LIMIT 1
        """),
        {"u": user_id},
    ).fetchone()
    return owned[0] if owned else None


def ensure_user_has_workspace(db: Session, user_id: str) -> str:
    """Return primary workspace id, creating a personal one if the user has none."""
    wid = primary_workspace_id_for_user(db, user_id)
    if wid:
        return wid
    return create_personal_workspace(db, user_id)

import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import boto3
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces", tags=["workspaces"], dependencies=[Depends(get_current_user)])

APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5173")
SES_FROM_EMAIL = os.getenv("SES_FROM_EMAIL", "noreply@litlens.app")


def _invite_base_url() -> str:
    """Base URL for /join links. CORS sometimes sets FRONTEND_ORIGIN=* — that is invalid here."""
    for raw in (os.getenv("FRONTEND_ORIGIN"), os.getenv("APP_BASE_URL"), "http://localhost:5173"):
        if not raw:
            continue
        u = raw.strip().rstrip("/")
        if u == "*" or not u.startswith(("http://", "https://")):
            continue
        return u
    logger.warning("invite_base_url: no valid FRONTEND_ORIGIN or APP_BASE_URL")
    return "http://localhost:5173"
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

_ses = None


def _get_ses():
    global _ses
    if _ses is None:
        _ses = boto3.client("ses", region_name=AWS_REGION)
    return _ses


class InviteRequest(BaseModel):
    email: str


class JoinRequest(BaseModel):
    token: str


def _parse_uuid(wid: str, label: str = "workspace_id") -> str:
    try:
        return str(uuid.UUID(wid))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {label}") from None


@router.get("/{workspace_id}/members")
def list_workspace_members(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    wid = _parse_uuid(workspace_id)
    in_ws = db.execute(
        text("""
            SELECT 1 FROM workspace_members
            WHERE workspace_id = CAST(:wid AS UUID) AND user_id = CAST(:uid AS UUID)
        """),
        {"wid": wid, "uid": current_user["id"]},
    ).fetchone()
    if not in_ws:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    ws = db.execute(
        text("SELECT owner_id::text FROM workspaces WHERE id = CAST(:wid AS UUID)"),
        {"wid": wid},
    ).fetchone()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    owner_id = ws._mapping["owner_id"]

    rows = db.execute(
        text("""
            SELECT u.id::text AS user_id, u.email, wm.role
            FROM workspace_members wm
            JOIN users u ON u.id = wm.user_id
            WHERE wm.workspace_id = CAST(:wid AS UUID)
            ORDER BY LOWER(u.email)
        """),
        {"wid": wid},
    ).fetchall()

    members = [
        {"user_id": r._mapping["user_id"], "email": r._mapping["email"], "role": r._mapping["role"]}
        for r in rows
    ]
    return {"owner_id": owner_id, "members": members}


@router.delete("/{workspace_id}/members/{member_user_id}")
def remove_workspace_member(
    workspace_id: str,
    member_user_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    wid = _parse_uuid(workspace_id)
    target_uid = _parse_uuid(member_user_id, "user_id")

    ws = db.execute(
        text("SELECT owner_id::text FROM workspaces WHERE id = CAST(:wid AS UUID)"),
        {"wid": wid},
    ).fetchone()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    owner_id = ws._mapping["owner_id"]
    if str(owner_id) != str(current_user["id"]):
        raise HTTPException(status_code=403, detail="Only the workspace owner can remove members")

    if str(target_uid) == str(owner_id):
        raise HTTPException(status_code=400, detail="Cannot remove the workspace owner")

    result = db.execute(
        text("""
            DELETE FROM workspace_members
            WHERE workspace_id = CAST(:wid AS UUID) AND user_id = CAST(:uid AS UUID)
        """),
        {"wid": wid, "uid": target_uid},
    )
    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(status_code=404, detail="Member not in this workspace")
    db.commit()
    return {"removed": True, "user_id": target_uid}


@router.post("/join")
def join_workspace(
    body: JoinRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Redeem an invite token; caller must be signed in with the invited email."""
    row = db.execute(
        text("""
            SELECT id, workspace_id, invited_email, expires_at
            FROM workspace_invites
            WHERE invite_token = :t
        """),
        {"t": body.token.strip()},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Invalid or unknown invite link")
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="This invite has expired")

    invited_raw = (row.invited_email or "").strip()
    invited = invited_raw.lower()
    signed_in = (current_user["email"] or "").strip().lower()
    if signed_in != invited:
        raise HTTPException(
            status_code=403,
            detail=(
                f"This invite was sent to {invited_raw}, but you are signed in as {current_user['email']}. "
                "Sign out, sign in with the invited address, then open this link again."
            ),
        )

    db.execute(
        text("""
            INSERT INTO workspace_members (workspace_id, user_id, role)
            VALUES (CAST(:wid AS UUID), CAST(:uid AS UUID), 'member')
            ON CONFLICT (workspace_id, user_id) DO NOTHING
        """),
        {"wid": str(row.workspace_id), "uid": current_user["id"]},
    )
    db.commit()
    return {"workspace_id": str(row.workspace_id), "ok": True}


@router.post("/{workspace_id}/invite")
def invite_member(
    workspace_id: str,
    body: InviteRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Validate workspace exists
    workspace = db.execute(
        text("SELECT id, name FROM workspaces WHERE id = CAST(:wid AS UUID)"),
        {"wid": workspace_id},
    ).fetchone()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    invite_id = str(uuid.uuid4())
    invite_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    join_url = f"{_invite_base_url()}/join?token={invite_token}"

    db.execute(
        text("""
            INSERT INTO workspace_invites (id, workspace_id, invited_email, invite_token, expires_at)
            VALUES (CAST(:id AS UUID), CAST(:wid AS UUID), :email, :token, :exp)
        """),
        {
            "id": invite_id,
            "wid": workspace_id,
            "email": body.email.lower().strip(),
            "token": invite_token,
            "exp": expires_at,
        },
    )
    db.commit()

    email_sent = _send_invite_email(
        to_email=body.email,
        workspace_name=workspace.name,
        inviter_email=current_user["email"],
        join_url=join_url,
    )

    return {"invite_id": invite_id, "join_url": join_url, "email_sent": email_sent}


def _send_invite_email(to_email: str, workspace_name: str, inviter_email: str, join_url: str) -> bool:
    """Send SES invite email. Returns False if skipped or delivery failed."""
    ses_email = os.getenv("SES_FROM_EMAIL")
    if not ses_email:
        return False
    try:
        _get_ses().send_email(
            Source=ses_email,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": f"You've been invited to '{workspace_name}' on LitLens"},
                "Body": {
                    "Text": {
                        "Data": (
                            f"{inviter_email} has invited you to collaborate on '{workspace_name}'.\n\n"
                            f"Click the link below to join:\n{join_url}\n\n"
                            "This link expires in 7 days."
                        )
                    }
                },
            },
        )
        return True
    except Exception:
        logger.exception("SES send_email failed for workspace invite")
        return False
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

router = APIRouter(prefix="/workspaces", tags=["workspaces"], dependencies=[Depends(get_current_user)])

APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5173")
SES_FROM_EMAIL = os.getenv("SES_FROM_EMAIL", "noreply@litlens.app")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

_ses = None


def _get_ses():
    global _ses
    if _ses is None:
        _ses = boto3.client("ses", region_name=AWS_REGION)
    return _ses


class InviteRequest(BaseModel):
    email: str


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
    join_url = f"{APP_BASE_URL}/join?token={invite_token}"

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

    # Send email via SES (gracefully skips if AWS not configured yet)
    _send_invite_email(
        to_email=body.email,
        workspace_name=workspace.name,
        inviter_email=current_user["email"],
        join_url=join_url,
    )

    return {"invite_id": invite_id, "join_url": join_url}


def _send_invite_email(to_email: str, workspace_name: str, inviter_email: str, join_url: str):
    """Send SES invite email. Silently skips if AWS SES is not configured."""
    ses_email = os.getenv("SES_FROM_EMAIL")
    if not ses_email:
        return  # SES not configured yet (wired up in Sprint 6)
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
    except Exception:
        pass  # Non-fatal — invite record is saved even if email fails
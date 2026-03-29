import asyncio
import io
import os
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from fastapi import WebSocket, WebSocketDisconnect
import y_py as Y
from ypy_websocket import WebsocketProvider

from app.auth.utils import decode_access_token

S3_BUCKET = os.getenv("S3_BUCKET")
S3_PREFIX = "yjs-snapshots"

_s3 = boto3.client("s3") if S3_BUCKET else None


async def load_ydoc_from_s3(workspace_id: str) -> Y.YDoc:
    """Load existing Yjs doc from S3, or create a fresh one."""
    doc = Y.YDoc()
    if not _s3 or not S3_BUCKET:
        return doc  # S3 not configured — return empty doc (Sprint 6 wires this up)
    try:
        key = f"{S3_PREFIX}/{workspace_id}.bin"
        response = _s3.get_object(Bucket=S3_BUCKET, Key=key)
        state = response["Body"].read()
        Y.apply_update(doc, state)
    except ClientError as e:
        if e.response["Error"]["Code"] != "NoSuchKey":
            raise
    return doc


async def save_ydoc_to_s3(workspace_id: str, doc: Y.YDoc) -> None:
    """Serialize Yjs doc and save to S3."""
    if not _s3 or not S3_BUCKET:
        return  # S3 not configured — skip silently
    try:
        state = Y.encode_state_as_update(doc)
        key = f"{S3_PREFIX}/{workspace_id}.bin"
        _s3.put_object(Bucket=S3_BUCKET, Key=key, Body=bytes(state))
    except Exception:
        pass  # Non-fatal — collaboration state is still in memory


async def websocket_endpoint(websocket: WebSocket, workspace_id: str, token: str):
    """
    WebSocket handler for real-time Yjs collaboration (US 5.8).
    Saves doc to S3 every 60s and on disconnect (US 5.10).
    """
    # Validate JWT from query param
    user_id = decode_access_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()

    ydoc = await load_ydoc_from_s3(workspace_id)

    # US 5.10: periodic save every 60 seconds
    async def periodic_save():
        while True:
            await asyncio.sleep(60)
            await save_ydoc_to_s3(workspace_id, ydoc)

    save_task = asyncio.create_task(periodic_save())

    try:
        async with WebsocketProvider(ydoc, websocket):
            await websocket.wait_for_disconnect()
    except WebSocketDisconnect:
        pass
    finally:
        save_task.cancel()
        await save_ydoc_to_s3(workspace_id, ydoc)  # final save on disconnect
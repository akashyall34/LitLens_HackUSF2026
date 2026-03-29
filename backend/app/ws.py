import asyncio
import os
from collections import defaultdict

import boto3
from botocore.exceptions import ClientError
from fastapi import WebSocket, WebSocketDisconnect
import y_py as Y
from ypy_websocket import WebsocketProvider

from app.auth.utils import decode_access_token

S3_BUCKET = os.getenv("S3_BUCKET")
S3_PREFIX = "yjs-snapshots"

_s3 = boto3.client("s3") if S3_BUCKET else None

# One shared Y.Doc per workspace so all WebSocket clients merge into the same CRDT.
_workspace_docs: dict[str, Y.YDoc] = {}
_workspace_refcount: dict[str, int] = defaultdict(int)
_workspace_lock = asyncio.Lock()
_workspace_save_tasks: dict[str, asyncio.Task] = {}


async def load_ydoc_from_s3(workspace_id: str) -> Y.YDoc:
    """Load existing Yjs doc from S3, or create a fresh one."""
    doc = Y.YDoc()
    if not _s3 or not S3_BUCKET:
        return doc
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
        return
    try:
        state = Y.encode_state_as_update(doc)
        key = f"{S3_PREFIX}/{workspace_id}.bin"
        _s3.put_object(Bucket=S3_BUCKET, Key=key, Body=bytes(state))
    except Exception:
        pass


async def _periodic_save_workspace(workspace_id: str, ydoc: Y.YDoc) -> None:
    try:
        while True:
            await asyncio.sleep(60)
            await save_ydoc_to_s3(workspace_id, ydoc)
    except asyncio.CancelledError:
        await save_ydoc_to_s3(workspace_id, ydoc)
        raise


async def _acquire_workspace_doc(workspace_id: str) -> Y.YDoc:
    async with _workspace_lock:
        if workspace_id not in _workspace_docs:
            _workspace_docs[workspace_id] = await load_ydoc_from_s3(workspace_id)
        _workspace_refcount[workspace_id] += 1
        ydoc = _workspace_docs[workspace_id]
        if workspace_id not in _workspace_save_tasks:
            _workspace_save_tasks[workspace_id] = asyncio.create_task(
                _periodic_save_workspace(workspace_id, ydoc)
            )
        return ydoc


async def _release_workspace_doc(workspace_id: str) -> None:
    task_to_cancel = None
    ydoc_to_save = None
    async with _workspace_lock:
        _workspace_refcount[workspace_id] -= 1
        if _workspace_refcount[workspace_id] > 0:
            return
        task_to_cancel = _workspace_save_tasks.pop(workspace_id, None)
        ydoc_to_save = _workspace_docs.pop(workspace_id, None)
        _workspace_refcount.pop(workspace_id, None)

    if task_to_cancel:
        task_to_cancel.cancel()
        try:
            await task_to_cancel
        except asyncio.CancelledError:
            pass
    if ydoc_to_save:
        await save_ydoc_to_s3(workspace_id, ydoc_to_save)


async def websocket_endpoint(websocket: WebSocket, workspace_id: str, token: str):
    """
    WebSocket handler for real-time Yjs collaboration (US 5.8).
    All connections for the same workspace_id share one Y.Doc so CRDT state syncs.
    """
    user_id = decode_access_token(token)
    if not user_id:
        await websocket.accept()
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()

    ydoc = await _acquire_workspace_doc(workspace_id)

    try:
        async with WebsocketProvider(ydoc, websocket):
            await websocket.wait_for_disconnect()
    except WebSocketDisconnect:
        pass
    finally:
        await _release_workspace_doc(workspace_id)

import os

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.routers.ingest import router as ingest_router
from app.routers import auth as auth_router
from app.routers import edges as edges_router
from app.routers import gaps as gaps_router
from app.routers import graph as graph_router
from app.routers import rag as rag_router
from app.routers import workspaces as workspaces_router
from app.ws import websocket_endpoint

load_dotenv()

frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

app = FastAPI(title="LitLens API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public routes — no auth required
app.include_router(auth_router.router)

# Protected routes — all require valid JWT
app.include_router(ingest_router)
app.include_router(graph_router.router)
app.include_router(gaps_router.router)
app.include_router(rag_router.router)
app.include_router(edges_router.router)
app.include_router(workspaces_router.router)

# WebSocket for real-time Yjs collaboration (US 5.8)
@app.websocket("/ws/{workspace_id}")
async def ws_endpoint(websocket: WebSocket, workspace_id: str, token: str):
    await websocket_endpoint(websocket, workspace_id, token)
    
@app.get("/health")
def health():
    return {"status": "ok"}
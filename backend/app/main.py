import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.ingest import router as ingest_router

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

app.include_router(ingest_router)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

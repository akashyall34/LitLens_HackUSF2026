import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from app.agents.tools.rag_tools import answer_rag_query
from app.dependencies import get_current_user
from app.redis_client import get_redis, check_rate_limit
from app.analytics import track_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"], dependencies=[Depends(get_current_user)])


class RAGHistoryTurn(BaseModel):
    query: str = Field(default="", max_length=8000)
    answer: str = Field(default="", max_length=32000)

    @field_validator("query", "answer", mode="before")
    @classmethod
    def coerce_str(cls, v):
        if v is None:
            return ""
        return v if isinstance(v, str) else str(v)


class RAGRequest(BaseModel):
    query: str = Field(max_length=8000)
    workspace_id: str
    history: list[RAGHistoryTurn] = Field(default_factory=list, max_length=24)


@router.post("/query")
async def rag_query(body: RAGRequest, current_user=Depends(get_current_user), redis=Depends(get_redis)):
    await check_rate_limit(redis, current_user["id"], "rag_query", 500)
    hist = [{"query": t.query, "answer": t.answer} for t in body.history]
    try:
        result = answer_rag_query(body.query, body.workspace_id, history=hist)
    except Exception:
        logger.exception("RAG query failed (embed/search/LLM)")
        raise HTTPException(
            status_code=502,
            detail="The answer service failed (often prompt size or model timeout). Try Clear, or a shorter follow-up.",
        ) from None

    await track_event(
        current_user["id"],
        "rag_query",
        {
            "workspace_id": body.workspace_id,
            "query": body.query[:200],
            "history_turns": len(hist),
        },
    )
    return result

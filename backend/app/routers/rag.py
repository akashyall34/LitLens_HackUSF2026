import os
from fastapi import APIRouter
from pydantic import BaseModel
from app.agents.tools.rag_tools import answer_rag_query

router = APIRouter(prefix="/rag", tags=["rag"])

class RAGRequest(BaseModel):
    query: str
    workspace_id: str

@router.post("/query")
async def rag_query(body: RAGRequest):
    result = answer_rag_query(body.query, body.workspace_id)
    return result

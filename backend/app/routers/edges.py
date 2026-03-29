import json
import os
import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException
from google import genai
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.dependencies import get_current_user

router = APIRouter(tags=["ai"], dependencies=[Depends(get_current_user)])

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
_client = genai.Client(api_key=GEMINI_API_KEY)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── US 4.5 helpers ──────────────────────────────────────────────────────────

def _classify_edges_batch(edges: list[dict]) -> list[dict]:
    """
    Classify up to 20 paper pairs in a single Gemini call.
    Returns [{index, edge_type, confidence}, ...].
    """
    pairs = "\n".join(
        f'{i+1}. A="{e["citing_title"][:80]}. {(e["citing_abstract"] or "")[:200]}" '
        f'B="{e["cited_title"][:80]}. {(e["cited_abstract"] or "")[:200]}"'
        for i, e in enumerate(edges)
    )
    prompt = f"""Classify the citation relationship for each pair below.
Relationships: extends | contradicts | uses_dataset | cites
- extends: A builds directly on B's method or framework
- contradicts: A challenges or disputes B's findings
- uses_dataset: A uses the same dataset as B
- cites: general citation, none of the above

Pairs:
{pairs}

Return a JSON array of {len(edges)} objects: [{{"index": 1, "edge_type": "...", "confidence": 0.0-1.0}}, ...]
Return only the JSON array, nothing else."""

    response = _client.models.generate_content(
        model="gemini-2.5-flash", contents=prompt
    )
    return json.loads(response.text)


# ── US 4.5 endpoint ─────────────────────────────────────────────────────────

@router.post("/edges/classify/{workspace_id}")
def classify_workspace_edges(
    workspace_id: str,
    db: Session = Depends(get_db),
):
    """
    Classify all citation edges in a workspace using Gemini.
    Batches 20 pairs per API call to stay within the 15 RPM free-tier limit.
    Updates edge_type and confidence in the citations table.
    """
    try:
        uuid_lib.UUID(workspace_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workspace ID")

    # Fetch all citations where the citing paper is in this workspace
    rows = db.execute(
        text("""
            SELECT
                c.citing_paper_id::text  AS citing_paper_id,
                c.cited_paper_id::text   AS cited_paper_id,
                p1.title                 AS citing_title,
                p1.abstract              AS citing_abstract,
                p2.title                 AS cited_title,
                p2.abstract              AS cited_abstract
            FROM citations c
            JOIN workspace_papers wp ON wp.paper_id = c.citing_paper_id
            JOIN papers p1 ON p1.id = c.citing_paper_id
            JOIN papers p2 ON p2.id = c.cited_paper_id
            WHERE wp.workspace_id = :wid
        """),
        {"wid": workspace_id},
    ).fetchall()

    if not rows:
        return {"classified": 0, "message": "No edges found in this workspace"}

    edges = [dict(row._mapping) for row in rows]
    total_classified = 0

    # Process in batches of 20 — never one call per edge
    for i in range(0, len(edges), 20):
        batch = edges[i : i + 20]
        results = _classify_edges_batch(batch)

        for result in results:
            idx = result["index"] - 1  # Gemini returns 1-indexed
            if idx >= len(batch):
                continue
            edge = batch[idx]
            db.execute(
                text("""
                    UPDATE citations
                    SET edge_type  = :edge_type,
                        confidence = :confidence
                    WHERE citing_paper_id = CAST(:citing_id AS UUID)
                      AND cited_paper_id  = CAST(:cited_id AS UUID)
                """),
                {
                    "edge_type": result.get("edge_type", "cites"),
                    "confidence": result.get("confidence", 1.0),
                    "citing_id": edge["citing_paper_id"],
                    "cited_id": edge["cited_paper_id"],
                },
            )
            total_classified += 1

        db.commit()

    return {"classified": total_classified}


# ── US 4.6 endpoint ─────────────────────────────────────────────────────────

class RelatedWorkRequest(BaseModel):
    workspace_id: str
    cluster_label: str | None = None
    paper_ids: list[str]


@router.post("/clusters/related-work")
def generate_related_work(
    request: RelatedWorkRequest,
    db: Session = Depends(get_db),
):
    """
    Generate a 2-paragraph related work section draft for a cluster of papers.
    Frontend sends the paper IDs in the selected cluster.
    """
    try:
        uuid_lib.UUID(request.workspace_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workspace ID")

    if not request.paper_ids:
        raise HTTPException(status_code=400, detail="No paper IDs provided")

    # Fetch paper metadata (cap at 8 to keep prompt under token limit)
    rows = db.execute(
        text("""
            SELECT title, abstract, authors, year
            FROM papers
            WHERE id::text = ANY(:ids)
            LIMIT 8
        """),
        {"ids": request.paper_ids},
    ).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="No papers found for given IDs")

    papers_text = "\n".join(
        f'- "{row.title}" ({row.year or "n.d."})'
        for row in rows
    )
    cluster_label = request.cluster_label or "this research area"

    prompt = f"""Write a 2-paragraph related work section for a paper that builds on this research cluster: "{cluster_label}".
Use these papers as sources:
{papers_text}

Write in academic style. Cite papers by title in brackets like [Paper Title].
Write exactly 2 paragraphs. Do not include any headings or labels."""

    response = _client.models.generate_content(
        model="gemini-2.5-flash", contents=prompt
    )

    return {
        "cluster_label": cluster_label,
        "draft": response.text,
        "papers_used": len(rows),
    }
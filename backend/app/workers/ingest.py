import os
import uuid

from arq.connections import RedisSettings

from app.clients.paper_lookup import fetch_paper_metadata
from app.workers.gaps import detect_gaps
from app.utils.embeddings import embed_texts
from app.db import SessionLocal
from app.models import Paper, PaperEmbedding, WorkspacePaper

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


def _normalize_doi(raw: str | None) -> str | None:
    if not raw:
        return None
    s = str(raw).strip()
    if s.lower().startswith("doi:"):
        s = s[4:].strip()
    return s.lower() if s else None


async def ingest_paper(ctx, url, workspace_id):
    job_id = ctx["job_id"]
    redis = ctx["redis"]
    
    await redis.set(f"job:{job_id}:status", "running")
    await redis.set(f"job:{job_id}:progress", 10)

    # step 1 - fetch papers metadata
    paper_metadata = fetch_paper_metadata(url)
    await redis.set(f"job:{job_id}:progress", 30)

    # step 2 - generate embedding
    text = f"{paper_metadata['title']}. {paper_metadata.get('abstract') or ''}"
    vectors = embed_texts([text])
    await redis.set(f"job:{job_id}:progress", 60)

    # step 3 - save to DB (reuse existing paper by DOI / Semantic Scholar id)
    db = SessionLocal()
    try:
        doi = _normalize_doi(paper_metadata.get("doi"))
        semantic_id = (paper_metadata.get("semantic_id") or "").strip() or None

        paper = None
        if doi:
            paper = db.query(Paper).filter(Paper.doi == doi).first()
        if paper is None and semantic_id:
            paper = db.query(Paper).filter(Paper.semantic_scholar_id == semantic_id).first()

        if paper is None:
            paper = Paper(
                title=paper_metadata["title"],
                abstract=paper_metadata.get("abstract"),
                year=paper_metadata.get("year"),
                doi=doi,
                semantic_scholar_id=semantic_id,
                source_url=paper_metadata.get("url"),
                citation_count=paper_metadata.get("citation_count", 0),
                venue=paper_metadata.get("venue"),
                authors=paper_metadata.get("authors", []),
            )
            db.add(paper)
            db.flush()

            embedding = PaperEmbedding(
                paper_id=paper.id,
                chunk_index=0,
                embedding=vectors[0],
            )
            db.add(embedding)
        else:
            # Refresh embedding so RAG uses up-to-date vector for this workspace ingest
            existing_emb = (
                db.query(PaperEmbedding)
                .filter(PaperEmbedding.paper_id == paper.id, PaperEmbedding.chunk_index == 0)
                .first()
            )
            if existing_emb:
                existing_emb.embedding = vectors[0]
            else:
                db.add(
                    PaperEmbedding(
                        paper_id=paper.id,
                        chunk_index=0,
                        embedding=vectors[0],
                    )
                )

        ws_id = uuid.UUID(workspace_id)
        already = (
            db.query(WorkspacePaper)
            .filter(
                WorkspacePaper.workspace_id == ws_id,
                WorkspacePaper.paper_id == paper.id,
            )
            .first()
        )
        if not already:
            db.add(WorkspacePaper(workspace_id=ws_id, paper_id=paper.id))

        db.commit()
        paper_id = str(paper.id)

    except Exception:
        db.rollback()
        await redis.set(f"job:{job_id}:status", "failed")
        raise
    
    finally:
        db.close()

    await redis.set(f"job:{job_id}:progress", 100)
    await redis.set(f"job:{job_id}:status", "done")
    await redis.set(f"job:{job_id}:paper_id", paper_id)

    return {"paper_id": paper_id}

class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
    functions = [ingest_paper, detect_gaps]
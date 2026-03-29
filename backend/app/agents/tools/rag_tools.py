import os
from google import genai
from sqlalchemy import text
from app.db import SessionLocal

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def _natural_rag_key(row) -> str:
    """Match graph dedupe: same logical paper may exist as multiple UUID rows."""
    raw = (getattr(row, "doi", None) or "").strip()
    if raw.lower().startswith("doi:"):
        raw = raw[4:].strip()
    doi = raw.lower() if raw else ""
    if doi:
        return f"doi:{doi}"
    sid = (getattr(row, "semantic_scholar_id", None) or "").strip()
    if sid:
        return f"ss:{sid}"
    return f"id:{row.paper_id}"


def embed_query(query):
    response = client.models.embed_content(
        model="gemini-embedding-2-preview",
        contents=[query],
    )
    return response.embeddings[0].values

def semantic_search(query_embedding, workspace_id, limit=8):
    db = SessionLocal()
    try:
        sql = text("""
            SELECT pe.paper_id, p.title, p.abstract, p.authors, p.year, p.venue,
                   p.doi, p.semantic_scholar_id,
                   1 - (pe.embedding <=> CAST(:embedding AS vector)) AS score
            FROM paper_embeddings pe
            JOIN workspace_papers wp ON wp.paper_id = pe.paper_id
            JOIN papers p ON p.id = pe.paper_id
            WHERE wp.workspace_id = CAST(:workspace_id AS uuid)
              AND pe.chunk_index = 0
            ORDER BY pe.embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
        """)
        rows = db.execute(sql, {
            "embedding": str(query_embedding),
            "workspace_id": workspace_id,
            "limit": limit * 8,
        }).fetchall()
        by_key: dict[str, dict] = {}
        for row in rows:
            key = _natural_rag_key(row)
            score = float(row.score)
            if key not in by_key or score > by_key[key]["score"]:
                by_key[key] = {
                    "paper_id": str(row.paper_id),
                    "title": row.title,
                    "abstract": row.abstract,
                    "authors": row.authors,
                    "year": row.year,
                    "venue": row.venue,
                    "score": score,
                }
        ranked = sorted(by_key.values(), key=lambda x: -x["score"])[:limit]
        return ranked
    finally:
        db.close()

def get_paper_details(paper_id):
    from app.models import Paper
    db = SessionLocal()
    try:
        paper = db.query(Paper).filter(Paper.id == paper_id).first()
        if not paper:
            return None
        return {
            "id": str(paper.id),
            "title": paper.title,
            "abstract": paper.abstract,
            "authors": paper.authors,
            "year": paper.year,
            "venue": paper.venue,
            "citation_count": paper.citation_count,
        }
    finally:
        db.close()

def _format_conversation_history(
    history: list[dict] | None,
    *,
    max_turns: int = 12,
    max_answer_chars: int = 1500,
) -> str:
    if not history:
        return ""
    blocks = []
    for turn in history[-max_turns:]:
        q = (turn.get("query") or "").strip()
        a = (turn.get("answer") or "").strip()
        if not q:
            continue
        if len(a) > max_answer_chars:
            a = a[: max_answer_chars - 1].rstrip() + "…"
        blocks.append(f"User: {q}\nAssistant: {a}")
    if not blocks:
        return ""
    return (
        "Earlier in this conversation (for follow-ups like 'elaborate', 'which paper', 'compare'):\n"
        + "\n\n---\n\n".join(blocks)
        + "\n\n"
    )


def answer_rag_query(query, workspace_id, history: list[dict] | None = None):
    import time

    history = history or []

    t0 = time.perf_counter()
    query_embedding = embed_query(query)
    chunks = semantic_search(query_embedding, workspace_id)
    vector_ms = (time.perf_counter() - t0) * 1000

    if not chunks:
        return {"answer": "No relevant papers found in your workspace.", "sources": [], "vector_search_ms": vector_ms}

    def _chunk_line(c):
        meta = f"{c['title']} ({c['year']})"
        if c.get("venue"):
            meta += f"; venue: {c['venue']}"
        return f"[{meta}]:\n{c['abstract'] or '(no abstract in index)'}"

    context = "\n\n".join(_chunk_line(c) for c in chunks)
    history_block = _format_conversation_history(history)

    prompt = f"""You are a research assistant. Ground every factual claim in the “Papers” section below.
Use venue/journal lines when the question asks where something was published.
Cite papers by title in brackets like [Paper Title].
If the answer is not in the papers, say so explicitly.

The user may refer to the prior dialogue for pronouns or follow-ups; still verify claims against the papers.

{history_block}Papers:
{context}

Current question: {query}"""

    t1 = time.perf_counter()
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    llm_ms = (time.perf_counter() - t1) * 1000

    text_out = (response.text or "").strip() or "(No text returned from the model.)"

    return {
        "answer": text_out,
        "sources": [{"paper_id": c["paper_id"], "title": c["title"], "score": c["score"]} for c in chunks],
        "vector_search_ms": round(vector_ms, 1),
        "llm_ms": round(llm_ms, 1),
    }

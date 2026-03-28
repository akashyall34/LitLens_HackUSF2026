import os
from google import genai
from sqlalchemy import text
from app.db import SessionLocal

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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
            SELECT pe.paper_id, p.title, p.abstract, p.authors, p.year,
                   1 - (pe.embedding <=> CAST(:embedding AS vector)) AS score
            FROM paper_embeddings pe
            JOIN workspace_papers wp ON wp.paper_id = pe.paper_id
            JOIN papers p ON p.id = pe.paper_id
            WHERE wp.workspace_id = CAST(:workspace_id AS uuid)
            ORDER BY pe.embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
        """)
        rows = db.execute(sql, {
            "embedding": str(query_embedding),
            "workspace_id": workspace_id,
            "limit": limit,
        }).fetchall()
        return [
            {
                "paper_id": str(row.paper_id),
                "title": row.title,
                "abstract": row.abstract,
                "authors": row.authors,
                "year": row.year,
                "score": float(row.score),
            }
            for row in rows
        ]
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

def answer_rag_query(query, workspace_id):
    import time

    t0 = time.perf_counter()
    query_embedding = embed_query(query)
    chunks = semantic_search(query_embedding, workspace_id)
    vector_ms = (time.perf_counter() - t0) * 1000

    if not chunks:
        return {"answer": "No relevant papers found in your workspace.", "sources": [], "vector_search_ms": vector_ms}

    context = "\n\n".join(
        f"[{c['title']} ({c['year']})]:\n{c['abstract'] or ''}"
        for c in chunks
    )

    prompt = f"""You are a research assistant. Answer the question below using ONLY the papers provided.
Cite papers by title in brackets like [Paper Title].
If the answer is not in the papers, say so explicitly.

Papers:
{context}

Question: {query}"""

    t1 = time.perf_counter()
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    llm_ms = (time.perf_counter() - t1) * 1000

    return {
        "answer": response.text,
        "sources": [{"paper_id": c["paper_id"], "title": c["title"], "score": c["score"]} for c in chunks],
        "vector_search_ms": round(vector_ms, 1),
        "llm_ms": round(llm_ms, 1),
    }

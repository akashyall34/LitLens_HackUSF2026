from sqlalchemy.orm import Session
from sqlalchemy import text


def detect_citation_gaps(workspace_id: str, db: Session) -> list[dict]:
    """
    Layer 1 citation gap detection (US 3.6).

    Finds papers cited by >= 2 workspace papers that are NOT in the workspace.
    Returns a list sorted by citation frequency descending.
    """
    # 1. Get all paper IDs currently in this workspace
    rows = db.execute(
        text("SELECT paper_id::text FROM workspace_papers WHERE workspace_id = :wid"),
        {"wid": workspace_id},
    ).fetchall()

    workspace_paper_ids = [r[0] for r in rows]
    if not workspace_paper_ids:
        return []

    # 2. Find cited papers NOT in the workspace, count how many workspace
    #    papers cite each one — only keep those cited by >= 2
    cited_rows = db.execute(
        text("""
            SELECT
                cited_paper_id::text          AS gap_id,
                COUNT(*)                       AS freq,
                array_agg(citing_paper_id::text) AS cited_by_ids
            FROM citations
            WHERE citing_paper_id::text  =  ANY(:ws_ids)
              AND cited_paper_id::text   != ALL(:ws_ids)
            GROUP BY cited_paper_id
            HAVING COUNT(*) >= 2
            ORDER BY freq DESC
        """),
        {"ws_ids": workspace_paper_ids},
    ).fetchall()

    if not cited_rows:
        return []

    gap_paper_ids = [r[0] for r in cited_rows]
    freq_map = {r[0]: (int(r[1]), list(r[2])) for r in cited_rows}

    # 3. Fetch metadata for gap papers
    paper_rows = db.execute(
        text("""
            SELECT id::text, title, authors, year, citation_count,
                   source_url, semantic_scholar_id
            FROM papers
            WHERE id::text = ANY(:gap_ids)
        """),
        {"gap_ids": gap_paper_ids},
    ).fetchall()

    # 4. Get titles of citing workspace papers (shown on the gap card)
    title_rows = db.execute(
        text("SELECT id::text, title FROM papers WHERE id::text = ANY(:ids)"),
        {"ids": workspace_paper_ids},
    ).fetchall()
    citing_titles = {r[0]: r[1] for r in title_rows}

    # 5. Build the result list
    gaps = []
    for row in paper_rows:
        pid = row[0]
        freq, citing_ids = freq_map[pid]

        # Build an ingestable URL for the "Add to workspace" button (US 3.8)
        semantic_id = row[6]
        ingest_url = row[5] or (
            f"https://www.semanticscholar.org/paper/{semantic_id}"
            if semantic_id else None
        )

        gaps.append({
            "paper": {
                "id": pid,
                "title": row[1],
                "authors": row[2] or [],
                "year": row[3],
                "citation_count": row[4] or 0,
                "url": ingest_url,   # frontend passes this to POST /ingest/url
                "semantic_id": semantic_id,
            },
            "cited_by_count": freq,
            "cited_by_papers": [citing_titles.get(cid, "Unknown") for cid in citing_ids[:5]],
            "why_matters": None,     # filled by E1's GapDetectionAgent
        })

    return sorted(gaps, key=lambda x: x["cited_by_count"], reverse=True)
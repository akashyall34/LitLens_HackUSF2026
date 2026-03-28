import os
from typing import Optional
import uuid as uuid_lib

import numpy as np
from fastapi import APIRouter, Depends, Query
from sklearn.cluster import KMeans
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import SessionLocal


router = APIRouter(prefix="/graph", tags=["graph"])

# 8 visually distinct colors — one per cluster (cycles if k > 8)
CLUSTER_COLORS = [
    "#4ECDC4",  # teal
    "#FF6B6B",  # red
    "#A78BFA",  # purple
    "#F59E0B",  # amber
    "#34D399",  # green
    "#F472B6",  # pink
    "#60A5FA",  # blue
    "#FB923C",  # orange
]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/{workspace_id}")
def get_graph(
    workspace_id: str,
    year_min: Optional[int] = Query(None, description="Min publication year"),
    year_max: Optional[int] = Query(None, description="Max publication year"),
    cluster_ids: Optional[str] = Query(None, description="Comma-separated cluster IDs to show"),
    db: Session = Depends(get_db),
):
    """
    Return the full graph payload for a workspace.
    US 2.8 — nodes/edges/clusters shape.
    US 2.9 — cluster colors computed by k-means on embeddings.
    US 2.10 — optional year_min, year_max, cluster_ids filters.
    """
    try:
        uuid_lib.UUID(workspace_id)
    except ValueError:
        return {"nodes": [], "edges": [], "clusters": []}

    # ── 1. Fetch workspace papers + their embeddings ───────────────────────
    rows = db.execute(
        text("""
            SELECT
                p.id::text        AS id,
                p.title,
                p.authors,
                p.year,
                p.citation_count,
                pe.embedding      AS embedding
            FROM papers p
            JOIN workspace_papers wp ON wp.paper_id = p.id
            LEFT JOIN paper_embeddings pe ON pe.paper_id = p.id
            WHERE wp.workspace_id = :workspace_id
        """),
        {"workspace_id": workspace_id},
    ).fetchall()

    if not rows:
        return {"nodes": [], "edges": [], "clusters": []}

    papers = [dict(row._mapping) for row in rows]

    # ── 2. Apply year filters (US 2.10) ───────────────────────────────────
    if year_min is not None:
        papers = [p for p in papers if p["year"] and p["year"] >= year_min]
    if year_max is not None:
        papers = [p for p in papers if p["year"] and p["year"] <= year_max]

    if not papers:
        return {"nodes": [], "edges": [], "clusters": []}

    # ── 3. K-means cluster assignment (US 2.9) ────────────────────────────
    papers_with_embedding = [p for p in papers if p["embedding"] is not None]
    cluster_assignments: dict[str, int] = {}

    if len(papers_with_embedding) >= 2:
        k = min(8, len(papers_with_embedding))
        matrix = np.array([p["embedding"] for p in papers_with_embedding])
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(matrix)

        for paper, label in zip(papers_with_embedding, labels):
            cluster_assignments[paper["id"]] = int(label)
    else:
        # Not enough papers to cluster — assign everyone to cluster 0
        for paper in papers_with_embedding:
            cluster_assignments[paper["id"]] = 0

    # Papers without embeddings yet get cluster 0
    for paper in papers:
        cluster_assignments.setdefault(paper["id"], 0)

    # ── 4. Apply cluster filter (US 2.10) ─────────────────────────────────
    if cluster_ids:
        allowed = {int(c) for c in cluster_ids.split(",") if c.strip().isdigit()}
        papers = [p for p in papers if cluster_assignments[p["id"]] in allowed]

    if not papers:
        return {"nodes": [], "edges": [], "clusters": []}

    paper_id_set = [p["id"] for p in papers]

    # ── 5. Build nodes list ───────────────────────────────────────────────
    nodes = []
    for paper in papers:
        pid = paper["id"]
        cid = cluster_assignments[pid]
        nodes.append(
            {
                "id": pid,
                "title": paper["title"],
                "authors": paper["authors"] or [],
                "year": paper["year"],
                "cluster_id": cid,
                "cluster_color": CLUSTER_COLORS[cid % len(CLUSTER_COLORS)],
                "citation_count": paper["citation_count"] or 0,
                "is_blind_spot": False,
            }
        )

    # ── 6. Fetch citation edges ───────────────────────────────────────────
    edge_rows = db.execute(
        text("""
            SELECT
                citing_paper_id::text  AS source,
                cited_paper_id::text   AS target,
                edge_type,
                confidence
            FROM citations
            WHERE citing_paper_id::text = ANY(:ids)
              AND cited_paper_id::text  = ANY(:ids)
        """),
        {"ids": paper_id_set},
    ).fetchall()

    edges = [
        {
            "source": row.source,
            "target": row.target,
            "edge_type": row.edge_type or "cites",
            "confidence": float(row.confidence) if row.confidence else 1.0,
        }
        for row in edge_rows
    ]

    # ── 7. Build clusters summary ─────────────────────────────────────────
    cluster_counts: dict[int, int] = {}
    for node in nodes:
        cid = node["cluster_id"]
        cluster_counts[cid] = cluster_counts.get(cid, 0) + 1

    # ── US 4.7: Read cluster labels written by E1's GapDetectionAgent ─────
    label_rows = db.execute(
        text("""
            SELECT DISTINCT cluster_label
            FROM blind_spots
            WHERE workspace_id = :wid
              AND cluster_label IS NOT NULL
              AND gap_type = 'semantic_gap'
            ORDER BY cluster_label
        """),
        {"wid": workspace_id},
    ).fetchall()
    cluster_labels = [r[0] for r in label_rows]

    clusters = [
        {
            "id": cid,
            "label": cluster_labels[i] if i < len(cluster_labels) else None,
            "color": CLUSTER_COLORS[cid % len(CLUSTER_COLORS)],
            "size": count,
        }
        for i, (cid, count) in enumerate(sorted(cluster_counts.items()))
    ]

    return {"nodes": nodes, "edges": edges, "clusters": clusters}
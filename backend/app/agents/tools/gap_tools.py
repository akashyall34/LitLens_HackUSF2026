import json
import logging
import os
import re
import uuid as uuid_lib

import numpy as np
from google import genai
from hdbscan import HDBSCAN
from sklearn.metrics.pairwise import cosine_similarity

from app.models import BlindSpot, Citation, Paper, PaperEmbedding, WorkspacePaper

logger = logging.getLogger(__name__)

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def _workspace_uuid(workspace_id):
    return workspace_id if isinstance(workspace_id, uuid_lib.UUID) else uuid_lib.UUID(str(workspace_id))


def _vec_to_numpy(raw) -> np.ndarray:
    if raw is None:
        raise ValueError("missing embedding")
    if isinstance(raw, str):
        raw = json.loads(raw)
    if hasattr(raw, "tolist"):
        raw = raw.tolist()
    arr = np.asarray(raw, dtype=np.float64)
    if arr.ndim != 1:
        arr = arr.flatten()
    return arr


def get_workspace_papers(workspace_id, db):
    wid = _workspace_uuid(workspace_id)
    rows = db.query(WorkspacePaper).filter(WorkspacePaper.workspace_id == wid).all()
    return [str(row.paper_id) for row in rows]


def get_workspace_embeddings(workspace_id, db):
    paper_ids = get_workspace_papers(workspace_id, db)
    if not paper_ids:
        return np.empty((0, 0))
    rows = (
        db.query(PaperEmbedding)
        .filter(
            PaperEmbedding.paper_id.in_(paper_ids),
            PaperEmbedding.chunk_index == 0,
        )
        .all()
    )
    vecs = []
    for row in rows:
        try:
            vecs.append(_vec_to_numpy(row.embedding))
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning("skip bad workspace embedding paper_id=%s: %s", row.paper_id, e)
    if not vecs:
        return np.empty((0, 0))
    return np.stack(vecs, axis=0)


def get_citation_gap_papers(workspace_id, db):
    workspace_ids = get_workspace_papers(workspace_id, db)
    if not workspace_ids:
        return []
    cited_rows = (
        db.query(Citation.cited_paper_id)
        .filter(Citation.citing_paper_id.in_(workspace_ids))
        .all()
    )
    cited_ids = {str(row[0]) for row in cited_rows}
    gap_ids = cited_ids - set(workspace_ids)
    if not gap_ids:
        return []
    return db.query(Paper).filter(Paper.id.in_(list(gap_ids))).all()


def get_candidate_embeddings(papers, db):
    paper_ids = [str(p.id) for p in papers]
    rows = (
        db.query(PaperEmbedding)
        .filter(
            PaperEmbedding.paper_id.in_(paper_ids),
            PaperEmbedding.chunk_index == 0,
        )
        .all()
    )
    embedding_map = {str(row.paper_id): row.embedding for row in rows}
    embeddings = []
    filtered_papers = []
    for p in papers:
        pid = str(p.id)
        if pid not in embedding_map:
            continue
        try:
            vec = _vec_to_numpy(embedding_map[pid])
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning("skip bad gap embedding paper_id=%s: %s", pid, e)
            continue
        embeddings.append(vec)
        filtered_papers.append(p)
    if not embeddings:
        return [], np.empty((0, 0))
    return filtered_papers, np.stack(embeddings, axis=0)


def run_hdbscan_clustering(embeddings: np.ndarray):
    clusterer = HDBSCAN(min_cluster_size=3, metric="euclidean")
    labels = clusterer.fit_predict(embeddings)
    return labels


def compute_cluster_coverage(labels, candidate_embeddings, workspace_embeddings):
    coverage = {}
    if workspace_embeddings.size == 0 or workspace_embeddings.shape[0] == 0:
        return coverage
    for cluster_id in set(labels):
        if cluster_id == -1:
            continue
        cluster_vecs = candidate_embeddings[labels == cluster_id]
        centroid = np.mean(cluster_vecs, axis=0).reshape(1, -1)
        sims = cosine_similarity(centroid, workspace_embeddings)
        coverage[cluster_id] = float(sims.max())
    return coverage


def _parse_llm_json_array(text: str) -> list:
    t = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", t)
    if fence:
        t = fence.group(1).strip()
    start = t.find("[")
    end = t.rfind("]")
    if start >= 0 and end > start:
        t = t[start : end + 1]
    return json.loads(t)


def label_all_clusters(clusters, workspace_titles):
    cluster_summaries = "\n".join(
        f'Cluster {c["id"]}: {", ".join(p.title for p in c["papers"][:5])}'
        for c in clusters
    )
    titles_preview = ", ".join((workspace_titles or ["(none)"])[:5])
    prompt = f"""A researcher has read these papers: {titles_preview}

These are topic clusters of papers they haven't read:
{cluster_summaries}

For EACH cluster return:
- label: a 2-4 word topic label (e.g. "Mechanistic Interpretability")
- why_matters: one sentence explaining why this gap matters given the researcher's papers

Return a JSON array: [{{"cluster_id": 0, "label": "...", "why_matters": "..."}}, ...]
Return only the JSON array, nothing else."""
    response = _client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    raw = response.text or "[]"
    try:
        return _parse_llm_json_array(raw)
    except (json.JSONDecodeError, ValueError):
        logger.exception("label_all_clusters: bad JSON from model: %s", raw[:500])
        return [
            {"cluster_id": c["id"], "label": "Unlabeled cluster", "why_matters": "Could not parse model output."}
            for c in clusters
        ]


def store_blind_spots(workspace_id, semantic_gaps, db):
    wid = _workspace_uuid(workspace_id)
    db.query(BlindSpot).filter(
        BlindSpot.workspace_id == wid,
        BlindSpot.gap_type == "semantic_gap",
    ).delete(synchronize_session=False)
    for gap in semantic_gaps:
        db.add(
            BlindSpot(
                workspace_id=wid,
                gap_type="semantic_gap",
                cluster_label=gap["label"],
                coverage_score=gap["coverage_score"],
                why_matters=gap["why_matters"],
                payload={"top_papers": [str(p.id) for p in gap["top_papers"]]},
            )
        )
    db.commit()


def detect_semantic_gaps(workspace_id, db):
    workspace_embeddings = get_workspace_embeddings(workspace_id, db)
    if workspace_embeddings.size == 0 or workspace_embeddings.shape[0] == 0:
        logger.info("detect_semantic_gaps: no workspace embeddings for %s", workspace_id)
        return []

    gap_papers = get_citation_gap_papers(workspace_id, db)
    if not gap_papers:
        logger.info("detect_semantic_gaps: no citation-gap papers for %s", workspace_id)
        return []

    gap_papers, candidate_embeddings = get_candidate_embeddings(gap_papers, db)
    if len(gap_papers) < 3:
        logger.info(
            "detect_semantic_gaps: need >=3 gap papers with embeddings, have %s",
            len(gap_papers),
        )
        return []

    labels = run_hdbscan_clustering(candidate_embeddings)
    coverage = compute_cluster_coverage(labels, candidate_embeddings, workspace_embeddings)

    workspace_paper_ids = get_workspace_papers(workspace_id, db)
    workspace_titles = [
        p.title
        for p in db.query(Paper).filter(Paper.id.in_(workspace_paper_ids)).all()
    ]

    clusters = []
    for cluster_id, cov_score in coverage.items():
        if cov_score < 0.65:
            cluster_papers = [
                gap_papers[i] for i, label in enumerate(labels) if label == cluster_id
            ]
            clusters.append({
                "id": cluster_id,
                "papers": cluster_papers,
                "coverage_score": cov_score,
            })

    if not clusters:
        return []

    labeled = label_all_clusters(clusters, workspace_titles)
    label_map = {}
    for item in labeled:
        cid = item.get("cluster_id")
        if cid is not None:
            try:
                label_map[int(cid)] = item
            except (TypeError, ValueError):
                continue

    semantic_gaps = []
    for c in clusters:
        info = label_map.get(c["id"], {})
        semantic_gaps.append({
            "label": info.get("label", "Unknown"),
            "coverage_score": c["coverage_score"],
            "why_matters": info.get("why_matters", ""),
            "top_papers": c["papers"][:5],
        })

    store_blind_spots(workspace_id, semantic_gaps, db)
    return semantic_gaps

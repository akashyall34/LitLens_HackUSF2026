import json
import os
import numpy as np
from hdbscan import HDBSCAN
from sklearn.metrics.pairwise import cosine_similarity
from google import genai

from app.models import Paper, PaperEmbedding, WorkspacePaper, BlindSpot, Citation

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def get_workspace_papers(workspace_id, db):
    rows = db.query(WorkspacePaper).filter(
        WorkspacePaper.workspace_id == workspace_id
    ).all()
    return [str(row.paper_id) for row in rows]


def get_workspace_embeddings(workspace_id, db):
    paper_ids = get_workspace_papers(workspace_id, db)
    rows = db.query(PaperEmbedding).filter(
        PaperEmbedding.paper_id.in_(paper_ids)
    ).all()
    return np.array([row.embedding for row in rows])


def get_citation_gap_papers(workspace_id, db):
    workspace_ids = get_workspace_papers(workspace_id, db)
    cited_ids = db.query(Citation.cited_paper_id).filter(
        Citation.citing_paper_id.in_(workspace_ids)
    ).all()
    cited_ids = {str(row[0]) for row in cited_ids}
    gap_ids = cited_ids - set(workspace_ids)
    papers = db.query(Paper).filter(Paper.id.in_(gap_ids)).all()
    return papers


def get_candidate_embeddings(papers, db):
    paper_ids = [str(p.id) for p in papers]
    rows = db.query(PaperEmbedding).filter(
        PaperEmbedding.paper_id.in_(paper_ids)
    ).all()
    embedding_map = {str(row.paper_id): row.embedding for row in rows}
    embeddings = []
    filtered_papers = []
    for p in papers:
        if str(p.id) in embedding_map:
            embeddings.append(embedding_map[str(p.id)])
            filtered_papers.append(p)
    return filtered_papers, np.array(embeddings)


def run_hdbscan_clustering(embeddings):
    clusterer = HDBSCAN(min_cluster_size=3, metric='euclidean')
    labels = clusterer.fit_predict(embeddings)
    return labels


def compute_cluster_coverage(labels, candidate_embeddings, workspace_embeddings):
    coverage = {}
    for cluster_id in set(labels):
        if cluster_id == -1:
            continue
        cluster_vecs = candidate_embeddings[labels == cluster_id]
        centroid = np.mean(cluster_vecs, axis=0).reshape(1, -1)
        sims = cosine_similarity(centroid, workspace_embeddings)
        coverage[cluster_id] = float(sims.max())
    return coverage


def label_all_clusters(clusters, workspace_titles):
    cluster_summaries = "\n".join(
        f'Cluster {c["id"]}: {", ".join(p.title for p in c["papers"][:5])}'
        for c in clusters
    )
    prompt = f"""A researcher has read these papers: {", ".join(workspace_titles[:5])}

These are topic clusters of papers they haven't read:
{cluster_summaries}

For EACH cluster return:
- label: a 2-4 word topic label (e.g. "Mechanistic Interpretability")
- why_matters: one sentence explaining why this gap matters given the researcher's papers

Return a JSON array: [{{"cluster_id": 0, "label": "...", "why_matters": "..."}}, ...]
Return only the JSON array, nothing else."""
    response = _client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return json.loads(response.text)


def store_blind_spots(workspace_id, semantic_gaps, db):
    for gap in semantic_gaps:
        blind_spot = BlindSpot(
            workspace_id=workspace_id,
            gap_type="semantic_gap",
            cluster_label=gap["label"],
            coverage_score=gap["coverage_score"],
            why_matters=gap["why_matters"],
            payload={"top_papers": [str(p.id) for p in gap["top_papers"]]},
        )
        db.add(blind_spot)
    db.commit()


def detect_semantic_gaps(workspace_id, db):
    workspace_embeddings = get_workspace_embeddings(workspace_id, db)
    gap_papers = get_citation_gap_papers(workspace_id, db)

    if not gap_papers:
        return []

    gap_papers, candidate_embeddings = get_candidate_embeddings(gap_papers, db)

    if len(gap_papers) < 3:
        return []

    labels = run_hdbscan_clustering(candidate_embeddings)
    coverage = compute_cluster_coverage(labels, candidate_embeddings, workspace_embeddings)

    workspace_paper_ids = get_workspace_papers(workspace_id, db)
    workspace_titles = [
        p.title for p in db.query(Paper).filter(Paper.id.in_(workspace_paper_ids)).all()
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
    label_map = {item["cluster_id"]: item for item in labeled}

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

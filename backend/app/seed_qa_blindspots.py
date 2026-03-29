"""
Demo data for the QA account so blind spots work without manual ingest.

Idempotent: safe on every login. Only runs for QA_ACCOUNT_EMAIL.
"""

import json
import logging
import os

import numpy as np
from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.demo_workspace import DEMO_WORKSPACE_ID

logger = logging.getLogger(__name__)

QA_ACCOUNT_EMAIL = "qatest2@test.com"

# Fixed UUIDs so re-seeding never duplicates logical rows.
QA_PAPER_IN_WS_A = "b1000001-0001-4001-8001-000000000001"
QA_PAPER_IN_WS_B = "b1000002-0002-4002-8002-000000000002"
QA_PAPER_GAP = "c2000001-0001-4001-8001-000000000099"

# Real S2 + DOI so “Add to workspace” / ingest URLs resolve (legacy seeds used fake ids).
_GAP_DOI = "10.48550/arXiv.1706.03762"
_GAP_S2 = "204e3073870fae3d05bcbc2f6a8e263d9b72e776"
_GAP_URL = f"https://www.semanticscholar.org/paper/{_GAP_S2}"

# Must match `PaperEmbedding` / Gemini embedding size used in ingest.
_EMB_DIM = 3072


def _embedding_axis(axis: int) -> str:
    v = np.zeros(_EMB_DIM, dtype=np.float64)
    if axis == 1:
        v[0] = 0.9
        v[1] = 0.1
    else:
        v[min(axis, _EMB_DIM - 1)] = 1.0
    n = np.linalg.norm(v)
    if n > 0:
        v /= n
    return "[" + ",".join(f"{float(x):.8f}" for x in v.tolist()) + "]"


def _semantic_cache_payload() -> str:
    gaps = [
        {
            "label": "Optimization & generalization theory",
            "coverage_score": 0.38,
            "why_matters": "Your workspace leans applied; several cited classics in this cluster rarely surface in standups. Closing this gap reduces duplicate literature review and missed baselines.",
            "top_papers": [
                {
                    "id": QA_PAPER_GAP,
                    "title": "Attention Is All You Need",
                },
            ],
        },
        {
            "label": "Evaluation methodology",
            "coverage_score": 0.55,
            "why_matters": "Papers in this theme shape how benchmarks are interpreted. The team cites overlapping work here but has not consolidated implications for your current milestones.",
            "top_papers": [
                {
                    "id": QA_PAPER_GAP,
                    "title": "Attention Is All You Need",
                },
            ],
        },
    ]
    return json.dumps(gaps)


def seed_qa_blindspots_data(db: Session, user_id: str) -> None:
    """Insert papers, workspace links, and shared citation gap. Does not commit."""
    wid = DEMO_WORKSPACE_ID
    authors_a = json.dumps(["M. Kapoor", "L. Chen"])
    authors_b = json.dumps(["J. Okonkwo"])
    authors_gap = json.dumps(
        [
            "A. Vaswani",
            "N. Shazeer",
            "N. Parmar",
            "J. Uszkoreit",
            "L. Jones",
            "A. N. Gomez",
            "Ł. Kaiser",
            "I. Polosukhin",
        ]
    )

    for pid, title, abstract, year, doi, sid, authors_json in (
        (
            QA_PAPER_IN_WS_A,
            "Efficient On-Device Federated Updates for Ranking Models",
            "We study communication-efficient federated rounds for production ranking systems.",
            2024,
            "10.9999/litlens.qa.fedrank",
            "litlens-qa-fedrank",
            authors_a,
        ),
        (
            QA_PAPER_IN_WS_B,
            "Privacy Accounting Under Continual Model Deployment",
            "Budget tracking for DP-SGD when models ship weekly with new data slices.",
            2023,
            "10.9999/litlens.qa.dpdeploy",
            "litlens-qa-dpdeploy",
            authors_b,
        ),
        (
            QA_PAPER_GAP,
            "Attention Is All You Need",
            "The dominant sequence transduction models are encoder-decoder RNNs; we propose the Transformer.",
            2017,
            _GAP_DOI,
            _GAP_S2,
            authors_gap,
        ),
    ):
        db.execute(
            text("""
                INSERT INTO papers (
                    id, title, abstract, year, doi, semantic_scholar_id,
                    source_url, citation_count, venue, authors, created_at
                )
                VALUES (
                    CAST(:id AS UUID), :title, :abstract, :year, :doi, :sid,
                    :url, :cc, :venue, CAST(:authors AS JSONB), NOW()
                )
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": pid,
                "title": title,
                "abstract": abstract,
                "year": year,
                "doi": doi,
                "sid": sid,
                "url": _GAP_URL if pid == QA_PAPER_GAP else f"https://www.semanticscholar.org/paper/{sid}",
                "cc": 1200,
                "venue": "LitLens QA seed",
                "authors": authors_json,
            },
        )

    # Overwrite legacy gap rows (fake S2 ids) so ingest URLs always resolve.
    db.execute(
        text("""
            UPDATE papers SET
                title = :title,
                abstract = :abstract,
                year = :year,
                doi = :doi,
                semantic_scholar_id = :sid,
                source_url = :url,
                citation_count = :cc,
                venue = :venue,
                authors = CAST(:authors AS JSONB)
            WHERE id = CAST(:id AS UUID)
        """),
        {
            "id": QA_PAPER_GAP,
            "title": "Attention Is All You Need",
            "abstract": (
                "The dominant sequence transduction models are encoder-decoder RNNs; "
                "we propose the Transformer."
            ),
            "year": 2017,
            "doi": _GAP_DOI,
            "sid": _GAP_S2,
            "url": _GAP_URL,
            "cc": 120000,
            "venue": "LitLens QA seed",
            "authors": authors_gap,
        },
    )

    # Two workspace papers cite the same external (gap) paper.
    for src, dst in (
        (QA_PAPER_IN_WS_A, QA_PAPER_GAP),
        (QA_PAPER_IN_WS_B, QA_PAPER_GAP),
    ):
        db.execute(
            text("""
                INSERT INTO citations (
                    citing_paper_id, cited_paper_id, edge_type, confidence, created_at
                )
                VALUES (
                    CAST(:src AS UUID), CAST(:dst AS UUID), 'cites', 1.0, NOW()
                )
                ON CONFLICT (citing_paper_id, cited_paper_id) DO NOTHING
            """),
            {"src": src, "dst": dst},
        )

    for pid in (QA_PAPER_IN_WS_A, QA_PAPER_IN_WS_B):
        db.execute(
            text("""
                INSERT INTO workspace_papers (workspace_id, paper_id, added_by, added_at)
                VALUES (
                    CAST(:wid AS UUID), CAST(:pid AS UUID), CAST(:uid AS UUID), NOW()
                )
                ON CONFLICT (workspace_id, paper_id) DO NOTHING
            """),
            {"wid": wid, "pid": pid, "uid": user_id},
        )

    # Orthogonal-ish vectors so conceptual scan finds a low-coverage gap cluster (dim must match DB).
    for pid, axis in (
        (QA_PAPER_IN_WS_A, 0),
        (QA_PAPER_IN_WS_B, 1),
        (QA_PAPER_GAP, 200),
    ):
        emb_lit = _embedding_axis(axis)
        try:
            db.execute(
                text("""
                    INSERT INTO paper_embeddings (paper_id, chunk_index, embedding, created_at)
                    VALUES (CAST(:pid AS UUID), 0, CAST(:emb AS vector), NOW())
                    ON CONFLICT (paper_id, chunk_index) DO NOTHING
                """),
                {"pid": pid, "emb": emb_lit},
            )
        except Exception as ex:
            logger.warning(
                "QA seed: could not insert embedding for %s (vector dim may not match DB): %s",
                pid,
                ex,
            )


def touch_qa_blindspots_redis() -> None:
    """Drop citation cache (rebuilt from DB) and set semantic gaps for the panel."""
    url = os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        r = Redis.from_url(url, decode_responses=True)
        wid = DEMO_WORKSPACE_ID
        r.delete(f"gaps:{wid}:citation")
        r.setex(f"gaps:{wid}:semantic", 86400, _semantic_cache_payload())
    except Exception:
        logger.exception("touch_qa_blindspots_redis failed (non-fatal)")


def should_seed_qa_blindspots(email: str | None) -> bool:
    return bool(email and email.lower().strip() == QA_ACCOUNT_EMAIL)

"""
Demo data for the QA account so blind spots work without manual ingest.

Idempotent: safe on every login. Only runs for QA_ACCOUNT_EMAIL.
"""

import json
import logging
import os

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


def _semantic_cache_payload() -> str:
    gaps = [
        {
            "label": "Optimization & generalization theory",
            "coverage_score": 0.38,
            "why_matters": "Your workspace leans applied; several cited classics in this cluster rarely surface in standups. Closing this gap reduces duplicate literature review and missed baselines.",
            "top_papers": [
                {
                    "id": QA_PAPER_GAP,
                    "title": "Foundational convergence analysis for large-scale stochastic optimization (demo reference)",
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
                    "title": "Foundational convergence analysis for large-scale stochastic optimization (demo reference)",
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
    authors_gap = json.dumps(["R. Vaswani", "S. Müller", "T. Ng"])

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
            "Foundational convergence analysis for large-scale stochastic optimization (demo reference)",
            "Surveys assumptions under which SGD-family methods converge and how they map to practice.",
            2018,
            "10.9999/litlens.qa.sgdclassic",
            "litlens-qa-sgdclassic",
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
                "url": f"https://www.semanticscholar.org/paper/{sid}",
                "cc": 1200,
                "venue": "LitLens QA seed",
                "authors": authors_json,
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

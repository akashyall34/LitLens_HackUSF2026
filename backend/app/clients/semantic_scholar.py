import os
from typing import Any

import httpx


SEMANTIC_SCHOLAR_PAPER_URL = "https://api.semanticscholar.org/graph/v1/paper"
SEMANTIC_SCHOLAR_FIELDS = (
    "paperId,title,abstract,authors,year,venue,citationCount,url,references.paperId"
)


def _normalize_identifier(paper_identifier: str) -> str:
    identifier = paper_identifier.strip()

    if "semanticscholar.org/paper/" in identifier:
        return identifier.rstrip("/").split("/")[-1]

    if identifier.lower().startswith("doi:"):
        return identifier

    if identifier.startswith("10."):
        return f"doi:{identifier}"

    return identifier


def fetch_semantic_scholar_metadata(paper_identifier: str) -> dict[str, Any]:
    """Fetch paper metadata from Semantic Scholar using URL, DOI, or paper ID."""
    resolved_identifier = _normalize_identifier(paper_identifier)
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")

    headers: dict[str, str] = {}
    if api_key:
        headers["X-API-KEY"] = api_key

    response = httpx.get(
        f"{SEMANTIC_SCHOLAR_PAPER_URL}/{resolved_identifier}",
        params={"fields": SEMANTIC_SCHOLAR_FIELDS},
        headers=headers,
        timeout=20.0,
    )
    response.raise_for_status()

    data = response.json()
    return {
        "title": data.get("title"),
        "abstract": data.get("abstract"),
        "authors": [author.get("name") for author in (data.get("authors") or [])],
        "year": data.get("year"),
        "semantic_id": data.get("paperId"),
        "citation_count": data.get("citationCount", 0),
        "venue": data.get("venue"),
        "url": data.get("url"),
        "references": [
            ref.get("paperId")
            for ref in (data.get("references") or [])
            if ref.get("paperId")
        ],
    }

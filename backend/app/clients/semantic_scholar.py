import os
from typing import Any

import httpx


SEMANTIC_SCHOLAR_PAPER_URL = "https://api.semanticscholar.org/graph/v1/paper"
SEMANTIC_SCHOLAR_FIELDS = (
    "paperId,title,abstract,authors,year,venue,citationCount,url,"
    "externalIds,references.paperId"
)
# Lighter follow-up calls (e.g. resolving reference IDs) — avoids nested reference fan-out.
SEMANTIC_SCHOLAR_FIELDS_BRIEF = (
    "paperId,title,abstract,authors,year,venue,citationCount,url,externalIds"
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


def _paper_dict_from_api(data: dict, *, parse_references: bool) -> dict[str, Any]:
    ext = data.get("externalIds") or {}
    doi_val = ext.get("DOI")
    if doi_val and not str(doi_val).lower().startswith("doi:"):
        doi_val = f"doi:{doi_val}"
    references: list[str] = []
    if parse_references:
        references = [
            ref.get("paperId")
            for ref in (data.get("references") or [])
            if ref.get("paperId")
        ]
    return {
        "title": data.get("title"),
        "abstract": data.get("abstract"),
        "authors": [author.get("name") for author in (data.get("authors") or [])],
        "year": data.get("year"),
        "doi": doi_val,
        "semantic_id": data.get("paperId"),
        "citation_count": data.get("citationCount", 0),
        "venue": data.get("venue"),
        "url": data.get("url"),
        "references": references,
    }


def _http_get_paper(resolved_identifier: str, fields: str) -> dict:
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    headers: dict[str, str] = {}
    if api_key:
        headers["X-API-KEY"] = api_key
    response = httpx.get(
        f"{SEMANTIC_SCHOLAR_PAPER_URL}/{resolved_identifier}",
        params={"fields": fields},
        headers=headers,
        timeout=20.0,
    )
    response.raise_for_status()
    return response.json()


def fetch_semantic_scholar_metadata(
    paper_identifier: str,
    *,
    include_references: bool = True,
) -> dict[str, Any]:
    """Fetch paper metadata from Semantic Scholar using URL, DOI, or paper ID."""
    resolved_identifier = _normalize_identifier(paper_identifier)
    fields = SEMANTIC_SCHOLAR_FIELDS if include_references else SEMANTIC_SCHOLAR_FIELDS_BRIEF
    data = _http_get_paper(resolved_identifier, fields)
    return _paper_dict_from_api(data, parse_references=include_references)

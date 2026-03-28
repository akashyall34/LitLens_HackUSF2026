from typing import Any

from app.clients.semantic_scholar import fetch_semantic_scholar_metadata


def fetch_paper_metadata(paper_identifier: str) -> dict[str, Any]:
    """Semantic Scholar-only paper lookup entrypoint.

    paper_identifier can be a Semantic Scholar paper URL, S2 paper ID, or DOI.
    """
    return fetch_semantic_scholar_metadata(paper_identifier)

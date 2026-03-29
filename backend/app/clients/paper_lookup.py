from typing import Any
import httpx
from app.clients.semantic_scholar import fetch_semantic_scholar_metadata
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
)
def fetch_paper_metadata(paper_identifier: str) -> dict[str, Any]:
    """Semantic Scholar-only paper lookup entrypoint.

    paper_identifier can be a Semantic Scholar paper URL, S2 paper ID, or DOI.
    """
    return fetch_semantic_scholar_metadata(paper_identifier)

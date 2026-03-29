import os
from google import genai
import httpx
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError, Exception)),
)

def embed_texts(texts):
    response = client.models.embed_content(model="gemini-embedding-2-preview", contents=texts)
    return [embedding.values for embedding in response.embeddings]
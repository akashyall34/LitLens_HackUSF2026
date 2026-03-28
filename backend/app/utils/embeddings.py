import os
from google import genai

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def embed_texts(texts):
    response = client.models.embed_content(model="gemini-embedding-2-preview", contents=texts,)
    return [embedding.values for embedding in response.embeddings]
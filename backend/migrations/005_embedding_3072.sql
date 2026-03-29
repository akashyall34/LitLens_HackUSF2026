-- Update embedding dimension from 768 to 3072 to match gemini-embedding-2-preview output
ALTER TABLE paper_embeddings
  ALTER COLUMN embedding TYPE vector(3072);

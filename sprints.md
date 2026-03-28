# LitLens — Agile Sprint Plan

**E1** = General engineer (frontend, core algorithms, RAG/AI layer)
**E2** = AWS engineer (infrastructure + backend API routes, cloud services, CI/CD)

*E2 owns all AWS work. Outside of AWS, remaining backend work is split evenly.*

---

## Resume Impact Summary

By the end of this roadmap your resume line reads:

*"Built LitLens — a production-grade literature blind spot detection platform on AWS (EC2 t2.micro, RDS + pgvector, ElastiCache, S3, SES) with a semantic knowledge graph (React Flow + Yjs CRDTs), citation gap analysis via Semantic Scholar API, HDBSCAN embedding clustering for conceptual gap detection (Gemini text-embedding-004), RAG queries grounded in user papers via Gemini 1.5 Flash (p95 <300ms vector search), and real-time collaborative annotation. Used by 30+ USF researchers."*

---

## Sprint 1 — Foundation

**The Goal:** All three systems (backend, database, frontend) are running locally and talking to each other before a single feature is built. No skipping this — a bad foundation costs 10x later.

**Resume Keywords Added:** FastAPI, PostgreSQL, pgvector, React, Vite, shadcn/ui, Tailwind CSS, Docker Compose, REST API design

---

> **Sprint Kickoff Order:** E2 commits `docker-compose.yml` (US 1.6) on day 1 before anything else. E1 cannot run migrations (US 1.2) until Postgres is up. Everything else is fully parallel after that.

---

### User Stories

**US 1.6 [E2] ⚡ Day 1 first:** As a developer, I have a local PostgreSQL instance with the `pgvector` extension enabled and all migrations applied via `docker-compose up` so E1 can develop against a real database immediately. *Unblocks: US 1.2*

**US 1.7 [E2] ⚡ Day 1 first:** As a developer, I have a local Redis instance running via Docker Compose so rate limiting and job queue code can be developed and tested locally.

**US 1.1 [E1]:** As a developer, I can run a FastAPI app with a `GET /health` endpoint returning `{"status": "ok"}` so the server is confirmed alive and the project structure is established.

**US 1.2 [E1] (after US 1.6):** As a developer, all database tables from the spec are created via SQL migrations (users, workspaces, workspace_members, papers, paper_embeddings, citations, workspace_papers, blind_spots, node_comments, edge_annotations) so the data layer is ready to use.

**US 1.3 [E1]:** As a developer, the React + Vite frontend is scaffolded with shadcn/ui, Tailwind CSS, Lucide React, and Framer Motion installed so the design system is in place from day one with zero CSS debt.

**US 1.4 [E1]:** As a developer, React Flow renders a hardcoded test graph with two custom node types — `PaperNode` (default) and `BlindSpotNode` (dashed red border) — so the graph shell exists and node styling is proven before real data arrives.

**US 1.5 [E1+E2]:** As a developer, the backend and frontend share a committed `.env.example` file listing every required variable (API URLs, DB connection strings, Redis URL, Gemini API key, Semantic Scholar key) so both engineers always know the full config surface. *Both engineers contribute their known variables before end of day 1.*

**US 1.8 [E2]:** As a developer, given an arXiv URL I can call a Python function that returns `{title, abstract, authors, year, arxiv_id}` from the arXiv API so paper metadata fetching is proven before ingestion is wired up.

**US 1.9 [E2]:** As a developer, given a `semantic_id` I can call a Python function that returns `{citation_count, venue, references[]}` from the Semantic Scholar API so citation graph fetching is proven before ingestion is wired up.

---

### Technical Execution Checklist

**Repository structure to establish:**
```
litlens/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app, mounts routers
│   │   ├── db.py            # SQLAlchemy session + engine
│   │   ├── models.py        # ORM models matching schema
│   │   ├── routers/         # one file per feature area
│   │   └── clients/
│   │       ├── arxiv.py     # arXiv API client [E2]
│   │       └── semantic_scholar.py  # Semantic Scholar client [E2]
│   ├── migrations/          # raw SQL migration files
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── graph/
│   │   │       ├── PaperNode.tsx
│   │   │       └── BlindSpotNode.tsx
│   │   └── App.tsx
│   └── package.json
├── docker-compose.yml       # postgres + redis
└── .env.example
```

**docker-compose.yml (E2 owns):**
```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: litlens
      POSTGRES_USER: litlens
      POSTGRES_PASSWORD: litlens
    ports: ["5432:5432"]
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
```

**pgvector migration (E1 owns):**
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE paper_embeddings (
  paper_id  UUID REFERENCES papers(id) PRIMARY KEY,
  embedding vector(768),
  chunk_index INT DEFAULT 0
);
CREATE INDEX ON paper_embeddings USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

**React Flow test graph (E1 owns):**
```tsx
const testNodes = [
  { id: '1', type: 'paperNode', position: { x: 0, y: 0 },
    data: { title: 'Attention Is All You Need', year: 2017, clusterColor: '#4ECDC4' } },
  { id: '2', type: 'blindSpotNode', position: { x: 200, y: 100 },
    data: { title: 'Missing Paper', year: 2020, clusterColor: '#FF6B6B' } },
]
```

**Semantic Scholar rate limiting (E2 owns):**
- Unauthenticated: 100 req / 5 min — register for a free API key to get 1 req/sec
- Add `X-API-KEY` header to all requests
- Implement a simple `asyncio.sleep(1)` between requests in the client

---

**Definition of Done:** `docker-compose up` starts Postgres + Redis. `uvicorn app.main:app` returns `{"status":"ok"}` at `/health`. All SQL migrations run without error. React dev server renders a graph with one yellow PaperNode and one red dashed BlindSpotNode. Both engineers can run the full stack locally using only `.env.example` as a reference.

---

## Sprint 2 — Core Ingestion Pipeline

**The Goal:** A user can paste arXiv links and see a real citation graph in the browser. This is the end-to-end spine of the entire product — every other feature is built on top of it.

**Resume Keywords Added:** Async job queues, Redis + arq, Gemini Embeddings API, pgvector, Semantic Scholar citation graph, React Flow, k-means clustering

---

> **Sprint Kickoff:** Both engineers agree on the Redis job key schema (see Shared Contracts below) before writing any code. E2 delivers US 2.6 and US 2.8 as early as possible — E1 develops against mock responses in parallel and swaps to real endpoints when ready. No waiting.

---

### User Stories

**US 2.6 [E2] ⚡ Early priority:** As a user, I can poll `GET /ingest/status/{job_id}` and receive `{status, progress, paper_id}` so the frontend can show a live progress indicator during ingestion. *Unblocks: E1 frontend polling logic*

**US 2.8 [E2] ⚡ Early priority:** As a user, `GET /graph/{workspace_id}` returns the full graph payload — `{nodes[], edges[], clusters[]}` — with cluster color assignments computed from k-means over paper embeddings. *Unblocks: US 2.4*

**US 2.9 [E2]:** As a developer, cluster coloring is computed by running k-means (scikit-learn, k=8) on paper embeddings and assigning a deterministic hex color per cluster ID so the graph is visually organized.

**US 2.10 [E2]:** As a user, I can filter the rendered graph by year range (slider) and topic cluster (toggle chips) so I can focus on relevant paper subsets.

**US 2.7 [E2]:** As a developer, I can submit ingestion jobs via DOI using `POST /ingest/doi` so papers without arXiv URLs can still be ingested.

**US 2.1 [E1]:** As a user, I can submit an arXiv URL via `POST /ingest/url` and receive a `job_id` immediately so the UI stays responsive while ingestion runs in the background.

**US 2.2 [E1]:** As a developer, the ingestion pipeline generates `text-embedding-004` embeddings for each paper's `"{title}. {abstract}"` string and stores the resulting `vector(768)` in `paper_embeddings` so vector search is possible.

**US 2.3 [E1]:** As a developer, the async job queue is implemented with Redis + `arq` so ingestion jobs run as background workers and never block the FastAPI request thread.

**US 2.4 [E1] (after US 2.8 or use mock):** As a user, I can see a real citation graph in the browser with cluster-colored nodes, a minimap, and zoom/pan controls after pasting arXiv links into the frontend.

**US 2.5 [E1]:** As a user, clicking a node opens a shadcn `Sheet` (PaperDetailPanel) from the right side of the screen, animated with Framer Motion, showing title, abstract, authors, year, citation count, and a link to the paper.

---

### Technical Execution Checklist

**arq job worker setup (E1 owns):**
```python
# backend/app/workers/ingest.py
async def ingest_paper(ctx, url: str, workspace_id: str):
    # 1. Fetch metadata from arXiv
    paper = await arxiv_client.fetch(url)
    # 2. Fetch citations from Semantic Scholar (1 hop, up to 100)
    citations = await semantic_scholar_client.fetch_references(paper.semantic_id)
    # 3. Store paper + citation edges in DB
    await db.upsert_paper(paper)
    await db.upsert_citations(citations)
    # 4. Generate embeddings (batch up to 100 per Gemini call)
    embedding = await gemini_client.embed(f"{paper.title}. {paper.abstract}")
    await db.store_embedding(paper.id, embedding)
    # 5. Add to workspace
    await db.add_to_workspace(paper.id, workspace_id)
```

**Gemini batching strategy (E1 owns):**
- Use `embed_content` with `task_type="RETRIEVAL_DOCUMENT"` for ingestion, `task_type="RETRIEVAL_QUERY"` for RAG queries
- Batch up to 100 texts per call to stay well within the 1,500 req/day free tier limit
- Store embeddings immediately — never re-embed on query
```python
import google.generativeai as genai
genai.configure(api_key=GEMINI_API_KEY)

async def embed_texts(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=texts,
        task_type=task_type
    )
    return result["embedding"]  # list of 768-dim vectors
```

**Graph endpoint response shape (E2 owns):**
```python
{
  "nodes": [
    { "id": "uuid", "title": "...", "authors": [...], "year": 2023,
      "cluster_id": 3, "cluster_color": "#4ECDC4", "citation_count": 142,
      "is_blind_spot": false }
  ],
  "edges": [
    { "source": "uuid", "target": "uuid", "edge_type": "cites", "confidence": 1.0 }
  ],
  "clusters": [
    { "id": 3, "label": null, "color": "#4ECDC4", "size": 12 }
  ]
}
```

**Ingestion rate limits to respect:**
- Semantic Scholar: 1 req/sec with API key — use `asyncio.sleep(1)` between reference fetches
- arXiv: 3 req/sec max — add `asyncio.sleep(0.35)` between requests
- Gemini embeddings: batch up to 100 abstracts per call — free tier 1,500 req/day, 15 RPM

**Shared Contract — Redis job key schema (agree before coding):**
```
job:{job_id}:status   → "pending" | "running" | "done" | "failed"
job:{job_id}:progress → integer 0–100
job:{job_id}:paper_id → uuid (set on completion)
```
E1 writes to these keys inside the arq worker. E2 reads them in `GET /ingest/status`. Both use identical key names — lock this in on day 1.

**Mock graph response for E1 (use until US 2.8 is ready):**
```typescript
// frontend/src/mocks/graph.ts — E1 develops against this shape, swaps to real API on merge
export const MOCK_GRAPH = {
  nodes: [
    { id: "1", title: "Attention Is All You Need", year: 2017,
      cluster_id: 0, cluster_color: "#4ECDC4", citation_count: 142, is_blind_spot: false },
    { id: "2", title: "BERT", year: 2018,
      cluster_id: 0, cluster_color: "#4ECDC4", citation_count: 89, is_blind_spot: false },
  ],
  edges: [{ source: "1", target: "2", edge_type: "cites", confidence: 1.0 }],
  clusters: [{ id: 0, label: null, color: "#4ECDC4", size: 2 }]
}
```

---

**Definition of Done:** Paste 5 arXiv links into the frontend → ingestion jobs run in the background → a real citation graph with cluster-colored nodes appears in the browser → clicking a node slides open a paper detail panel from the right.

---

## Sprint 3 — Blind Spot Engine

**The Goal:** The killer feature works end-to-end. A researcher adds papers and the system tells them — with explanation — what foundational work they're missing and what conceptual territory they've never engaged with.

**Resume Keywords Added:** HDBSCAN clustering, cosine similarity, semantic gap detection, citation graph analysis, LLM-generated explanations, pgvector, scikit-learn

---

> **Sprint Kickoff:** E2 delivers Layer 1 (US 3.6) as the very first task — Layer 2 (US 3.1) takes Layer 1's output as input and cannot run without it. E1 develops Layer 2 against the Layer 1 fixture below in parallel, then integrates once US 3.6 is merged. Both engineers agree on the Redis cache key schema before coding. E1 also develops the BlindSpotPanel UI against the mock gaps response, swapping to the real `GET /gaps` endpoint when E2 delivers US 3.7.

---

### User Stories

**US 3.6 [E2] ⚡ First task of sprint:** As a developer, Layer 1 citation gap detection runs correctly — it identifies papers cited by ≥2 workspace papers that the user hasn't read, counts citation frequency across workspace papers, and ranks results by frequency descending. *Unblocks: US 3.1*

**US 3.7 [E2] ⚡ Early priority:** As a user, `GET /gaps/{workspace_id}` returns the full gap payload with citation gaps and semantic gaps, each with paper metadata, scores, and `why_matters` text. *Unblocks: US 3.5*

**US 3.8 [E2]:** As a user, each gap card has an "Add to workspace" button that fires `POST /ingest/url` for that paper so I can ingest a missing paper in one click without leaving the panel.

**US 3.9 [E2]:** As a developer, gap detection results are cached in Redis with a TTL of 1 hour so repeated `GET /gaps` calls don't rerun the HDBSCAN algorithm unnecessarily.

**US 3.1 [E1] (develop against fixture, integrate after US 3.6):** As a developer, Layer 2 semantic gap detection runs correctly — HDBSCAN clusters the candidate embedding space, coverage is measured per cluster via cosine similarity, and clusters with coverage < 0.65 are flagged as conceptual blind spots.

**US 3.2 [E1]:** As a user, each semantic gap cluster is assigned a 2–4 word LLM-generated label (e.g. "Mechanistic Interpretability", "Tool Use & Guardrails") by feeding the top 5 paper titles and abstracts in that cluster to `gemini-1.5-flash`.

**US 3.3 [E1]:** As a user, each gap card shows a one-sentence `why_matters` explanation generated by LLM that connects the gap to the user's existing papers so I immediately understand why this gap is relevant to my research.

**US 3.4 [E1]:** As a user, `POST /gaps/{workspace_id}/detect` kicks off a full gap detection run as a background job and returns a `job_id` so the UI can poll for completion.

**US 3.5 [E1] (develop against mock, integrate after US 3.7):** As a user, the `BlindSpotPanel` is a shadcn `Sheet` anchored to the left side of the workspace page with two `Tabs` — "Citation Gaps" and "Conceptual Gaps" — each listing ranked gap cards built from shadcn `Card` components with badge, title, score, and explanation.

---

### Technical Execution Checklist

**Shared Contract — Redis cache key schema (agree before coding):**
```
gaps:{workspace_id}:citation   → JSON list of citation gap results, TTL 1hr
gaps:{workspace_id}:semantic   → JSON list of semantic gap results, TTL 1hr
```
E2 writes these in US 3.9. E1's Layer 2 reads citation gaps from DB (not cache) — cache is only for the API response layer.

**Layer 1 test fixture for E1 (committed to `tests/fixtures/layer1_output.json`):**
```json
[
  { "paper_id": "uuid-a", "gap_type": "citation_gap", "citation_freq": 5,
    "cited_by_papers": ["Paper X", "Paper Y", "Paper Z", "Paper W", "Paper V"],
    "paper": { "title": "Attention Is All You Need", "year": 2017, "authors": ["Vaswani et al."] }},
  { "paper_id": "uuid-b", "gap_type": "citation_gap", "citation_freq": 3,
    "cited_by_papers": ["Paper X", "Paper Y", "Paper Z"],
    "paper": { "title": "BERT", "year": 2018, "authors": ["Devlin et al."] }}
]
```
E1 loads this fixture in `detect_semantic_gaps` during development so Layer 2 runs without needing a live DB. Swap to real DB call after US 3.6 is merged.

**Layer 1 — Citation gap algorithm (E2 owns):**
```python
def detect_citation_gaps(workspace_id, db):
    workspace_ids = get_workspace_paper_ids(workspace_id)
    all_cited_ids = get_all_cited_paper_ids(workspace_ids)
    gap_ids = all_cited_ids - set(workspace_ids)

    citation_freq = Counter()
    for gap_id in gap_ids:
        citing = get_papers_citing(gap_id, within=workspace_ids)
        citation_freq[gap_id] = len(citing)

    return sorted(
        [BlindSpot(paper_id=pid, gap_type="citation_gap", citation_freq=freq)
         for pid, freq in citation_freq.items() if freq >= 2],
        key=lambda x: x.citation_freq, reverse=True
    )
```

**Layer 2 — Semantic gap algorithm (E1 owns):**
```python
def detect_semantic_gaps(workspace_id, db):
    workspace_embeddings = get_workspace_embeddings(workspace_id)
    gap_candidates = get_citation_gap_papers(workspace_id)
    candidate_embeddings = get_embeddings(gap_candidates)

    clusterer = HDBSCAN(min_cluster_size=3, metric='cosine')
    cluster_labels = clusterer.fit_predict(candidate_embeddings)

    gaps = []
    for cluster_id in set(cluster_labels):
        if cluster_id == -1: continue  # noise
        cluster_papers = [gap_candidates[i] for i, l in enumerate(cluster_labels) if l == cluster_id]
        centroid = np.mean([candidate_embeddings[i] for i, l in enumerate(cluster_labels) if l == cluster_id], axis=0)
        coverage = float(cosine_similarity(centroid.reshape(1,-1), workspace_embeddings).max())
        if coverage < 0.65:
            gaps.append(SemanticGap(
                cluster_label=generate_cluster_label(cluster_papers),
                coverage_score=coverage,
                top_papers=cluster_papers[:5],
                why_matters=generate_why_matters(cluster_papers, workspace_id)
            ))
    return sorted(gaps, key=lambda x: x.coverage_score)
```

**LLM prompt for cluster labeling (E1 owns):**
```python
prompt = f"""
These {len(papers)} academic papers form a coherent topic cluster.
Give a 2-4 word label for this cluster.
Papers: {format_papers(papers[:5])}
Return only the label, nothing else.
"""
```

**Mock gaps response for E1 BlindSpotPanel (use until US 3.7 is ready):**
```typescript
// frontend/src/mocks/gaps.ts
export const MOCK_GAPS = {
  citation_gaps: [
    { paper: { id: "1", title: "Attention Is All You Need", authors: ["Vaswani et al."], year: 2017, url: "#" },
      cited_by_count: 5, cited_by_papers: ["Paper A", "Paper B", "Paper C", "Paper D", "Paper E"],
      why_matters: "Foundational work on transformer architecture cited heavily across your corpus." }
  ],
  semantic_gaps: [
    { cluster_label: "Mechanistic Interpretability", coverage_score: 0.12,
      top_papers: [{ id: "2", title: "Towards Monosemanticity", semantic_score: 0.91 }],
      why_matters: "Your papers frequently reference this topic but you have no direct coverage." }
  ]
}
```

**Gap card UI anatomy (E1 owns):**
- Citation gap card: paper title, authors, year, "Cited by N of your papers" badge, `why_matters` text, "Add to workspace" button
- Semantic gap card: cluster label, coverage score bar, top 3 paper titles, `why_matters` text, "Explore cluster" action

---

**Definition of Done:** Ingest 10 real arXiv papers → click "Detect Blind Spots" → the BlindSpotPanel populates with citation gaps ranked by frequency and conceptual gaps with LLM-generated labels and one-sentence explanations. At least one gap card makes a non-obvious, accurate recommendation.

---

## Sprint 4 — AI Layer

**The Goal:** The product stops being a graph viewer and becomes a research assistant. Researchers can ask questions about their papers, see how papers relate intellectually, and generate related work drafts.

**Resume Keywords Added:** RAG (Retrieval-Augmented Generation), pgvector similarity search, IVFFlat indexing, LLM prompting, semantic edge classification, p95 latency tracking, Gemini 1.5 Flash

---

### User Stories

**US 4.1 [E1]:** As a user, I can type a natural language question into the `RAGQueryBox` at the bottom of the workspace and receive a cited answer grounded exclusively in my workspace papers.

**US 4.2 [E1]:** As a developer, the RAG pipeline embeds the query using `text-embedding-004`, runs a pgvector `<=>` cosine similarity search scoped to the workspace (top 8 chunks), builds a context window under 6000 tokens, and calls `gemini-1.5-flash` for answer generation.

**US 4.3 [E1]:** As a developer, the IVFFlat index on `paper_embeddings` is used for approximate nearest-neighbor search so p95 vector search latency stays under 300ms even as the workspace grows.

**US 4.4 [E1]:** As a user, React Flow edges are styled by their classified type: `extends` (teal #4ECDC4), `contradicts` (red #FF6B6B, dashed), `uses_dataset` (purple #A78BFA), `cites` (gray #94A3B8), with a small inline label so paper relationships are visually meaningful.

**US 4.5 [E2]:** As a developer, each citation edge is classified as `extends | contradicts | uses_dataset | cites` via `gemini-1.5-flash` using both paper abstracts as context, with a confidence score stored in the `citations` table.

**US 4.6 [E2]:** As a user, I can select a cluster on the graph and trigger a "Generate Related Work" action that produces a 2-paragraph related work section draft citing the papers in that cluster.

**US 4.7 [E2]:** As a user, auto-generated cluster labels (from Sprint 3) appear as text badges on or near each cluster's centroid node so the topic landscape is labeled without any manual effort.

---

### Technical Execution Checklist

**RAG pgvector query (E1 owns):**
```sql
SELECT pe.paper_id, p.title, pe.embedding,
       1 - (pe.embedding <=> $1::vector) AS score
FROM paper_embeddings pe
JOIN workspace_papers wp ON wp.paper_id = pe.paper_id
JOIN papers p ON p.id = pe.paper_id
WHERE wp.workspace_id = $2
ORDER BY pe.embedding <=> $1::vector
LIMIT 8;
```

**RAG LLM call (E1 owns):**
```python
import google.generativeai as genai

model = genai.GenerativeModel("gemini-1.5-flash")

prompt = f"""You are a research assistant. Answer only from the provided papers.
Cite every claim with the paper title in brackets like [Paper Title].

Question: {query}

Context:
{format_chunks(top_chunks)}"""

response = model.generate_content(prompt)
answer = response.text
```

**Edge classification prompt (E2 owns):**
```python
prompt = f"""
Paper A: {paper_a.title}. {paper_a.abstract[:300]}
Paper B: {paper_b.title}. {paper_b.abstract[:300]}

Paper A cites Paper B. Classify the relationship:
- extends: A builds directly on B's method or framework
- contradicts: A challenges or disputes B's findings
- uses_dataset: A uses the same dataset as B
- cites: general citation, none of the above

Return JSON: {{"edge_type": "...", "confidence": 0.0-1.0}}
"""
```

**Latency targets:**
- p95 vector search (pgvector query only): < 300ms
- p95 total RAG response (vector search + LLM generation): < 3s
- Log both separately per request so they can be tracked independently

**Related work draft prompt (E2 owns):**
```python
prompt = f"""
Write a 2-paragraph related work section for a paper that builds on this research cluster: "{cluster_label}".
Use these papers as sources: {format_papers(cluster_papers[:8])}
Write in academic style. Cite papers by title in brackets.
"""
```

---

**Definition of Done:** Type "what do my papers say about hallucination?" into the RAGQueryBox → receive a multi-sentence answer with bracketed paper citations within 3 seconds. Graph edges show color-coded relationship types. Selecting a cluster shows a "Generate Related Work" button that produces a readable 2-paragraph draft.

---

## Sprint 5 — Auth & Collaboration

**The Goal:** Multiple researchers can work in the same workspace simultaneously. Changes to edge annotations and comments appear in real time for all connected users. Auth gates everything.

**Resume Keywords Added:** JWT authentication, bcrypt, Yjs CRDTs, WebSockets, real-time collaboration, AWS SES, workspace access control, live presence

---

> **Sprint Kickoff:** E2 ships auth endpoints (US 5.6) and JWT middleware (US 5.7) on day 1 — every E1 story in this sprint requires a valid token to test. E2 also ships the WebSocket server (US 5.8) as the second priority so E1 can test Yjs sync. Both engineers agree on the invite API contract (see Shared Contracts) before building the invite flow.

---

### User Stories

**US 5.6 [E2] ⚡ Day 1 first:** As a developer, `POST /auth/register` and `POST /auth/login` hash passwords with bcrypt, issue a 15-min JWT access token and a 7-day refresh token, and store the refresh token hash in the database. *Unblocks: all E1 stories*

**US 5.7 [E2] ⚡ Day 1 first:** As a developer, all non-auth API endpoints are protected by a FastAPI dependency that validates the JWT and returns 401 on failure so unauthenticated access is impossible. *Unblocks: all E1 stories*

**US 5.8 [E2] ⚡ Early priority:** As a developer, the WebSocket server at `WS /ws/{workspace_id}?token=...` validates the JWT from the query param, loads or creates the Yjs document for that workspace, and uses `ypy_websocket.WebsocketProvider` to manage sync so collaboration state is maintained across all connected clients. *Unblocks: US 5.3, 5.4, 5.5*

**US 5.9 [E2]:** As a user, the BlindSpotPanel shows a "Team Coverage" section aggregating gaps across all workspace members so the team sees their collective literature blind spots, not just individual ones.

**US 5.10 [E2]:** As a developer, Yjs document snapshots are serialized and persisted to S3 on WebSocket disconnect so collaboration state (edge annotations, comments) survives server restarts.

**US 5.11 [E2]:** As a user, when I invite a collaborator by email they receive a workspace invite email via AWS SES with a direct join link so they don't need to navigate the app to find the workspace.

**US 5.1 [E1] (after US 5.6 + 5.7):** As a user, I can register and log in via a clean auth UI and the frontend automatically refreshes my JWT access token before it expires (15 min TTL) so my session never interrupts my work.

**US 5.2 [E1] (after US 5.6 + 5.7, invite contract agreed):** As a user, I can create a workspace and invite collaborators by email from the workspace settings page so lab mates can join my literature review.

**US 5.3 [E1] (after US 5.8):** As a user, two people in the same workspace see edge annotation changes in real time — when one person changes an edge type, the other sees it update on their graph within milliseconds via Yjs CRDT sync.

**US 5.4 [E1] (after US 5.8):** As a user, I can add a comment to any paper node by clicking it and typing in the PaperDetailPanel, and all online teammates see the new comment appear instantly via Yjs.

**US 5.5 [E1] (parallel — Yjs awareness is frontend-only):** As a user, a small colored avatar dot appears next to each node that a teammate is currently hovering over so I have spatial awareness of what my collaborators are looking at.

---

### Technical Execution Checklist

**Shared Contract — Invite API (agree before US 5.2 and US 5.11):**
```
POST /workspaces/{id}/invite   { email: string }
→ { invite_id: uuid, join_url: "https://litlens.app/join?token={invite_token}" }
```
E1 fires the POST and renders the success state. E2 sends the SES email using `join_url`. Both agree on this shape before building — otherwise the invite UI and email will mismatch.

**JWT setup (E2 owns):**
```python
# Access token: 15 minutes, signed with HS256
# Refresh token: 7 days, hash stored in DB for revocation
ACCESS_TOKEN_EXPIRE = timedelta(minutes=15)
REFRESH_TOKEN_EXPIRE = timedelta(days=7)

def create_access_token(user_id: str) -> str:
    return jwt.encode({"sub": user_id, "exp": datetime.utcnow() + ACCESS_TOKEN_EXPIRE},
                      SECRET_KEY, algorithm="HS256")
```

**WebSocket server (E2 owns):**
```python
@app.websocket("/ws/{workspace_id}")
async def websocket_endpoint(websocket: WebSocket, workspace_id: str, token: str):
    user = verify_jwt(token)  # 401 close if invalid
    await websocket.accept()
    ydoc = await load_ydoc_from_s3(workspace_id)
    async with ypy_websocket.WebsocketProvider(ydoc, websocket):
        try:
            await websocket.wait_for_disconnect()
        finally:
            await save_ydoc_to_s3(workspace_id, ydoc)
```

**Frontend Yjs wiring (E1 owns):**
```typescript
const ydoc = new Y.Doc()
const provider = new WebsocketProvider(WS_URL, workspaceId, ydoc)
const edgeAnnotations = ydoc.getMap('edge_annotations') // { edgeKey → {type, annotatedBy} }
const comments = ydoc.getArray('comments')              // append-only

// Intercept React Flow node drag and write to Yjs instead of local state
const onNodesChange = useCallback((changes) => {
  changes.forEach(change => {
    if (change.type === 'position') {
      ydoc.getMap('node_positions').set(change.id, change.position)
    }
  })
}, [ydoc])

// Live presence
provider.awareness.setLocalStateField('user', { name: user.email, color: userColor })
```

**Yjs shared data structures:**
- `ydoc.getMap('edge_annotations')` — key: `"${citing_id}→${cited_id}"`, value: `{type, annotatedBy, note}`
- `ydoc.getArray('comments')` — append-only, each item: `{paper_id, author, content, created_at}`
- `ydoc.getMap('node_positions')` — key: `paper_id`, value: `{x, y}` for persistent layout
- `ydoc.getMap('awareness')` — managed by Yjs awareness protocol automatically

---

**Definition of Done:** Open the same workspace in two browser windows. In window A, change an edge type annotation. In window B, see it update in under 500ms without a page refresh. Add a comment in window A — see it appear in window B instantly. Both windows show each other's presence dot on hovered nodes.

---

## Sprint 6 — Production Hardening

**The Goal:** The app is deployed on real AWS infrastructure and accessible at a stable URL. Someone else can use it without your laptop. Performance is measured, limits are enforced, and failures are observable.

**Resume Keywords Added:** AWS EC2, AWS RDS (PostgreSQL + pgvector), AWS ElastiCache (Redis), AWS S3, AWS SES, AWS SSM Parameter Store, Docker, GitHub Actions CI/CD, Vercel, rate limiting, p95 latency tracking

---

> **Sprint Kickoff:** E1 delivers the Dockerfile (US 6.4) as the first task — E2 cannot do the EC2 deploy (US 6.5) without a working image. E2 provisions EC2, RDS, and ElastiCache in parallel while E1 finishes the Dockerfile. RDS and ElastiCache connection string swaps (US 6.6, 6.7) must be done together — both engineers coordinate on this step since it changes the database and Redis URL that E1's workers and E2's infrastructure both rely on.

---

### User Stories

**US 6.4 [E1] ⚡ First task of sprint:** As a developer, a `Dockerfile` for the FastAPI backend and a `docker-compose.yml` for full local dev (backend + postgres + redis) are committed so the production container is tested locally before it touches AWS. *Unblocks: US 6.5*

**US 6.1 [E1]:** As a developer, a Redis token bucket enforces per-user rate limits (100 ingestion jobs/day, 500 RAG queries/day) in FastAPI middleware so the system is protected from abuse before it has real users.

**US 6.2 [E1]:** As a developer, ingestion jobs retry failed arXiv and Semantic Scholar API calls up to 3 times with exponential backoff (1s, 2s, 4s) so transient network errors don't surface as user-facing failures.

**US 6.3 [E1]:** As a developer, every API endpoint logs its response time, and p95 latency per endpoint is queryable from PostgreSQL so performance regressions are detectable before users notice them.

**US 6.5 [E2] (after US 6.4):** As a developer, the FastAPI container is built and deployed to an AWS EC2 t2.micro instance via SSH + docker-compose and accessible at a stable HTTPS URL so the backend is live on free-tier infrastructure.

**US 6.6 [E2]:** As a developer, the local PostgreSQL is replaced with AWS RDS (PostgreSQL 16 + pgvector extension enabled) and all migrations are applied so the database is managed, backed up, and production-grade.

**US 6.7 [E2]:** As a developer, the local Redis is replaced with AWS ElastiCache (Redis 7) and the connection string is updated in all workers and middleware so rate limiting and job queues run on managed infrastructure.

**US 6.8 [E2]:** As a developer, an S3 bucket is configured with two prefixes — `pdfs/` for cached arXiv PDFs and `yjs-snapshots/` for Yjs doc serializations — with appropriate IAM policies so the app can read/write without using root credentials.

**US 6.9 [E2]:** As a developer, all secrets (database URL, Redis URL, Gemini API key, JWT secret) are stored in AWS SSM Parameter Store (free standard tier) and pulled into the EC2 instance's `.env` file at deploy time so no credentials exist in the codebase or Docker image.

**US 6.10 [E2]:** As a developer, the React frontend is deployed to Vercel pointed at the EC2 backend URL so the frontend is on a global CDN with zero server management.

**US 6.11 [E2]:** As a developer, a GitHub Actions workflow runs `ruff` lint + `pytest` on every PR and SSHes into the EC2 instance to run `git pull && docker-compose up -d --build` on every push to `main` so the deploy pipeline is fully automated.

---

### Technical Execution Checklist

**Dockerfile (E1 owns):**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Rate limiting middleware (E1 owns):**
```python
# Redis token bucket: refill 100 ingestion tokens per day per user
async def check_rate_limit(user_id: str, action: str, limit: int):
    key = f"rate:{user_id}:{action}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 86400)  # 24hr TTL
    if count > limit:
        raise HTTPException(429, "Rate limit exceeded")
```

**p95 latency logging (E1 owns):**
```python
# FastAPI middleware — log every request duration to a latency_logs table
@app.middleware("http")
async def latency_middleware(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = (time.monotonic() - start) * 1000
    await db.log_latency(endpoint=request.url.path, duration_ms=duration_ms)
    return response
```

**Connection string swap coordination (E1 + E2 together):**
When E2 is ready to cut over to RDS (US 6.6) and ElastiCache (US 6.7), do it in one coordinated step:
1. E2 provisions RDS and ElastiCache, gets the endpoint URLs
2. E2 adds `DATABASE_URL` and `REDIS_URL` to SSM Parameter Store
3. Both engineers update their local `.env` to point at the new services
4. E1 confirms arq workers and rate limiting middleware connect successfully before the deploy goes out
5. E2 runs migrations against RDS — only after E1 confirms the schema hasn't changed

Do NOT swap one without the other in the same deploy — a Redis URL pointing at ElastiCache while Postgres is still local will cause worker failures.

**EC2 t2.micro setup (E2 owns):**
- AMI: Amazon Linux 2023 (free tier eligible)
- Install Docker + docker-compose on first launch via user data script
- Open ports 80 (HTTP), 443 (HTTPS), 22 (SSH) in the security group
- Use an Elastic IP (free while attached to a running instance) for a stable address
- Pull secrets from SSM Parameter Store at deploy time and write to `.env`

**SSM Parameter Store secret pull at deploy (E2 owns):**
```bash
# Run on EC2 before docker-compose up — pulls all secrets into .env
aws ssm get-parameters-by-path --path /litlens/ --with-decryption \
  --query "Parameters[*].[Name,Value]" --output text \
  | awk '{gsub("/litlens/","",$1); print toupper($1)"="$2}' > .env
```

**GitHub Actions deploy step (E2 owns):**
```yaml
- name: Deploy to EC2
  uses: appleboy/ssh-action@v1
  with:
    host: ${{ secrets.EC2_HOST }}
    username: ec2-user
    key: ${{ secrets.EC2_SSH_KEY }}
    script: |
      cd /home/ec2-user/litlens
      git pull origin main
      aws ssm get-parameters-by-path --path /litlens/ --with-decryption \
        --query "Parameters[*].[Name,Value]" --output text \
        | awk '{gsub("/litlens/","",$1); print toupper($1)"="$2}' > .env
      docker-compose up -d --build
```

---

**Definition of Done:** `git push origin main` triggers the GitHub Actions pipeline. Tests pass. The EC2 instance pulls the new image and restarts via docker-compose. The app is live at a real HTTPS URL. A colleague can register, create a workspace, paste an arXiv link, and see a citation graph — using only their browser, with your laptop closed.

---

## Sprint 7 — Real Users & Resume Polish

**The Goal:** 10–30 real researchers use the app on their actual literature reviews. Metrics are captured. The project presents itself on GitHub without needing you to explain it.

**Resume Keywords Added:** User research, DAU tracking, observability, CloudWatch, technical writing

---

### User Stories

**US 7.1 [E1]:** As a researcher, I can use LitLens end-to-end on my actual literature review and be shown at least one blind spot I was genuinely unaware of so the tool proves its value on real research.

**US 7.2 [E1]:** As a developer, DAU, papers ingested per session, blind spots surfaced per session, RAG queries per session, and "Add to workspace" click rate are tracked in a `usage_events` table so resume metrics can be filled in from real data.

**US 7.3 [E1]:** As a visitor to the GitHub repo, I can understand what LitLens does, see a 30-second demo GIF, and run it locally in under 5 minutes using only the README so the project presents itself without explanation.

**US 7.4 [E2]:** As a developer, CloudWatch alarms notify via email when the EC2 instance fails a status check or when RDS CPU exceeds 80% so production failures are caught before users report them.

**US 7.5 [E2]:** As a developer, RDS automated backups are enabled with a 7-day retention window and a manual restore has been tested so data loss risk is understood and mitigated.

---

### Technical Execution Checklist

**Usage event tracking (E1 owns):**
```python
# Fire-and-forget — don't block request on analytics write
async def track_event(user_id: str, event: str, metadata: dict):
    await db.execute(
        "INSERT INTO usage_events (user_id, event, metadata, created_at) VALUES ($1,$2,$3,NOW())",
        user_id, event, json.dumps(metadata)
    )
# Events to track:
# "paper_ingested", "blind_spot_surfaced", "rag_query", "gap_added_to_workspace"
```

**How to get real users (non-technical):**
- Ask USF lab mates doing literature reviews right now — offer to sit with them for 20 minutes
- Post in department Slack: "I built a tool that finds gaps in your lit review — takes 5 minutes to try"
- Ask one professor to share with their grad students
- Sit with 2–3 researchers and watch them use it — their confusion is more valuable than any metric

**README must include:**
- One-sentence description at the top
- Demo GIF (record with Loom or QuickTime → convert via `ffmpeg -i demo.mov -vf fps=10 demo.gif`)
- Architecture diagram (export from the project spec)
- Tech stack table
- `git clone` → `cp .env.example .env` → `docker-compose up` → `npm run dev` in 4 commands

**CloudWatch alarms (E2 owns):**
- EC2 status check failed: `aws cloudwatch put-metric-alarm --alarm-name litlens-ec2-status --metric-name StatusCheckFailed --namespace AWS/EC2 ...`
- RDS CPU > 80%: standard RDS CloudWatch metric, threshold alarm → SNS → email

---

**Definition of Done:** 10+ real researchers have run the app on actual literature reviews. The `usage_events` table has real data to fill in resume metrics. The GitHub README renders a demo GIF and local setup works in under 5 minutes on a clean machine.

---

## Roadmap Summary

| Sprint | Feature | E1 Stories | E2 Stories |
|--------|---------|-----------|-----------|
| 1 | Foundation | 5 | 4 |
| 2 | Core Ingestion Pipeline | 5 | 5 |
| 3 | Blind Spot Engine | 5 | 4 |
| 4 | AI Layer | 4 | 3 |
| 5 | Auth & Collaboration | 5 | 6 |
| 6 | Production Hardening | 4 | 7 |
| 7 | Real Users & Resume Polish | 3 | 2 |
| **Total** | | **31** | **31** |

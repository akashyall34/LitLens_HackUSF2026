LitLens — Full Technical Specification
Production-grade literature blind spot detection and knowledge graph platform

1. What It Does
Researchers paste arXiv links or search a topic → LitLens builds a visual citation knowledge graph, detects foundational gaps in their literature coverage using both citation analysis and semantic embedding clustering, surfaces what they're missing and why, and answers questions grounded in their reading.
The one-sentence pitch: It finds what you don't know you're missing.

2. Why It's Unique
Tool	What it does	What it misses
Connected Papers	Citation graph from one seed	No gap detection, no AI, no collab
ResearchRabbit	Paper recommendations	No graph, no RAG, no blind spots
Elicit / Consensus	AI Q&A over papers	No graph, no gap detection
BrowseGraph	Passive browsing capture	No citation intelligence
LitLens	All of the above + blind spot detection	Nothing like it exists
3. Full Feature Set
3.1 Core
* Paper ingestion via arXiv URL, DOI, or topic search
* Citation graph built automatically via Semantic Scholar API
* Visual graph canvas with cluster coloring, zoom, filter by year/topic
* Citation gap detection — papers cited by ≥2 of yours that you haven't read
* Semantic gap detection — conceptual territory present in your citations but absent in your papers
* Ranked gap list by citation frequency + semantic relevance
3.2 AI Layer
* RAG queries: "what do my papers say about X?"
* Auto-generated cluster labels (e.g. "Tool Use & Guardrails", "Alignment Techniques")
* Semantic edge typing: extends / contradicts / uses same dataset
* Related work draft generator across a selected cluster
3.3 Collaboration
* Multi-user workspaces — invite lab mates
* Real-time co-annotation of edges via WebSockets + Yjs
* Shared blind spot panel — see what your whole team is missing
* Comments on nodes
3.4 Production
* Auth + JWT with refresh tokens
* Rate limiting per user (token bucket)
* p95 latency tracking per endpoint
* Docker + AWS EC2 (t2.micro) deployment
* GitHub Actions CI/CD pipeline

4. Tech Stack
Layer	Tech	Why
Backend	FastAPI	Async, Python native, fast to build
Backend compute	AWS EC2 (t2.micro)	Free tier, run FastAPI + arq worker via Docker Compose on a single instance
Database	AWS RDS (PostgreSQL + pgvector)	Managed Postgres with automated backups, same pgvector extension
Cache	AWS ElastiCache (Redis)	Managed Redis for rate limiting, session caching, job queues
File storage	AWS S3	Raw PDFs, Yjs snapshots — cheap, trivial boto3 integration
Email	AWS SES	Workspace invite emails — standard AWS pattern
Graph canvas	React Flow	Better DX and visual quality than Cytoscape.js; built-in minimap, zoom, node selection; MIT licensed
UI components	shadcn/ui + Tailwind CSS	Own the code, Radix UI accessibility, modern default theme with no extra effort
Icons	Lucide React	Same ecosystem as shadcn/ui
Animations	Framer Motion	Panel open/close transitions, graph state changes
Real-time	WebSockets + Yjs	CRDTs without building from scratch
Embeddings	Gemini gemini-embedding-2-preview	Free via Google AI Studio, 768 dimensions
LLM + Agents	Gemini 2.0 Flash via Google ADK	Free tier, powers all agents and LLM generation; ADK provides sub_agent routing and built-in test UI
Multi-agent	Google ADK	Purpose-built agent framework for Gemini; declarative Agent definition, sub_agents, automatic tool-use loop
Clustering	scikit-learn (HDBSCAN)	Handles variable cluster sizes better than k-means for papers
External APIs	Semantic Scholar + arXiv	Free, reliable, citation data nobody else surfaces this way
Frontend deploy	Vercel	Simpler than S3+CloudFront for React, free tier sufficient
CI/CD	GitHub Actions → EC2	Auto-deploy main branch to EC2 on push via SSH + docker-compose
5. System Architecture
┌─────────────────────────────────────────────────────┐
│                    React Frontend                    │
│  React Flow graph   │ Blind Spot Panel │ RAG Query   │
│  Yjs real-time sync │ Paper Detail     │ Auth UI     │
└──────────────┬──────────────────────────────────────┘
               │ REST + WebSocket
┌──────────────▼──────────────────────────────────────┐
│           FastAPI on AWS EC2 (t2.micro)               │
│                                                      │
│  /ingest  /graph  /gaps  /rag  /collab  /auth        │
│                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │  Ingestion  │  │  Gap Engine  │  │  RAG Layer │  │
│  │  Pipeline   │  │  Layer 1 + 2 │  │            │  │
│  └──────┬──────┘  └──────┬───────┘  └─────┬──────┘  │
└─────────┼────────────────┼────────────────┼─────────┘
          │                │                │
┌─────────▼────────────────▼────────────────▼─────────┐
│           AWS RDS — PostgreSQL + pgvector            │
│  papers │ citations │ embeddings │ workspaces │ users│
└──────────────────────────┬──────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │   AWS ElastiCache        │
              │   (Redis)                │
              │  rate limits │ sessions  │
              │  job queue   │ cache     │
              └─────────────────────────┘

AWS S3:
  paper PDFs ──────────────► cached on first fetch from arXiv
  Yjs snapshots ──────────► persisted per workspace

AWS SES:
  workspace invites ───────► email delivery

External (read-only):
  arXiv API ──────────────► paper metadata + abstracts
  Semantic Scholar API ───► citation graph + author data
  Gemini API ──────────────► embeddings + text generation

6. Database Schema
-- Users and workspaces
CREATE TABLE users (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email       TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE workspaces (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL,
  owner_id    UUID REFERENCES users(id),
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE workspace_members (
  workspace_id UUID REFERENCES workspaces(id),
  user_id      UUID REFERENCES users(id),
  role         TEXT DEFAULT 'member', -- owner | member
  PRIMARY KEY (workspace_id, user_id)
);

-- Papers
CREATE TABLE papers (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  arxiv_id        TEXT UNIQUE,
  semantic_id     TEXT UNIQUE,         -- Semantic Scholar paper ID
  doi             TEXT,
  title           TEXT NOT NULL,
  abstract        TEXT,
  authors         JSONB,               -- [{name, affiliations}]
  year            INT,
  venue           TEXT,
  citation_count  INT DEFAULT 0,
  url             TEXT,
  fetched_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Embeddings via pgvector
CREATE TABLE paper_embeddings (
  paper_id    UUID REFERENCES papers(id) PRIMARY KEY,
  embedding   vector(768),             -- Gemini gemini-embedding-2-preview
  chunk_index INT DEFAULT 0            -- 0 = abstract, 1+ = full text chunks
);
CREATE INDEX ON paper_embeddings USING ivfflat (embedding vector_cosine_ops);

-- Citation graph edges
CREATE TABLE citations (
  citing_paper_id   UUID REFERENCES papers(id),
  cited_paper_id    UUID REFERENCES papers(id),
  edge_type         TEXT DEFAULT 'cites', -- extends | contradicts | uses_dataset | cites
  confidence        FLOAT DEFAULT 1.0,
  PRIMARY KEY (citing_paper_id, cited_paper_id)
);

-- Workspace ↔ paper membership (which papers are "in" a workspace)
CREATE TABLE workspace_papers (
  workspace_id  UUID REFERENCES workspaces(id),
  paper_id      UUID REFERENCES papers(id),
  added_by      UUID REFERENCES users(id),
  added_at      TIMESTAMPTZ DEFAULT NOW(),
  is_read       BOOLEAN DEFAULT TRUE,   -- papers added by user = read
  PRIMARY KEY (workspace_id, paper_id)
);

-- Gap detection results (cached per workspace)
CREATE TABLE blind_spots (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id    UUID REFERENCES workspaces(id),
  paper_id        UUID REFERENCES papers(id),
  gap_type        TEXT,                -- citation_gap | semantic_gap
  citation_freq   INT DEFAULT 0,       -- how many workspace papers cite this
  semantic_score  FLOAT,               -- distance from nearest cluster centroid
  cluster_label   TEXT,                -- e.g. "Mechanistic Interpretability"
  why_matters     TEXT,                -- LLM-generated explanation
  detected_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Collaboration: node comments
CREATE TABLE node_comments (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  UUID REFERENCES workspaces(id),
  paper_id      UUID REFERENCES papers(id),
  author_id     UUID REFERENCES users(id),
  content       TEXT NOT NULL,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Collaboration: edge annotations (Yjs doc stored as snapshot)
CREATE TABLE edge_annotations (
  workspace_id      UUID REFERENCES workspaces(id),
  citing_paper_id   UUID REFERENCES papers(id),
  cited_paper_id    UUID REFERENCES papers(id),
  yjs_snapshot      BYTEA,             -- serialized Yjs doc
  updated_at        TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (workspace_id, citing_paper_id, cited_paper_id)
);

7. API Contracts
7.1 Auth
POST /auth/register     { email, password } → { user_id, access_token, refresh_token }
POST /auth/login        { email, password } → { access_token, refresh_token }
POST /auth/refresh      { refresh_token }   → { access_token }
7.2 Ingestion
POST /ingest/url        { url: "https://arxiv.org/abs/2310.01234", workspace_id }
POST /ingest/doi        { doi: "10.48550/...", workspace_id }
POST /ingest/search     { query: "LLM agent reliability", workspace_id, limit: 20 }
GET  /ingest/status/{job_id}   → { status, progress, paper_id }
Ingestion is async — returns a job_id immediately, frontend polls status.
7.3 Graph
GET  /graph/{workspace_id}
     → {
         nodes: [{ id, title, authors, year, cluster_id, cluster_label, citation_count }],
         edges: [{ source, target, edge_type, confidence }],
         clusters: [{ id, label, color, centroid }]
       }

PATCH /graph/{workspace_id}/edge
     { citing_id, cited_id, edge_type }   → { updated_edge }
7.4 Blind Spots
POST /gaps/{workspace_id}/detect
     → { job_id }   (async, triggers full gap detection run)

GET  /gaps/{workspace_id}
     → {
         citation_gaps: [{
           paper: { id, title, authors, year, url },
           cited_by_count: 8,
           cited_by_papers: ["Paper A", "Paper B", ...],
           why_matters: "Foundational work on..."
         }],
         semantic_gaps: [{
           cluster_label: "Mechanistic Interpretability",
           coverage_score: 0.03,
           top_papers: [{ id, title, semantic_score }],
           why_matters: "Your papers reference this topic frequently but..."
         }]
       }
7.5 RAG
POST /rag/query
     { workspace_id, query: "what do my papers say about hallucination?" }
     → {
         answer: "...",
         citations: [{ paper_id, title, chunk_text, relevance_score }]
       }
7.6 Collaboration
GET  /workspaces/{id}/members          → [{ user_id, email, role }]
POST /workspaces/{id}/invite           { email } → { invite_id }
WS   /ws/{workspace_id}?token=...      Yjs sync channel

8. Ingestion Pipeline (Your Piece — Hours 2-8)
Input: arXiv URL / DOI / search query
         │
         ▼
1. Fetch paper metadata
   ├── arXiv API: abstract, title, authors, year
   └── Semantic Scholar API: citation count, semantic_id, venue

         │
         ▼
2. Pull citation graph (1 hop)
   └── Semantic Scholar /paper/{id}/references
       → up to 100 references per paper
       → store each as a papers row (stub if not yet ingested)
       → store citation edges

         │
         ▼
3. Generate embeddings
   └── Gemini gemini-embedding-2-preview
       Input: f"{title}. {abstract}"
       Output: vector(768) → stored in paper_embeddings

         │
         ▼
4. Classify edge types (async, runs after all papers ingested)
   └── Batch 20 citation pairs per gemini-2.5-flash call:
       Prompt: "Classify the relationship for each pair below.
                Return a JSON array of {n} objects with edge_type and confidence."
       Never one call per edge — prevents hitting the 15 RPM free-tier limit

         │
         ▼
5. Emit completion event → WebSocket → frontend re-renders graph

8.1 ADK IngestionAgent
The ingestion pipeline runs inside a Google ADK agent. The arq background worker delegates to it:

```python
from google.adk.agents import Agent
from app.agents.tools.ingest_tools import (
    fetch_arxiv_paper, fetch_semantic_scholar_data,
    generate_paper_embedding, store_paper, store_citation
)

ingestion_agent = Agent(
    name="ingestion_agent",
    model="gemini-2.5-flash",
    instruction="""You are a paper ingestion specialist for LitLens.
Given an arXiv URL and workspace_id, work through these steps in order:
1. fetch_arxiv_paper — title, abstract, authors, year, arxiv_id
2. fetch_semantic_scholar_data — semantic_id, citation_count, references list
3. generate_paper_embedding — 768-dim vector for the paper
4. store_paper — persist all metadata + embedding to DB, add to workspace
5. store_citation — for each reference, create a citation edge
Confirm with a summary of what was stored.""",
    tools=[fetch_arxiv_paper, fetch_semantic_scholar_data,
           generate_paper_embedding, store_paper, store_citation]
)

# arq worker — delegates to the agent
async def ingest_paper(ctx, url: str, workspace_id: str):
    result = await run_agent(ingestion_agent, f"Ingest into workspace {workspace_id}: {url}")
    return result
```

Rate limiting strategy for external APIs:
* Semantic Scholar: 100 req/5min unauthenticated, 1 req/sec with API key (get the key, it's free)
* arXiv: No hard limit but be polite — 3 req/sec max
* Gemini: Batch embed requests — up to 100 texts per call, free tier 1,500 req/day

9. The Two Gap Detection Layers (P3's Piece + Your Algorithm)
9.1 Layer 1 — Citation Gap Detection
def detect_citation_gaps(workspace_id: str, db: Session) -> list[BlindSpot]:
    # Get all papers IN the workspace (papers the user has read)
    workspace_paper_ids = get_workspace_paper_ids(workspace_id)

    # Get all papers CITED BY workspace papers
    cited_paper_ids = get_all_cited_paper_ids(workspace_paper_ids)

    # Find cited papers NOT in the workspace
    gap_paper_ids = cited_paper_ids - set(workspace_paper_ids)

    # Count how many workspace papers cite each gap paper
    citation_freq = Counter()
    for gap_id in gap_paper_ids:
        citing_papers = get_papers_citing(gap_id, within=workspace_paper_ids)
        citation_freq[gap_id] = len(citing_papers)

    # Threshold: cited by ≥2 workspace papers
    blind_spots = [
        BlindSpot(
            paper_id=paper_id,
            gap_type="citation_gap",
            citation_freq=freq,
            cited_by_papers=get_papers_citing(paper_id, within=workspace_paper_ids)
        )
        for paper_id, freq in citation_freq.items()
        if freq >= 2
    ]

    # Rank by citation frequency descending
    return sorted(blind_spots, key=lambda x: x.citation_freq, reverse=True)
Output: "Attention Is All You Need is cited by 8 of your papers. You haven't read it."
9.2 Layer 2 — Semantic Gap Detection
This is the novel algorithm. Citation counting tells you what papers you're missing. Semantic analysis tells you what ideas you're missing.
def detect_semantic_gaps(workspace_id: str, db: Session) -> list[SemanticGap]:

    # Step 1: Get embeddings for all workspace papers (papers user HAS read)
    workspace_embeddings = get_workspace_embeddings(workspace_id)
    # shape: (n_workspace_papers, 768)

    # Step 2: Get embeddings for all cited papers NOT in workspace (candidates)
    gap_candidates = get_citation_gap_papers(workspace_id)
    candidate_embeddings = get_embeddings(gap_candidates)
    # shape: (n_candidates, 768)

    # Step 3: Cluster the CANDIDATE embedding space
    # HDBSCAN handles variable cluster sizes better than k-means for academic papers
    clusterer = HDBSCAN(min_cluster_size=3, metric='cosine')
    cluster_labels = clusterer.fit_predict(candidate_embeddings)
    # Output: each candidate paper assigned to a topic cluster

    # Step 4: For each cluster, measure coverage in workspace papers
    gaps = []
    for cluster_id in set(cluster_labels):
        if cluster_id == -1:
            continue  # HDBSCAN noise points

        cluster_papers = get_papers_in_cluster(cluster_id, gap_candidates, cluster_labels)
        cluster_centroid = np.mean(
            [candidate_embeddings[i] for i in cluster_papers], axis=0
        )

        # Measure how well this cluster is covered by workspace papers
        # Coverage = max cosine similarity between cluster centroid and any workspace paper
        coverage_scores = cosine_similarity(
            cluster_centroid.reshape(1, -1),
            workspace_embeddings
        )
        coverage = float(coverage_scores.max())

        # Low coverage = conceptual blind spot
        if coverage < 0.65:  # tune this threshold with real data
            cluster_label = generate_cluster_label(cluster_papers)  # LLM call
            gaps.append(SemanticGap(
                cluster_label=cluster_label,
                coverage_score=coverage,
                top_papers=rank_papers_in_cluster(cluster_papers),
                why_matters=generate_why_matters(cluster_papers, workspace_id)
            ))

    # Rank by coverage_score ascending (most uncovered first)
    return sorted(gaps, key=lambda x: x.coverage_score)


def label_all_clusters(clusters: list[dict], workspace_titles: list[str]) -> list[dict]:
    # One call for ALL clusters — not one per cluster. Reduces 2N calls to 1.
    cluster_summaries = "\n".join(
        f'Cluster {c["id"]}: {", ".join(p["title"] for p in c["papers"][:5])}'
        for c in clusters
    )
    prompt = f"""A researcher has read: {", ".join(workspace_titles[:5])}

Topic clusters of papers they haven't read:
{cluster_summaries}

For EACH cluster return a 2-4 word label and one-sentence why_matters explanation.
Return JSON array: [{{"cluster_id": 0, "label": "...", "why_matters": "..."}}, ...]
Return only the JSON array."""
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return json.loads(response.text)
Output: "Your papers frequently cite work on Mechanistic Interpretability but you have zero direct coverage of this topic — here are the 3 most important papers to read."

9.3 ADK GapDetectionAgent
Both detection layers are orchestrated by a single ADK agent with tool functions that implement each algorithm step:

```python
from google.adk.agents import Agent
from app.agents.tools.gap_tools import (
    get_workspace_papers, find_citation_gaps, get_candidate_embeddings,
    run_hdbscan_clustering, compute_cluster_coverage,
    generate_cluster_label, generate_why_matters, store_blind_spots
)

gap_detection_agent = Agent(
    name="gap_detection_agent",
    model="gemini-2.5-flash",
    instruction="""You are a research gap detection specialist for LitLens.
Given a workspace_id, run the full pipeline in order:
1. get_workspace_papers — what the researcher has read
2. find_citation_gaps — Layer 1: papers cited ≥2 times but unread
3. get_candidate_embeddings — embeddings for citation gap papers
4. run_hdbscan_clustering — cluster the candidate embedding space
5. compute_cluster_coverage — coverage score per cluster vs workspace
6. For clusters with coverage < 0.65: generate_cluster_label + generate_why_matters
7. store_blind_spots — persist all findings
Return: "Found N citation gaps and M semantic gaps." """,
    tools=[get_workspace_papers, find_citation_gaps, get_candidate_embeddings,
           run_hdbscan_clustering, compute_cluster_coverage,
           generate_cluster_label, generate_why_matters, store_blind_spots]
)
```

10. RAG Query Layer
Query: "what do my papers say about hallucination?"
         │
         ▼
1. Embed the query
   └── Gemini gemini-embedding-2-preview → vector(768)

         │
         ▼
2. Vector similarity search in pgvector
   └── SELECT paper_id, chunk_text, 1 - (embedding <=> query_vec) AS score
       FROM paper_embeddings
       JOIN workspace_papers USING (paper_id)
       WHERE workspace_id = $1
       ORDER BY embedding <=> query_vec
       LIMIT 8

         │
         ▼
3. Build context window
   └── Concatenate top 8 chunks with paper titles as headers
       Keep under 6000 tokens

         │
         ▼
4. Generate answer
   System: "You are a research assistant. Answer only from the provided papers.
            Always cite which paper each claim comes from."
   User:   "{query}\n\nContext:\n{chunks}"
   Model:  gemini-2.5-flash via ResearchAgent (free tier, fast, sufficient)

         │
         ▼
5. Return structured response
   {
     answer: "Your papers discuss hallucination primarily in three contexts...",
     citations: [
       { paper_id, title, chunk_text, relevance_score },
       ...
     ]
   }
Latency target: p95 < 300ms for vector search, < 3s total with LLM generation

10.1 ADK ResearchAgent
The RAG pipeline runs as an ADK agent — the agent decides which papers to retrieve and synthesizes the answer:

```python
from google.adk.agents import Agent
from app.agents.tools.rag_tools import embed_query, semantic_search, get_paper_details

research_agent = Agent(
    name="research_agent",
    model="gemini-2.5-flash",
    instruction="""You are a research assistant for LitLens.
Answer questions grounded exclusively in the user's workspace papers.
1. embed_query — convert the question to a 768-dim vector
2. semantic_search — retrieve the top 8 relevant chunks from the workspace
3. get_paper_details — look up any paper you want to cite
4. Synthesize a clear answer citing papers as [Paper Title]
Never state anything not supported by the retrieved chunks.""",
    tools=[embed_query, semantic_search, get_paper_details]
)
```

10.2 Multi-Agent Orchestrator
A top-level ADK orchestrator routes all requests to the appropriate specialist agent:

```python
from google.adk.agents import Agent

orchestrator = Agent(
    name="litlens_orchestrator",
    model="gemini-2.5-flash",
    instruction="""You are the LitLens orchestrator. Route user requests immediately:
- Paper ingestion (arXiv URLs, DOIs, search queries) → ingestion_agent
- Gap detection and blind spot analysis → gap_detection_agent
- Research questions about workspace papers → research_agent
Delegate immediately — do not attempt to answer yourself.""",
    sub_agents=[ingestion_agent, gap_detection_agent, research_agent]
)
```

Run `adk web` from the backend directory to interactively test all agents during development.

11. Collaboration Layer (Yjs + WebSockets)
How Yjs works in this context
Yjs is a CRDT (Conflict-free Replicated Data Type) library. It means two users can edit the same shared data structure simultaneously and their changes will merge correctly without conflicts — no locking, no "who saved last wins."
In LitLens, Yjs manages:
* Edge type annotations (user A says "extends", user B says "contradicts" → last write wins per edge, tracked)
* Node comments (append-only, always merge correctly)
* Blind spot panel state (which gaps are dismissed, which are starred)
WebSocket server setup (FastAPI)
from fastapi import WebSocket
import ypy_websocket

@app.websocket("/ws/{workspace_id}")
async def websocket_endpoint(websocket: WebSocket, workspace_id: str):
    await websocket.accept()
    user = await authenticate_ws(websocket)

    # Load or create Yjs doc for this workspace
    ydoc = await load_ydoc(workspace_id)

    async with ypy_websocket.WebsocketProvider(ydoc, websocket):
        # Sync runs automatically — ypy_websocket handles the protocol
        try:
            await websocket.wait_for_disconnect()
        finally:
            await save_ydoc_snapshot(workspace_id, ydoc)
Frontend Yjs setup
import * as Y from 'yjs'
import { WebsocketProvider } from 'y-websocket'

const ydoc = new Y.Doc()
const provider = new WebsocketProvider(
  `wss://your-api.your-ecs-domain.com/ws/${workspaceId}`,
  workspaceId,
  ydoc
)

// Shared edge annotations map: edgeKey → { type, annotatedBy, note }
const edgeAnnotations = ydoc.getMap('edge_annotations')

// Shared comments array
const comments = ydoc.getArray('comments')

// Live presence — show who else is viewing
const awareness = provider.awareness
awareness.setLocalStateField('user', { name: currentUser.name, color: randomColor() })

12. Frontend Architecture
Component tree
App
├── AuthProvider (JWT context)
├── WorkspaceProvider (current workspace context)
├── Router
│   ├── /login         → LoginPage
│   ├── /workspace/:id → WorkspacePage
│   │   ├── GraphCanvas          (React Flow)
│   │   │   ├── NodeTooltip      (paper title on hover)
│   │   │   └── EdgeTypeOverlay  (Yjs-synced edge labels)
│   │   ├── PaperDetailPanel     (right sidebar, click a node)
│   │   │   ├── PaperMetadata
│   │   │   ├── NodeComments     (Yjs-synced)
│   │   │   └── RelatedWorkDraft
│   │   ├── BlindSpotPanel       (left sidebar)
│   │   │   ├── CitationGapList
│   │   │   ├── SemanticGapList
│   │   │   └── TeamBlindSpots   (shared gaps across workspace members)
│   │   └── RAGQueryBox          (bottom bar)
│   └── /workspace/:id/settings → WorkspaceSettings (invite members)
React Flow key config
// Node types: PaperNode (default), BlindSpotNode (gap — dashed red border)
// Edge types: color-coded by edge_type (extends=#4ECDC4, contradicts=#FF6B6B dashed, cites=gray)
// Node size mapped to citation_count (min 20px, max 60px via inline style)
// Layout: dagre (hierarchical) or d3-force via @reactflow/layout — switch based on graph size
// Built-ins used: MiniMap, Controls, Background, NodeToolbar (paper title on hover)

const nodeStyle = (clusterColor, citationCount, isBlindSpot) => ({
  background: clusterColor,
  width: Math.max(20, Math.min(60, citationCount / 8)),
  border: isBlindSpot ? '3px dashed #FF6B6B' : undefined,
})

const edgeStyles = {
  extends:     { stroke: '#4ECDC4' },
  contradicts: { stroke: '#FF6B6B', strokeDasharray: '5,5' },
  uses_dataset:{ stroke: '#A78BFA' },
  cites:       { stroke: '#94A3B8' },
}

13. Auth Flow
Register/Login → bcrypt password hash → JWT (15min) + refresh token (7days)
                                           │
                              ┌────────────▼────────────┐
                              │  All API requests need   │
                              │  Authorization: Bearer   │
                              └────────────┬────────────┘
                                           │
                              ┌────────────▼────────────┐
                              │  Token expires →         │
                              │  POST /auth/refresh      │
                              │  → new access_token      │
                              └─────────────────────────┘
Rate limiting via Redis token bucket:
* Free tier: 100 ingestion requests/day, 500 RAG queries/day
* Enforced in FastAPI middleware before hitting any endpoint

14. Build Timeline — Week by Week
Week 1 — Foundation
Goal: All three systems running and talking to each other before writing features.
* FastAPI skeleton with health check endpoint
* PostgreSQL schema from Section 6 — run all migrations
* pgvector extension enabled, paper_embeddings table created
* arXiv API client: fetch paper by URL, return { title, abstract, authors, year }
* Semantic Scholar API client: fetch citations by semantic_id
* React + Vite scaffold with shadcn/ui + Tailwind CSS initialized
* React Flow rendering hardcoded test nodes and edges
* .env contract agreed across backend and frontend
* Google ADK installed; IngestionAgent, GapDetectionAgent, ResearchAgent, and Orchestrator defined with empty tool stubs; `adk web` confirms routing
End of week checkpoint: Paste one arXiv URL → paper metadata appears in database.

Week 2 — Core Pipeline
Goal: Full ingestion end-to-end, graph visible in the browser.
* Full ingestion flow: URL → metadata → citations (1 hop) → embeddings → stored
* Async job queue via Redis + arq (Python async job runner)
* Citation graph endpoint returning nodes + edges
* React Flow rendering real graph data from the API
* Node click → PaperDetailPanel showing title, abstract, authors, link
* Cluster coloring: run k-means on embeddings, assign color per cluster
* Filter controls: year range slider, topic cluster toggle
End of week checkpoint: Paste 5 arXiv links → see a real citation graph with colored clusters.

Week 3 — Blind Spot Engine
Goal: The killer feature working end-to-end.
* Layer 1: Citation gap detection algorithm (Section 9.1)
* Layer 2: Semantic gap detection via HDBSCAN clustering (Section 9.2)
* Cluster auto-labeling via LLM (2-4 word label per cluster)
* why_matters generation via LLM per gap
* BlindSpotPanel UI: two sections (Citation Gaps, Conceptual Gaps)
* Each gap card: paper title, why it's a gap, citation frequency or coverage score
* "Add to workspace" button on each gap card — one click to ingest the missing paper
* Ranked ordering: most critical gaps first
End of week checkpoint: 10 papers ingested → blind spot panel shows meaningful gaps with labels.

Week 4 — AI Layer
Goal: RAG working, edge types classified, related work draft generating.
* RAG query box (Section 10): embed → pgvector search → LLM answer with citations
* Semantic edge typing: classify each citation edge as extends/contradicts/uses_dataset/cites
* Edge type shown as color + label on graph
* Related work draft generator: select a cluster → generate a 2-paragraph related work section
* Auto-generated cluster labels appearing on graph nodes
End of week checkpoint: Type a question → get an answer citing specific papers from your workspace.

Week 5 — Collaboration
Goal: Two users can work in the same workspace simultaneously.
* JWT auth: register, login, refresh token
* Workspace creation + invite by email
* WebSocket server (Section 11)
* Yjs sync: edge annotations, comments
* Live presence indicator (colored dot = teammate is online)
* Shared blind spot panel: gaps visible to all workspace members
* Node comments: anyone in workspace can add/see comments
End of week checkpoint: Two browser windows open to the same workspace → annotations sync in real time.

Week 6 — Production Hardening
Goal: Deployed, stable, measurable.
* Rate limiting middleware (Redis token bucket)
* Error handling: retry logic for arXiv/Semantic Scholar API failures
* p95 latency tracking: log response times per endpoint, store in PostgreSQL
* Docker: Dockerfile + docker-compose for local dev parity
* Deploy FastAPI container to AWS EC2 (t2.micro) — SSH in, run docker-compose up -d
* Swap local PostgreSQL for AWS RDS (same pgvector extension, update connection string)
* Swap local Redis for AWS ElastiCache (update connection string)
* Set up S3 bucket for PDF caching and Yjs snapshots (boto3, ~2 hours)
* Configure SES for workspace invite emails (~1 hour)
* Deploy frontend to Vercel
* GitHub Actions: lint + test on every PR, auto-deploy main to EC2 via SSH + docker-compose
* Environment variable management via AWS SSM Parameter Store (free standard tier)
End of week checkpoint: App is live at a real URL. Someone else can use it without your laptop.

Week 7 — Real Users
Goal: 20-30 researchers using it on their actual lit reviews.
How to get real users as a student:
* USF lab mates doing literature reviews right now — ask directly
* Post in your department Slack/Discord: "I built a tool that finds gaps in your lit review — try it for free, takes 5 minutes"
* Ask one professor to share with their grad students
* Offer to sit with 2-3 researchers and watch them use it (this is gold for fixing UX)
What to track:
* DAU (daily active users)
* Papers ingested per session
* Blind spots surfaced per session
* RAG queries per session
* Which gap cards users click "Add to workspace" on (= gaps they found useful)
End of week checkpoint: 10+ real users have run the app on their actual research. You have at least one quote.

Week 8 — Resume Ready
Goal: The project presents itself.
* Quantify every metric from Week 7
* GitHub README:
    * 30-second demo GIF (record with Loom or QuickTime, convert to GIF)
    * One-sentence description
    * Screenshot of the graph + blind spot panel
    * Tech stack table
    * Local setup instructions (should work in < 5 minutes)
    * Link to live demo
* Write final resume bullet (Section 15)
* Prepare 3-4 technical talking points for interviews (Section 16)

15. Resume Bullet
"Built LitLens, a production-grade research knowledge graph platform — FastAPI on AWS EC2, pgvector on RDS, ElastiCache (Redis), paper artifacts on S3 — detecting literature blind spots via citation gap analysis (Semantic Scholar API) and semantic topic clustering over paper embeddings (HDBSCAN + Gemini gemini-embedding-2-preview), Google ADK multi-agent orchestration (IngestionAgent → GapDetectionAgent → ResearchAgent via Gemini 2.0 Flash), real-time collaborative graph annotation via Yjs CRDTs, and RAG queries grounded in user papers — used by 30+ USF researchers with p95 query latency <300ms"

16. Interview Talking Points
These are the four technical areas where an interviewer will dig in. Prepare 3-5 minutes on each.
16.1 The Semantic Gap Detection Algorithm
"The naive approach is counting citations — if a paper is cited a lot by your papers and you haven't read it, that's a gap. But that only tells you what papers you're missing. I wanted to tell you what ideas you're missing. So I embed all the papers in your citation graph, cluster the embedding space using HDBSCAN, and then measure how much of each topic cluster your actual papers cover. A cluster with high citation frequency but low coverage in your workspace is a conceptual blind spot — you keep citing this area but never directly engaging with it. That's the novel part."
16.2 pgvector vs Qdrant
"I deliberately kept everything in PostgreSQL rather than adding a separate vector database. pgvector gives me vector similarity search as a PostgreSQL extension — I get to use the same database for relational queries and vector search, with joins, transactions, and familiar tooling. The tradeoff is it's slower than Qdrant at very large scale, but for tens of thousands of papers and 30 users, the operational simplicity of one database is worth more than the performance difference."
16.3 Yjs CRDTs for collaboration
"The real-time collaboration problem is hard because two users editing the same graph annotation simultaneously need their changes to merge correctly. I used Yjs, which implements CRDTs — Conflict-free Replicated Data Types. The key property is that no matter what order operations arrive in, they always converge to the same state. For edge type annotations, that means two people can both update the same edge simultaneously and the result is deterministic. I didn't build the CRDT — Yjs does that — but I had to understand the data model well enough to structure the shared document correctly and handle the persistence (saving Yjs snapshots to PostgreSQL so the state survives server restarts)."
16.4 RAG latency optimization
"My target was p95 < 300ms for the vector search component. The main levers were: using an IVFFlat index on pgvector (approximate nearest neighbor, much faster than exact search at the cost of a small accuracy tradeoff), pre-filtering the embedding search to only papers in the current workspace (reducing the search space dramatically), and batching embedding generation at ingestion time so query time never needs to call the embeddings API at query time. The LLM generation step adds 1-2 seconds on top, but I separate the latency reporting so I can show the vector retrieval is fast even when generation is not."
16.5 Google ADK Multi-Agent Architecture
"I structured LitLens as three specialized agents — IngestionAgent, GapDetectionAgent, and ResearchAgent — coordinated by a top-level Orchestrator. I used Google ADK because it provides a clean declarative way to define agents and their tools, built-in sub_agent routing so the orchestrator can delegate without manual intent parsing, and a browser-based test UI (`adk web`) that let me verify the routing before any tool implementations existed. The key architectural decision was keeping all agents stateless — they read and write to the database but carry no in-memory state between calls. That means any agent call can fail and retry safely, which matters when you're doing 5+ sequential API calls in the ingestion pipeline. The GapDetectionAgent is the most interesting because it has to decide which clusters cross the coverage threshold — it's not just a pipeline, it's reasoning over the clustering results before deciding what to store."

17. Metrics That Go On Your Resume
Fill these in after Week 7:
Metric	Target	Actual
Active researchers onboarded	30+	__
Papers ingested total	500+	__
Citations mapped	2000+	__
Blind spots surfaced per session	5-10	__
Conceptual gaps detected (semantic layer)	measurable	__
RAG queries run total	200+	__
p95 vector search latency	<300ms	__
p95 total RAG query latency	<3s	__
18. What Each Part Signals to Interviewers
Feature	What it signals
pgvector + embedding pipeline	You understand vector search and AI infrastructure end-to-end
HDBSCAN semantic gap detection	You can design novel algorithms, not just glue APIs together
Google ADK multi-agent system	You can architect and build production multi-agent AI systems
Yjs CRDTs	You've solved a genuinely hard distributed systems problem
Real users + tracked metrics	You shipped something people actually used and measured it
FastAPI + PostgreSQL + Redis	Standard production backend stack, not toy tutorial code
RAG with citation grounding	Core AI engineering pattern, demonstrated end-to-end
Async job queue (ingestion)	You understand that AI pipelines are slow and need background processing
JWT + rate limiting	You thought about security and abuse, not just the happy path

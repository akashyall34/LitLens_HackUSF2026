# LitLens

**LitLens turns a list of paper URLs into an interactive citation graph that shows you exactly which research topics you haven't read yet.**

Paste a DOI or URL → LitLens ingests the paper, maps its citation network, clusters topics with K-means, and surfaces blind spots your literature review is missing — all in your browser.

> 🚀 **Live app:** https://litlens-research.vercel.app  

---

## Development
- CRDT (multi-user workspace) In Progress...

---

## Media

<img width="2558" height="1342" alt="image1" src="https://github.com/user-attachments/assets/211abfae-ac50-4146-b4a1-c18067895900" />

---

## Demo

<!-- Record a 30-second screen capture with Loom or QuickTime, then convert:
     ffmpeg -i demo.mov -vf fps=10,scale=1200:-1 demo.gif
     Then drop demo.gif into the repo root and uncomment the line below. -->
<!-- ![LitLens Demo](demo.gif) -->

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
│   React + Vite (Vercel CDN)  ←→  Yjs WebSocket (collab)    │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTPS / WSS
┌────────────────────▼────────────────────────────────────────┐
│                    EC2 (Docker)                             │
│  Caddy (TLS termination)                                    │
│    └─► FastAPI (uvicorn)                                    │
│          ├─ /ingest  → arq job queue → Redis               │
│          ├─ /graph   → PostgreSQL + pgvector               │
│          ├─ /gaps    → citation gap + HDBSCAN clustering    │
│          ├─ /rag     → Google Gemini (ADK agent)           │
│          ├─ /edges   → Gemini edge classification          │
│          ├─ /auth    → JWT (access + refresh tokens)       │
│          └─ /ws      → Yjs collaboration + S3 snapshots    │
└──────────┬─────────────────────────────────────────────────┘
           │
    ┌──────┴──────┐──────────────┐──────────────┐
    │             │              │              │
  AWS RDS     Redis (EC2)      AWS S3        AWS SES
 PostgreSQL   job queue +    Yjs snapshots  invite emails
 + pgvector   rate limiting
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, Vite, React Flow, Tailwind CSS, Yjs, Axios |
| **Backend** | FastAPI, Python 3.11, uvicorn, arq (job queue) |
| **Database** | PostgreSQL 16 + pgvector (AWS RDS) |
| **Cache / Queue** | Redis 7 (self-hosted on EC2) |
| **AI** | Google Gemini 2.5 Flash (embeddings, edge classification, RAG) |
| **Clustering** | scikit-learn K-means, HDBSCAN |
| **Auth** | JWT (PyJWT), bcrypt, refresh token rotation |
| **Collaboration** | Yjs CRDTs, ypy-websocket |
| **Infrastructure** | AWS EC2, RDS, S3, SES, SSM Parameter Store |
| **Reverse Proxy** | Caddy (automatic HTTPS via Let's Encrypt) |
| **Frontend Hosting** | Vercel (global CDN) |
| **CI/CD** | GitHub Actions (ruff lint + pytest + SSH deploy) |

---

## Local Setup

**Prerequisites:** Docker Desktop, Node.js 18+, a [Google Gemini API key](https://aistudio.google.com/app/apikey)

```bash
# 1. Clone and configure
git clone https://github.com/akashyall34/LitLens_HackUSF2026.git
cd LitLens_HackUSF2026
cp .env.example .env
# Edit .env and fill in GEMINI_API_KEY (everything else works with defaults)

# 2. Start the backend + database + Redis
docker-compose up --build

# 3. Apply database migrations (in a new terminal)
for f in backend/migrations/*.sql; do
  docker exec -i litlens-postgres psql -U litlens -d litlens < "$f"
done

# 4. Start the frontend
cd frontend && npm install && npm run dev
```

Open **http://localhost:5173** — register an account and paste a paper URL or DOI to get started.

**Per-user workspaces:** new accounts get their own workspace; collaborators join via **Settings → invite email** (join link). QA blind-spot seed data loads for `qatest2@test.com` only.

---

## Project Structure

```
LitLens_HackUSF2026/
├── backend/
│   ├── app/
│   │   ├── routers/          # FastAPI route handlers
│   │   │   ├── auth.py       # register / login / refresh
│   │   │   ├── ingest.py     # paper ingestion (URL + DOI)
│   │   │   ├── graph.py      # citation graph + k-means clusters
│   │   │   ├── gaps.py       # blind spot detection + team coverage
│   │   │   ├── edges.py      # Gemini edge classification
│   │   │   ├── rag.py        # retrieval-augmented generation
│   │   │   └── workspaces.py # workspace management + SES invites
│   │   ├── agents/           # Google ADK agents (RAG, gap detection)
│   │   ├── gaps/             # citation gap algorithm
│   │   ├── workers/          # arq background workers
│   │   ├── auth/             # JWT utilities
│   │   ├── analytics.py      # usage event tracking (US 7.2)
│   │   ├── ws.py             # Yjs WebSocket + S3 persistence
│   │   ├── db.py             # SQLAlchemy session
│   │   └── main.py           # FastAPI app + CORS + middleware
│   ├── migrations/           # SQL schema migrations
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/       # React components
│       ├── lib/
│       │   ├── auth.ts       # Axios + JWT interceptors
│       │   └── collaboration.ts  # Yjs provider
│       └── App.tsx           # Main app + React Flow graph
├── .github/workflows/
│   └── ci-cd.yml             # Lint → Test → Deploy pipeline
├── docker-compose.yml        # Local dev stack
├── docker-compose.prod.yml   # Production EC2 stack
├── Caddyfile                 # HTTPS reverse proxy config
├── ec2-setup.sh              # EC2 first-boot setup script
└── deploy.sh                 # EC2 redeploy script
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Create account (returns `workspace_id`) |
| `POST` | `/auth/login` | Get JWT tokens + `workspace_id` |
| `GET` | `/auth/me` | Current user + primary `workspace_id` |
| `POST` | `/auth/refresh` | Rotate refresh token |
| `POST` | `/workspaces/join` | Redeem invite token (body: `{ token }`) |
| `POST` | `/ingest/url` | Queue paper ingestion by URL |
| `POST` | `/ingest/doi` | Queue paper ingestion by DOI |
| `GET` | `/ingest/status/{job_id}` | Poll ingestion job |
| `GET` | `/graph/{workspace_id}` | Get citation graph nodes + edges |
| `GET` | `/gaps/{workspace_id}` | Get citation + semantic blind spots |
| `POST` | `/gaps/{workspace_id}/detect` | Trigger async gap detection |
| `POST` | `/rag/query` | RAG over workspace (`query`, `workspace_id`, optional `history[]`) |
| `POST` | `/edges/classify` | Classify edge relationships via Gemini |
| `POST` | `/workspaces/{id}/invite` | Send collaborator invite email |
| `WS` | `/ws/{workspace_id}?token=` | Real-time Yjs collaboration |
| `GET` | `/health` | Health check |

---

## Environment Variables

Copy `.env.example` to `.env`. Required variables:

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio API key |
| `JWT_SECRET` | Long random string for signing JWTs |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `S3_BUCKET` | AWS S3 bucket for Yjs snapshots (optional locally) |
| `SES_FROM_EMAIL` | Verified SES email for invites (optional locally) |

---

## CI/CD Pipeline

Every push to `main` automatically:
1. Runs `ruff` lint on the backend
2. Runs `pytest` smoke tests
3. SSHes into the EC2 instance and runs `deploy.sh` (git pull + docker-compose up)

PRs must pass lint + tests before merge.

---

## Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes
4. Push and open a PR — the CI pipeline runs automatically

---

## Hackathon demo checklist

- **Live path:** open the Vercel URL → register a fresh account **or** use `qatest2@test.com` for pre-seeded blind-spot demo data → **Add paper** → graph → **Blind Spots** (citation vs conceptual tabs) → bottom **RAG** thread with a follow-up question → **Settings** invite if showing collaboration.
- **Backup:** 60-second screen recording if Wi‑Fi or API quota fails; mention `GET /health` on the API host for “stack is up.”
- **Honest limitation (post-hackathon):** several routes take `workspace_id` from the client but do not yet assert **workspace membership** on every read (graph/gaps/ingest). Fine for a trusted demo; tighten before a public multi-tenant launch.
- **Secrets:** production `JWT_SECRET`, `GEMINI_API_KEY`, and DB URLs belong in env/SSM — never commit `.env`.

---

## Team

Built at **HackUSF 2026** by two engineers over 7 sprints.

- **E1** — Frontend, core algorithms, RAG/AI layer
- **E2** — AWS infrastructure, backend API, CI/CD

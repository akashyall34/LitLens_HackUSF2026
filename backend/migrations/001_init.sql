CREATE EXTENSION IF NOT EXISTS vector;

-- Users and collaboration
CREATE TABLE IF NOT EXISTS users (
	id UUID PRIMARY KEY,
	email TEXT NOT NULL UNIQUE,
	full_name TEXT,
	created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workspaces (
	id UUID PRIMARY KEY,
	name TEXT NOT NULL,
	owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
	created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workspace_members (
	workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
	user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
	role TEXT NOT NULL DEFAULT 'member',
	joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	PRIMARY KEY (workspace_id, user_id)
);

-- Papers and citations
CREATE TABLE IF NOT EXISTS papers (
	id UUID PRIMARY KEY,
	title TEXT NOT NULL,
	abstract TEXT,
	year INT,
	arxiv_id TEXT,
	doi TEXT,
	semantic_scholar_id TEXT,
	source_url TEXT,
	citation_count INT NOT NULL DEFAULT 0,
	venue TEXT,
	authors JSONB NOT NULL DEFAULT '[]'::jsonb,
	created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workspace_papers (
	workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
	paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
	added_by UUID REFERENCES users(id) ON DELETE SET NULL,
	added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	PRIMARY KEY (workspace_id, paper_id)
);

CREATE TABLE IF NOT EXISTS citations (
	citing_paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
	cited_paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
	edge_type TEXT NOT NULL DEFAULT 'cites',
	confidence DOUBLE PRECISION NOT NULL DEFAULT 1.0,
	created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	PRIMARY KEY (citing_paper_id, cited_paper_id)
);

-- Vector embeddings
CREATE TABLE IF NOT EXISTS paper_embeddings (
	paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
	chunk_index INT NOT NULL DEFAULT 0,
	embedding vector(768) NOT NULL,
	created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	PRIMARY KEY (paper_id, chunk_index)
);

-- Blind spots and annotations
CREATE TABLE IF NOT EXISTS blind_spots (
	id UUID PRIMARY KEY,
	workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
	gap_type TEXT NOT NULL,
	paper_id UUID REFERENCES papers(id) ON DELETE SET NULL,
	cluster_label TEXT,
	coverage_score DOUBLE PRECISION,
	citation_freq INT,
	why_matters TEXT,
	payload JSONB,
	created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS node_comments (
	id UUID PRIMARY KEY,
	workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
	paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
	author_id UUID REFERENCES users(id) ON DELETE SET NULL,
	content TEXT NOT NULL,
	created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS edge_annotations (
	id UUID PRIMARY KEY,
	workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
	citing_paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
	cited_paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
	edge_type TEXT NOT NULL,
	note TEXT,
	annotated_by UUID REFERENCES users(id) ON DELETE SET NULL,
	created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	UNIQUE (workspace_id, citing_paper_id, cited_paper_id)
);

-- Useful indexes
CREATE INDEX IF NOT EXISTS idx_workspaces_owner_id ON workspaces(owner_id);
CREATE INDEX IF NOT EXISTS idx_workspace_members_user_id ON workspace_members(user_id);
CREATE INDEX IF NOT EXISTS idx_workspace_papers_workspace_id ON workspace_papers(workspace_id);
CREATE INDEX IF NOT EXISTS idx_workspace_papers_paper_id ON workspace_papers(paper_id);
CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year);
CREATE INDEX IF NOT EXISTS idx_papers_arxiv_id ON papers(arxiv_id);
CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi);
CREATE INDEX IF NOT EXISTS idx_papers_semantic_scholar_id ON papers(semantic_scholar_id);
CREATE INDEX IF NOT EXISTS idx_citations_cited_paper_id ON citations(cited_paper_id);
CREATE INDEX IF NOT EXISTS idx_blind_spots_workspace_id ON blind_spots(workspace_id);
CREATE INDEX IF NOT EXISTS idx_blind_spots_gap_type ON blind_spots(gap_type);
CREATE INDEX IF NOT EXISTS idx_node_comments_workspace_paper ON node_comments(workspace_id, paper_id);
CREATE INDEX IF NOT EXISTS idx_edge_annotations_workspace ON edge_annotations(workspace_id);

-- Vector index for semantic search
CREATE INDEX IF NOT EXISTS idx_paper_embeddings_ivfflat
	ON paper_embeddings USING ivfflat (embedding vector_cosine_ops)
	WITH (lists = 100);
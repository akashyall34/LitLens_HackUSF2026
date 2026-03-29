import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Double, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text, nullable=False, unique=True)
    full_name = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class Paper(Base):
    __tablename__ = "papers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    abstract = Column(Text)
    year = Column(Integer)
    doi = Column(Text)
    semantic_scholar_id = Column(Text)
    source_url = Column(Text)
    citation_count = Column(Integer, nullable=False, default=0)
    venue = Column(Text)
    authors = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class PaperEmbedding(Base):
    __tablename__ = "paper_embeddings"

    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True)
    chunk_index = Column(Integer, nullable=False, default=0, primary_key=True)
    embedding = Column(Vector(768), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class Citation(Base):
    __tablename__ = "citations"

    citing_paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True)
    cited_paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True)
    edge_type = Column(Text, nullable=False, default="cites")
    confidence = Column(Double, nullable=False, default=1.0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class WorkspacePaper(Base):
    __tablename__ = "workspace_papers"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True)
    added_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    added_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

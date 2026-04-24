"""Pydantic schemas for API request/response models."""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


# ── Ingestion ───────────────────────────────────────────────────────────────

class IngestGitHubRequest(BaseModel):
    """Request to ingest a GitHub repository."""
    repo_url: str = Field(..., description="GitHub repository URL")
    branch: str = Field(default="main", description="Branch to clone")


class IngestResponse(BaseModel):
    """Response after ingestion completes."""
    project_id: str
    total_files: int
    parsed_files: int
    total_functions: int
    total_classes: int
    total_imports: int
    status: str = "completed"


# ── Query ───────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    """Chat query request."""
    project_id: str
    question: str
    include_graph: bool = Field(default=True, description="Include dependency context")
    top_k: int = Field(default=5, description="Number of code chunks to retrieve")


class CodeReference(BaseModel):
    """A reference to a specific code location."""
    file_path: str
    start_line: int
    end_line: int
    content: str
    relevance_score: float = 0.0


class QueryResponse(BaseModel):
    """Chat query response."""
    answer: str
    references: list[CodeReference] = []
    graph_context: list[str] = []


# ── Graph ───────────────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    """A node in the dependency graph."""
    id: str
    label: str
    type: str  # "file", "function", "class"
    file_path: Optional[str] = None
    line_number: Optional[int] = None


class GraphEdge(BaseModel):
    """An edge in the dependency graph."""
    source: str
    target: str
    type: str  # "imports", "calls", "inherits"


class GraphData(BaseModel):
    """Full graph data for visualization."""
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# ── Files ───────────────────────────────────────────────────────────────────

class FileNode(BaseModel):
    """Represents a file or directory in the tree."""
    name: str
    path: str
    type: str  # "file" or "directory"
    children: list[FileNode] = []
    language: Optional[str] = None
    size: Optional[int] = None


class FileContent(BaseModel):
    """File content with metadata."""
    path: str
    content: str
    language: str
    functions: list[dict] = []
    classes: list[dict] = []
    imports: list[str] = []


# ── Projects ────────────────────────────────────────────────────────────────

class ProjectInfo(BaseModel):
    """Project metadata."""
    project_id: str
    name: str
    source: str  # "github" or "upload"
    total_files: int
    languages: list[str]
    status: str


class ProjectList(BaseModel):
    """List of ingested projects."""
    projects: list[ProjectInfo]

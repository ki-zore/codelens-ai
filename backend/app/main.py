"""
AI Codebase Debugging & Knowledge Assistant — FastAPI Backend

Main application entry point.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import ingest, query, files

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("🚀 Starting AI Codebase Assistant...")
    logger.info(f"   LLM Model: {settings.llm_model}")
    logger.info(f"   Embedding Model: {settings.embedding_model}")
    logger.info(f"   Repos Dir: {settings.repos_dir}")
    logger.info(f"   FAISS Dir: {settings.faiss_dir}")
    yield
    logger.info("👋 Shutting down AI Codebase Assistant")


app = FastAPI(
    title="AI Codebase Debugging & Knowledge Assistant",
    description=(
        "A system that ingests codebases, builds structural + semantic understanding, "
        "and allows developers to query, debug, and explore using natural language."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(ingest.router)
app.include_router(query.router)
app.include_router(files.router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "name": "AI Codebase Assistant",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    from app.services.vector_store import vector_store, FAISS_AVAILABLE, ST_AVAILABLE

    return {
        "status": "healthy",
        "faiss_available": FAISS_AVAILABLE,
        "sentence_transformers_available": ST_AVAILABLE,
        "llm_model": settings.llm_model,
        "embedding_model": settings.embedding_model,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )

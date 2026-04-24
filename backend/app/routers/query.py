"""
Query API endpoints.

Handles chat queries with streaming and non-streaming responses.
"""

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import QueryRequest, QueryResponse
from app.services.query_engine import query_engine
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/query", tags=["Query"])


@router.post("/", response_model=QueryResponse)
async def query_codebase(request: QueryRequest):
    """Query a codebase with a natural language question."""
    if not vector_store.has_index(request.project_id):
        raise HTTPException(
            status_code=404,
            detail=f"No index found for project {request.project_id}"
        )

    try:
        result = await query_engine.query(
            project_id=request.project_id,
            question=request.question,
            top_k=request.top_k,
            include_graph=request.include_graph,
        )
        return QueryResponse(**result)
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def query_codebase_stream(request: QueryRequest):
    """
    Query a codebase with streaming response.

    Returns a stream of JSON lines:
    - {"type": "text", "content": "..."} - text chunks
    - {"type": "references", "references": [...]} - code references
    - {"type": "done"} - stream complete
    """
    if not vector_store.has_index(request.project_id):
        raise HTTPException(
            status_code=404,
            detail=f"No index found for project {request.project_id}"
        )

    async def event_generator():
        try:
            async for chunk in query_engine.query_stream(
                project_id=request.project_id,
                question=request.question,
                top_k=request.top_k,
                include_graph=request.include_graph,
            ):
                yield chunk
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield json.dumps({"type": "error", "content": str(e)}) + "\n"

    return StreamingResponse(
        event_generator(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/search")
async def search_code(project_id: str, query: str, top_k: int = 10):
    """
    Semantic search for code without LLM generation.
    Returns raw search results.
    """
    if not vector_store.has_index(project_id):
        raise HTTPException(
            status_code=404,
            detail=f"No index found for project {project_id}"
        )

    results = vector_store.search(project_id, query, top_k=top_k)
    return {"results": results, "total": len(results)}

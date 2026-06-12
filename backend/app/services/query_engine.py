"""
Query engine that combines RAG (vector search) and LLM generation for answers.
"""

import logging
from typing import AsyncGenerator

from app.services.vector_store import vector_store
from app.services.llm import llm_service

logger = logging.getLogger(__name__)


class QueryEngine:
    """
    Orchestrates the query pipeline:
    1. Retrieve relevant code chunks via vector search
    2. Enrich context with dependency graph traversal
    3. Send enriched context to LLM for answer generation
    """

    async def query(self, project_id: str, question: str,
                    top_k: int = 5) -> dict:
        """
        Answer a question about a codebase.

        Args:
            project_id: Project to query
            question: Natural language question
            top_k: Number of code chunks to retrieve

        Returns:
            Dict with answer and references
        """
        # Step 1: Retrieve relevant code via vector search
        code_chunks = vector_store.search(project_id, question, top_k=top_k)

        # Step 2: Generate answer with LLM
        answer = await llm_service.generate_response(
            question=question,
            code_context=code_chunks,
        )

        # Build references
        references = [
            {
                "file_path": c["file_path"],
                "start_line": c["start_line"],
                "end_line": c["end_line"],
                "content": c["content"][:500],  # Truncate for response
                "relevance_score": c.get("relevance_score", 0),
            }
            for c in code_chunks
        ]

        return {
            "answer": answer,
            "references": references,
        }

    async def query_stream(self, project_id: str, question: str,
                           top_k: int = 5) -> AsyncGenerator[str, None]:
        """
        Stream an answer to a question about a codebase.

        Yields chunks of the response as they are generated.
        Also yields a final JSON chunk with references.
        """
        import json

        # Step 1: Retrieve relevant code
        code_chunks = vector_store.search(project_id, question, top_k=top_k)

        # Step 2: Stream LLM response
        async for text_chunk in llm_service.generate_response_stream(
            question=question,
            code_context=code_chunks,
        ):
            yield json.dumps({"type": "text", "content": text_chunk}) + "\n"

        # Send references as final chunk
        references = [
            {
                "file_path": c["file_path"],
                "start_line": c["start_line"],
                "end_line": c["end_line"],
                "content": c["content"][:300],
                "relevance_score": c.get("relevance_score", 0),
            }
            for c in code_chunks
        ]

        yield json.dumps({
            "type": "references",
            "references": references,
        }) + "\n"

        yield json.dumps({"type": "done"}) + "\n"


# Singleton instance
query_engine = QueryEngine()

"""
Query engine that combines RAG (vector search) with
graph traversal and LLM generation for rich answers.
"""

import logging
from typing import AsyncGenerator

from app.services.vector_store import vector_store
from app.services.graph_builder import graph_builder
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
                    top_k: int = 5, include_graph: bool = True) -> dict:
        """
        Answer a question about a codebase.

        Args:
            project_id: Project to query
            question: Natural language question
            top_k: Number of code chunks to retrieve
            include_graph: Whether to include dependency context

        Returns:
            Dict with answer, references, and graph context
        """
        # Step 1: Retrieve relevant code via vector search
        code_chunks = vector_store.search(project_id, question, top_k=top_k)

        # Step 2: Enrich with graph context
        graph_context = []
        if include_graph and code_chunks:
            for chunk in code_chunks[:3]:  # Top 3 files
                file_path = chunk.get("file_path", "")
                related = graph_builder.get_related_context(
                    project_id, file_path, depth=2
                )
                graph_context.extend(related)

        # Step 3: Generate answer with LLM
        answer = await llm_service.generate_response(
            question=question,
            code_context=code_chunks,
            graph_context=graph_context,
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
            "graph_context": list(set(graph_context))[:20],
        }

    async def query_stream(self, project_id: str, question: str,
                           top_k: int = 5,
                           include_graph: bool = True) -> AsyncGenerator[str, None]:
        """
        Stream an answer to a question about a codebase.

        Yields chunks of the response as they are generated.
        Also yields a final JSON chunk with references.
        """
        import json

        # Step 1: Retrieve relevant code
        code_chunks = vector_store.search(project_id, question, top_k=top_k)

        # Step 2: Enrich with graph context
        graph_context = []
        if include_graph and code_chunks:
            for chunk in code_chunks[:3]:
                file_path = chunk.get("file_path", "")
                related = graph_builder.get_related_context(
                    project_id, file_path, depth=2
                )
                graph_context.extend(related)

        # Step 3: Stream LLM response
        async for text_chunk in llm_service.generate_response_stream(
            question=question,
            code_context=code_chunks,
            graph_context=graph_context,
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
            "graph_context": list(set(graph_context))[:20],
        }) + "\n"

        yield json.dumps({"type": "done"}) + "\n"


# Singleton instance
query_engine = QueryEngine()

"""
LLM integration service for code understanding and question answering.

Supports Google Gemini models with streaming responses.
"""

import logging
from typing import AsyncGenerator, Optional

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from app.config import settings

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an expert AI code assistant specialized in understanding, debugging, and explaining codebases. You have access to the following context about a codebase:

1. **Code Chunks**: Relevant code snippets retrieved via semantic search
2. **Dependency Graph**: Structural relationships between files, functions, and classes

Your responsibilities:
- Answer questions about the codebase accurately
- Explain code behavior, patterns, and architecture
- Identify potential bugs, performance issues, and security concerns
- Suggest improvements and best practices
- Trace code flows and dependencies

Guidelines:
- Reference specific files and line numbers when possible
- Use code blocks with syntax highlighting
- Be concise but thorough
- If you're not sure about something, say so
- Structure your response with headers and bullet points for clarity
- When explaining code flow, trace through the dependency chain
"""


class LLMService:
    """Service for interacting with Gemini APIs."""

    def __init__(self):
        self._initialized = False

    def _ensure_initialized(self):
        """Initialize the Gemini client if not already done."""
        if not self._initialized:
            if not settings.gemini_api_key:
                logger.error("GEMINI_API_KEY is not set")
                return
            genai.configure(api_key=settings.gemini_api_key)
            self._initialized = True

    async def generate_response(
        self,
        question: str,
        code_context: list[dict],
        graph_context: list[str],
        model_name: Optional[str] = None,
    ) -> str:
        """
        Generate a response to a code question.

        Args:
            question: User's question
            code_context: Retrieved code chunks
            graph_context: Dependency graph relationships
            model_name: Gemini model to use (defaults to config)

        Returns:
            Generated response text
        """
        self._ensure_initialized()
        prompt = self._build_prompt(question, code_context, graph_context)

        try:
            model = genai.GenerativeModel(
                model_name=(model_name or settings.llm_model).replace("models/", ""),
                system_instruction=SYSTEM_PROMPT
            )
            response = await model.generate_content_async(
                prompt,
                generation_config=GenerationConfig(
                    temperature=0.1,
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return f"Error generating response: {str(e)}"

    async def generate_response_stream(
        self,
        question: str,
        code_context: list[dict],
        graph_context: list[str],
        model_name: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a response to a code question.

        Yields chunks of the response as they are generated.
        """
        self._ensure_initialized()
        prompt = self._build_prompt(question, code_context, graph_context)

        try:
            model = genai.GenerativeModel(
                model_name=(model_name or settings.llm_model).replace("models/", ""),
                system_instruction=SYSTEM_PROMPT
            )
            stream = await model.generate_content_async(
                prompt,
                generation_config=GenerationConfig(
                    temperature=0.1,
                ),
                stream=True
            )

            async for chunk in stream:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"LLM streaming error: {e}")
            yield f"Error: {str(e)}"

    def _build_prompt(self, question: str, code_context: list[dict],
                      graph_context: list[str]) -> str:
        """Build the prompt with code and graph context."""
        sections = []

        # Code context
        if code_context:
            sections.append("## Relevant Code\n")
            for i, chunk in enumerate(code_context, 1):
                score = chunk.get("relevance_score", 0)
                sections.append(
                    f"### [{i}] {chunk['file_path']} "
                    f"(lines {chunk['start_line']}-{chunk['end_line']}, "
                    f"relevance: {score:.2f})\n"
                    f"```\n{chunk['content']}\n```\n"
                )

        # Graph context
        if graph_context:
            sections.append("## Dependency Relationships\n")
            for rel in graph_context[:20]:  # Limit to avoid token overflow
                sections.append(f"- {rel}")
            sections.append("")

        # Question
        sections.append(f"## Question\n{question}")

        return "\n".join(sections)


# Singleton instance
llm_service = LLMService()

"""
Code parser service using Tree-sitter for AST parsing,
with regex-based fallback for unsupported languages.
"""

import logging
from typing import Optional

from app.utils.code_utils import (
    extract_functions_simple,
    extract_classes_simple,
    extract_imports_simple,
    extract_function_calls,
)
from app.utils.file_utils import get_language

logger = logging.getLogger(__name__)

# Try to import tree-sitter; fall back gracefully
try:
    import tree_sitter
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    logger.warning("tree-sitter not available; using regex-based parsing")


class ParseResult:
    """Result of parsing a single file."""

    def __init__(self, file_path: str, language: str):
        self.file_path = file_path
        self.language = language
        self.functions: list[dict] = []
        self.classes: list[dict] = []
        self.imports: list[str] = []
        self.function_calls: list[str] = []
        self.errors: list[str] = []

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "language": self.language,
            "functions": self.functions,
            "classes": self.classes,
            "imports": self.imports,
            "function_calls": self.function_calls,
            "errors": self.errors,
        }


class CodeParser:
    """
    Parses source code files to extract structural information.

    Uses Tree-sitter when available for accurate AST parsing,
    falls back to regex-based parsing otherwise.
    """

    def __init__(self):
        self._ts_parsers: dict = {}
        self._init_tree_sitter()

    def _init_tree_sitter(self):
        """Initialize tree-sitter parsers for supported languages."""
        if not TREE_SITTER_AVAILABLE:
            return

        # Tree-sitter language modules need to be installed separately
        # We'll use regex fallback for now and can add TS languages later
        logger.info("Tree-sitter available. Using regex-based parsing for MVP.")

    def parse_file(self, file_path: str, content: str) -> ParseResult:
        """
        Parse a source file and extract structural information.

        Args:
            file_path: Path to the source file
            content: File content as string

        Returns:
            ParseResult with extracted functions, classes, imports, calls
        """
        language = get_language(file_path) or "unknown"
        result = ParseResult(file_path, language)

        if not content or not content.strip():
            return result

        try:
            # Extract structural elements
            result.functions = extract_functions_simple(content, language)
            result.classes = extract_classes_simple(content, language)
            result.imports = extract_imports_simple(content, language)
            result.function_calls = extract_function_calls(content, language)

            logger.debug(
                f"Parsed {file_path}: {len(result.functions)} functions, "
                f"{len(result.classes)} classes, {len(result.imports)} imports"
            )
        except Exception as e:
            result.errors.append(str(e))
            logger.error(f"Error parsing {file_path}: {e}")

        return result

    def parse_files(self, files: list[tuple[str, str]]) -> list[ParseResult]:
        """
        Parse multiple files.

        Args:
            files: List of (file_path, content) tuples

        Returns:
            List of ParseResult objects
        """
        results = []
        for file_path, content in files:
            result = self.parse_file(file_path, content)
            results.append(result)
        return results


# Singleton instance
parser = CodeParser()

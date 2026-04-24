"""Utility functions for file operations."""

import os
from pathlib import Path
from typing import Optional

# Supported programming languages and their extensions
LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".r": "r",
    ".R": "r",
    ".sql": "sql",
    ".sh": "bash",
    ".bash": "bash",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".xml": "xml",
    ".md": "markdown",
    ".toml": "toml",
}

# Directories to skip during ingestion
SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "env",
    ".env", "dist", "build", ".next", ".nuxt", "vendor", ".idea",
    ".vscode", "target", "bin", "obj", ".tox", ".pytest_cache",
    ".mypy_cache", "coverage", ".coverage", "htmlcov", "egg-info",
}

# Files to skip
SKIP_FILES = {
    ".DS_Store", "Thumbs.db", ".gitignore", ".gitattributes",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "Pipfile.lock", "poetry.lock", "composer.lock",
}

# Maximum file size to process (500KB)
MAX_FILE_SIZE = 500 * 1024


def get_language(file_path: str) -> Optional[str]:
    """Get the programming language based on file extension."""
    ext = Path(file_path).suffix.lower()
    return LANGUAGE_MAP.get(ext)


def should_process_file(file_path: str) -> bool:
    """Check if a file should be processed during ingestion."""
    path = Path(file_path)

    # Skip hidden files
    if path.name.startswith("."):
        return False

    # Skip files in skip list
    if path.name in SKIP_FILES:
        return False

    # Skip non-code files
    if get_language(file_path) is None:
        return False

    # Skip large files
    try:
        if path.stat().st_size > MAX_FILE_SIZE:
            return False
    except OSError:
        return False

    return True


def should_skip_directory(dir_name: str) -> bool:
    """Check if a directory should be skipped during traversal."""
    return dir_name in SKIP_DIRS or dir_name.startswith(".")


def collect_files(repo_path: str) -> list[str]:
    """Recursively collect all processable files from a directory."""
    files = []
    for root, dirs, filenames in os.walk(repo_path):
        # Filter out directories to skip (modifies dirs in-place)
        dirs[:] = [d for d in dirs if not should_skip_directory(d)]

        for filename in filenames:
            file_path = os.path.join(root, filename)
            if should_process_file(file_path):
                files.append(file_path)

    return sorted(files)


def get_relative_path(file_path: str, base_path: str) -> str:
    """Get the relative path of a file from the base directory."""
    return os.path.relpath(file_path, base_path)


def read_file_safe(file_path: str) -> Optional[str]:
    """Safely read a file's content, returning None on error."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None

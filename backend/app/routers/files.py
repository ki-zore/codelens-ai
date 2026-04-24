"""
File browsing API endpoints.

Provides file tree and content for the file explorer.
"""

import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.models.schemas import FileNode, FileContent
from app.services.ingestion import project_store, ingestion_service
from app.utils.file_utils import get_language, read_file_safe, should_skip_directory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/files", tags=["Files"])


@router.get("/{project_id}/tree")
async def get_file_tree(project_id: str):
    """Get the file tree for a project."""
    project = project_store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    repo_path = project.get("repo_path")
    if not repo_path or not os.path.exists(repo_path):
        raise HTTPException(status_code=404, detail="Project files not found")

    tree = _build_file_tree(repo_path, repo_path)
    return tree


@router.get("/{project_id}/content/{file_path:path}")
async def get_file_content(project_id: str, file_path: str):
    """Get the content of a specific file."""
    project = project_store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    repo_path = project.get("repo_path")
    if not repo_path:
        raise HTTPException(status_code=404, detail="Project files not found")

    full_path = os.path.join(repo_path, file_path)

    # Security: prevent path traversal
    if not os.path.abspath(full_path).startswith(os.path.abspath(repo_path)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    content = read_file_safe(full_path)
    if content is None:
        raise HTTPException(status_code=500, detail="Could not read file")

    language = get_language(full_path) or "text"

    # Get parse results for this file
    parse_results = ingestion_service.get_parse_results(project_id)
    file_info = parse_results.get(file_path, {})

    return FileContent(
        path=file_path,
        content=content,
        language=language,
        functions=file_info.get("functions", []),
        classes=file_info.get("classes", []),
        imports=file_info.get("imports", []),
    )


def _build_file_tree(dir_path: str, base_path: str) -> dict:
    """Recursively build a file tree structure."""
    name = os.path.basename(dir_path) or dir_path
    rel_path = os.path.relpath(dir_path, base_path)

    if os.path.isfile(dir_path):
        language = get_language(dir_path)
        size = os.path.getsize(dir_path)
        return {
            "name": name,
            "path": rel_path if rel_path != "." else name,
            "type": "file",
            "language": language,
            "size": size,
            "children": [],
        }

    children = []
    try:
        entries = sorted(os.listdir(dir_path))

        # Directories first, then files
        dirs = []
        files = []
        for entry in entries:
            full_entry = os.path.join(dir_path, entry)
            if os.path.isdir(full_entry):
                if not should_skip_directory(entry):
                    dirs.append(entry)
            else:
                files.append(entry)

        for d in dirs:
            child_tree = _build_file_tree(os.path.join(dir_path, d), base_path)
            children.append(child_tree)

        for f in files:
            child_tree = _build_file_tree(os.path.join(dir_path, f), base_path)
            children.append(child_tree)

    except PermissionError:
        pass

    return {
        "name": name,
        "path": rel_path if rel_path != "." else "",
        "type": "directory",
        "children": children,
    }

"""
Repository ingestion service.

Handles cloning GitHub repos, processing uploaded ZIPs,
parsing files, generating embeddings, and building graphs.
"""

import json
import logging
import os
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Optional

from app.config import settings
from app.services.parser import parser, ParseResult
from app.services.vector_store import vector_store
from app.services.graph_builder import graph_builder
from app.utils.file_utils import collect_files, get_language, read_file_safe, get_relative_path
from app.utils.code_utils import chunk_code

logger = logging.getLogger(__name__)

# Try to import gitpython
try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    logger.warning("GitPython not available; GitHub cloning disabled")


class ProjectStore:
    """Simple JSON-based project metadata store."""

    def __init__(self):
        self._projects: dict[str, dict] = {}
        self._load()

    def _store_path(self) -> Path:
        return settings.faiss_path / "projects.json"

    def _load(self):
        path = self._store_path()
        if path.exists():
            with open(path, "r") as f:
                self._projects = json.load(f)

    def _save(self):
        settings.faiss_path.mkdir(parents=True, exist_ok=True)
        with open(self._store_path(), "w") as f:
            json.dump(self._projects, f, indent=2)

    def add(self, project_id: str, info: dict):
        self._projects[project_id] = info
        self._save()

    def get(self, project_id: str) -> Optional[dict]:
        return self._projects.get(project_id)

    def list_all(self) -> list[dict]:
        return [
            {**v, "project_id": k}
            for k, v in self._projects.items()
        ]

    def delete(self, project_id: str):
        self._projects.pop(project_id, None)
        self._save()


project_store = ProjectStore()


class IngestionService:
    """
    Handles full codebase ingestion pipeline:
    1. Clone / Extract source code
    2. Parse files for structural info
    3. Generate embeddings and build vector index
    4. Build dependency graph
    """

    async def ingest_github(self, repo_url: str, branch: str = "main") -> dict:
        """
        Ingest a GitHub repository.

        Args:
            repo_url: GitHub repository URL
            branch: Branch to clone

        Returns:
            Ingestion result dict
        """
        if not GIT_AVAILABLE:
            raise RuntimeError("GitPython not installed. Cannot clone repos.")

        project_id = str(uuid.uuid4())[:8]
        repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        repo_path = settings.repos_path / project_id

        logger.info(f"Cloning {repo_url} (branch: {branch}) to {repo_path}")

        try:
            git.Repo.clone_from(
                repo_url,
                str(repo_path),
                branch=branch,
                depth=1,  # Shallow clone
            )
        except Exception as e:
            raise RuntimeError(f"Failed to clone repository: {e}")

        result = await self._process_directory(project_id, str(repo_path))
        result["name"] = repo_name
        result["source"] = "github"
        result["repo_url"] = repo_url

        project_store.add(project_id, result)
        return result

    async def ingest_zip(self, file_path: str, original_name: str) -> dict:
        """
        Ingest a ZIP file upload.

        Args:
            file_path: Path to the uploaded ZIP file
            original_name: Original filename

        Returns:
            Ingestion result dict
        """
        project_id = str(uuid.uuid4())[:8]
        extract_path = settings.repos_path / project_id

        logger.info(f"Extracting ZIP to {extract_path}")

        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                zf.extractall(str(extract_path))
        except Exception as e:
            raise RuntimeError(f"Failed to extract ZIP: {e}")

        # If ZIP contains a single top-level directory, use that
        contents = list(extract_path.iterdir())
        if len(contents) == 1 and contents[0].is_dir():
            actual_path = str(contents[0])
        else:
            actual_path = str(extract_path)

        result = await self._process_directory(project_id, actual_path)
        result["name"] = original_name.replace(".zip", "")
        result["source"] = "upload"

        project_store.add(project_id, result)
        return result

    async def _process_directory(self, project_id: str, dir_path: str) -> dict:
        """
        Process a directory of source code:
        1. Collect files
        2. Parse each file
        3. Build embeddings index
        4. Build dependency graph
        """
        # Step 1: Collect files
        files = collect_files(dir_path)
        logger.info(f"Found {len(files)} processable files")

        if not files:
            return {
                "project_id": project_id,
                "total_files": 0,
                "parsed_files": 0,
                "total_functions": 0,
                "total_classes": 0,
                "total_imports": 0,
                "languages": [],
                "status": "empty",
            }

        # Step 2: Read and parse files
        file_contents = []
        for fp in files:
            content = read_file_safe(fp)
            if content:
                file_contents.append((fp, content))

        parse_results = parser.parse_files(file_contents)

        # Gather stats
        total_functions = sum(len(r.functions) for r in parse_results)
        total_classes = sum(len(r.classes) for r in parse_results)
        total_imports = sum(len(r.imports) for r in parse_results)
        languages = list(set(r.language for r in parse_results if r.language != "unknown"))

        # Step 3: Chunk code and build vector index
        all_chunks = []
        for fp, content in file_contents:
            rel_path = get_relative_path(fp, dir_path)
            chunks = chunk_code(content, rel_path)
            all_chunks.extend(chunks)

        logger.info(f"Generated {len(all_chunks)} code chunks")

        if all_chunks:
            try:
                vector_store.build_index(project_id, all_chunks)
            except Exception as e:
                logger.error(f"Failed to build vector index: {e}")

        # Step 4: Build dependency graph
        try:
            graph_builder.build_graph(project_id, parse_results, dir_path)
        except Exception as e:
            logger.error(f"Failed to build graph: {e}")

        # Save parse results for later use
        self._save_parse_results(project_id, parse_results, dir_path)

        result = {
            "project_id": project_id,
            "total_files": len(files),
            "parsed_files": len(parse_results),
            "total_functions": total_functions,
            "total_classes": total_classes,
            "total_imports": total_imports,
            "languages": languages,
            "status": "completed",
            "repo_path": dir_path,
        }

        logger.info(f"Ingestion complete: {result}")
        return result

    def _save_parse_results(self, project_id: str, results: list[ParseResult],
                            base_path: str):
        """Save parse results to disk for file browsing."""
        data_dir = settings.faiss_path / project_id
        data_dir.mkdir(parents=True, exist_ok=True)

        data = {}
        for r in results:
            rel_path = get_relative_path(r.file_path, base_path)
            data[rel_path] = r.to_dict()
            data[rel_path]["file_path"] = rel_path

        with open(data_dir / "parse_results.json", "w") as f:
            json.dump(data, f, indent=2)

    def get_parse_results(self, project_id: str) -> dict:
        """Load parse results from disk."""
        path = settings.faiss_path / project_id / "parse_results.json"
        if path.exists():
            with open(path, "r") as f:
                return json.load(f)
        return {}

    def delete_project(self, project_id: str):
        """Delete a project and all associated data."""
        import shutil
        import time

        def remove_readonly(func, path, excinfo):
            os.chmod(path, 0o777)
            func(path)

        # 1. Delete index and graph first (releases memory)
        try:
            vector_store.delete_index(project_id)
        except Exception as e:
            logger.error(f"Error deleting index for {project_id}: {e}")

        # 2. Delete repo files
        repo_path = settings.repos_path / project_id
        if repo_path.exists():
            try:
                # Small delay to let OS release file handles
                shutil.rmtree(str(repo_path), onerror=remove_readonly)
            except Exception as e:
                logger.error(f"Error deleting repo path {repo_path}: {e}")

        # 3. Delete from store last
        project_store.delete(project_id)



# Singleton instance
ingestion_service = IngestionService()

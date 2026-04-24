"""
Embedding generation and FAISS vector store service.

Generates embeddings using sentence-transformers and stores them
in a FAISS index for fast similarity search.
"""

import json
import logging
import os
import pickle
from pathlib import Path
from typing import Optional

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

# Try to import FAISS
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS not available")

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False
    logger.warning("sentence-transformers not available")


class VectorStore:
    """
    Manages code embeddings and FAISS vector indexes.

    Provides methods to:
    - Generate embeddings for code chunks
    - Build/load FAISS indexes
    - Perform similarity search
    """

    def __init__(self):
        self._model: Optional[SentenceTransformer] = None
        self._indexes: dict[str, faiss.IndexFlatIP] = {}
        self._metadata: dict[str, list[dict]] = {}
        self._dimension: int = 384  # Default for all-MiniLM-L6-v2

    @property
    def model(self) -> Optional[SentenceTransformer]:
        """Lazy-load the embedding model."""
        if self._model is None and ST_AVAILABLE:
            logger.info(f"Loading embedding model: {settings.embedding_model}")
            self._model = SentenceTransformer(settings.embedding_model)
            self._dimension = self._model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded. Dimension: {self._dimension}")
        return self._model

    def generate_embeddings(self, texts: list[str]) -> np.ndarray:
        """
        Generate embeddings for a list of text strings.

        Args:
            texts: List of code chunks or text to embed

        Returns:
            numpy array of embeddings (normalized)
        """
        if not self.model:
            raise RuntimeError("Embedding model not available")

        embeddings = self.model.encode(
            texts,
            show_progress_bar=True,
            normalize_embeddings=True,
            batch_size=32,
        )
        return np.array(embeddings, dtype=np.float32)

    def build_index(self, project_id: str, chunks: list[dict]) -> int:
        """
        Build a FAISS index from code chunks.

        Args:
            project_id: Unique project identifier
            chunks: List of chunk dicts with 'content' key

        Returns:
            Number of vectors indexed
        """
        if not FAISS_AVAILABLE:
            raise RuntimeError("FAISS not available")

        texts = [
            f"File: {c['file_path']}\n"
            f"Lines {c['start_line']}-{c['end_line']}\n\n"
            f"{c['content']}"
            for c in chunks
        ]

        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        embeddings = self.generate_embeddings(texts)

        # Build FAISS index (Inner Product = cosine similarity for normalized vectors)
        index = faiss.IndexFlatIP(self._dimension)
        index.add(embeddings)

        self._indexes[project_id] = index
        self._metadata[project_id] = chunks

        # Persist to disk
        self._save_index(project_id)

        logger.info(f"Index built for {project_id}: {index.ntotal} vectors")
        return index.ntotal

    def search(self, project_id: str, query: str, top_k: int = 5) -> list[dict]:
        """
        Search the vector index for relevant code chunks.

        Args:
            project_id: Project to search in
            query: Natural language query
            top_k: Number of results to return

        Returns:
            List of matching chunks with relevance scores
        """
        if project_id not in self._indexes:
            self._load_index(project_id)

        if project_id not in self._indexes:
            logger.warning(f"No index found for project {project_id}")
            return []

        index = self._indexes[project_id]
        metadata = self._metadata[project_id]

        # Generate query embedding
        query_embedding = self.generate_embeddings([query])

        # Search
        scores, indices = index.search(query_embedding, min(top_k, index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(metadata):
                continue
            chunk = metadata[idx].copy()
            chunk["relevance_score"] = float(score)
            results.append(chunk)

        return results

    def _save_index(self, project_id: str):
        """Save index and metadata to disk."""
        index_dir = settings.faiss_path / project_id
        index_dir.mkdir(parents=True, exist_ok=True)

        if project_id in self._indexes:
            faiss.write_index(
                self._indexes[project_id],
                str(index_dir / "index.faiss")
            )

        if project_id in self._metadata:
            with open(index_dir / "metadata.pkl", "wb") as f:
                pickle.dump(self._metadata[project_id], f)

        logger.info(f"Index saved for {project_id}")

    def _load_index(self, project_id: str) -> bool:
        """Load index and metadata from disk."""
        index_dir = settings.faiss_path / project_id

        index_path = index_dir / "index.faiss"
        meta_path = index_dir / "metadata.pkl"

        if not index_path.exists() or not meta_path.exists():
            return False

        try:
            self._indexes[project_id] = faiss.read_index(str(index_path))
            with open(meta_path, "rb") as f:
                self._metadata[project_id] = pickle.load(f)
            logger.info(f"Index loaded for {project_id}")
            return True
        except Exception as e:
            logger.error(f"Error loading index for {project_id}: {e}")
            return False

    def has_index(self, project_id: str) -> bool:
        """Check if an index exists for a project."""
        if project_id in self._indexes:
            return True
        return (settings.faiss_path / project_id / "index.faiss").exists()

    def delete_index(self, project_id: str):
        """Delete an index for a project."""
        self._indexes.pop(project_id, None)
        self._metadata.pop(project_id, None)

        index_dir = settings.faiss_path / project_id
        if index_dir.exists():
            import shutil
            shutil.rmtree(index_dir)


# Singleton instance
vector_store = VectorStore()

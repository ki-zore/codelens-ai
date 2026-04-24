"""Application configuration loaded from environment variables."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings."""

    # API Keys
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")

    # LLM Configuration
    llm_model: str = os.getenv("LLM_MODEL", "gemini-1.5-flash")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    # Storage Paths
    repos_dir: str = os.getenv("REPOS_DIR", "./repos")
    faiss_dir: str = os.getenv("FAISS_DIR", "./faiss_indexes")

    # CORS
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:5173")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    @property
    def repos_path(self) -> Path:
        path = Path(self.repos_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def faiss_path(self) -> Path:
        path = Path(self.faiss_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    class Config:
        env_file = ".env"


settings = Settings()

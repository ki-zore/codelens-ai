"""
Ingestion API endpoints.

Handles GitHub repo cloning and ZIP file uploads.
"""

import logging
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks

from app.models.schemas import IngestGitHubRequest, IngestResponse
from app.services.ingestion import ingestion_service, project_store
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingest", tags=["Ingestion"])


@router.post("/github", response_model=IngestResponse)
async def ingest_github(request: IngestGitHubRequest):
    """Ingest a GitHub repository by URL."""
    try:
        result = await ingestion_service.ingest_github(
            repo_url=request.repo_url,
            branch=request.branch,
        )
        return IngestResponse(
            project_id=result["project_id"],
            total_files=result["total_files"],
            parsed_files=result["parsed_files"],
            total_functions=result["total_functions"],
            total_classes=result["total_classes"],
            total_imports=result["total_imports"],
            status=result["status"],
        )
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload", response_model=IngestResponse)
async def ingest_upload(file: UploadFile = File(...)):
    """Ingest a codebase from a ZIP file upload."""
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are accepted")

    # Save uploaded file temporarily
    temp_dir = settings.repos_path / "_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / file.filename

    try:
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        result = await ingestion_service.ingest_zip(
            file_path=str(temp_path),
            original_name=file.filename,
        )

        return IngestResponse(
            project_id=result["project_id"],
            total_files=result["total_files"],
            parsed_files=result["parsed_files"],
            total_functions=result["total_functions"],
            total_classes=result["total_classes"],
            total_imports=result["total_imports"],
            status=result["status"],
        )
    except Exception as e:
        logger.error(f"Upload ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temp file
        if temp_path.exists():
            os.remove(temp_path)


@router.get("/projects")
async def list_projects():
    """List all ingested projects."""
    projects = project_store.list_all()
    return {"projects": projects}


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get project details."""
    project = project_store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {**project, "project_id": project_id}


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project and all associated data."""
    project = project_store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    ingestion_service.delete_project(project_id)
    return {"status": "deleted", "project_id": project_id}

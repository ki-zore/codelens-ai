"""
Graph API endpoints.

Provides graph data for visualization and structural queries.
"""

import logging

from fastapi import APIRouter, HTTPException

from app.models.schemas import GraphData
from app.services.graph_builder import graph_builder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/graph", tags=["Graph"])


@router.get("/{project_id}", response_model=GraphData)
async def get_graph(project_id: str):
    """Get the full dependency graph for a project."""
    graph = graph_builder.get_graph(project_id)
    if graph is None:
        raise HTTPException(
            status_code=404,
            detail=f"No graph found for project {project_id}"
        )

    data = graph_builder.get_graph_data(project_id)
    return GraphData(**data)


@router.get("/{project_id}/neighbors/{node_id:path}")
async def get_neighbors(project_id: str, node_id: str):
    """Get immediate neighbors of a node in the graph."""
    graph = graph_builder.get_graph(project_id)
    if graph is None:
        raise HTTPException(
            status_code=404,
            detail=f"No graph found for project {project_id}"
        )

    neighbors = graph_builder.get_node_neighbors(project_id, node_id)
    return neighbors


@router.get("/{project_id}/context/{file_path:path}")
async def get_context(project_id: str, file_path: str, depth: int = 2):
    """Get dependency context for a file."""
    graph = graph_builder.get_graph(project_id)
    if graph is None:
        raise HTTPException(
            status_code=404,
            detail=f"No graph found for project {project_id}"
        )

    context = graph_builder.get_related_context(project_id, file_path, depth)
    return {"file_path": file_path, "context": context}


@router.get("/{project_id}/stats")
async def get_graph_stats(project_id: str):
    """Get graph statistics."""
    graph = graph_builder.get_graph(project_id)
    if graph is None:
        raise HTTPException(
            status_code=404,
            detail=f"No graph found for project {project_id}"
        )

    import networkx as nx

    # Calculate statistics
    node_types = {}
    for _, attrs in graph.nodes(data=True):
        t = attrs.get("type", "unknown")
        node_types[t] = node_types.get(t, 0) + 1

    edge_types = {}
    for _, _, attrs in graph.edges(data=True):
        t = attrs.get("type", "unknown")
        edge_types[t] = edge_types.get(t, 0) + 1

    return {
        "total_nodes": graph.number_of_nodes(),
        "total_edges": graph.number_of_edges(),
        "node_types": node_types,
        "edge_types": edge_types,
        "density": nx.density(graph),
        "is_dag": nx.is_directed_acyclic_graph(graph),
    }

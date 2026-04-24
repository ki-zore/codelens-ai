"""
Dependency graph builder using NetworkX.

Builds a graph of relationships between files, functions, classes,
and imports for structural code understanding.
"""

import json
import logging
from pathlib import Path
from typing import Optional

import networkx as nx

from app.config import settings
from app.services.parser import ParseResult

logger = logging.getLogger(__name__)


class GraphBuilder:
    """
    Builds and manages dependency graphs for code projects.

    Graph node types: file, function, class
    Graph edge types: imports, calls, inherits, contains
    """

    def __init__(self):
        self._graphs: dict[str, nx.DiGraph] = {}

    def build_graph(self, project_id: str, parse_results: list[ParseResult],
                    base_path: str) -> nx.DiGraph:
        """
        Build a dependency graph from parsed code files.

        Args:
            project_id: Unique project identifier
            parse_results: List of ParseResult from code parser
            base_path: Base directory path for relative paths

        Returns:
            NetworkX directed graph
        """
        G = nx.DiGraph()

        # Phase 1: Add file nodes
        for result in parse_results:
            rel_path = str(Path(result.file_path).relative_to(base_path))
            G.add_node(
                rel_path,
                type="file",
                language=result.language,
                label=Path(result.file_path).name,
            )

            # Add function nodes
            for func in result.functions:
                func_id = f"{rel_path}::{func['name']}"
                G.add_node(
                    func_id,
                    type="function",
                    label=func["name"],
                    file_path=rel_path,
                    start_line=func["start_line"],
                    end_line=func["end_line"],
                    signature=func.get("signature", ""),
                )
                # File contains function
                G.add_edge(rel_path, func_id, type="contains")

            # Add class nodes
            for cls in result.classes:
                cls_id = f"{rel_path}::{cls['name']}"
                G.add_node(
                    cls_id,
                    type="class",
                    label=cls["name"],
                    file_path=rel_path,
                    start_line=cls["start_line"],
                    end_line=cls["end_line"],
                )
                # File contains class
                G.add_edge(rel_path, cls_id, type="contains")

                # Class inheritance
                for base in cls.get("bases", []):
                    base_name = base.strip()
                    if base_name:
                        G.add_edge(cls_id, base_name, type="inherits")

        # Phase 2: Build import edges
        file_map = self._build_file_map(parse_results, base_path)

        for result in parse_results:
            rel_path = str(Path(result.file_path).relative_to(base_path))

            for imp in result.imports:
                target = self._resolve_import(imp, rel_path, file_map, result.language)
                if target and G.has_node(target):
                    G.add_edge(rel_path, target, type="imports")

        # Phase 3: Build function call edges
        func_map = {}
        for result in parse_results:
            rel_path = str(Path(result.file_path).relative_to(base_path))
            for func in result.functions:
                func_map[func["name"]] = f"{rel_path}::{func['name']}"

        for result in parse_results:
            rel_path = str(Path(result.file_path).relative_to(base_path))
            for func in result.functions:
                caller_id = f"{rel_path}::{func['name']}"
                for call_name in result.function_calls:
                    if call_name != func["name"] and call_name in func_map:
                        callee_id = func_map[call_name]
                        if G.has_node(callee_id):
                            G.add_edge(caller_id, callee_id, type="calls")

        self._graphs[project_id] = G
        self._save_graph(project_id)

        logger.info(
            f"Graph built for {project_id}: "
            f"{G.number_of_nodes()} nodes, {G.number_of_edges()} edges"
        )
        return G

    def get_graph(self, project_id: str) -> Optional[nx.DiGraph]:
        """Get the graph for a project, loading from disk if needed."""
        if project_id not in self._graphs:
            self._load_graph(project_id)
        return self._graphs.get(project_id)

    def get_graph_data(self, project_id: str) -> dict:
        """Get graph data in a format suitable for frontend visualization."""
        G = self.get_graph(project_id)
        if G is None:
            return {"nodes": [], "edges": []}

        nodes = []
        for node_id, attrs in G.nodes(data=True):
            nodes.append({
                "id": node_id,
                "label": attrs.get("label", node_id),
                "type": attrs.get("type", "unknown"),
                "file_path": attrs.get("file_path"),
                "line_number": attrs.get("start_line"),
            })

        edges = []
        for source, target, attrs in G.edges(data=True):
            edges.append({
                "source": source,
                "target": target,
                "type": attrs.get("type", "unknown"),
            })

        return {"nodes": nodes, "edges": edges}

    def get_related_context(self, project_id: str, file_path: str,
                            depth: int = 2) -> list[str]:
        """
        Get contextually related nodes for a given file.
        Traverses the graph up to `depth` hops.

        Returns list of descriptive strings about relationships.
        """
        G = self.get_graph(project_id)
        if G is None or file_path not in G:
            return []

        context = []
        visited = set()

        def traverse(node, current_depth):
            if current_depth > depth or node in visited:
                return
            visited.add(node)

            # Outgoing edges (what this node depends on)
            for _, target, data in G.out_edges(node, data=True):
                edge_type = data.get("type", "relates to")
                target_label = G.nodes[target].get("label", target)
                target_type = G.nodes[target].get("type", "unknown")
                context.append(
                    f"{G.nodes[node].get('label', node)} "
                    f"--[{edge_type}]--> "
                    f"{target_label} ({target_type})"
                )
                traverse(target, current_depth + 1)

            # Incoming edges (what depends on this node)
            for source, _, data in G.in_edges(node, data=True):
                edge_type = data.get("type", "relates to")
                source_label = G.nodes[source].get("label", source)
                source_type = G.nodes[source].get("type", "unknown")
                context.append(
                    f"{source_label} ({source_type}) "
                    f"--[{edge_type}]--> "
                    f"{G.nodes[node].get('label', node)}"
                )
                traverse(source, current_depth + 1)

        traverse(file_path, 0)
        return list(set(context))  # Deduplicate

    def get_node_neighbors(self, project_id: str, node_id: str) -> dict:
        """Get immediate neighbors of a node."""
        G = self.get_graph(project_id)
        if G is None or node_id not in G:
            return {"incoming": [], "outgoing": []}

        incoming = []
        for source, _, data in G.in_edges(node_id, data=True):
            incoming.append({
                "node": source,
                "type": data.get("type"),
                "label": G.nodes[source].get("label", source),
            })

        outgoing = []
        for _, target, data in G.out_edges(node_id, data=True):
            outgoing.append({
                "node": target,
                "type": data.get("type"),
                "label": G.nodes[target].get("label", target),
            })

        return {"incoming": incoming, "outgoing": outgoing}

    def _build_file_map(self, results: list[ParseResult],
                        base_path: str) -> dict[str, str]:
        """Build a mapping from module names to file paths."""
        file_map = {}
        for result in results:
            rel_path = str(Path(result.file_path).relative_to(base_path))
            # Map by filename without extension
            stem = Path(result.file_path).stem
            file_map[stem] = rel_path
            # Map by relative path
            module_path = rel_path.replace("/", ".").replace("\\", ".")
            if module_path.endswith(".py"):
                module_path = module_path[:-3]
            file_map[module_path] = rel_path
        return file_map

    def _resolve_import(self, import_name: str, current_file: str,
                        file_map: dict, language: str) -> Optional[str]:
        """Resolve an import name to a file path in the project."""
        # Direct match
        if import_name in file_map:
            return file_map[import_name]

        # Try common variations
        parts = import_name.split(".")
        for i in range(len(parts), 0, -1):
            partial = ".".join(parts[:i])
            if partial in file_map:
                return file_map[partial]

        # Try just the last part (module name)
        last_part = parts[-1]
        if last_part in file_map:
            return file_map[last_part]

        return None

    def _save_graph(self, project_id: str):
        """Save graph to disk as JSON."""
        graph_dir = settings.faiss_path / project_id
        graph_dir.mkdir(parents=True, exist_ok=True)

        G = self._graphs[project_id]
        data = nx.node_link_data(G)

        with open(graph_dir / "graph.json", "w") as f:
            json.dump(data, f, indent=2)

    def _load_graph(self, project_id: str) -> bool:
        """Load graph from disk."""
        graph_path = settings.faiss_path / project_id / "graph.json"
        if not graph_path.exists():
            return False

        try:
            with open(graph_path, "r") as f:
                data = json.load(f)
            self._graphs[project_id] = nx.node_link_graph(data)
            return True
        except Exception as e:
            logger.error(f"Error loading graph for {project_id}: {e}")
            return False


# Singleton instance
graph_builder = GraphBuilder()

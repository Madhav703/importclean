"""Import dependency graph builder and renderer."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class DependencyGraph:
    """Render an import dependency graph for a project.

    Supports two output formats:
    - Plain text tree (default)
    - Graphviz ``.dot`` format
    """

    def __init__(self, graph: dict[str, set[str]]) -> None:
        self._graph = graph

    @classmethod
    def from_detector(cls, detector: object) -> "DependencyGraph":  # type: ignore[override]
        """Construct from a :class:`CircularImportDetector` instance."""
        graph = getattr(detector, "graph", {})
        return cls(graph)

    def render_tree(self, root: Optional[str] = None) -> str:
        """Return a plain-text tree rooted at *root* (or all modules if None)."""
        lines: list[str] = []
        visited: set[str] = set()

        def _render(module: str, prefix: str, is_last: bool) -> None:
            if module in visited:
                lines.append(f"{prefix}{'└── ' if is_last else '├── '}{module} (circular)")
                return
            visited.add(module)
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{module}")
            children = sorted(self._graph.get(module, set()))
            child_prefix = prefix + ("    " if is_last else "│   ")
            for i, child in enumerate(children):
                _render(child, child_prefix, i == len(children) - 1)
            visited.discard(module)

        if root:
            roots = [root]
        else:
            roots = sorted(self._graph.keys())

        for i, mod in enumerate(roots):
            lines.append(mod)
            children = sorted(self._graph.get(mod, set()))
            prefix = ""
            for j, child in enumerate(children):
                _render(child, prefix, j == len(children) - 1)
            if i < len(roots) - 1:
                lines.append("")

        return "\n".join(lines)

    def render_dot(self, title: str = "importclean") -> str:
        """Return a Graphviz ``.dot`` representation of the dependency graph."""
        lines = [f'digraph "{title}" {{', "    rankdir=LR;", "    node [shape=box];"]
        for module, deps in sorted(self._graph.items()):
            safe_mod = _dot_id(module)
            for dep in sorted(deps):
                safe_dep = _dot_id(dep)
                lines.append(f'    "{safe_mod}" -> "{safe_dep}";')
        lines.append("}")
        return "\n".join(lines)

    def save_dot(self, output_path: Path, title: str = "importclean") -> None:
        """Write the ``.dot`` file to *output_path*."""
        output_path.write_text(self.render_dot(title), encoding="utf-8")


def _dot_id(name: str) -> str:
    return name.replace('"', '\\"')

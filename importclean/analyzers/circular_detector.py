"""Detect circular import chains across a Python project."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Optional

from importclean.models import CircularImport


class CircularImportDetector:
    """Build an import dependency graph and find cycles using DFS."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._graph: dict[str, set[str]] = {}

    def build_graph(self, py_files: list[Path]) -> None:
        """Populate the dependency graph from all *py_files*."""
        for path in py_files:
            module_name = self._path_to_module(path)
            self._graph[module_name] = self._extract_imports(path)

    def detect_cycles(self) -> list[CircularImport]:
        """Return all distinct circular import chains."""
        visited: set[str] = set()
        in_stack: set[str] = set()
        cycles: list[CircularImport] = []

        for node in list(self._graph):
            if node not in visited:
                self._dfs(node, visited, in_stack, [], cycles)
        return cycles

    def _dfs(
        self,
        node: str,
        visited: set[str],
        in_stack: set[str],
        path: list[str],
        cycles: list[CircularImport],
    ) -> None:
        visited.add(node)
        in_stack.add(node)
        path.append(node)

        for neighbor in self._graph.get(node, set()):
            if neighbor not in self._graph:
                continue
            if neighbor not in visited:
                self._dfs(neighbor, visited, in_stack, path, cycles)
            elif neighbor in in_stack:
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles.append(CircularImport(cycle=cycle))

        path.pop()
        in_stack.discard(node)

    def _path_to_module(self, path: Path) -> str:
        try:
            rel = path.relative_to(self._root)
        except ValueError:
            return path.stem
        # When root is a file itself, rel is just '.' or the filename
        rel_str = str(rel)
        if rel_str in (".", ""):
            return path.stem
        try:
            rel_no_suffix = rel.with_suffix("")
        except ValueError:
            return path.stem
        parts = list(rel_no_suffix.parts)
        if not parts:
            return path.stem
        if parts[-1] == "__init__":
            parts = parts[:-1]
        if not parts:
            return path.stem
        return ".".join(parts)

    def _extract_imports(self, path: Path) -> set[str]:
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(path))
        except (SyntaxError, OSError):
            return set()

        deps: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    deps.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    deps.add(node.module.split(".")[0])
        return deps

    @property
    def graph(self) -> dict[str, set[str]]:
        return dict(self._graph)

"""Detect expensive (heavy) imports and suggest lazy-loading alternatives."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Optional

from importclean.models import HeavyImport, ImportInfo, ImportKind


_LAZY_SUGGESTION_TEMPLATE = (
    "Consider lazy-importing '{module}' inside the function(s) that use it "
    "to avoid paying its import cost at module load time."
)


class HeavyImportDetector:
    """Identify globally-imported heavy modules only used in specific functions."""

    def __init__(self, heavy_modules: frozenset[str]) -> None:
        self._heavy = heavy_modules

    def detect(self, source: str, imports: list[ImportInfo]) -> list[HeavyImport]:
        """Return :class:`HeavyImport` suggestions for *source*."""
        results: list[HeavyImport] = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return results

        global_heavy = [
            imp
            for imp in imports
            if not imp.is_in_function
            and not imp.is_in_class
            and self._is_heavy(imp)
        ]
        if not global_heavy:
            return results

        func_usages = self._usages_per_function(tree)

        for imp in global_heavy:
            name = imp.effective_name
            used_globally = self._used_outside_functions(tree, name)
            if used_globally:
                continue
            functions_using = [fn for fn, names in func_usages.items() if name in names]
            if functions_using:
                suggestion = _LAZY_SUGGESTION_TEMPLATE.format(module=imp.module)
                results.append(HeavyImport(import_info=imp, suggestion=suggestion))
        return results

    def _is_heavy(self, imp: ImportInfo) -> bool:
        top = imp.module.split(".")[0].lstrip(".")
        return top in self._heavy

    def _usages_per_function(self, tree: ast.AST) -> dict[str, set[str]]:
        result: dict[str, set[str]] = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names: set[str] = set()
                for child in ast.walk(node):
                    if isinstance(child, ast.Name):
                        names.add(child.id)
                    elif isinstance(child, ast.Attribute):
                        root = child
                        while isinstance(root, ast.Attribute):
                            root = root.value  # type: ignore[assignment]
                        if isinstance(root, ast.Name):
                            names.add(root.id)
                result[node.name] = names
        return result

    def _used_outside_functions(self, tree: ast.AST, name: str) -> bool:
        """Return True if *name* is referenced at module scope (not inside a function/class)."""
        return self._check_scope(tree, name, at_top_level=True)

    def _check_scope(self, node: ast.AST, name: str, at_top_level: bool) -> bool:
        """Recursively check for *name* usage, not descending into function/class bodies."""
        if isinstance(node, ast.Name) and node.id == name and not at_top_level is False:
            return True
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # Don't recurse into function/class bodies
                continue
            if isinstance(child, ast.Name) and child.id == name:
                return True
            if self._check_scope(child, name, at_top_level):
                return True
        return False

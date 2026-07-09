"""Determine which imported names are actually used in source code."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Optional

from importclean.models import ImportInfo, ImportKind


class UsageAnalyzer(ast.NodeVisitor):
    """Walk a Python AST and collect every name/attribute reference.

    After visiting, :attr:`used_names` contains every bare identifier
    referenced in the file (excluding import statements themselves).
    This is used to decide which imports are unused.
    """

    def __init__(self) -> None:
        self._used: set[str] = set()
        self._in_import: bool = False

    @classmethod
    def collect_used(cls, source: str, path: Optional[Path] = None) -> set[str]:
        """Return the set of names referenced in *source* outside import stmts."""
        try:
            tree = ast.parse(source, filename=str(path or "<string>"))
        except SyntaxError:
            return set()
        analyzer = cls()
        analyzer.visit(tree)
        return analyzer._used

    # ------------------------------------------------------------------
    # Skip the import statements themselves when collecting names
    # ------------------------------------------------------------------

    def visit_Import(self, node: ast.Import) -> None:
        pass

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        pass

    # ------------------------------------------------------------------
    # Collect every name that appears outside of import statements
    # ------------------------------------------------------------------

    def visit_Name(self, node: ast.Name) -> None:
        self._used.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Collect the root of attribute chains (e.g. ``np`` in ``np.array``)
        root = node
        while isinstance(root, ast.Attribute):
            root = root.value  # type: ignore[assignment]
        if isinstance(root, ast.Name):
            self._used.add(root.id)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Collect decorator names
        for decorator in node.decorator_list:
            self.visit(decorator)
        # Collect type annotation names
        if node.returns:
            self.visit(node.returns)
        for arg in (*node.args.args, *node.args.posonlyargs, *node.args.kwonlyargs):
            if arg.annotation:
                self.visit(arg.annotation)
        if node.args.vararg and node.args.vararg.annotation:
            self.visit(node.args.vararg.annotation)
        if node.args.kwarg and node.args.kwarg.annotation:
            self.visit(node.args.kwarg.annotation)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self.visit(node.annotation)
        if node.value:
            self.visit(node.value)

    def visit_Constant(self, node: ast.Constant) -> None:
        # Forward-reference strings like ``"MyClass"`` treated conservatively
        pass


def find_unused_imports(
    imports: list[ImportInfo],
    used_names: set[str],
) -> list[ImportInfo]:
    """Return the subset of *imports* whose effective names are not in *used_names*.

    Conservative rules:
    - Star imports are **never** removed.
    - ``__all__`` causes all from-imports in the same module to be kept.
    - Conditional, TYPE_CHECKING, and try/except imports are kept.
    - ``__future__`` imports are always kept.
    - Imports that define ``__all__``, ``__version__``, etc. are kept.
    - If the module name itself is referenced (e.g. ``sys.path``), keep it.
    """
    # If __all__ exists, keep all top-level names conservatively
    all_defined = "__all__" in used_names

    unused: list[ImportInfo] = []
    for imp in imports:
        if _should_always_keep(imp, used_names, all_defined):
            continue
        effective = imp.effective_name
        if effective not in used_names:
            unused.append(imp)
    return unused


def _should_always_keep(imp: ImportInfo, used_names: set[str], all_defined: bool) -> bool:
    if imp.kind == ImportKind.FROM_STAR:
        return True
    if imp.module.startswith("__future__"):
        return True
    if imp.is_conditional:
        return True
    if imp.is_type_checking:
        return True
    # Dunder attributes at module level are often part of the public API
    if imp.name and imp.name.startswith("__") and not imp.is_in_function:
        return True
    if all_defined:
        return True
    return False

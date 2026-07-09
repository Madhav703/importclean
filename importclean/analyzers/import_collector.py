"""AST-based import statement collector."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Optional

from importclean.models import ImportInfo, ImportKind


class ImportCollector(ast.NodeVisitor):
    """Collect all import statements from a Python AST.

    Handles:
    - ``import module`` and ``import module as alias``
    - ``from module import name`` and ``from module import name as alias``
    - Multiline / parenthesized imports
    - Relative imports (``from . import x``)
    - Conditional imports (inside ``if`` / ``try`` blocks)
    - Imports inside functions and classes
    - ``TYPE_CHECKING`` guarded imports
    - Star imports (``from module import *``)
    """

    def __init__(self) -> None:
        self._imports: list[ImportInfo] = []
        self._depth_function: int = 0
        self._depth_class: int = 0
        self._in_type_checking: bool = False
        self._conditional_depth: int = 0

    @classmethod
    def collect(cls, source: str, path: Optional[Path] = None) -> list[ImportInfo]:
        """Parse *source* and return all :class:`ImportInfo` objects found."""
        try:
            tree = ast.parse(source, filename=str(path or "<string>"))
        except SyntaxError:
            return []
        collector = cls()
        collector.visit(tree)
        return collector._imports

    # ------------------------------------------------------------------
    # AST visitor helpers
    # ------------------------------------------------------------------

    def _is_type_checking_block(self, node: ast.If) -> bool:
        test = node.test
        if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
            return True
        if isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING":
            return True
        return False

    def visit_If(self, node: ast.If) -> None:
        in_tc = self._is_type_checking_block(node)
        prev = self._in_type_checking
        if in_tc:
            self._in_type_checking = True
        self._conditional_depth += 1
        self.generic_visit(node)
        self._conditional_depth -= 1
        self._in_type_checking = prev

    def visit_Try(self, node: ast.Try) -> None:
        self._conditional_depth += 1
        self.generic_visit(node)
        self._conditional_depth -= 1

    def visit_TryStar(self, node: ast.AST) -> None:  # Python 3.11+
        self._conditional_depth += 1
        self.generic_visit(node)
        self._conditional_depth -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._depth_function += 1
        self.generic_visit(node)
        self._depth_function -= 1

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._depth_class += 1
        self.generic_visit(node)
        self._depth_class -= 1

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            info = ImportInfo(
                module=alias.name,
                name=None,
                alias=alias.asname,
                kind=ImportKind.MODULE,
                lineno=node.lineno,
                col_offset=node.col_offset,
                is_conditional=self._conditional_depth > 0,
                is_in_function=self._depth_function > 0,
                is_in_class=self._depth_class > 0,
                is_type_checking=self._in_type_checking,
            )
            self._imports.append(info)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        level = node.level or 0
        relative_prefix = "." * level

        for alias in node.names:
            if alias.name == "*":
                kind = ImportKind.FROM_STAR
            elif level > 0:
                kind = ImportKind.RELATIVE
            else:
                kind = ImportKind.FROM

            info = ImportInfo(
                module=f"{relative_prefix}{module}",
                name=alias.name,
                alias=alias.asname,
                kind=kind,
                lineno=node.lineno,
                col_offset=node.col_offset,
                is_conditional=self._conditional_depth > 0,
                is_in_function=self._depth_function > 0,
                is_in_class=self._depth_class > 0,
                is_type_checking=self._in_type_checking,
            )
            self._imports.append(info)

"""Import sorting compatible with PEP 8 / isort conventions."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Optional


_STDLIB_TOP = frozenset(
    {
        "__future__",
        "abc", "ast", "asyncio", "builtins", "collections", "concurrent",
        "contextlib", "copy", "dataclasses", "datetime", "enum", "functools",
        "gc", "glob", "hashlib", "heapq", "http", "importlib", "inspect",
        "io", "itertools", "json", "logging", "math", "multiprocessing",
        "operator", "os", "pathlib", "pickle", "platform", "queue", "random",
        "re", "shutil", "signal", "socket", "sqlite3", "ssl", "string",
        "struct", "subprocess", "sys", "tempfile", "threading", "time",
        "traceback", "typing", "unittest", "urllib", "uuid", "warnings",
        "weakref", "xml", "zipfile",
    }
)


def sort_imports(source: str) -> str:
    """Return *source* with import statements sorted in PEP 8 order.

    Groups:
    1. ``__future__`` imports
    2. Standard library imports
    3. Third-party imports
    4. Local / relative imports

    Within each group imports are sorted alphabetically.  Blank lines
    between groups are preserved / added as required.  Non-import code
    is not touched.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source

    lines = source.splitlines(keepends=True)
    import_ranges = _collect_import_ranges(tree, lines)
    if not import_ranges:
        return source

    sorted_block = _build_sorted_block(import_ranges, lines)
    first_line = import_ranges[0][0]
    last_line = import_ranges[-1][1]

    new_lines = lines[:first_line] + sorted_block + lines[last_line + 1:]
    return "".join(new_lines)


def _collect_import_ranges(
    tree: ast.Module, lines: list[str]
) -> list[tuple[int, int]]:
    """Return (start_line, end_line) for each contiguous import block (0-indexed)."""
    import_lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            # end_lineno may span multiline imports
            for lineno in range(node.lineno - 1, (node.end_lineno or node.lineno)):
                import_lines.add(lineno)

    if not import_lines:
        return []

    sorted_lines = sorted(import_lines)
    ranges: list[tuple[int, int]] = []
    start = sorted_lines[0]
    prev = sorted_lines[0]
    for ln in sorted_lines[1:]:
        if ln <= prev + 2:  # Allow one blank line between groups
            prev = ln
        else:
            ranges.append((start, prev))
            start = ln
            prev = ln
    ranges.append((start, prev))
    return ranges


def _build_sorted_block(
    ranges: list[tuple[int, int]], lines: list[str]
) -> list[str]:
    raw_stmts: list[str] = []
    for start, end in ranges:
        raw_stmts.extend(lines[start : end + 1])

    # Parse individual import strings
    buckets: dict[int, list[str]] = {0: [], 1: [], 2: [], 3: []}
    current: list[str] = []
    for raw in raw_stmts:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        current.append(raw)
        if not stripped.endswith("\\") and "(" not in stripped:
            stmt = "".join(current)
            bucket = _classify(stmt)
            buckets[bucket].append(stmt)
            current = []

    result: list[str] = []
    for bucket_id in sorted(buckets):
        stmts = sorted(buckets[bucket_id], key=_sort_key)
        if not stmts:
            continue
        result.extend(stmts)
        result.append("\n")
    return result


def _classify(stmt: str) -> int:
    stripped = stmt.strip()
    if stripped.startswith("from __future__"):
        return 0
    if stripped.startswith("from .") or stripped.startswith("from .."):
        return 3
    module = _extract_top_module(stripped)
    if module in _STDLIB_TOP:
        return 1
    return 2


def _extract_top_module(stmt: str) -> str:
    if stmt.startswith("from "):
        parts = stmt.split()
        if len(parts) >= 2:
            return parts[1].split(".")[0]
    if stmt.startswith("import "):
        parts = stmt.split()
        if len(parts) >= 2:
            return parts[1].split(".")[0].rstrip(",")
    return ""


def _sort_key(stmt: str) -> str:
    return _extract_top_module(stmt.strip())

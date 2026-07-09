"""Source code validation after transformation."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Optional


def validate_source(source: str, path: Optional[Path] = None) -> Optional[str]:
    """Parse and compile *source* to verify syntactic correctness.

    Returns ``None`` on success, or an error message string on failure.
    """
    filename = str(path or "<string>")
    try:
        tree = ast.parse(source, filename=filename)
        compile(tree, filename, "exec")
    except SyntaxError as exc:
        return f"SyntaxError: {exc.msg} (line {exc.lineno})"
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"
    return None

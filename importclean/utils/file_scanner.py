"""Recursive project file scanner."""

from __future__ import annotations

import fnmatch
from pathlib import Path


class FileScanner:
    """Discover Python source files in a project tree.

    Respects the ignore-directory list from the active :class:`Config` and
    skips hidden directories automatically.
    """

    def __init__(self, ignore_dirs: frozenset[str]) -> None:
        self._ignore_dirs = ignore_dirs

    def scan(self, root: Path) -> list[Path]:
        """Return all ``.py`` files under *root*, respecting ignore rules."""
        if root.is_file():
            if root.suffix == ".py":
                return [root]
            return []
        return sorted(self._walk(root))

    def _walk(self, directory: Path) -> list[Path]:
        results: list[Path] = []
        try:
            entries = list(directory.iterdir())
        except PermissionError:
            return results

        for entry in entries:
            if entry.is_dir():
                if self._should_ignore_dir(entry):
                    continue
                results.extend(self._walk(entry))
            elif entry.is_file() and entry.suffix == ".py":
                results.append(entry)
        return results

    def _should_ignore_dir(self, path: Path) -> bool:
        name = path.name
        if name.startswith("."):
            return True
        for pattern in self._ignore_dirs:
            if fnmatch.fnmatch(name, pattern):
                return True
        return False

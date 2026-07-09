"""Data models used throughout importclean."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class ImportKind(str, Enum):
    """Category of an import statement."""

    MODULE = "module"
    FROM = "from"
    FROM_STAR = "from_star"
    RELATIVE = "relative"


@dataclass(frozen=True)
class ImportInfo:
    """Metadata about a single import or imported name."""

    module: str
    name: Optional[str]
    alias: Optional[str]
    kind: ImportKind
    lineno: int
    col_offset: int
    is_conditional: bool = False
    is_in_function: bool = False
    is_in_class: bool = False
    is_type_checking: bool = False

    @property
    def effective_name(self) -> str:
        """The name by which this import is referenced in code."""
        if self.alias:
            return self.alias
        if self.name:
            return self.name
        return self.module.split(".")[0]

    def __str__(self) -> str:
        if self.kind == ImportKind.FROM:
            target = f"{self.name} as {self.alias}" if self.alias else self.name
            return f"from {self.module} import {target}"
        target = f"{self.module} as {self.alias}" if self.alias else self.module
        return f"import {target}"


@dataclass
class UnusedImport:
    """An import that was determined to be unused."""

    import_info: ImportInfo
    reason: str = "unused"

    def __str__(self) -> str:
        return f"{self.import_info} (line {self.import_info.lineno})"


@dataclass
class DuplicateImport:
    """A pair of duplicate import statements."""

    original: ImportInfo
    duplicate: ImportInfo

    def __str__(self) -> str:
        return f"Duplicate at line {self.duplicate.lineno} of {self.original}"


@dataclass
class CircularImport:
    """A circular dependency chain between modules."""

    cycle: list[str]

    def __str__(self) -> str:
        return " → ".join(self.cycle)


@dataclass
class HeavyImport:
    """An import of a known-expensive module that could be lazy-loaded."""

    import_info: ImportInfo
    suggestion: str


@dataclass
class FileReport:
    """Analysis result for a single Python file."""

    path: Path
    unused: list[UnusedImport] = field(default_factory=list)
    duplicates: list[DuplicateImport] = field(default_factory=list)
    heavy: list[HeavyImport] = field(default_factory=list)
    syntax_error: Optional[str] = None
    modified: bool = False
    original_source: str = ""
    cleaned_source: str = ""

    @property
    def has_issues(self) -> bool:
        return bool(self.unused or self.duplicates or self.heavy)

    @property
    def total_removals(self) -> int:
        return len(self.unused) + len(self.duplicates)


@dataclass
class CleanReport:
    """Aggregated result for an entire project scan."""

    root: Path
    file_reports: list[FileReport] = field(default_factory=list)
    circular_imports: list[CircularImport] = field(default_factory=list)
    elapsed: float = 0.0
    _start: float = field(default_factory=time.monotonic, repr=False)

    def finish(self) -> None:
        """Record the elapsed time."""
        self.elapsed = time.monotonic() - self._start

    @property
    def files_scanned(self) -> int:
        return len(self.file_reports)

    @property
    def files_modified(self) -> int:
        return sum(1 for r in self.file_reports if r.modified)

    @property
    def total_unused(self) -> int:
        return sum(len(r.unused) for r in self.file_reports)

    @property
    def total_duplicates(self) -> int:
        return sum(len(r.duplicates) for r in self.file_reports)

    @property
    def files_with_errors(self) -> int:
        return sum(1 for r in self.file_reports if r.syntax_error)

    def summary(self) -> str:
        lines = [
            f"Files scanned:          {self.files_scanned}",
            f"Files modified:         {self.files_modified}",
            f"Unused imports removed: {self.total_unused}",
            f"Duplicate imports removed: {self.total_duplicates}",
            f"Circular imports:       {len(self.circular_imports)}",
            f"Execution time:         {self.elapsed:.2f} seconds",
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict:  # type: ignore[type-arg]
        return {
            "files": self.files_scanned,
            "modified": self.files_modified,
            "unused_imports": self.total_unused,
            "duplicates": self.total_duplicates,
            "circular_imports": len(self.circular_imports),
            "elapsed_seconds": round(self.elapsed, 3),
        }

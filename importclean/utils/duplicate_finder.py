"""Detect duplicate import statements within a single file."""

from __future__ import annotations

from importclean.models import DuplicateImport, ImportInfo, ImportKind


def find_duplicates(imports: list[ImportInfo]) -> list[DuplicateImport]:
    """Return :class:`DuplicateImport` pairs for repeated import entries.

    Two imports are considered duplicates when they import the same symbol
    from the same module with the same alias, regardless of line position.
    The first occurrence is kept; all subsequent ones are flagged.
    """
    seen: dict[tuple, ImportInfo] = {}
    duplicates: list[DuplicateImport] = []

    for imp in imports:
        key = _dedup_key(imp)
        if key in seen:
            duplicates.append(DuplicateImport(original=seen[key], duplicate=imp))
        else:
            seen[key] = imp

    return duplicates


def _dedup_key(imp: ImportInfo) -> tuple:  # type: ignore[type-arg]
    return (imp.module, imp.name, imp.alias, imp.kind)

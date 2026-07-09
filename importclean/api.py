"""Public Python API for importclean."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from importclean.config import Config, load_config
from importclean.engine import process_file as _process_file
from importclean.engine import process_project
from importclean.models import CleanReport, FileReport
from importclean.plugins.registry import PluginRegistry
from importclean.utils.file_scanner import FileScanner


def clean_project(
    path: str | Path = ".",
    dry_run: bool = False,
    safe_mode: bool = True,
    sort_imports: bool = False,
    remove_unused: bool = True,
    remove_duplicates: bool = True,
    workers: int = 0,
    registry: Optional[PluginRegistry] = None,
    config: Optional[Config] = None,
) -> CleanReport:
    """Analyze and clean an entire Python project.

    Parameters
    ----------
    path:
        Root directory or a single ``.py`` file to process.
    dry_run:
        When ``True``, no files are written; the report describes what
        *would* change.
    safe_mode:
        When ``True`` (default), conditional and TYPE_CHECKING imports
        are never removed.
    sort_imports:
        Sort remaining imports in PEP 8 order after cleaning.
    remove_unused:
        Remove imports whose names are never referenced in the file.
    remove_duplicates:
        Remove repeated identical import statements.
    workers:
        Number of parallel worker processes.  ``0`` uses the CPU count.
    registry:
        Optional :class:`PluginRegistry` with custom rules.
    config:
        Optional pre-built :class:`Config` object; all other keyword
        arguments are ignored when this is supplied.

    Returns
    -------
    CleanReport
        Aggregated result describing every file analysed.
    """
    root = Path(path).resolve()

    if config is None:
        config = load_config(
            root if root.is_dir() else root.parent,
            overrides={
                "safe_mode": safe_mode,
                "sort_imports": sort_imports,
                "remove_unused": remove_unused,
                "remove_duplicates": remove_duplicates,
                "workers": workers,
            },
        )

    scanner = FileScanner(config.all_ignore_dirs)
    py_files = scanner.scan(root)

    return process_project(root, config, py_files, dry_run=dry_run, registry=registry)


def clean_file(
    path: str | Path,
    dry_run: bool = False,
    safe_mode: bool = True,
    sort_imports: bool = False,
    config: Optional[Config] = None,
) -> FileReport:
    """Analyze and clean a single Python file.

    Parameters
    ----------
    path:
        Path to the ``.py`` file.
    dry_run:
        When ``True``, the file is not written.
    safe_mode:
        Conservative import retention (see :func:`clean_project`).
    sort_imports:
        Sort remaining imports after cleaning.
    config:
        Optional pre-built :class:`Config` object.

    Returns
    -------
    FileReport
        Result for the single file.
    """
    resolved = Path(path).resolve()

    if config is None:
        config = load_config(
            resolved.parent,
            overrides={
                "safe_mode": safe_mode,
                "sort_imports": sort_imports,
            },
        )

    return _process_file(resolved, config, dry_run=dry_run)

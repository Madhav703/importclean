"""Core processing engine for importclean.

Orchestrates scanning, analysis, transformation, and validation of a single
Python file.  The :func:`process_file` function is the atomic unit of work;
:func:`process_project` applies it across an entire directory tree using
optional multiprocessing.
"""

from __future__ import annotations

import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial
from pathlib import Path
from typing import Optional

from importclean.analyzers.import_collector import ImportCollector
from importclean.analyzers.usage_analyzer import UsageAnalyzer, find_unused_imports
from importclean.analyzers.heavy_detector import HeavyImportDetector
from importclean.analyzers.circular_detector import CircularImportDetector
from importclean.config import Config
from importclean.models import (
    CleanReport,
    DuplicateImport,
    FileReport,
    ImportInfo,
    UnusedImport,
)
from importclean.plugins.registry import PluginRegistry
from importclean.transformers.import_remover import remove_imports
from importclean.transformers.import_sorter import sort_imports
from importclean.utils.duplicate_finder import find_duplicates
from importclean.utils.validator import validate_source


def process_file(
    path: Path,
    config: Config,
    dry_run: bool = False,
    registry: Optional[PluginRegistry] = None,
) -> FileReport:
    """Analyze and optionally clean a single Python file.

    Returns a :class:`FileReport` describing all findings.  If *dry_run* is
    ``True``, the original file is never touched.

    Safety guarantees:
    - The cleaned source is validated with ``ast.parse`` + ``compile``.
    - If validation fails, the original file is restored and the error is
      recorded in the report.
    - Star imports are never removed.
    - Conditional, TYPE_CHECKING, and try/except imports are never removed.
    """
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        report = FileReport(path=path)
        report.syntax_error = str(exc)
        return report

    return _analyze_and_clean(source, path, config, dry_run, registry)


def _analyze_and_clean(
    source: str,
    path: Path,
    config: Config,
    dry_run: bool,
    registry: Optional[PluginRegistry],
) -> FileReport:
    report = FileReport(path=path, original_source=source)

    # 1. Collect all imports
    imports = ImportCollector.collect(source, path)
    if not imports:
        return report

    # 2. Find used names
    used_names = UsageAnalyzer.collect_used(source, path)

    # 3. Detect unused imports
    if config.remove_unused:
        unused_infos = find_unused_imports(imports, used_names)
        report.unused = [UnusedImport(import_info=imp) for imp in unused_infos]

    # 4. Detect duplicates
    if config.remove_duplicates:
        report.duplicates = find_duplicates(imports)

    # 5. Detect heavy imports
    if config.detect_heavy:
        detector = HeavyImportDetector(config.heavy_modules)
        report.heavy = detector.detect(source, imports)

    # 6. Run custom plugin rules
    if registry and len(registry) > 0:
        import ast as _ast

        try:
            tree = _ast.parse(source, filename=str(path))
        except SyntaxError:
            tree = None  # type: ignore[assignment]
        if tree is not None:
            for imp in imports:
                for result in registry.run_all(imp, tree):  # type: ignore[arg-type]
                    if result.should_remove:
                        report.unused.append(UnusedImport(import_info=imp, reason=result.message))

    if not report.has_issues:
        return report

    # 7. Build cleaned source
    to_remove = [u.import_info for u in report.unused]
    dup_to_remove = [d.duplicate for d in report.duplicates]
    cleaned = remove_imports(source, to_remove, dup_to_remove)

    if config.sort_imports:
        cleaned = sort_imports(cleaned)

    # 8. Validate cleaned source
    error = validate_source(cleaned, path)
    if error:
        report.syntax_error = f"Validation failed after cleaning: {error}"
        report.cleaned_source = source
        return report

    report.cleaned_source = cleaned

    # 9. Write to disk (unless dry-run)
    if not dry_run and cleaned != source:
        try:
            path.write_text(cleaned, encoding="utf-8")
            report.modified = True
        except OSError as exc:
            report.syntax_error = f"Write error: {exc}"

    return report


def process_project(
    root: Path,
    config: Config,
    py_files: list[Path],
    dry_run: bool = False,
    registry: Optional[PluginRegistry] = None,
) -> CleanReport:
    """Process all *py_files* and return an aggregated :class:`CleanReport`."""
    report = CleanReport(root=root)

    workers = config.workers or _default_workers()
    _process = partial(
        _process_file_worker,
        config=config,
        dry_run=dry_run,
    )

    if workers <= 1 or len(py_files) < 4:
        for path in py_files:
            fr = process_file(path, config, dry_run, registry)
            report.file_reports.append(fr)
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_process, path): path for path in py_files}
            for future in as_completed(futures):
                try:
                    fr = future.result()
                    report.file_reports.append(fr)
                except Exception as exc:
                    path = futures[future]
                    fr = FileReport(path=path)
                    fr.syntax_error = str(exc)
                    report.file_reports.append(fr)

    # Sort by path for deterministic output
    report.file_reports.sort(key=lambda r: r.path)

    # Circular import detection (single-process; needs all files)
    if config.detect_circular:
        detector = CircularImportDetector(root)
        detector.build_graph(py_files)
        report.circular_imports = detector.detect_cycles()

    report.finish()
    return report


def _process_file_worker(
    path: Path,
    config: Config,
    dry_run: bool,
) -> FileReport:
    """Top-level callable for multiprocessing workers (no registry support)."""
    return process_file(path, config, dry_run, registry=None)


def _default_workers() -> int:
    try:
        cpu = multiprocessing.cpu_count()
        return max(1, min(cpu, 8))
    except NotImplementedError:
        return 1

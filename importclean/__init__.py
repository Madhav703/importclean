"""importclean — Detect and remove unused imports from Python projects.

This package provides both a library API and a command-line interface for
statically analyzing Python source files, identifying unused imports, and
safely removing them while preserving all code behavior and formatting.

Example usage::

    from importclean import clean_project

    report = clean_project(
        path=".",
        dry_run=True,
        safe_mode=True,
    )
    print(report.summary())
"""

from importclean.api import clean_file, clean_project
from importclean.models import CleanReport, FileReport

__version__ = "0.1.0"
__all__ = [
    "__version__",
    "clean_project",
    "clean_file",
    "CleanReport",
    "FileReport",
]

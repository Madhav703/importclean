"""Unified diff reporter for importclean."""

from __future__ import annotations

import difflib
from pathlib import Path

from rich.console import Console
from rich.syntax import Syntax

from importclean.models import CleanReport, FileReport


class DiffReporter:
    """Display Git-style unified diffs for each modified file."""

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()

    def print_diffs(self, report: CleanReport) -> None:
        """Print unified diffs for every file that would be modified."""
        shown = 0
        for fr in report.file_reports:
            if fr.original_source and fr.cleaned_source and fr.original_source != fr.cleaned_source:
                self._print_file_diff(fr)
                shown += 1
        if shown == 0:
            self._console.print("[green]No changes to display.[/green]")

    def _print_file_diff(self, fr: FileReport) -> None:
        rel = _rel(fr.path)
        original_lines = fr.original_source.splitlines(keepends=True)
        cleaned_lines = fr.cleaned_source.splitlines(keepends=True)
        diff = list(
            difflib.unified_diff(
                original_lines,
                cleaned_lines,
                fromfile=f"a/{rel}",
                tofile=f"b/{rel}",
                lineterm="",
            )
        )
        if diff:
            diff_text = "\n".join(diff)
            syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=False)
            self._console.print(syntax)

    def get_diff(self, fr: FileReport) -> str:
        """Return the unified diff string for a single :class:`FileReport`."""
        if not fr.original_source or not fr.cleaned_source:
            return ""
        rel = _rel(fr.path)
        original_lines = fr.original_source.splitlines(keepends=True)
        cleaned_lines = fr.cleaned_source.splitlines(keepends=True)
        return "".join(
            difflib.unified_diff(
                original_lines,
                cleaned_lines,
                fromfile=f"a/{rel}",
                tofile=f"b/{rel}",
            )
        )


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)

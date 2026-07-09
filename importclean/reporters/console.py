"""Rich-based console reporter for importclean results."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from importclean.models import CleanReport, FileReport


class ConsoleReporter:
    """Render a :class:`CleanReport` to the terminal using Rich."""

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()

    def print_report(self, report: CleanReport, verbose: bool = False) -> None:
        """Print a full summary of the cleaning run."""
        if verbose:
            for fr in report.file_reports:
                if fr.has_issues or fr.syntax_error:
                    self._print_file_report(fr)

        if report.circular_imports:
            self._print_circular(report)

        self._print_summary(report)

    def _print_file_report(self, fr: FileReport) -> None:
        rel = _rel(fr.path)

        if fr.syntax_error:
            self._console.print(f"[red]✖[/red] {rel}: {fr.syntax_error}")
            return

        lines = []
        for unused in fr.unused:
            lines.append(
                f"  [yellow]−[/yellow] line {unused.import_info.lineno}: {unused.import_info}"
            )
        for dup in fr.duplicates:
            lines.append(
                f"  [blue]≡[/blue] line {dup.duplicate.lineno}: duplicate of line {dup.original.lineno}"
            )
        for heavy in fr.heavy:
            lines.append(f"  [magenta]⚡[/magenta] {heavy.suggestion}")

        if lines:
            self._console.print(f"[bold]{rel}[/bold]")
            for line in lines:
                self._console.print(line)

    def _print_circular(self, report: CleanReport) -> None:
        table = Table(title="Circular Imports", box=box.ROUNDED, show_header=False)
        table.add_column("Cycle", style="red")
        for ci in report.circular_imports:
            table.add_row(str(ci))
        self._console.print(table)

    def _print_summary(self, report: CleanReport) -> None:
        table = Table(box=box.SIMPLE, show_header=False)
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        rows = [
            ("Files scanned", str(report.files_scanned)),
            ("Files modified", str(report.files_modified)),
            ("Unused imports removed", str(report.total_unused)),
            ("Duplicate imports removed", str(report.total_duplicates)),
            ("Circular imports", str(len(report.circular_imports))),
            ("Execution time", f"{report.elapsed:.2f}s"),
        ]
        for label, value in rows:
            table.add_row(label, value)

        self._console.print(Panel(table, title="[bold green]importclean[/bold green]"))

    def print_stats(self, report: CleanReport) -> None:
        """Print only the statistics table."""
        self._print_summary(report)

    def print_check_result(self, report: CleanReport) -> None:
        """Print a check-mode result (no files modified)."""
        total_issues = report.total_unused + report.total_duplicates
        if total_issues == 0:
            self._console.print("[green]✔ No unused imports found.[/green]")
        else:
            self._console.print(
                f"[red]✖ Found {total_issues} unused/duplicate import(s) in "
                f"{report.files_scanned} file(s).[/red]"
            )
            for fr in report.file_reports:
                if fr.has_issues:
                    self._print_file_report(fr)


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)

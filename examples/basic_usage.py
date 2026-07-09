"""Basic usage examples for importclean.

Run with:
    python examples/basic_usage.py
"""

from importclean import clean_project, clean_file
from importclean.reporters.json_reporter import JsonReporter
from importclean.reporters.diff import DiffReporter
from rich.console import Console

console = Console()


def example_clean_project():
    """Dry-run the current directory and print a summary."""
    report = clean_project(
        path=".",
        dry_run=True,
        safe_mode=True,
    )
    console.print(report.summary())


def example_clean_single_file(path: str):
    """Dry-run a single file and show a diff."""
    fr = clean_file(path, dry_run=True)
    from importclean.models import CleanReport
    from pathlib import Path

    report = CleanReport(root=Path("."))
    report.file_reports.append(fr)

    dr = DiffReporter(console)
    dr.print_diffs(report)


def example_json_output():
    """Output results as JSON."""
    report = clean_project(path=".", dry_run=True)
    jr = JsonReporter()
    print(jr.to_json(report))


if __name__ == "__main__":
    example_clean_project()

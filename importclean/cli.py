"""Command-line interface for importclean."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from importclean.api import clean_project
from importclean.config import load_config
from importclean.analyzers.circular_detector import CircularImportDetector
from importclean.reporters.console import ConsoleReporter
from importclean.reporters.diff import DiffReporter
from importclean.reporters.graph import DependencyGraph
from importclean.reporters.json_reporter import JsonReporter
from importclean.utils.file_scanner import FileScanner


_console = Console()
_err_console = Console(stderr=True)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(package_name="importclean", prog_name="importclean")
@click.argument("target", default=".", required=False)
@click.option("--check", is_flag=True, help="Report unused imports without modifying files.")
@click.option("--diff", is_flag=True, help="Show unified diffs of proposed changes.")
@click.option("--graph", is_flag=True, help="Print the import dependency graph.")
@click.option("--stats", is_flag=True, help="Print statistics only.")
@click.option("--json", "output_json", is_flag=True, help="Output results as JSON.")
@click.option("--verify", is_flag=True, help="Verify all files parse cleanly (no cleaning).")
@click.option("--dry-run", is_flag=True, help="Preview changes without writing files.")
@click.option("--sort", is_flag=True, help="Sort imports in PEP 8 order.")
@click.option("--no-duplicates", is_flag=True, default=False, help="Skip duplicate removal.")
@click.option("--dot", type=click.Path(), default=None, help="Write dependency graph as .dot file.")
@click.option("--workers", type=int, default=0, help="Number of parallel workers (0=auto).")
@click.option("-v", "--verbose", is_flag=True, help="Show per-file details.")
def main(
    target: str,
    check: bool,
    diff: bool,
    graph: bool,
    stats: bool,
    output_json: bool,
    verify: bool,
    dry_run: bool,
    sort: bool,
    no_duplicates: bool,
    dot: Optional[str],
    workers: int,
    verbose: bool,
) -> None:
    """importclean — Remove unused imports from Python projects.

    TARGET can be a file, directory, or package (default: current directory).

    \b
    Examples:
      importclean .
      importclean src/
      importclean myfile.py --diff
      importclean . --check
      importclean . --graph
      importclean . --json
    """
    root = Path(target).resolve()
    if not root.exists():
        _err_console.print(f"[red]Error:[/red] path does not exist: {target}")
        sys.exit(1)

    config = load_config(
        root if root.is_dir() else root.parent,
        overrides={
            "sort_imports": sort,
            "remove_duplicates": not no_duplicates,
            "workers": workers,
        },
    )
    scanner = FileScanner(config.all_ignore_dirs)
    py_files = scanner.scan(root)

    if not py_files:
        _console.print("[yellow]No Python files found.[/yellow]")
        sys.exit(0)

    # --graph mode: just show the dependency graph
    if graph or dot:
        _run_graph(root, py_files, dot, output_json)
        return

    # --verify mode: check that all files parse cleanly (no cleaning)
    if verify:
        _run_verify(py_files)
        return

    actual_dry_run = dry_run or check or diff or stats or output_json

    report = clean_project(
        path=root,
        dry_run=actual_dry_run,
        sort_imports=sort,
        remove_duplicates=not no_duplicates,
        workers=workers,
        config=config,
    )

    reporter = ConsoleReporter(_console)

    if output_json:
        jr = JsonReporter()
        _console.print_json(jr.to_json(report))
        _raise_if_check_fails(check, report)
        return

    if diff:
        dr = DiffReporter(_console)
        dr.print_diffs(report)
        _raise_if_check_fails(check, report)
        return

    if stats:
        reporter.print_stats(report)
        return

    if check:
        reporter.print_check_result(report)
        total = report.total_unused + report.total_duplicates
        if total > 0:
            sys.exit(1)
        return

    reporter.print_report(report, verbose=verbose)

    if report.files_with_errors > 0:
        sys.exit(2)


def _run_graph(
    root: Path,
    py_files: list[Path],
    dot_path: Optional[str],
    output_json: bool,
) -> None:
    detector = CircularImportDetector(root)
    detector.build_graph(py_files)
    dg = DependencyGraph(detector.graph)

    if dot_path:
        out = Path(dot_path)
        dg.save_dot(out)
        _console.print(f"[green]Dependency graph written to:[/green] {out}")
        return

    if output_json:
        data = {mod: sorted(deps) for mod, deps in detector.graph.items()}
        _console.print_json(json.dumps(data, indent=2))
        return

    _console.print(dg.render_tree())


def _run_verify(py_files: list[Path]) -> None:
    from importclean.utils.validator import validate_source

    errors = 0
    for path in py_files:
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            _err_console.print(f"[red]✖[/red] {path}: {exc}")
            errors += 1
            continue
        error = validate_source(source, path)
        if error:
            _err_console.print(f"[red]✖[/red] {path}: {error}")
            errors += 1

    if errors == 0:
        _console.print(f"[green]✔ All {len(py_files)} files are valid Python.[/green]")
    else:
        _console.print(f"[red]✖ {errors} file(s) have syntax errors.[/red]")
        sys.exit(1)


def _raise_if_check_fails(check: bool, report: object) -> None:
    if check:
        total = getattr(report, "total_unused", 0) + getattr(report, "total_duplicates", 0)
        if total > 0:
            sys.exit(1)

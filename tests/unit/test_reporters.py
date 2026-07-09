"""Tests for console and diff reporters."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from importclean.models import (
    CircularImport,
    CleanReport,
    DuplicateImport,
    FileReport,
    HeavyImport,
    ImportInfo,
    ImportKind,
    UnusedImport,
)
from importclean.reporters.console import ConsoleReporter
from importclean.reporters.diff import DiffReporter


def _console() -> Console:
    return Console(file=StringIO(), width=120, highlight=False, markup=True)


def _make_import(module: str = "os", lineno: int = 1) -> ImportInfo:
    return ImportInfo(
        module=module, name=None, alias=None,
        kind=ImportKind.MODULE, lineno=lineno, col_offset=0,
    )


def _make_full_report() -> CleanReport:
    fr = FileReport(path=Path("test.py"))
    imp = _make_import("os")
    fr.unused = [UnusedImport(import_info=imp)]
    imp2 = _make_import("sys", lineno=2)
    imp2_dup = _make_import("sys", lineno=3)
    fr.duplicates = [DuplicateImport(original=imp2, duplicate=imp2_dup)]
    fr.heavy = [HeavyImport(import_info=_make_import("pandas"), suggestion="lazy-load pandas")]
    fr.original_source = "import os\nimport sys\nimport sys\nprint('hi')\n"
    fr.cleaned_source = "import sys\nprint('hi')\n"
    fr.modified = True

    report = CleanReport(root=Path("."))
    report.file_reports.append(fr)
    report.circular_imports = [CircularImport(cycle=["a", "b", "a"])]
    report.finish()
    return report


class TestConsoleReporter:
    def test_print_report_no_error(self):
        console = _console()
        reporter = ConsoleReporter(console)
        report = _make_full_report()
        reporter.print_report(report, verbose=True)
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert len(output) > 0

    def test_print_report_verbose_shows_files(self):
        console = _console()
        reporter = ConsoleReporter(console)
        report = _make_full_report()
        reporter.print_report(report, verbose=True)
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "test.py" in output

    def test_print_stats(self):
        console = _console()
        reporter = ConsoleReporter(console)
        report = _make_full_report()
        reporter.print_stats(report)
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "Files scanned" in output

    def test_print_check_result_no_issues(self):
        console = _console()
        reporter = ConsoleReporter(console)
        report = CleanReport(root=Path("."))
        report.file_reports.append(FileReport(path=Path("clean.py")))
        reporter.print_check_result(report)
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "No unused imports" in output

    def test_print_check_result_with_issues(self):
        console = _console()
        reporter = ConsoleReporter(console)
        report = _make_full_report()
        reporter.print_check_result(report)
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "unused" in output.lower() or "import" in output.lower()

    def test_syntax_error_file_shown(self):
        console = _console()
        reporter = ConsoleReporter(console)
        fr = FileReport(path=Path("bad.py"))
        fr.syntax_error = "SyntaxError: invalid syntax"
        report = CleanReport(root=Path("."))
        report.file_reports.append(fr)
        reporter.print_report(report, verbose=True)
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "SyntaxError" in output

    def test_circular_imports_shown(self):
        console = _console()
        reporter = ConsoleReporter(console)
        report = CleanReport(root=Path("."))
        report.circular_imports = [CircularImport(cycle=["a", "b", "a"])]
        reporter.print_report(report, verbose=False)
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "a" in output


class TestDiffReporter:
    def test_print_diffs_with_changes(self):
        console = _console()
        reporter = DiffReporter(console)
        report = _make_full_report()
        reporter.print_diffs(report)
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert len(output) > 0

    def test_print_diffs_no_changes(self):
        console = _console()
        reporter = DiffReporter(console)
        report = CleanReport(root=Path("."))
        fr = FileReport(path=Path("clean.py"))
        fr.original_source = "import os\nos.getcwd()\n"
        fr.cleaned_source = "import os\nos.getcwd()\n"
        report.file_reports.append(fr)
        reporter.print_diffs(report)
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "No changes" in output

    def test_get_diff_returns_string(self):
        reporter = DiffReporter()
        fr = FileReport(path=Path("test.py"))
        fr.original_source = "import os\nprint('hi')\n"
        fr.cleaned_source = "print('hi')\n"
        diff = reporter.get_diff(fr)
        assert "import os" in diff
        assert "---" in diff

    def test_get_diff_empty_when_no_source(self):
        reporter = DiffReporter()
        fr = FileReport(path=Path("test.py"))
        diff = reporter.get_diff(fr)
        assert diff == ""

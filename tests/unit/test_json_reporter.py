"""Tests for the JSON reporter."""

from __future__ import annotations

import json
from pathlib import Path

from importclean.models import CleanReport, FileReport, ImportInfo, ImportKind, UnusedImport
from importclean.reporters.json_reporter import JsonReporter


def _make_report_with_unused() -> CleanReport:
    fr = FileReport(path=Path("demo.py"))
    imp = ImportInfo(
        module="os", name=None, alias=None,
        kind=ImportKind.MODULE, lineno=1, col_offset=0,
    )
    fr.unused = [UnusedImport(import_info=imp)]
    report = CleanReport(root=Path("."))
    report.file_reports.append(fr)
    return report


class TestJsonReporter:
    def test_output_is_valid_json(self):
        report = _make_report_with_unused()
        jr = JsonReporter()
        output = jr.to_json(report)
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_summary_present(self):
        report = _make_report_with_unused()
        jr = JsonReporter()
        data = json.loads(jr.to_json(report))
        assert "summary" in data
        assert "files" in data["summary"]

    def test_files_key_present(self):
        report = _make_report_with_unused()
        jr = JsonReporter()
        data = json.loads(jr.to_json(report))
        assert "files" in data
        assert isinstance(data["files"], list)

    def test_unused_entry_has_line(self):
        report = _make_report_with_unused()
        jr = JsonReporter()
        data = json.loads(jr.to_json(report))
        file_entry = data["files"][0]
        assert file_entry["unused"][0]["line"] == 1

    def test_clean_report_empty(self):
        report = CleanReport(root=Path("."))
        jr = JsonReporter()
        data = json.loads(jr.to_json(report))
        assert data["files"] == []

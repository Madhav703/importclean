"""Tests for data models."""

from __future__ import annotations

from pathlib import Path

from importclean.models import (
    CircularImport,
    CleanReport,
    FileReport,
    ImportInfo,
    ImportKind,
    UnusedImport,
)


class TestImportInfo:
    def test_effective_name_alias(self):
        imp = ImportInfo(
            module="numpy", name=None, alias="np",
            kind=ImportKind.MODULE, lineno=1, col_offset=0,
        )
        assert imp.effective_name == "np"

    def test_effective_name_name(self):
        imp = ImportInfo(
            module="os", name="path", alias=None,
            kind=ImportKind.FROM, lineno=1, col_offset=0,
        )
        assert imp.effective_name == "path"

    def test_effective_name_module_root(self):
        imp = ImportInfo(
            module="os.path", name=None, alias=None,
            kind=ImportKind.MODULE, lineno=1, col_offset=0,
        )
        assert imp.effective_name == "os"

    def test_str_module_import(self):
        imp = ImportInfo(
            module="os", name=None, alias=None,
            kind=ImportKind.MODULE, lineno=1, col_offset=0,
        )
        assert str(imp) == "import os"

    def test_str_from_import(self):
        imp = ImportInfo(
            module="pathlib", name="Path", alias=None,
            kind=ImportKind.FROM, lineno=1, col_offset=0,
        )
        assert str(imp) == "from pathlib import Path"

    def test_str_aliased_import(self):
        imp = ImportInfo(
            module="numpy", name=None, alias="np",
            kind=ImportKind.MODULE, lineno=1, col_offset=0,
        )
        assert str(imp) == "import numpy as np"


class TestCleanReport:
    def _make_report(self, unused=0, dups=0, modified=False):
        fr = FileReport(path=Path("test.py"))
        imp = ImportInfo(
            module="os", name=None, alias=None,
            kind=ImportKind.MODULE, lineno=1, col_offset=0,
        )
        fr.unused = [UnusedImport(import_info=imp) for _ in range(unused)]
        fr.modified = modified
        report = CleanReport(root=Path("."))
        report.file_reports.append(fr)
        return report

    def test_files_scanned(self):
        r = self._make_report()
        assert r.files_scanned == 1

    def test_total_unused(self):
        r = self._make_report(unused=3)
        assert r.total_unused == 3

    def test_files_modified(self):
        r = self._make_report(modified=True)
        assert r.files_modified == 1

    def test_to_dict_keys(self):
        r = self._make_report()
        d = r.to_dict()
        assert "files" in d
        assert "modified" in d
        assert "unused_imports" in d
        assert "duplicates" in d

    def test_summary_string(self):
        r = self._make_report(unused=2)
        r.finish()
        summary = r.summary()
        assert "2" in summary
        assert "seconds" in summary

    def test_circular_import_str(self):
        ci = CircularImport(cycle=["a", "b", "c", "a"])
        assert "→" in str(ci)
        assert "a" in str(ci)

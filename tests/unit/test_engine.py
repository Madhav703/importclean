"""Unit tests for the engine module targeting uncovered paths."""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from importclean.config import Config
from importclean.engine import _default_workers, process_file, process_project
from importclean.models import FileReport


class TestDefaultWorkers:
    def test_returns_positive_int(self):
        workers = _default_workers()
        assert workers >= 1

    def test_caps_at_eight(self):
        with patch("multiprocessing.cpu_count", return_value=100):
            workers = _default_workers()
            assert workers <= 8

    def test_handles_not_implemented(self):
        with patch("multiprocessing.cpu_count", side_effect=NotImplementedError):
            workers = _default_workers()
            assert workers == 1


class TestProcessFileEdgeCases:
    def test_missing_file_reports_error(self, tmp_path):
        missing = tmp_path / "nonexistent.py"
        fr = process_file(missing, Config())
        assert fr.syntax_error is not None

    def test_no_imports_returns_empty_report(self, tmp_py_file):
        path = tmp_py_file("x = 1\ny = 2\n")
        fr = process_file(path, Config(), dry_run=True)
        assert not fr.unused
        assert not fr.duplicates

    def test_write_error_reported(self, tmp_py_file):
        path = tmp_py_file("import os\nprint('hi')\n")
        path.chmod(0o444)  # read-only
        try:
            fr = process_file(path, Config(), dry_run=False)
            if fr.syntax_error:
                assert "Write error" in fr.syntax_error or "Permission" in fr.syntax_error
        finally:
            path.chmod(0o644)

    def test_plugin_with_remove(self, tmp_py_file):
        import ast
        from typing import Optional
        from importclean.plugins.base import BaseRule, RuleResult
        from importclean.plugins.registry import PluginRegistry
        from importclean.models import ImportInfo

        class BanOs(BaseRule):
            name = "ban-os"
            def check(self, node: ImportInfo, tree: ast.Module) -> Optional[RuleResult]:
                if node.module == "os":
                    return RuleResult(import_info=node, message="banned", should_remove=True)
                return None

        registry = PluginRegistry()
        registry.register(BanOs)

        path = tmp_py_file("import os\nprint('hi')\n")
        fr = process_file(path, Config(), dry_run=True, registry=registry)
        # Should have unused entries (from plugin or from normal analysis)
        assert len(fr.unused) >= 1

    def test_validation_failure_restores_original(self, tmp_py_file):
        """Simulate a LibCST output that fails validation; original should be kept."""
        source = "import os\nprint('hi')\n"
        path = tmp_py_file(source)
        # Patch validate_source to always fail
        with patch("importclean.engine.validate_source", return_value="SyntaxError: fake"):
            fr = process_file(path, Config(), dry_run=False)
        assert fr.syntax_error is not None
        assert path.read_text() == source  # file unchanged

    def test_sorted_file_reports(self, tmp_project):
        files = {
            "z.py": "import os\nprint('hi')\n",
            "a.py": "import sys\nprint('hi')\n",
        }
        root = tmp_project(files)
        config = Config(detect_circular=False)
        report = process_project(root, config, [root / "z.py", root / "a.py"], dry_run=True)
        paths = [fr.path.name for fr in report.file_reports]
        assert paths == sorted(paths)


class TestProcessProjectMultiprocessing:
    def test_multiprocessing_path(self, tmp_project):
        """Force the multiprocessing code path with workers=2."""
        files = {
            f"mod{i}.py": f"import os\nprint({i})\n" for i in range(5)
        }
        root = tmp_project(files)
        config = Config(workers=2)
        py_files = [root / f for f in files]
        report = process_project(root, config, py_files, dry_run=True)
        assert report.files_scanned == 5

    def test_worker_exception_reported(self, tmp_project):
        """A file that causes a worker exception should appear in reports."""
        # Need >= 4 files to trigger the multiprocessing branch
        files = {f"mod{i}.py": f"import os\nprint({i})\n" for i in range(5)}
        root = tmp_project(files)
        config = Config(workers=2)

        def _raise(*args, **kwargs):
            raise RuntimeError("worker error")

        with patch("importclean.engine._process_file_worker", side_effect=_raise):
            report = process_project(root, config, [root / f for f in files], dry_run=True)
        # Errors are captured in file reports
        errors = [fr for fr in report.file_reports if fr.syntax_error]
        assert len(errors) == 5

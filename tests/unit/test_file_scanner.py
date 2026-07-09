"""Tests for the recursive file scanner."""

from __future__ import annotations

from pathlib import Path

import pytest

from importclean.utils.file_scanner import FileScanner


def make_scanner(**extra_ignore):
    from importclean.config import _DEFAULT_IGNORE_DIRS

    ignore = frozenset(_DEFAULT_IGNORE_DIRS)
    return FileScanner(ignore)


class TestFileScanner:
    def test_scans_py_files(self, tmp_project):
        root = tmp_project({"a.py": "x=1\n", "b.py": "y=2\n"})
        scanner = make_scanner()
        files = scanner.scan(root)
        names = {f.name for f in files}
        assert "a.py" in names
        assert "b.py" in names

    def test_skips_non_py_files(self, tmp_project):
        root = tmp_project({"a.py": "x=1\n", "readme.md": "# hi\n"})
        scanner = make_scanner()
        files = scanner.scan(root)
        assert all(f.suffix == ".py" for f in files)

    def test_skips_hidden_directories(self, tmp_project):
        root = tmp_project({".hidden/secret.py": "x=1\n", "main.py": "y=2\n"})
        scanner = make_scanner()
        files = scanner.scan(root)
        names = {f.name for f in files}
        assert "secret.py" not in names
        assert "main.py" in names

    def test_skips_venv_directory(self, tmp_project):
        root = tmp_project({".venv/lib/site.py": "x=1\n", "app.py": "y=2\n"})
        scanner = make_scanner()
        files = scanner.scan(root)
        names = {f.name for f in files}
        assert "site.py" not in names
        assert "app.py" in names

    def test_recursive_scan(self, tmp_project):
        root = tmp_project({
            "pkg/__init__.py": "",
            "pkg/utils.py": "x=1\n",
            "main.py": "y=2\n",
        })
        scanner = make_scanner()
        files = scanner.scan(root)
        assert len(files) == 3

    def test_single_file_scan(self, tmp_py_file):
        path = tmp_py_file("import os\n")
        scanner = make_scanner()
        files = scanner.scan(path)
        assert files == [path]

    def test_non_python_single_file_empty(self, tmp_path):
        f = tmp_path / "readme.md"
        f.write_text("hi")
        scanner = make_scanner()
        assert scanner.scan(f) == []

    def test_returns_sorted_paths(self, tmp_project):
        root = tmp_project({"z.py": "", "a.py": "", "m.py": ""})
        scanner = make_scanner()
        files = scanner.scan(root)
        assert files == sorted(files)

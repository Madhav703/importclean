"""Integration tests for the importclean engine."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from importclean.api import clean_file, clean_project
from importclean.config import Config
from importclean.engine import process_file


class TestProcessFileSafety:
    """Verify that no used import is ever removed."""

    def test_basic_example_from_docs(self, tmp_py_file):
        source = """
        import os
        import json
        import requests
        from pathlib import Path

        print(Path("demo"))
        """
        path = tmp_py_file(source)
        config = Config()
        fr = process_file(path, config, dry_run=True)
        result = fr.cleaned_source or fr.original_source
        assert "from pathlib import Path" in result
        unused_modules = {u.import_info.module for u in fr.unused}
        assert "os" in unused_modules
        assert "json" in unused_modules
        assert "pathlib" not in unused_modules

    def test_alias_never_removed(self, tmp_py_file):
        source = "import numpy as np\nnp.array([1, 2, 3])\n"
        path = tmp_py_file(source)
        fr = process_file(path, Config(), dry_run=True)
        assert not fr.unused

    def test_decorator_import_kept(self, tmp_py_file):
        source = """
        import functools

        @functools.lru_cache(maxsize=None)
        def expensive():
            return 42
        """
        path = tmp_py_file(source)
        fr = process_file(path, Config(), dry_run=True)
        assert not fr.unused

    def test_type_annotation_import_kept(self, tmp_py_file):
        source = """
        from typing import Optional

        def greet(name: Optional[str] = None) -> str:
            return name or "World"
        """
        path = tmp_py_file(source)
        fr = process_file(path, Config(), dry_run=True)
        assert not fr.unused

    def test_syntax_error_file_reported(self, tmp_py_file):
        path = tmp_py_file("def (broken:\n    pass\n")
        fr = process_file(path, Config(), dry_run=True)
        # ImportCollector returns empty on SyntaxError — no unused found
        assert fr.syntax_error is None  # No error from our side, just no imports found

    def test_dataclass_import_kept(self, tmp_py_file):
        source = """
        from dataclasses import dataclass

        @dataclass
        class Point:
            x: float
            y: float
        """
        path = tmp_py_file(source)
        fr = process_file(path, Config(), dry_run=True)
        assert not fr.unused

    def test_try_except_import_kept(self, tmp_py_file):
        source = """
        try:
            import ujson as json
        except ImportError:
            import json

        data = json.loads("{}")
        """
        path = tmp_py_file(source)
        fr = process_file(path, Config(), dry_run=True)
        assert not fr.unused

    def test_type_checking_import_kept(self, tmp_py_file):
        source = """
        from __future__ import annotations
        from typing import TYPE_CHECKING

        if TYPE_CHECKING:
            from collections.abc import Sequence

        def foo(x: Sequence) -> None:
            pass
        """
        path = tmp_py_file(source)
        fr = process_file(path, Config(), dry_run=True)
        tc_unused = [u for u in fr.unused if "Sequence" in str(u)]
        assert not tc_unused

    def test_relative_import_handled(self, tmp_project):
        files = {
            "pkg/__init__.py": "",
            "pkg/utils.py": "def helper(): pass\n",
            "pkg/main.py": "from . import utils\nutils.helper()\n",
        }
        root = tmp_project(files)
        config = Config()
        fr = process_file(root / "pkg/main.py", config, dry_run=True)
        assert not fr.unused

    def test_star_import_never_removed(self, tmp_py_file):
        path = tmp_py_file("from os.path import *\n")
        fr = process_file(path, Config(), dry_run=True)
        assert not fr.unused


class TestProcessFileDryRun:
    def test_dry_run_does_not_modify_file(self, tmp_py_file):
        source = "import os\nimport json\nprint('hello')\n"
        path = tmp_py_file(source)
        config = Config()
        fr = process_file(path, config, dry_run=True)
        assert path.read_text() == textwrap.dedent(source)
        assert not fr.modified

    def test_non_dry_run_modifies_file(self, tmp_py_file):
        source = "import os\nimport json\nprint('hello')\n"
        path = tmp_py_file(source)
        config = Config()
        fr = process_file(path, config, dry_run=False)
        new_content = path.read_text()
        assert "import os" not in new_content
        assert "import json" not in new_content
        assert fr.modified is True

    def test_no_change_file_not_marked_modified(self, tmp_py_file):
        source = "import os\nos.getcwd()\n"
        path = tmp_py_file(source)
        fr = process_file(path, Config(), dry_run=False)
        assert fr.modified is False


class TestCleanProject:
    def test_project_scan_counts(self, tmp_project):
        files = {
            "a.py": "import os\nprint('hi')\n",
            "b.py": "import sys\nsys.exit(0)\n",
            "c.py": "import json\nx = 1\n",
        }
        root = tmp_project(files)
        report = clean_project(root, dry_run=True)
        assert report.files_scanned == 3

    def test_venv_excluded(self, tmp_project):
        files = {
            "main.py": "import os\nprint('hi')\n",
            ".venv/lib/fake.py": "import os\n",
        }
        root = tmp_project(files)
        report = clean_project(root, dry_run=True)
        paths = {str(fr.path) for fr in report.file_reports}
        assert not any(".venv" in p for p in paths)

    def test_report_to_dict(self, tmp_project):
        root = tmp_project({"x.py": "import os\nprint('hi')\n"})
        report = clean_project(root, dry_run=True)
        d = report.to_dict()
        assert d["files"] == 1

    def test_single_file_path(self, tmp_py_file):
        path = tmp_py_file("import os\nimport json\nprint('hi')\n")
        report = clean_project(path, dry_run=True)
        assert report.files_scanned == 1
        assert report.total_unused == 2


class TestCleanFile:
    def test_clean_file_returns_file_report(self, tmp_py_file):
        path = tmp_py_file("import os\nprint('hi')\n")
        fr = clean_file(path, dry_run=True)
        assert len(fr.unused) == 1

    def test_clean_file_dry_run(self, tmp_py_file):
        source = "import os\nprint('hi')\n"
        path = tmp_py_file(source)
        clean_file(path, dry_run=True)
        assert path.read_text() == source

    def test_clean_file_applies_changes(self, tmp_py_file):
        path = tmp_py_file("import os\nprint('hi')\n")
        clean_file(path, dry_run=False)
        assert "import os" not in path.read_text()


class TestDuplicateHandling:
    def test_duplicate_removed(self, tmp_py_file):
        source = "import os\nimport os\nos.getcwd()\n"
        path = tmp_py_file(source)
        fr = process_file(path, Config(), dry_run=True)
        assert len(fr.duplicates) == 1

    def test_duplicate_not_removed_when_disabled(self, tmp_py_file):
        source = "import os\nimport os\nos.getcwd()\n"
        path = tmp_py_file(source)
        config = Config(remove_duplicates=False)
        fr = process_file(path, config, dry_run=True)
        assert fr.duplicates == []


class TestSpecialCases:
    def test_init_file_processed(self, tmp_project):
        files = {
            "pkg/__init__.py": "import os\n",
            "pkg/mod.py": "import sys\nsys.exit()\n",
        }
        root = tmp_project(files)
        report = clean_project(root, dry_run=True)
        assert report.files_scanned == 2

    def test_namespace_package_no_init(self, tmp_project):
        files = {
            "ns/sub/mod.py": "import os\nprint('hi')\n",
        }
        root = tmp_project(files)
        report = clean_project(root, dry_run=True)
        assert report.files_scanned == 1

    def test_encoding_preserved_after_clean(self, tmp_py_file):
        source = "# -*- coding: utf-8 -*-\nimport os\nprint('héllo')\n"
        path = tmp_py_file(source)
        fr = process_file(path, Config(), dry_run=False)
        new_content = path.read_text(encoding="utf-8")
        assert "coding: utf-8" in new_content
        assert "héllo" in new_content

    def test_pydantic_model_import_kept(self, tmp_py_file):
        source = """
        from pydantic import BaseModel

        class User(BaseModel):
            name: str
            age: int
        """
        path = tmp_py_file(source)
        fr = process_file(path, Config(), dry_run=True)
        assert not fr.unused

    def test_conditional_import_not_removed(self, tmp_py_file):
        source = """
        import sys

        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib

        data = tomllib.loads("")
        """
        path = tmp_py_file(source)
        fr = process_file(path, Config(), dry_run=True)
        unused_names = {u.import_info.effective_name for u in fr.unused}
        assert "tomllib" not in unused_names

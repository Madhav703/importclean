"""Integration tests for the CLI."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
from click.testing import CliRunner

from importclean.cli import main


@pytest.fixture
def runner():
    return CliRunner()


class TestCLIBasic:
    def test_help_exits_zero(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "importclean" in result.output.lower()

    def test_version_flag(self, runner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0

    def test_nonexistent_path_exits_nonzero(self, runner):
        result = runner.invoke(main, ["/does/not/exist"])
        assert result.exit_code != 0

    def test_clean_single_file(self, runner, tmp_py_file):
        path = tmp_py_file("import os\nimport json\nprint('hello')\n")
        result = runner.invoke(main, [str(path)])
        assert result.exit_code in (0, 1)
        content = path.read_text()
        assert "import os" not in content

    def test_check_mode_no_issues(self, runner, tmp_py_file):
        path = tmp_py_file("import os\nos.getcwd()\n")
        result = runner.invoke(main, [str(path), "--check"])
        assert result.exit_code == 0

    def test_check_mode_finds_issues(self, runner, tmp_py_file):
        path = tmp_py_file("import os\nprint('hi')\n")
        result = runner.invoke(main, [str(path), "--check"])
        assert result.exit_code == 1

    def test_dry_run_no_file_modification(self, runner, tmp_py_file):
        source = "import os\nprint('hi')\n"
        path = tmp_py_file(source)
        runner.invoke(main, [str(path), "--dry-run"])
        assert path.read_text() == source

    def test_diff_mode(self, runner, tmp_py_file):
        path = tmp_py_file("import os\nprint('hi')\n")
        result = runner.invoke(main, [str(path), "--diff"])
        assert result.exit_code == 0

    def test_stats_mode(self, runner, tmp_py_file):
        path = tmp_py_file("import os\nprint('hi')\n")
        result = runner.invoke(main, [str(path), "--stats"])
        assert result.exit_code == 0

    def test_json_output(self, runner, tmp_py_file):
        path = tmp_py_file("import os\nprint('hi')\n")
        result = runner.invoke(main, [str(path), "--json"])
        assert result.exit_code == 0
        # Find JSON in output
        out = result.output.strip()
        # rich may add ANSI; strip and find the JSON blob
        import re
        ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
        clean_out = ansi_escape.sub('', out)
        data = json.loads(clean_out)
        assert "summary" in data

    def test_verify_valid_file(self, runner, tmp_py_file):
        path = tmp_py_file("import os\nos.getcwd()\n")
        result = runner.invoke(main, [str(path), "--verify"])
        assert result.exit_code == 0

    def test_verify_invalid_file(self, runner, tmp_py_file):
        path = tmp_py_file("def (broken:\n    pass\n")
        result = runner.invoke(main, [str(path), "--verify"])
        assert result.exit_code == 1

    def test_sort_flag(self, runner, tmp_py_file):
        path = tmp_py_file("import sys\nimport os\nsys.exit(0)\nos.getcwd()\n")
        result = runner.invoke(main, [str(path), "--sort"])
        assert result.exit_code == 0


class TestCLIGraph:
    def test_graph_mode(self, runner, tmp_project):
        files = {
            "main.py": "import utils\n",
            "utils.py": "x = 1\n",
        }
        root = tmp_project(files)
        result = runner.invoke(main, [str(root), "--graph"])
        assert result.exit_code == 0

    def test_graph_dot_output(self, runner, tmp_project):
        files = {
            "a.py": "import b\n",
            "b.py": "x = 1\n",
        }
        root = tmp_project(files)
        dot_path = str(root / "graph.dot")
        result = runner.invoke(main, [str(root), "--dot", dot_path])
        assert result.exit_code == 0
        assert (root / "graph.dot").exists()


class TestCLIProject:
    def test_no_py_files(self, runner, tmp_path):
        (tmp_path / "readme.md").write_text("# hi")
        result = runner.invoke(main, [str(tmp_path)])
        assert result.exit_code == 0

    def test_scan_directory(self, runner, tmp_project):
        files = {
            "a.py": "import os\nprint('hi')\n",
            "b.py": "import sys\nsys.exit(0)\n",
        }
        root = tmp_project(files)
        result = runner.invoke(main, [str(root)])
        assert result.exit_code in (0, 1)

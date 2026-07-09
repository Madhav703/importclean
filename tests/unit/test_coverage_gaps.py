"""Tests targeting specific coverage gaps identified by coverage.py."""

from __future__ import annotations

import ast
import sys
import textwrap
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import pytest

from importclean.analyzers.circular_detector import CircularImportDetector
from importclean.analyzers.import_collector import ImportCollector
from importclean.analyzers.usage_analyzer import UsageAnalyzer
from importclean.config import Config, load_config
from importclean.models import ImportInfo, ImportKind
from importclean.reporters.graph import DependencyGraph
from importclean.transformers.import_remover import (
    ImportRemover,
    _alias_asname,
    _alias_name,
    remove_imports,
)
from importclean.transformers.import_sorter import sort_imports
from importclean.utils.file_scanner import FileScanner
from importclean.utils.validator import validate_source


# ---------------------------------------------------------------------------
# import_collector.py — TryStar (Python 3.11+), async function
# ---------------------------------------------------------------------------


class TestImportCollectorEdges:
    def test_async_function_import(self):
        source = "async def foo():\n    import os\n"
        imports = ImportCollector.collect(source)
        assert imports[0].is_in_function is True

    def test_import_at_class_level(self):
        source = "class Foo:\n    import os\n"
        imports = ImportCollector.collect(source)
        assert imports[0].is_in_class is True
        assert imports[0].is_in_function is False

    def test_nested_if_conditional(self):
        source = "if True:\n    if True:\n        import os\n"
        imports = ImportCollector.collect(source)
        assert imports[0].is_conditional is True

    def test_from_relative_no_module(self):
        source = "from . import utils\n"
        imports = ImportCollector.collect(source)
        assert imports[0].kind == ImportKind.RELATIVE
        assert imports[0].module == "."


# ---------------------------------------------------------------------------
# usage_analyzer.py — Constant, AnnAssign, async function
# ---------------------------------------------------------------------------


class TestUsageAnalyzerEdges:
    def test_ann_assign_with_value(self):
        source = "from typing import List\nx: List[int] = []\n"
        used = UsageAnalyzer.collect_used(source)
        assert "List" in used

    def test_ann_assign_without_value(self):
        source = "from typing import Optional\nx: Optional[str]\n"
        used = UsageAnalyzer.collect_used(source)
        assert "Optional" in used

    def test_async_function_annotations(self):
        source = textwrap.dedent("""
        from typing import Awaitable
        async def foo() -> Awaitable[int]:
            pass
        """)
        used = UsageAnalyzer.collect_used(source)
        assert "Awaitable" in used

    def test_kwonly_arg_annotation(self):
        source = textwrap.dedent("""
        from typing import Optional
        def foo(*, x: Optional[int] = None) -> None:
            pass
        """)
        used = UsageAnalyzer.collect_used(source)
        assert "Optional" in used

    def test_vararg_annotation(self):
        source = textwrap.dedent("""
        from typing import Any
        def foo(*args: Any) -> None:
            pass
        """)
        used = UsageAnalyzer.collect_used(source)
        assert "Any" in used

    def test_kwarg_annotation(self):
        source = textwrap.dedent("""
        from typing import Any
        def foo(**kwargs: Any) -> None:
            pass
        """)
        used = UsageAnalyzer.collect_used(source)
        assert "Any" in used

    def test_syntax_error_returns_empty_set(self):
        result = UsageAnalyzer.collect_used("def (broken:")
        assert result == set()


# ---------------------------------------------------------------------------
# import_remover.py — ImportStar, non-list names, exception in metadata
# ---------------------------------------------------------------------------


class TestImportRemoverEdges:
    def test_star_import_not_removed(self):
        source = "from os.path import *\n"
        imp = ImportInfo(
            module="os.path", name="*", alias=None,
            kind=ImportKind.FROM_STAR, lineno=1, col_offset=0,
        )
        result = remove_imports(source, [imp], [])
        assert "import *" in result

    def test_import_names_not_sequence_kept(self):
        # ImportStar object instead of sequence — should be kept as-is
        source = "from os import *\n"
        result = remove_imports(source, [], [])
        assert result == source

    def test_exception_in_metadata_returns_original(self):
        source = "import os\nprint('hi')\n"
        imp = ImportInfo(
            module="os", name=None, alias=None,
            kind=ImportKind.MODULE, lineno=1, col_offset=0,
        )
        with patch("libcst.metadata.MetadataWrapper", side_effect=RuntimeError("test")):
            result = remove_imports(source, [imp], [])
        assert result == source

    def test_alias_name_attribute_chain(self):
        import libcst as cst
        # "import a.b.c as x"
        stmt = cst.parse_statement("import a.b\n")
        alias = stmt.body[0].names[0]  # type: ignore[index]
        name = _alias_name(alias)
        assert name == "a.b"

    def test_alias_asname_non_name_inner(self):
        import libcst as cst
        alias = cst.parse_statement("import os\n").body[0].names[0]  # type: ignore[index]
        # No asname — should return ""
        assert _alias_asname(alias) == ""


# ---------------------------------------------------------------------------
# import_sorter.py — empty import ranges, non-backslash multiline
# ---------------------------------------------------------------------------


class TestImportSorterEdges:
    def test_empty_string(self):
        assert sort_imports("") == ""

    def test_comment_only(self):
        source = "# just a comment\n"
        result = sort_imports(source)
        # May return same or rearranged, but should not crash
        assert "comment" in result

    def test_sorts_third_party_after_stdlib(self):
        source = "import requests\nimport os\nimport sys\n"
        result = sort_imports(source)
        os_pos = result.index("import os")
        req_pos = result.index("import requests")
        assert os_pos < req_pos


# ---------------------------------------------------------------------------
# circular_detector.py — build_graph with __init__.py, permission error
# ---------------------------------------------------------------------------


class TestCircularDetectorEdges:
    def test_init_module_path(self, tmp_project):
        files = {
            "pkg/__init__.py": "import os\n",
            "pkg/mod.py": "from . import mod\n",
        }
        root = tmp_project(files)
        detector = CircularImportDetector(root)
        py_files = [root / "pkg/__init__.py", root / "pkg/mod.py"]
        detector.build_graph(py_files)
        assert "pkg" in detector.graph

    def test_file_outside_root_uses_stem(self, tmp_path):
        other_root = tmp_path / "other"
        other_root.mkdir()
        f = tmp_path / "standalone.py"
        f.write_text("import os\n")
        detector = CircularImportDetector(other_root)
        mod = detector._path_to_module(f)
        assert mod == "standalone"

    def test_no_cycles_empty_graph(self):
        detector = CircularImportDetector(Path("."))
        cycles = detector.detect_cycles()
        assert cycles == []


# ---------------------------------------------------------------------------
# graph_reporter.py — from_detector, render_tree single entry
# ---------------------------------------------------------------------------


class TestGraphReporterEdges:
    def test_from_detector(self):
        from importclean.analyzers.circular_detector import CircularImportDetector
        detector = CircularImportDetector(Path("."))
        dg = DependencyGraph.from_detector(detector)
        assert isinstance(dg, DependencyGraph)

    def test_render_tree_empty_graph(self):
        dg = DependencyGraph({})
        assert dg.render_tree() == ""

    def test_render_tree_with_circular(self):
        # Graph with a self-cycle
        dg = DependencyGraph({"a": {"b"}, "b": {"a"}})
        result = dg.render_tree()
        assert "a" in result

    def test_render_dot_with_special_chars(self):
        dg = DependencyGraph({'module "quoted"': {"other"}})
        dot = dg.render_dot()
        assert "digraph" in dot


# ---------------------------------------------------------------------------
# file_scanner.py — permission error on directory
# ---------------------------------------------------------------------------


class TestFileScannerEdges:
    def test_permission_error_skipped(self, tmp_path):
        restricted = tmp_path / "restricted"
        restricted.mkdir()
        (restricted / "secret.py").write_text("x = 1\n")
        restricted.chmod(0o000)
        try:
            scanner = FileScanner(frozenset())
            files = scanner.scan(tmp_path)
            # Should not raise; restricted dir is silently skipped
            names = {f.name for f in files}
            assert "secret.py" not in names
        finally:
            restricted.chmod(0o755)


# ---------------------------------------------------------------------------
# validator.py — compile() exception path
# ---------------------------------------------------------------------------


class TestValidatorEdges:
    def test_generic_exception_during_compile(self):
        source = "x = 1\n"
        with patch("importclean.utils.validator.compile", side_effect=MemoryError("oom")):
            result = validate_source(source)
        assert result is not None
        assert "MemoryError" in result


# ---------------------------------------------------------------------------
# config.py — tomllib import path (Python < 3.11 shim)
# ---------------------------------------------------------------------------


class TestConfigEdges:
    def test_load_config_invalid_toml(self, tmp_path):
        (tmp_path / ".importclean.toml").write_text("not valid toml [\n")
        with pytest.raises(Exception):
            load_config(tmp_path)

    def test_heavy_modules_property(self):
        config = Config()
        assert "pandas" in config.heavy_modules


# ---------------------------------------------------------------------------
# cli.py — remaining branches
# ---------------------------------------------------------------------------


class TestCLIEdges:
    def test_json_graph_output(self, tmp_project):
        from click.testing import CliRunner
        from importclean.cli import main

        files = {"a.py": "import b\n", "b.py": "x = 1\n"}
        root = tmp_project(files)
        runner = CliRunner()
        result = runner.invoke(main, [str(root), "--graph", "--json"])
        assert result.exit_code == 0

    def test_no_py_files_exits_cleanly(self, tmp_path):
        from click.testing import CliRunner
        from importclean.cli import main

        runner = CliRunner()
        result = runner.invoke(main, [str(tmp_path)])
        assert result.exit_code == 0

    def test_check_mode_with_diff(self, tmp_py_file):
        from click.testing import CliRunner
        from importclean.cli import main

        path = tmp_py_file("import os\nprint('hi')\n")
        runner = CliRunner()
        result = runner.invoke(main, [str(path), "--diff", "--check"])
        # Should exit 1 since there are unused imports
        assert result.exit_code == 1

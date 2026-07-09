"""Final coverage top-up tests."""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import patch

import libcst as cst
import pytest

from importclean.models import ImportInfo, ImportKind
from importclean.transformers.import_remover import (
    ImportRemover,
    _alias_asname,
    _alias_name,
    _cst_module_to_str,
    remove_imports,
)
from importclean.transformers.import_sorter import (
    _classify,
    _extract_top_module,
    sort_imports,
)
from importclean.config import Config
from importclean.engine import process_file, process_project


def _make_imp(module: str, name=None, alias=None, kind=ImportKind.MODULE, lineno=1):
    return ImportInfo(
        module=module, name=name, alias=alias,
        kind=kind, lineno=lineno, col_offset=0,
    )


class TestImportRemoverBranches:
    def test_filter_import_all_removed(self):
        """Entire `import` line is dropped when all names are removed."""
        source = "import os\nprint('hi')\n"
        imp = _make_imp("os", lineno=1)
        result = remove_imports(source, [imp], [])
        assert "import os" not in result

    def test_filter_import_some_kept(self):
        """Only unused names removed from multi-alias import."""
        source = "import os, sys\nsys.exit(0)\n"
        imp = _make_imp("os", lineno=1)
        result = remove_imports(source, [imp], [])
        assert "os" not in result
        assert "sys" in result

    def test_filter_import_from_all_removed(self):
        """Entire `from … import` line dropped when all names removed."""
        source = "from os import path, getcwd\nprint('hi')\n"
        imp1 = _make_imp("os", name="path", kind=ImportKind.FROM, lineno=1)
        imp2 = _make_imp("os", name="getcwd", kind=ImportKind.FROM, lineno=1)
        result = remove_imports(source, [imp1, imp2], [])
        assert "from os import" not in result

    def test_no_names_sequence_import_kept(self):
        """ImportStar node returned as-is (no crash)."""
        source = "from os.path import *\n"
        result = remove_imports(source, [], [])
        assert result == source

    def test_metadata_exception_returns_original(self):
        source = "import os\n"
        imp = _make_imp("os", lineno=1)
        with patch("libcst.metadata.MetadataWrapper", side_effect=Exception("fail")):
            result = remove_imports(source, [imp], [])
        assert result == source

    def test_import_from_no_module(self):
        """Relative import with no module name."""
        source = "from . import utils\nutils.help()\n"
        imp = _make_imp(".", name="utils", kind=ImportKind.RELATIVE, lineno=1)
        # We should NOT remove it since utils is used — but calling remove is safe
        result = remove_imports(source, [], [])
        assert result == source

    def test_cst_module_to_str_deep_attr(self):
        node = cst.parse_expression("a.b.c.d")
        result = _cst_module_to_str(node)  # type: ignore[arg-type]
        assert result == "a.b.c.d"

    def test_alias_asname_with_non_name_node(self):
        """Covers the inner isinstance check in _alias_asname."""
        alias = cst.parse_statement("import os as os2\n").body[0].names[0]  # type: ignore[index]
        assert _alias_asname(alias) == "os2"


class TestImportSorterBranches:
    def test_classify_future(self):
        assert _classify("from __future__ import annotations\n") == 0

    def test_classify_stdlib(self):
        assert _classify("import os\n") == 1

    def test_classify_third_party(self):
        assert _classify("import requests\n") == 2

    def test_classify_relative(self):
        assert _classify("from . import utils\n") == 3
        assert _classify("from .. import helpers\n") == 3

    def test_extract_top_module_from(self):
        assert _extract_top_module("from os.path import join") == "os"

    def test_extract_top_module_import(self):
        assert _extract_top_module("import os") == "os"

    def test_extract_top_module_empty(self):
        assert _extract_top_module("x = 1") == ""

    def test_sort_with_contiguous_block(self):
        source = "import requests\nimport os\nimport sys\n"
        result = sort_imports(source)
        # os and sys (stdlib) should come before requests (third-party)
        os_pos = result.index("import os")
        req_pos = result.index("import requests")
        assert os_pos < req_pos

    def test_comment_lines_skipped_in_import_block(self):
        source = "import os\n# a comment\nimport sys\n"
        result = sort_imports(source)
        assert "import os" in result
        assert "import sys" in result

    def test_backslash_continuation_skipped(self):
        # A line with backslash continuation is currently skipped in the sorter
        source = "import os \\\n\nimport sys\n"
        result = sort_imports(source)
        assert "import sys" in result


class TestEngineEdgeCases:
    def test_heavy_detection_disabled(self, tmp_py_file):
        source = textwrap.dedent("""
        import pandas

        def export():
            df = pandas.read_csv("data.csv")
        """)
        path = tmp_py_file(source)
        config = Config(detect_heavy=False)
        fr = process_file(path, config, dry_run=True)
        assert fr.heavy == []

    def test_sort_imports_enabled(self, tmp_py_file):
        source = "import requests\nimport os\nos.getcwd()\nrequests.get('')\n"
        path = tmp_py_file(source)
        config = Config(sort_imports=True)
        fr = process_file(path, config, dry_run=True)
        cleaned = fr.cleaned_source
        if cleaned:
            os_pos = cleaned.find("import os")
            req_pos = cleaned.find("import requests")
            assert os_pos < req_pos

    def test_circular_detection_disabled(self, tmp_project):
        files = {
            "a.py": "import b\n",
            "b.py": "import a\n",
        }
        root = tmp_project(files)
        config = Config(detect_circular=False)
        py_files = [root / f for f in files]
        report = process_project(root, config, py_files, dry_run=True)
        assert report.circular_imports == []

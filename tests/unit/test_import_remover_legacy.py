"""Tests for legacy ImportRemover and remaining import_remover helpers."""

from __future__ import annotations

import textwrap

import libcst as cst
import pytest

from importclean.models import ImportInfo, ImportKind
from importclean.transformers.import_remover import (
    ImportRemover,
    _alias_asname,
    _alias_name,
    _cst_attr_to_str,
    _cst_module_to_str,
    _fix_alias_commas,
    remove_imports,
)


def _make_imp(module: str, name=None, alias=None, kind=ImportKind.MODULE, lineno=1):
    return ImportInfo(
        module=module, name=name, alias=alias,
        kind=kind, lineno=lineno, col_offset=0,
    )


class TestHelperFunctions:
    def test_alias_name_simple(self):
        alias = cst.parse_statement("import os\n").body[0].names[0]  # type: ignore[index]
        assert _alias_name(alias) == "os"

    def test_alias_asname_with_asname(self):
        alias = cst.parse_statement("import numpy as np\n").body[0].names[0]  # type: ignore[index]
        assert _alias_asname(alias) == "np"

    def test_alias_asname_without(self):
        alias = cst.parse_statement("import os\n").body[0].names[0]  # type: ignore[index]
        assert _alias_asname(alias) == ""

    def test_cst_module_to_str_none(self):
        assert _cst_module_to_str(None) == ""

    def test_cst_module_to_str_name(self):
        node = cst.parse_expression("os")
        assert _cst_module_to_str(node) == "os"  # type: ignore[arg-type]

    def test_cst_module_to_str_attribute(self):
        node = cst.parse_expression("os.path")
        assert _cst_module_to_str(node) == "os.path"  # type: ignore[arg-type]

    def test_cst_attr_to_str(self):
        node = cst.parse_expression("a.b.c")
        assert _cst_attr_to_str(node) == "a.b.c"  # type: ignore[arg-type]

    def test_fix_alias_commas_empty(self):
        assert _fix_alias_commas([]) == []

    def test_fix_alias_commas_removes_trailing(self):
        # Parse "from os import path, getcwd," (trailing comma)
        tree = cst.parse_module("from os import (\n    path,\n    getcwd,\n)\n")
        stmt = tree.body[0].body[0]  # type: ignore[index]
        aliases = list(stmt.names)
        result = _fix_alias_commas(aliases)
        assert result[-1].comma == cst.MaybeSentinel.DEFAULT


class TestRemoveImportsEdgeCases:
    def test_remove_module_import_with_alias(self):
        source = "import numpy as np\nprint('hi')\n"
        imp = _make_imp("numpy", alias="np", lineno=1)
        result = remove_imports(source, [imp], [])
        assert "import numpy" not in result

    def test_remove_from_import_with_alias(self):
        source = "from os import path as p\nprint('hi')\n"
        imp = _make_imp("os", name="path", alias="p", kind=ImportKind.FROM, lineno=1)
        result = remove_imports(source, [imp], [])
        assert "import path" not in result

    def test_libcst_parse_error_returns_original(self):
        # This source cannot be parsed by LibCST either
        source = "x = (\n"
        result = remove_imports(source, [], [])
        assert result == source

    def test_dotted_module_import(self):
        source = "import os.path\nprint('hi')\n"
        imp = _make_imp("os.path", lineno=1)
        result = remove_imports(source, [imp], [])
        assert "import os.path" not in result

    def test_multiple_imports_on_one_line_partial(self):
        source = "import os, sys\nsys.exit(0)\n"
        imp = _make_imp("os", lineno=1)
        result = remove_imports(source, [imp], [])
        assert "import os" not in result
        assert "sys" in result

    def test_import_from_dotted_module(self):
        source = "from os.path import join, exists\njoin('a', 'b')\n"
        imp = _make_imp("os.path", name="exists", kind=ImportKind.FROM, lineno=1)
        result = remove_imports(source, [imp], [])
        assert "exists" not in result
        assert "join" in result

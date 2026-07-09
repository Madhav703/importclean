"""Tests for the ImportCollector AST visitor."""

from __future__ import annotations

import textwrap

import pytest

from importclean.analyzers.import_collector import ImportCollector
from importclean.models import ImportKind


def collect(source: str):
    return ImportCollector.collect(textwrap.dedent(source))


class TestBasicImports:
    def test_simple_module_import(self):
        imports = collect("import os")
        assert len(imports) == 1
        assert imports[0].module == "os"
        assert imports[0].kind == ImportKind.MODULE
        assert imports[0].alias is None

    def test_module_import_with_alias(self):
        imports = collect("import numpy as np")
        assert imports[0].module == "numpy"
        assert imports[0].alias == "np"
        assert imports[0].effective_name == "np"

    def test_from_import(self):
        imports = collect("from pathlib import Path")
        assert imports[0].module == "pathlib"
        assert imports[0].name == "Path"
        assert imports[0].kind == ImportKind.FROM

    def test_from_import_with_alias(self):
        imports = collect("from collections import OrderedDict as OD")
        assert imports[0].alias == "OD"
        assert imports[0].effective_name == "OD"

    def test_multiple_from_imports(self):
        imports = collect("from os import path, mkdir, remove")
        assert len(imports) == 3
        names = {imp.name for imp in imports}
        assert names == {"path", "mkdir", "remove"}

    def test_star_import(self):
        imports = collect("from os.path import *")
        assert imports[0].kind == ImportKind.FROM_STAR

    def test_relative_import(self):
        imports = collect("from . import utils")
        assert imports[0].kind == ImportKind.RELATIVE
        assert imports[0].module == "."

    def test_relative_import_with_module(self):
        imports = collect("from ..models import User")
        assert imports[0].kind == ImportKind.RELATIVE
        assert imports[0].module == "..models"

    def test_future_import(self):
        imports = collect("from __future__ import annotations")
        assert imports[0].module == "__future__"

    def test_multiline_import(self):
        source = """
        from os import (
            path,
            getcwd,
            listdir,
        )
        """
        imports = collect(source)
        assert len(imports) == 3


class TestContextualImports:
    def test_import_inside_function(self):
        source = """
        def foo():
            import os
        """
        imports = collect(source)
        assert imports[0].is_in_function is True

    def test_import_inside_class(self):
        source = """
        class Foo:
            import os
        """
        imports = collect(source)
        assert imports[0].is_in_class is True

    def test_import_inside_if(self):
        source = """
        if True:
            import os
        """
        imports = collect(source)
        assert imports[0].is_conditional is True

    def test_import_inside_try(self):
        source = """
        try:
            import ujson as json
        except ImportError:
            import json
        """
        imports = collect(source)
        assert all(imp.is_conditional for imp in imports)

    def test_type_checking_import(self):
        source = """
        from typing import TYPE_CHECKING
        if TYPE_CHECKING:
            from mymodule import MyType
        """
        imports = collect(source)
        tc_imports = [i for i in imports if i.is_type_checking]
        assert len(tc_imports) == 1
        assert tc_imports[0].name == "MyType"

    def test_import_inside_nested_function(self):
        source = """
        def outer():
            def inner():
                import sys
        """
        imports = collect(source)
        assert imports[0].is_in_function is True

    def test_syntax_error_returns_empty(self):
        imports = collect("def (broken:")
        assert imports == []


class TestLineNumbers:
    def test_lineno_captured(self):
        source = "\nimport os\n"
        imports = collect(source)
        assert imports[0].lineno == 2

    def test_from_import_lineno(self):
        source = "import os\nfrom pathlib import Path\n"
        imports = collect(source)
        assert imports[1].lineno == 2

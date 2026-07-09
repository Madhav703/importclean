"""Tests for the UsageAnalyzer and find_unused_imports."""

from __future__ import annotations

import textwrap

import pytest

from importclean.analyzers.import_collector import ImportCollector
from importclean.analyzers.usage_analyzer import UsageAnalyzer, find_unused_imports
from importclean.models import ImportKind


def analyze(source: str):
    src = textwrap.dedent(source)
    imports = ImportCollector.collect(src)
    used = UsageAnalyzer.collect_used(src)
    unused = find_unused_imports(imports, used)
    return imports, used, unused


class TestUsedNameCollection:
    def test_simple_name_used(self):
        _, used, _ = analyze("import os\nprint(os.getcwd())")
        assert "os" in used

    def test_alias_used(self):
        _, used, _ = analyze("import numpy as np\nnp.array([])")
        assert "np" in used

    def test_decorator_name_collected(self):
        source = """
        import functools
        @functools.wraps
        def foo():
            pass
        """
        _, used, _ = analyze(source)
        assert "functools" in used

    def test_type_annotation_collected(self):
        source = """
        from typing import Optional
        def foo(x: Optional[int]) -> None:
            pass
        """
        _, used, _ = analyze(source)
        assert "Optional" in used

    def test_base_class_collected(self):
        source = """
        import abc
        class Foo(abc.ABC):
            pass
        """
        _, used, _ = analyze(source)
        assert "abc" in used

    def test_import_names_excluded_from_used(self):
        source = "import os\nimport json"
        _, used, _ = analyze(source)
        assert "os" not in used
        assert "json" not in used


class TestFindUnusedImports:
    def test_basic_unused(self):
        _, _, unused = analyze("import os\nimport json\nprint('hello')")
        unused_names = {u.module for u in unused}
        assert "os" in unused_names
        assert "json" in unused_names

    def test_used_import_not_removed(self):
        source = """
        import os
        print(os.getcwd())
        """
        _, _, unused = analyze(source)
        assert not unused

    def test_alias_prevents_removal(self):
        source = """
        import numpy as np
        x = np.array([1, 2, 3])
        """
        _, _, unused = analyze(source)
        assert not unused

    def test_partial_from_import(self):
        source = """
        from os import path, mkdir, remove
        path.join("a", "b")
        """
        _, _, unused = analyze(source)
        unused_names = {u.name for u in unused}
        assert "mkdir" in unused_names
        assert "remove" in unused_names
        assert "path" not in unused_names

    def test_star_import_never_removed(self):
        source = "from os.path import *\n"
        _, _, unused = analyze(source)
        assert not unused

    def test_future_import_never_removed(self):
        source = "from __future__ import annotations\n"
        _, _, unused = analyze(source)
        assert not unused

    def test_type_checking_import_never_removed(self):
        source = """
        from typing import TYPE_CHECKING
        if TYPE_CHECKING:
            from mymod import MyType
        """
        _, _, unused = analyze(source)
        tc = [u for u in unused if getattr(u, "name", None) == "MyType"]
        assert not tc

    def test_conditional_import_never_removed(self):
        source = """
        try:
            import ujson as json
        except ImportError:
            import json
        """
        _, _, unused = analyze(source)
        assert not unused

    def test_all_defined_keeps_imports(self):
        source = """
        from mymod import helper1, helper2
        __all__ = ["helper1", "helper2"]
        """
        _, _, unused = analyze(source)
        assert not unused

    def test_dunder_name_never_removed(self):
        source = "from mymod import __version__\n"
        _, _, unused = analyze(source)
        assert not unused

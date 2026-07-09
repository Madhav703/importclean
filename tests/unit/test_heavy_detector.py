"""Tests for the heavy import detector."""

from __future__ import annotations

import textwrap

from importclean.analyzers.heavy_detector import HeavyImportDetector
from importclean.analyzers.import_collector import ImportCollector
from importclean.config import _HEAVY_MODULES


def detect(source: str):
    src = textwrap.dedent(source)
    imports = ImportCollector.collect(src)
    detector = HeavyImportDetector(_HEAVY_MODULES)
    return detector.detect(src, imports)


class TestHeavyImportDetector:
    def test_no_heavy_imports(self):
        assert detect("import os\nos.getcwd()\n") == []

    def test_global_heavy_only_in_function(self):
        source = """
        import pandas

        def export():
            df = pandas.read_csv("data.csv")
        """
        results = detect(source)
        assert len(results) == 1
        assert "pandas" in results[0].suggestion

    def test_heavy_used_globally_not_flagged(self):
        source = """
        import pandas
        df = pandas.DataFrame()
        """
        results = detect(source)
        assert results == []

    def test_heavy_inside_function_not_flagged(self):
        source = """
        def foo():
            import pandas
            return pandas.read_csv("f.csv")
        """
        results = detect(source)
        assert results == []

    def test_numpy_suggestion(self):
        source = """
        import numpy as np

        def compute():
            return np.array([1, 2, 3])
        """
        results = detect(source)
        assert len(results) == 1
        assert "numpy" in results[0].suggestion

    def test_syntax_error_returns_empty(self):
        results = detect("def (broken:\n")
        assert results == []

"""Tests for the duplicate import detector."""

from __future__ import annotations

import textwrap

from importclean.analyzers.import_collector import ImportCollector
from importclean.utils.duplicate_finder import find_duplicates


def dups(source: str):
    imports = ImportCollector.collect(textwrap.dedent(source))
    return find_duplicates(imports)


class TestDuplicateFinder:
    def test_no_duplicates(self):
        assert dups("import os\nimport sys\n") == []

    def test_duplicate_module_import(self):
        result = dups("import os\nimport os\n")
        assert len(result) == 1
        assert result[0].original.lineno == 1
        assert result[0].duplicate.lineno == 2

    def test_duplicate_from_import(self):
        result = dups("from os import path\nfrom os import path\n")
        assert len(result) == 1

    def test_different_aliases_not_duplicate(self):
        result = dups("import os as o\nimport os as operating_system\n")
        assert result == []

    def test_triple_duplicate(self):
        result = dups("import os\nimport os\nimport os\n")
        assert len(result) == 2

    def test_duplicate_with_alias(self):
        result = dups("import numpy as np\nimport numpy as np\n")
        assert len(result) == 1

    def test_same_name_different_module_not_duplicate(self):
        result = dups("from os import path\nfrom sys import path\n")
        assert result == []

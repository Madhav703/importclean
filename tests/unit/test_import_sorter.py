"""Tests for the import sorter."""

from __future__ import annotations

from importclean.transformers.import_sorter import sort_imports


class TestImportSorter:
    def test_no_imports_unchanged(self):
        source = "x = 1\ny = 2\n"
        assert sort_imports(source) == source

    def test_stdlib_before_third_party(self):
        source = "import requests\nimport os\n"
        result = sort_imports(source)
        os_pos = result.index("import os")
        req_pos = result.index("import requests")
        assert os_pos < req_pos

    def test_future_comes_first(self):
        source = "import os\nfrom __future__ import annotations\n"
        result = sort_imports(source)
        future_pos = result.index("from __future__")
        os_pos = result.index("import os")
        assert future_pos < os_pos

    def test_relative_imports_last(self):
        source = "import os\nfrom . import utils\nimport requests\n"
        result = sort_imports(source)
        rel_pos = result.index("from . import utils")
        os_pos = result.index("import os")
        assert os_pos < rel_pos

    def test_syntax_error_returns_original(self):
        source = "def (broken:\n"
        assert sort_imports(source) == source

    def test_alphabetical_within_group(self):
        source = "import sys\nimport os\nimport abc\n"
        result = sort_imports(source)
        abc_pos = result.index("import abc")
        os_pos = result.index("import os")
        sys_pos = result.index("import sys")
        assert abc_pos < os_pos < sys_pos

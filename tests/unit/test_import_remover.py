"""Tests for the LibCST-based ImportRemover transformer."""

from __future__ import annotations

import textwrap

import pytest

from importclean.analyzers.import_collector import ImportCollector
from importclean.analyzers.usage_analyzer import UsageAnalyzer, find_unused_imports
from importclean.transformers.import_remover import remove_imports


def clean(source: str) -> str:
    src = textwrap.dedent(source)
    imports = ImportCollector.collect(src)
    used = UsageAnalyzer.collect_used(src)
    unused = find_unused_imports(imports, used)
    return remove_imports(src, unused, [])


class TestRemoveUnusedImports:
    def test_removes_single_unused_module(self):
        source = """
        import os
        import json
        from pathlib import Path
        print(Path("demo"))
        """
        result = clean(source)
        assert "import os" not in result
        assert "import json" not in result
        assert "from pathlib import Path" in result

    def test_keeps_used_module(self):
        source = """
        import os
        os.getcwd()
        """
        result = clean(source)
        assert "import os" in result

    def test_partial_from_import_cleanup(self):
        source = """
        from os import path, mkdir, remove
        path.join("a", "b")
        """
        result = clean(source)
        assert "path" in result
        assert "mkdir" not in result
        assert "remove" not in result

    def test_alias_preserved(self):
        source = """
        import numpy as np
        np.array([])
        """
        result = clean(source)
        assert "import numpy as np" in result

    def test_preserves_blank_lines(self):
        source = "import os\n\nimport json\n\nprint('hello')\n"
        result = clean(source)
        assert "import os" not in result
        assert "import json" not in result
        assert "print" in result

    def test_preserves_encoding_comment(self):
        source = "# -*- coding: utf-8 -*-\nimport os\nprint('hi')\n"
        result = clean(source)
        assert "coding: utf-8" in result

    def test_preserves_shebang(self):
        source = "#!/usr/bin/env python3\nimport os\nprint('hi')\n"
        result = clean(source)
        assert "#!/usr/bin/env python3" in result

    def test_multiline_parenthesized_partial(self):
        source = """
        from os import (
            path,
            getcwd,
            listdir,
        )
        path.join("a", "b")
        """
        result = clean(source)
        assert "path" in result
        assert "getcwd" not in result
        assert "listdir" not in result

    def test_no_changes_when_all_used(self):
        source = "import os\nos.getcwd()\n"
        imports = ImportCollector.collect(source)
        used = UsageAnalyzer.collect_used(source)
        unused = find_unused_imports(imports, used)
        result = remove_imports(source, unused, [])
        assert result == source

    def test_invalid_source_returns_original(self):
        source = "def (broken:\n    pass\n"
        result = remove_imports(source, [], [])
        assert result == source


class TestRemoveDuplicates:
    def test_removes_duplicate_import(self):
        source = "import os\nimport os\nos.getcwd()\n"
        imports = ImportCollector.collect(source)
        from importclean.utils.duplicate_finder import find_duplicates

        dups = find_duplicates(imports)
        assert len(dups) == 1
        dup_infos = [d.duplicate for d in dups]
        result = remove_imports(source, [], dup_infos)
        lines = [l for l in result.splitlines() if "import os" in l]
        assert len(lines) == 1

    def test_removes_duplicate_from_import(self):
        source = "from os import path\nfrom os import path\npath.join('a', 'b')\n"
        imports = ImportCollector.collect(source)
        from importclean.utils.duplicate_finder import find_duplicates

        dups = find_duplicates(imports)
        dup_infos = [d.duplicate for d in dups]
        result = remove_imports(source, [], dup_infos)
        lines = [l for l in result.splitlines() if "from os import path" in l]
        assert len(lines) == 1

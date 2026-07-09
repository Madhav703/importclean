"""Tests for the source code validator."""

from __future__ import annotations

from importclean.utils.validator import validate_source


class TestValidateSource:
    def test_valid_source_returns_none(self):
        assert validate_source("import os\nprint(os.getcwd())\n") is None

    def test_syntax_error_returns_message(self):
        result = validate_source("def (broken:\n    pass\n")
        assert result is not None
        assert "SyntaxError" in result

    def test_empty_source_valid(self):
        assert validate_source("") is None

    def test_encoding_declaration_valid(self):
        assert validate_source("# -*- coding: utf-8 -*-\nx = 1\n") is None

    def test_complex_valid_source(self):
        source = """
from __future__ import annotations
from typing import Optional, List

class Foo:
    def bar(self, x: Optional[int] = None) -> List[str]:
        return []
"""
        assert validate_source(source) is None

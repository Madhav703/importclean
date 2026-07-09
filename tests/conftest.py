"""Shared pytest fixtures for importclean tests."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest


@pytest.fixture
def tmp_py_file(tmp_path: Path):
    """Factory fixture: create a temporary .py file with given content."""

    def _make(content: str, name: str = "module.py") -> Path:
        path = tmp_path / name
        path.write_text(textwrap.dedent(content), encoding="utf-8")
        return path

    return _make


@pytest.fixture
def tmp_project(tmp_path: Path):
    """Factory fixture: create a temporary project directory from a dict of files."""

    def _make(files: dict) -> Path:  # type: ignore[type-arg]
        for rel, content in files.items():
            full = tmp_path / rel
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(textwrap.dedent(content), encoding="utf-8")
        return tmp_path

    return _make

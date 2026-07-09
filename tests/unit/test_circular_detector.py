"""Tests for the circular import detector."""

from __future__ import annotations

from pathlib import Path

import pytest

from importclean.analyzers.circular_detector import CircularImportDetector


class TestCircularImportDetector:
    def test_no_cycles(self, tmp_project):
        files = {
            "a.py": "import b\n",
            "b.py": "import c\n",
            "c.py": "x = 1\n",
        }
        root = tmp_project(files)
        detector = CircularImportDetector(root)
        detector.build_graph([root / f for f in files])
        cycles = detector.detect_cycles()
        assert cycles == []

    def test_simple_cycle(self, tmp_project):
        files = {
            "a.py": "import b\n",
            "b.py": "import a\n",
        }
        root = tmp_project(files)
        detector = CircularImportDetector(root)
        py_files = [root / f for f in files]
        detector.build_graph(py_files)
        cycles = detector.detect_cycles()
        assert len(cycles) >= 1

    def test_three_node_cycle(self, tmp_project):
        files = {
            "a.py": "import b\n",
            "b.py": "import c\n",
            "c.py": "import a\n",
        }
        root = tmp_project(files)
        detector = CircularImportDetector(root)
        py_files = [root / f for f in files]
        detector.build_graph(py_files)
        cycles = detector.detect_cycles()
        assert len(cycles) >= 1
        cycle_modules = set(cycles[0].cycle)
        assert len(cycle_modules) >= 3

    def test_cycle_string_representation(self, tmp_project):
        files = {
            "x.py": "import y\n",
            "y.py": "import x\n",
        }
        root = tmp_project(files)
        detector = CircularImportDetector(root)
        detector.build_graph([root / f for f in files])
        cycles = detector.detect_cycles()
        assert len(cycles) >= 1
        s = str(cycles[0])
        assert "→" in s

    def test_syntax_error_file_skipped(self, tmp_project):
        files = {
            "good.py": "import os\n",
            "bad.py": "def (broken:\n",
        }
        root = tmp_project(files)
        detector = CircularImportDetector(root)
        detector.build_graph([root / f for f in files])
        cycles = detector.detect_cycles()
        assert cycles == []

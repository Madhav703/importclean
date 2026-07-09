"""Tests for the dependency graph reporter."""

from __future__ import annotations

from importclean.reporters.graph import DependencyGraph


class TestDependencyGraph:
    def test_empty_graph_tree(self):
        dg = DependencyGraph({})
        result = dg.render_tree()
        assert result == ""

    def test_single_node_tree(self):
        dg = DependencyGraph({"main": {"utils"}})
        result = dg.render_tree()
        assert "main" in result
        assert "utils" in result

    def test_dot_output_contains_arrow(self):
        dg = DependencyGraph({"a": {"b"}})
        dot = dg.render_dot()
        assert "->" in dot
        assert '"a"' in dot
        assert '"b"' in dot

    def test_dot_output_has_digraph(self):
        dg = DependencyGraph({"a": set()})
        dot = dg.render_dot()
        assert dot.startswith("digraph")

    def test_save_dot(self, tmp_path):
        dg = DependencyGraph({"main": {"api", "utils"}})
        out = tmp_path / "graph.dot"
        dg.save_dot(out)
        content = out.read_text()
        assert "digraph" in content
        assert "main" in content

    def test_tree_rooted_at_module(self):
        dg = DependencyGraph({"main": {"api"}, "api": {"utils"}, "utils": set()})
        result = dg.render_tree(root="main")
        assert "main" in result

"""Tests for the plugin system."""

from __future__ import annotations

import ast
from typing import Optional

import pytest

from importclean.models import ImportInfo, ImportKind
from importclean.plugins.base import BaseRule, RuleResult
from importclean.plugins.registry import PluginRegistry


def _make_import(module: str = "os") -> ImportInfo:
    return ImportInfo(
        module=module, name=None, alias=None,
        kind=ImportKind.MODULE, lineno=1, col_offset=0,
    )


class BanOsRule(BaseRule):
    name = "ban-os"

    def check(self, node: ImportInfo, tree: ast.Module) -> Optional[RuleResult]:
        if node.module == "os":
            return RuleResult(import_info=node, message="os is banned", should_remove=True)
        return None


class NeverFireRule(BaseRule):
    name = "never-fire"

    def check(self, node: ImportInfo, tree: ast.Module) -> Optional[RuleResult]:
        return None


class TestPluginRegistry:
    def test_empty_registry(self):
        reg = PluginRegistry()
        assert len(reg) == 0

    def test_register_rule(self):
        reg = PluginRegistry()
        reg.register(BanOsRule)
        assert len(reg) == 1

    def test_rule_fires_on_match(self):
        reg = PluginRegistry()
        reg.register(BanOsRule)
        tree = ast.parse("")
        imp = _make_import("os")
        results = list(reg.run_all(imp, tree))
        assert len(results) == 1
        assert results[0].should_remove is True

    def test_rule_does_not_fire_on_no_match(self):
        reg = PluginRegistry()
        reg.register(BanOsRule)
        tree = ast.parse("")
        imp = _make_import("sys")
        results = list(reg.run_all(imp, tree))
        assert results == []

    def test_never_fire_rule_returns_nothing(self):
        reg = PluginRegistry()
        reg.register(NeverFireRule)
        tree = ast.parse("")
        imp = _make_import("os")
        assert list(reg.run_all(imp, tree)) == []

    def test_multiple_rules(self):
        reg = PluginRegistry()
        reg.register(BanOsRule)
        reg.register(NeverFireRule)
        tree = ast.parse("")
        imp = _make_import("os")
        results = list(reg.run_all(imp, tree))
        assert len(results) == 1

    def test_iterator(self):
        reg = PluginRegistry()
        reg.register(BanOsRule)
        rules = list(reg)
        assert len(rules) == 1
        assert isinstance(rules[0], BanOsRule)

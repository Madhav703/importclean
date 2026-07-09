"""Global plugin registry for importclean rules."""

from __future__ import annotations

import ast
from typing import Iterator, Type

from importclean.models import ImportInfo
from importclean.plugins.base import BaseRule, RuleResult


class PluginRegistry:
    """Register and run custom :class:`BaseRule` plugins.

    Usage::

        registry = PluginRegistry()
        registry.register(MyCustomRule)

        for result in registry.run_all(import_info, tree):
            print(result.message)
    """

    def __init__(self) -> None:
        self._rules: list[BaseRule] = []

    def register(self, rule_class: Type[BaseRule]) -> None:
        """Register a rule class (instantiates it immediately)."""
        instance = rule_class()
        self._rules.append(instance)

    def run_all(
        self,
        import_info: ImportInfo,
        tree: ast.Module,
    ) -> Iterator[RuleResult]:
        """Run every registered rule against *import_info* and yield results."""
        for rule in self._rules:
            result = rule.check(import_info, tree)
            if result is not None:
                yield result

    def __len__(self) -> int:
        return len(self._rules)

    def __iter__(self) -> Iterator[BaseRule]:
        return iter(self._rules)

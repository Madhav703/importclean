"""Example: writing a custom importclean plugin rule.

This example bans direct usage of the ``pickle`` module and suggests
a safer alternative.
"""

import ast
from typing import Optional

from importclean import clean_project
from importclean.models import ImportInfo
from importclean.plugins.base import BaseRule, RuleResult
from importclean.plugins.registry import PluginRegistry


class NoPickleRule(BaseRule):
    """Flag any import of ``pickle`` as a security concern."""

    name = "no-pickle"

    def check(self, node: ImportInfo, tree: ast.Module) -> Optional[RuleResult]:
        if node.module in ("pickle", "cPickle"):
            return RuleResult(
                import_info=node,
                message=(
                    "Avoid importing 'pickle' directly — "
                    "consider 'json' or 'msgpack' for safer serialization."
                ),
                should_remove=False,
            )
        return None


def main() -> None:
    registry = PluginRegistry()
    registry.register(NoPickleRule)

    report = clean_project(
        path=".",
        dry_run=True,
        registry=registry,
    )
    print(report.summary())


if __name__ == "__main__":
    main()

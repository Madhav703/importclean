"""Base class for importclean custom rules."""

from __future__ import annotations

import ast
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from importclean.models import ImportInfo


@dataclass
class RuleResult:
    """Result returned by a custom rule check."""

    import_info: ImportInfo
    message: str
    should_remove: bool = False


class BaseRule(ABC):
    """Abstract base class for custom import rules.

    Subclass this and register your rule with :class:`PluginRegistry`
    to add project-specific import policies::

        from importclean.plugins import BaseRule, RuleResult

        class NoBotocore(BaseRule):
            name = "no-botocore"

            def check(self, node: ImportInfo, tree: ast.Module) -> RuleResult | None:
                if "botocore" in node.module:
                    return RuleResult(
                        import_info=node,
                        message="Prefer boto3 over direct botocore usage.",
                        should_remove=False,
                    )
                return None
    """

    #: Unique rule identifier used in reports.
    name: str = ""

    @abstractmethod
    def check(
        self,
        node: ImportInfo,
        tree: ast.Module,
    ) -> Optional[RuleResult]:
        """Inspect *node* in the context of *tree* and return a result or None."""
        ...

"""LibCST-based transformer that removes unused and duplicate imports."""

from __future__ import annotations

from typing import Optional, Union

import libcst as cst

from importclean.models import ImportInfo


class ImportRemover(cst.CSTTransformer):
    """Position-aware CST transformer that removes specified imports.

    Uses LibCST's :class:`~libcst.metadata.PositionProvider` to match
    import statements to their line numbers, then removes individual
    :class:`~libcst.ImportAlias` entries (partial cleanup) or entire
    :class:`~libcst.SimpleStatementLine` nodes (full removal).

    Blank lines, comments, encoding declarations, and all non-import
    code are left completely untouched.
    """

    METADATA_DEPENDENCIES = (cst.metadata.PositionProvider,)

    def __init__(
        self,
        to_remove: list[ImportInfo],
        duplicates_to_remove: list[ImportInfo],
    ) -> None:
        self._target_lines: dict[int, set[str]] = {}
        for imp in (*to_remove, *duplicates_to_remove):
            self._target_lines.setdefault(imp.lineno, set()).add(self._key(imp))

    @staticmethod
    def _key(imp: ImportInfo) -> str:
        if imp.name:
            return f"{imp.module}:{imp.name}:{imp.alias or ''}"
        return f"{imp.module}::{imp.alias or ''}"

    def leave_SimpleStatementLine(
        self,
        original_node: cst.SimpleStatementLine,
        updated_node: cst.SimpleStatementLine,
    ) -> Union[cst.SimpleStatementLine, cst.RemovalSentinel]:
        try:
            pos = self.get_metadata(cst.metadata.PositionProvider, original_node)
            lineno = pos.start.line
        except Exception:
            return updated_node

        if lineno not in self._target_lines:
            return updated_node

        keys = self._target_lines[lineno]
        new_body = []
        for stmt in updated_node.body:
            result = self._process_stmt(stmt, keys)
            if result is not None:
                new_body.append(result)

        if not new_body:
            return cst.RemovalSentinel.REMOVE
        return updated_node.with_changes(body=new_body)

    def _process_stmt(
        self,
        stmt: cst.BaseSmallStatement,
        keys: set[str],
    ) -> Optional[cst.BaseSmallStatement]:
        if isinstance(stmt, cst.Import):
            return self._filter_import(stmt, keys)
        if isinstance(stmt, cst.ImportFrom):
            return self._filter_import_from(stmt, keys)
        return stmt

    def _filter_import(
        self, node: cst.Import, keys: set[str]
    ) -> Optional[cst.Import]:
        if not isinstance(node.names, (list, tuple)):
            return node
        new_names = [
            a for a in node.names if not self._alias_in_keys(a, module=None, keys=keys)
        ]
        if not new_names:
            return None  # type: ignore[return-value]
        if len(new_names) == len(node.names):
            return node
        return node.with_changes(names=_fix_alias_commas(new_names))

    def _filter_import_from(
        self, node: cst.ImportFrom, keys: set[str]
    ) -> Optional[cst.ImportFrom]:
        if isinstance(node.names, cst.ImportStar):
            return node
        if not isinstance(node.names, (list, tuple)):
            return node
        module = _cst_module_to_str(node.module) if node.module else ""
        new_names = [
            a for a in node.names if not self._alias_in_keys(a, module=module, keys=keys)
        ]
        if not new_names:
            return None  # type: ignore[return-value]
        if len(new_names) == len(node.names):
            return node
        return node.with_changes(names=_fix_alias_commas(new_names))

    def _alias_in_keys(
        self,
        alias: cst.ImportAlias,
        module: Optional[str],
        keys: set[str],
    ) -> bool:
        name = _alias_name(alias)
        asname = _alias_asname(alias)
        if module is not None:
            return f"{module}:{name}:{asname}" in keys
        return f"{name}::{asname}" in keys


def remove_imports(
    source: str,
    to_remove: list[ImportInfo],
    duplicates_to_remove: list[ImportInfo],
) -> str:
    """Return *source* with the specified imports removed.

    Uses LibCST's position metadata to ensure accurate line-number matching.
    Falls back to the original source if transformation fails.
    """
    if not to_remove and not duplicates_to_remove:
        return source

    try:
        wrapper = cst.metadata.MetadataWrapper(cst.parse_module(source))
        transformer = ImportRemover(to_remove, duplicates_to_remove)
        new_tree = wrapper.visit(transformer)
        return new_tree.code
    except Exception:
        return source


def _alias_name(alias: cst.ImportAlias) -> str:
    name_node = alias.name
    if isinstance(name_node, cst.Attribute):
        return _cst_attr_to_str(name_node)
    if isinstance(name_node, cst.Name):
        return name_node.value
    return ""


def _alias_asname(alias: cst.ImportAlias) -> str:
    if alias.asname is None:
        return ""
    asname_node = alias.asname
    if isinstance(asname_node, cst.AsName):
        inner = asname_node.name
        if isinstance(inner, cst.Name):
            return inner.value
    return ""


def _cst_module_to_str(module: Optional[Union[cst.Attribute, cst.Name]]) -> str:
    if module is None:
        return ""
    if isinstance(module, cst.Name):
        return module.value
    if isinstance(module, cst.Attribute):
        return _cst_attr_to_str(module)
    return ""


def _cst_attr_to_str(node: cst.Attribute) -> str:
    parts = []
    current: cst.BaseExpression = node
    while isinstance(current, cst.Attribute):
        parts.append(current.attr.value)
        current = current.value
    if isinstance(current, cst.Name):
        parts.append(current.value)
    return ".".join(reversed(parts))


def _fix_alias_commas(aliases: list[cst.ImportAlias]) -> list[cst.ImportAlias]:
    """Remove trailing comma from the last alias in a list."""
    if not aliases:
        return aliases
    last = aliases[-1]
    if last.comma != cst.MaybeSentinel.DEFAULT:
        aliases[-1] = last.with_changes(comma=cst.MaybeSentinel.DEFAULT)
    return aliases

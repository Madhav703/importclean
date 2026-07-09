# API Reference

## Top-Level Functions

### `clean_project`

```python
from importclean import clean_project

report = clean_project(
    path=".",
    dry_run=False,
    safe_mode=True,
    sort_imports=False,
    remove_unused=True,
    remove_duplicates=True,
    workers=0,
    registry=None,
    config=None,
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `path` | `str \| Path` | `"."` | Root directory or single `.py` file |
| `dry_run` | `bool` | `False` | Preview changes without writing files |
| `safe_mode` | `bool` | `True` | Never remove conditional / TYPE_CHECKING imports |
| `sort_imports` | `bool` | `False` | Sort remaining imports in PEP 8 order |
| `remove_unused` | `bool` | `True` | Remove unused imports |
| `remove_duplicates` | `bool` | `True` | Remove duplicate import statements |
| `workers` | `int` | `0` | Parallel worker count (0 = CPU count) |
| `registry` | `PluginRegistry \| None` | `None` | Custom rule registry |
| `config` | `Config \| None` | `None` | Pre-built config (overrides other params) |

**Returns:** `CleanReport`

---

### `clean_file`

```python
from importclean import clean_file

file_report = clean_file(
    path="src/module.py",
    dry_run=True,
    safe_mode=True,
    sort_imports=False,
    config=None,
)
```

**Returns:** `FileReport`

---

## Data Models

### `CleanReport`

| Attribute | Type | Description |
|---|---|---|
| `root` | `Path` | Project root |
| `file_reports` | `list[FileReport]` | Per-file results |
| `circular_imports` | `list[CircularImport]` | Detected cycles |
| `elapsed` | `float` | Wall-clock seconds |
| `files_scanned` | `int` | Total `.py` files processed |
| `files_modified` | `int` | Files actually changed |
| `total_unused` | `int` | Unused imports removed |
| `total_duplicates` | `int` | Duplicate imports removed |

Methods:
- `summary() -> str` — human-readable summary
- `to_dict() -> dict` — JSON-serializable dictionary

### `FileReport`

| Attribute | Type | Description |
|---|---|---|
| `path` | `Path` | File path |
| `unused` | `list[UnusedImport]` | Unused imports found |
| `duplicates` | `list[DuplicateImport]` | Duplicate imports found |
| `heavy` | `list[HeavyImport]` | Expensive imports |
| `syntax_error` | `str \| None` | Error message if validation failed |
| `modified` | `bool` | Whether the file was written |
| `original_source` | `str` | File content before cleaning |
| `cleaned_source` | `str` | File content after cleaning |

---

## Plugin System

```python
from importclean.plugins.base import BaseRule, RuleResult
from importclean.plugins.registry import PluginRegistry

class MyRule(BaseRule):
    name = "my-rule"

    def check(self, node: ImportInfo, tree: ast.Module) -> RuleResult | None:
        # Return RuleResult to flag, None to pass
        ...

registry = PluginRegistry()
registry.register(MyRule)
report = clean_project(".", registry=registry)
```

---

## Configuration

### `Config`

| Field | Type | Default | Description |
|---|---|---|---|
| `ignore` | `list[str]` | `[]` | Additional dirs to skip |
| `safe_mode` | `bool` | `True` | Conservative removal |
| `sort_imports` | `bool` | `False` | Sort after cleaning |
| `remove_unused` | `bool` | `True` | Remove unused |
| `remove_duplicates` | `bool` | `True` | Remove duplicates |
| `detect_circular` | `bool` | `True` | Detect circular imports |
| `detect_heavy` | `bool` | `True` | Flag heavy imports |
| `suggest_lazy` | `bool` | `True` | Suggest lazy loading |
| `workers` | `int` | `0` | Parallel workers |

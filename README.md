# importclean

**A production-ready Python import cleaner.** Detect and safely remove unused imports from an entire project while preserving code behavior, formatting, and style.

[![PyPI](https://img.shields.io/pypi/v/importclean)](https://pypi.org/project/importclean/)
[![Python](https://img.shields.io/pypi/pyversions/importclean)](https://pypi.org/project/importclean/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/importclean/importclean/actions/workflows/ci.yml/badge.svg)](https://github.com/importclean/importclean/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen)](https://github.com/importclean/importclean)


## Features

- **AST + LibCST analysis** — detects every import variant without reformatting unrelated code
- **Safe by default** — never removes conditional, `TYPE_CHECKING`, `try/except`, or star imports
- **Partial cleanup** — removes only unused names from `from x import a, b, c`
- **Alias detection** — `import numpy as np` is kept when `np` is used
- **Duplicate removal** — collapses repeated identical import statements
- **Circular import detection** — finds cycles across the whole project
- **Dependency graph** — renders ASCII trees and Graphviz `.dot` files
- **Heavy import suggestions** — recommends lazy imports for expensive modules
- **Import sorting** — PEP 8 / isort-compatible grouping
- **Post-clean validation** — every modified file is re-parsed and compiled; originals are restored on failure
- **Multiprocessing** — scales to thousands of files
- **Plugin system** — add custom rules for project-specific policies
- **`.importclean.toml`** configuration


## Installation

```bash
pip install importclean
```

For development:

```bash
git clone https://github.com/Madhav703/importclean
cd importclean
pip install -e ".[dev]"
```


## Quick Start

### CLI

```bash
importclean .

importclean . --dry-run

importclean . --check

# Show unified diffs
importclean . --diff

# Print import dependency graph
importclean . --graph

# Output results as JSON
importclean . --json

# Print statistics only
importclean . --stats

# Verify all files are syntactically valid
importclean . --verify

# Sort imports in PEP 8 order
importclean . --sort

# Write dependency graph as Graphviz .dot
importclean . --dot graph.dot

# Clean a single file
importclean myfile.py

# Verbose output (per-file details)
importclean . -v
```

### Python API

```python
from importclean import clean_project, clean_file

# Clean an entire project (dry run)
report = clean_project(
    path=".",
    dry_run=True,
    safe_mode=True,
)
print(report.summary())

# Clean a single file
file_report = clean_file("src/mymodule.py", dry_run=False)
print(f"Removed {len(file_report.unused)} unused imports")
```


## Configuration

Create `.importclean.toml` in your project root:

```toml
ignore = [
    ".venv",
    "tests",
    "migrations",
]

safe_mode      = true
sort_imports   = true
remove_unused  = true
workers        = 4
```


## Safety Guarantees

importclean will **never**:

- Remove an import that is actually used
- Remove star imports (`from x import *`)
- Remove `__future__` imports
- Remove `TYPE_CHECKING`-guarded imports
- Remove `try/except`-wrapped imports
- Save a file that fails `ast.parse()` or `compile()` after transformation
- Alter any code outside of import statements

If post-clean validation fails, the original file is restored automatically and the error is reported.


## What Gets Removed

| Pattern | Behavior |
|---|---|
| `import os` (unused) | Removed |
| `import os` (used) | Kept |
| `import numpy as np` + `np.array(...)` | Kept |
| `from os import path, mkdir` (only `path` used) | `mkdir` removed |
| `from os.path import *` | **Never removed** |
| Duplicate `import os` | Second occurrence removed |
| `if TYPE_CHECKING: from x import T` | **Never removed** |
| `try: import ujson as json` | **Never removed** |


## Plugin System

```python
import ast
from typing import Optional
from importclean import clean_project
from importclean.models import ImportInfo
from importclean.plugins.base import BaseRule, RuleResult
from importclean.plugins.registry import PluginRegistry

class NoPickleRule(BaseRule):
    name = "no-pickle"

    def check(self, node: ImportInfo, tree: ast.Module) -> Optional[RuleResult]:
        if node.module == "pickle":
            return RuleResult(
                import_info=node,
                message="Prefer json or msgpack over pickle.",
                should_remove=False,
            )
        return None

registry = PluginRegistry()
registry.register(NoPickleRule)

report = clean_project(".", dry_run=True, registry=registry)
```


## Development

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=importclean --cov-report=term-missing

# Lint
ruff check importclean tests

# Type check
mypy importclean

# Format
black importclean tests
```


## License

MIT - see [LICENSE](LICENSE).

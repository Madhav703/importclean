from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[no-redef]

_CONFIG_FILENAME = ".importclean.toml"

_DEFAULT_IGNORE_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        "build",
        "dist",
        ".tox",
        ".eggs",
        "*.egg-info",
        "node_modules",
        ".ruff_cache",
        ".hypothesis",
    }
)

_HEAVY_MODULES = frozenset(
    {
        "pandas",
        "numpy",
        "torch",
        "tensorflow",
        "cv2",
        "sklearn",
        "scipy",
        "matplotlib",
        "seaborn",
        "PIL",
        "Pillow",
        "keras",
        "transformers",
        "datasets",
        "xgboost",
        "lightgbm",
        "statsmodels",
    }
)


@dataclass
class Config:
    """Runtime configuration for importclean."""

    ignore: list[str] = field(default_factory=list)
    safe_mode: bool = True
    sort_imports: bool = False
    remove_unused: bool = True
    remove_duplicates: bool = True
    detect_circular: bool = True
    detect_heavy: bool = True
    suggest_lazy: bool = True
    workers: int = 0
    extra_ignore_dirs: frozenset[str] = field(default_factory=frozenset)

    @property
    def all_ignore_dirs(self) -> frozenset[str]:
        base = set(_DEFAULT_IGNORE_DIRS)
        base.update(self.ignore)
        base.update(self.extra_ignore_dirs)
        return frozenset(base)

    @property
    def heavy_modules(self) -> frozenset[str]:
        return _HEAVY_MODULES


def load_config(root: Path, overrides: Optional[dict] = None) -> Config:  # type: ignore[type-arg]
    """Load configuration from .importclean.toml, applying any CLI overrides."""
    config_path = _find_config(root)
    data: dict = {}  # type: ignore[type-arg]
    if config_path is not None:
        with config_path.open("rb") as fh:
            data = tomllib.load(fh)
    if overrides:
        data.update({k: v for k, v in overrides.items() if v is not None})
    return _parse_config(data)


def _find_config(root: Path) -> Optional[Path]:
    candidate = root / _CONFIG_FILENAME
    if candidate.is_file():
        return candidate
    for parent in root.parents:
        candidate = parent / _CONFIG_FILENAME
        if candidate.is_file():
            return candidate
    return None


def _parse_config(data: dict) -> Config:  # type: ignore[type-arg]
    return Config(
        ignore=data.get("ignore", []),
        safe_mode=data.get("safe_mode", True),
        sort_imports=data.get("sort_imports", False),
        remove_unused=data.get("remove_unused", True),
        remove_duplicates=data.get("remove_duplicates", True),
        detect_circular=data.get("detect_circular", True),
        detect_heavy=data.get("detect_heavy", True),
        suggest_lazy=data.get("suggest_lazy", True),
        workers=data.get("workers", 0),
    )

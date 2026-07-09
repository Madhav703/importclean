# Changelog

All notable changes to importclean are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
importclean uses [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added
- Plugin system for custom import rules
- Import sorting (PEP 8 / isort-compatible)
- Dependency graph rendering (ASCII tree + Graphviz `.dot`)
- Heavy import detection with lazy-load suggestions
- `--verify` CLI flag to check file validity without cleaning
- `--dot` CLI flag to export dependency graph as Graphviz file
- `postTaskExecution` hook support in GitHub Actions

### Changed
- Nothing yet.

### Fixed
- Nothing yet.

---

## [0.1.0] — 2024-01-01

### Added
- Initial release.
- AST-based import collection supporting all import variants.
- LibCST-based source transformation preserving formatting.
- Unused import detection with alias, decorator, and annotation awareness.
- Duplicate import detection and removal.
- Circular import detection via DFS.
- Post-clean validation with automatic rollback on failure.
- Multiprocessing support for large projects.
- `.importclean.toml` configuration file support.
- Rich-based console reporter.
- Unified diff reporter.
- JSON reporter.
- CLI with `--check`, `--diff`, `--dry-run`, `--stats`, `--json`, `--graph`, `--verify`.
- Python library API (`clean_project`, `clean_file`).
- GitHub Actions CI/CD workflow.
- Full pytest test suite targeting ≥95% coverage.

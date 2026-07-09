# Contributing to importclean

Thank you for your interest in contributing! This document covers how to set up your environment, run tests, and submit changes.

---

## Development Setup

```bash
git clone https://github.com/Madhav703/importclean
cd importclean
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

---

## Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=importclean --cov-report=term-missing

# Specific file
pytest tests/unit/test_import_collector.py

# Parallel (faster)
pytest -n auto
```

---

## Code Quality

Before submitting a PR, run:

```bash
ruff check importclean tests        # lint
black --check importclean tests     # formatting
mypy importclean                    # type checking
```

Auto-fix formatting:

```bash
black importclean tests
ruff check --fix importclean tests
```

---

## Branching and PR Guidelines

- Branch from `main` for all changes.
- Branch naming: `feat/short-description`, `fix/short-description`, `docs/short-description`.
- Keep PRs focused — one feature or fix per PR.
- Include tests for every new behavior.
- Update `CHANGELOG.md` under `[Unreleased]`.
- All CI checks must pass before merge.

---

## Adding a New Feature

1. Open an issue describing the feature before starting work.
2. Write a failing test first.
3. Implement the feature.
4. Ensure `pytest --cov` still reports ≥95% coverage.
5. Update `README.md` and `CHANGELOG.md`.
6. Submit a PR.

---

## Reporting Bugs

Please include:
- Python version (`python --version`)
- importclean version (`importclean --version`)
- A minimal reproduction (a snippet or small file that triggers the bug)
- Expected behavior vs. actual behavior

---

## Code of Conduct

Be respectful, constructive, and welcoming. We follow the [Contributor Covenant](https://www.contributor-covenant.org/).

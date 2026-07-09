"""Tests for configuration loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from importclean.config import Config, load_config, _DEFAULT_IGNORE_DIRS


class TestConfigDefaults:
    def test_default_config_values(self):
        config = Config()
        assert config.safe_mode is True
        assert config.sort_imports is False
        assert config.remove_unused is True
        assert config.remove_duplicates is True

    def test_default_ignore_dirs_contains_git(self):
        config = Config()
        assert ".git" in config.all_ignore_dirs

    def test_default_ignore_dirs_contains_venv(self):
        config = Config()
        assert ".venv" in config.all_ignore_dirs

    def test_custom_ignore_merged(self):
        config = Config(ignore=["my_custom_dir"])
        assert "my_custom_dir" in config.all_ignore_dirs
        assert ".git" in config.all_ignore_dirs


class TestConfigLoading:
    def test_load_config_no_file(self, tmp_path):
        config = load_config(tmp_path)
        assert isinstance(config, Config)

    def test_load_config_from_toml(self, tmp_path):
        toml_content = """
ignore = ["tests", "migrations"]
safe_mode = false
sort_imports = true
"""
        (tmp_path / ".importclean.toml").write_text(toml_content)
        config = load_config(tmp_path)
        assert "tests" in config.ignore
        assert config.safe_mode is False
        assert config.sort_imports is True

    def test_overrides_take_precedence(self, tmp_path):
        toml_content = "safe_mode = false\n"
        (tmp_path / ".importclean.toml").write_text(toml_content)
        config = load_config(tmp_path, overrides={"safe_mode": True})
        assert config.safe_mode is True

    def test_workers_configurable(self, tmp_path):
        toml_content = "workers = 4\n"
        (tmp_path / ".importclean.toml").write_text(toml_content)
        config = load_config(tmp_path)
        assert config.workers == 4

"""Tests for config module: data dirs, config loading, project resolution."""

import os
import pytest

from jlcpcb_tool.config import (
    _data_dir,
    find_project_dir,
    get_config,
    get_secret,
    load_global_config,
)


class TestDataDir:
    def test_returns_path(self):
        d = _data_dir()
        assert d.name == "jlcpcb"

    def test_macos_path(self, monkeypatch):
        monkeypatch.setattr("sys.platform", "darwin")
        d = _data_dir()
        assert "Application Support" in str(d) or "jlcpcb" in str(d)

    def test_linux_path(self, monkeypatch):
        monkeypatch.setattr("sys.platform", "linux")
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        d = _data_dir()
        assert ".local/share/jlcpcb" in str(d)

    def test_xdg_override(self, monkeypatch):
        monkeypatch.setattr("sys.platform", "linux")
        monkeypatch.setenv("XDG_DATA_HOME", "/tmp/custom-data")
        d = _data_dir()
        assert str(d) == "/tmp/custom-data/jlcpcb"


class TestLoadGlobalConfig:
    def test_missing_config(self, monkeypatch, tmp_path):
        monkeypatch.setattr("jlcpcb_tool.config._data_dir", lambda: tmp_path)
        assert load_global_config() == {}

    def test_valid_config(self, monkeypatch, tmp_path):
        monkeypatch.setattr("jlcpcb_tool.config._data_dir", lambda: tmp_path)
        (tmp_path / "config.yaml").write_text("openrouter_api_key: test-key\n")
        config = load_global_config()
        assert config["openrouter_api_key"] == "test-key"


class TestGetConfig:
    def test_from_config_file(self, monkeypatch, tmp_path):
        monkeypatch.setattr("jlcpcb_tool.config._data_dir", lambda: tmp_path)
        (tmp_path / "config.yaml").write_text("my_setting: hello\n")
        assert get_config("my_setting") == "hello"

    def test_env_var_overrides(self, monkeypatch, tmp_path):
        monkeypatch.setattr("jlcpcb_tool.config._data_dir", lambda: tmp_path)
        (tmp_path / "config.yaml").write_text("my_setting: from-file\n")
        monkeypatch.setenv("JLCPCB_MY_SETTING", "from-env")
        assert get_config("my_setting") == "from-env"

    def test_default_when_missing(self, monkeypatch, tmp_path):
        monkeypatch.setattr("jlcpcb_tool.config._data_dir", lambda: tmp_path)
        assert get_config("nonexistent", default="fallback") == "fallback"


class TestGetSecret:
    def test_delegates_to_get_config(self, monkeypatch, tmp_path):
        monkeypatch.setattr("jlcpcb_tool.config._data_dir", lambda: tmp_path)
        (tmp_path / "config.yaml").write_text("openrouter_api_key: sk-test\n")
        assert get_secret("openrouter_api_key") == "sk-test"


class TestFindProjectDir:
    def test_explicit_override(self, tmp_path):
        (tmp_path / ".jlcpcb").mkdir()
        (tmp_path / ".jlcpcb" / "project.yaml").write_text("name: test\n")
        assert find_project_dir(override=str(tmp_path)) == tmp_path

    def test_override_not_found(self, tmp_path):
        assert find_project_dir(override=str(tmp_path)) is None

    def test_env_var(self, monkeypatch, tmp_path):
        (tmp_path / ".jlcpcb").mkdir()
        (tmp_path / ".jlcpcb" / "project.yaml").write_text("name: test\n")
        monkeypatch.setenv("JLCPCB_PROJECT", str(tmp_path))
        assert find_project_dir() == tmp_path

    def test_env_var_not_found(self, monkeypatch, tmp_path):
        monkeypatch.setenv("JLCPCB_PROJECT", str(tmp_path))
        assert find_project_dir() is None

    def test_walk_up(self, monkeypatch, tmp_path):
        (tmp_path / ".jlcpcb").mkdir()
        (tmp_path / ".jlcpcb" / "project.yaml").write_text("name: test\n")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        monkeypatch.chdir(subdir)
        monkeypatch.delenv("JLCPCB_PROJECT", raising=False)
        assert find_project_dir() == tmp_path

    def test_no_project(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("JLCPCB_PROJECT", raising=False)
        assert find_project_dir() is None

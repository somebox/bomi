"""Tests for CLI commands using Click CliRunner."""

import json
import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from jlcpcb_tool.cli import cli
from jlcpcb_tool.db import Database
from jlcpcb_tool.models import Attribute, Part, PriceTier


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_db(tmp_path, sample_part):
    """Create a temp DB and patch get_db to use it."""
    db = Database(tmp_path / "test.db")
    db.upsert_part(sample_part)
    return db


@pytest.fixture
def patched_db(mock_db):
    """Patch get_db to return our test database."""
    with patch("jlcpcb_tool.cli.get_db", return_value=mock_db):
        yield mock_db


class TestInfo:
    def test_info_table(self, runner, patched_db):
        result = runner.invoke(cli, ["info", "C8287"])
        assert result.exit_code == 0
        assert "C8287" in result.output
        assert "YAGEO" in result.output
        assert "RC0402FR-0710KL" in result.output

    def test_info_json(self, runner, patched_db):
        result = runner.invoke(cli, ["info", "C8287", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "ok"
        assert data["count"] == 1
        assert data["results"][0]["lcsc_code"] == "C8287"

    def test_info_not_found(self, runner, patched_db):
        result = runner.invoke(cli, ["info", "C99999"])
        assert result.exit_code != 0
        assert "not found" in result.output


class TestQuery:
    def test_query_all(self, runner, patched_db):
        result = runner.invoke(cli, ["query"])
        assert result.exit_code == 0
        assert "C8287" in result.output

    def test_query_keyword(self, runner, patched_db):
        result = runner.invoke(cli, ["query", "10k"])
        assert result.exit_code == 0
        assert "C8287" in result.output

    def test_query_no_match(self, runner, patched_db):
        result = runner.invoke(cli, ["query", "nonexistent_xyz"])
        assert result.exit_code == 0
        assert "No results" in result.output

    def test_query_json(self, runner, patched_db):
        result = runner.invoke(cli, ["query", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "ok"
        assert data["command"] == "query"

    def test_query_csv(self, runner, patched_db):
        result = runner.invoke(cli, ["query", "--format", "csv"])
        assert result.exit_code == 0
        assert "lcsc_code" in result.output
        assert "C8287" in result.output

    def test_query_basic_only(self, runner, patched_db):
        result = runner.invoke(cli, ["query", "--basic-only"])
        assert result.exit_code == 0
        assert "C8287" in result.output

    def test_query_attr_filter(self, runner, patched_db):
        result = runner.invoke(cli, ["query", "--attr", "Resistance >= 5k"])
        assert result.exit_code == 0
        assert "C8287" in result.output


class TestCompare:
    def test_compare_single(self, runner, patched_db):
        result = runner.invoke(cli, ["compare", "C8287"])
        assert result.exit_code == 0
        assert "C8287" in result.output

    def test_compare_not_found(self, runner, patched_db):
        result = runner.invoke(cli, ["compare", "C99999"])
        assert result.exit_code != 0

    def test_compare_json(self, runner, patched_db):
        result = runner.invoke(cli, ["compare", "C8287", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["command"] == "compare"


class TestDbCommands:
    def test_stats(self, runner, patched_db):
        result = runner.invoke(cli, ["db", "stats"])
        assert result.exit_code == 0
        assert "Parts:" in result.output

    def test_stats_json(self, runner, patched_db):
        result = runner.invoke(cli, ["db", "stats", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "parts" in data["results"][0]

    def test_clear(self, runner, patched_db):
        result = runner.invoke(cli, ["db", "clear"], input="y\n")
        assert result.exit_code == 0
        assert "cleared" in result.output


class TestInit:
    def test_init_creates_project(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli, ["init", "--name", "test-board"])
        assert result.exit_code == 0
        assert "Created" in result.output
        assert (tmp_path / ".jlcpcb" / "project.yaml").exists()

    def test_init_already_exists(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".jlcpcb").mkdir()
        (tmp_path / ".jlcpcb" / "project.yaml").write_text("name: existing\n")
        result = runner.invoke(cli, ["init", "--name", "test"])
        assert result.exit_code != 0
        assert "already exists" in result.output


class TestSelect:
    def test_select_cached_part(self, runner, patched_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ["init", "--name", "test"])
        monkeypatch.setattr(
            "jlcpcb_tool.project.get_db_path",
            lambda: patched_db.db_path,
        )
        result = runner.invoke(cli, ["select", "C8287", "--ref", "R1", "--qty", "2"])
        assert result.exit_code == 0
        assert "R1" in result.output

    def test_select_no_project(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("JLCPCB_PROJECT", raising=False)
        result = runner.invoke(cli, ["select", "C8287", "--ref", "R1"])
        assert result.exit_code != 0
        assert "No project" in result.output


class TestDeselect:
    def test_deselect(self, runner, patched_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ["init", "--name", "test"])
        monkeypatch.setattr(
            "jlcpcb_tool.project.get_db_path",
            lambda: patched_db.db_path,
        )
        runner.invoke(cli, ["select", "C8287", "--ref", "R1"])
        result = runner.invoke(cli, ["deselect", "R1"])
        assert result.exit_code == 0
        assert "Removed" in result.output

    def test_deselect_not_found(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ["init", "--name", "test"])
        result = runner.invoke(cli, ["deselect", "R99"])
        assert result.exit_code != 0
        assert "not found" in result.output


class TestRelabel:
    def test_relabel(self, runner, patched_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ["init", "--name", "test"])
        monkeypatch.setattr(
            "jlcpcb_tool.project.get_db_path",
            lambda: patched_db.db_path,
        )
        runner.invoke(cli, ["select", "C8287", "--ref", "R1"])
        result = runner.invoke(cli, ["relabel", "R1", "R2"])
        assert result.exit_code == 0
        assert "R2" in result.output


class TestBom:
    def test_bom_table(self, runner, patched_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ["init", "--name", "test"])
        monkeypatch.setattr(
            "jlcpcb_tool.project.get_db_path",
            lambda: patched_db.db_path,
        )
        runner.invoke(cli, ["select", "C8287", "--ref", "R1"])
        result = runner.invoke(cli, ["bom"])
        assert result.exit_code == 0
        assert "C8287" in result.output

    def test_bom_json(self, runner, patched_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ["init", "--name", "test"])
        monkeypatch.setattr(
            "jlcpcb_tool.project.get_db_path",
            lambda: patched_db.db_path,
        )
        runner.invoke(cli, ["select", "C8287", "--ref", "R1"])
        result = runner.invoke(cli, ["bom", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "ok"
        assert len(data["data"]) == 1

    def test_bom_csv(self, runner, patched_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ["init", "--name", "test"])
        monkeypatch.setattr(
            "jlcpcb_tool.project.get_db_path",
            lambda: patched_db.db_path,
        )
        runner.invoke(cli, ["select", "C8287", "--ref", "R1"])
        result = runner.invoke(cli, ["bom", "--format", "csv"])
        assert result.exit_code == 0
        assert "Ref,LCSC" in result.output
        assert "C8287" in result.output

    def test_bom_no_project(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("JLCPCB_PROJECT", raising=False)
        result = runner.invoke(cli, ["bom"])
        assert result.exit_code != 0


class TestStatus:
    def test_status(self, runner, patched_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ["init", "--name", "test"])
        monkeypatch.setattr(
            "jlcpcb_tool.project.get_db_path",
            lambda: patched_db.db_path,
        )
        runner.invoke(cli, ["select", "C8287", "--ref", "R1"])
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "test" in result.output
        assert "Selections: 1" in result.output
        assert "Est. cost:" in result.output


class TestSearch:
    @patch("jlcpcb_tool.cli.JLCPCBClient")
    def test_search_calls_api(self, mock_client_cls, runner, patched_db,
                               sample_search_response):
        mock_client = MagicMock()
        mock_client.search.return_value = sample_search_response
        mock_client_cls.return_value = mock_client

        result = runner.invoke(cli, ["search", "10k resistor"])
        assert result.exit_code == 0
        mock_client.search.assert_called_once()
        assert "C8287" in result.output

    @patch("jlcpcb_tool.cli.JLCPCBClient")
    def test_search_json(self, mock_client_cls, runner, patched_db,
                          sample_search_response):
        mock_client = MagicMock()
        mock_client.search.return_value = sample_search_response
        mock_client_cls.return_value = mock_client

        result = runner.invoke(cli, ["search", "10k", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "ok"

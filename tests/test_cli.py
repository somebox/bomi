"""Tests for CLI commands using Click CliRunner."""

import json
import pytest
import yaml
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
import requests

from bomi.cli import cli
from bomi.db import Database
from bomi.models import Attribute, Part, PriceTier


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
    """Patch get_db to return our test database.

    The real close() is replaced with a no-op so that commands which open
    and close the DB multiple times (e.g. search --category) don't break
    subsequent calls that reuse the same patched instance.
    """
    mock_db.close = lambda: None
    with patch("bomi.cli.get_db", return_value=mock_db):
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

    def test_info_by_designator(self, runner, patched_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ["init", "--name", "test"])
        monkeypatch.setattr("bomi.project.get_db_path", lambda: patched_db.db_path)
        monkeypatch.setattr("bomi.cli.get_db", lambda: Database(patched_db.db_path))
        runner.invoke(cli, ["select", "C8287", "--ref", "R1"])
        result = runner.invoke(cli, ["info", "R1"])
        assert result.exit_code == 0
        assert "C8287" in result.output
        assert "YAGEO" in result.output

    def test_info_designator_without_lcsc_rejected(self, runner, patched_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ["init", "--name", "test"])
        project_yaml = tmp_path / ".bomi" / "project.yaml"
        data = yaml.safe_load(project_yaml.read_text())
        data["selections"] = [{"ref": "R1", "lcsc": None, "quantity": 1}]
        project_yaml.write_text(yaml.safe_dump(data, sort_keys=False))
        monkeypatch.setattr("bomi.project.get_db_path", lambda: patched_db.db_path)
        monkeypatch.setattr("bomi.cli.get_db", lambda: Database(patched_db.db_path))
        result = runner.invoke(cli, ["info", "R1"])
        assert result.exit_code != 0
        assert "has no selected LCSC part yet" in result.output


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

    def test_query_category_valid(self, runner, patched_db):
        patched_db.upsert_categories(SAMPLE_CATEGORIES)
        result = runner.invoke(cli, ["query", "--category", "Chip Resistor"])
        assert result.exit_code == 0
        assert "C8287" in result.output

    def test_query_category_invalid(self, runner, patched_db):
        patched_db.upsert_categories(SAMPLE_CATEGORIES)
        result = runner.invoke(cli, ["query", "--category", "DefinitelyNotACategory"])
        assert result.exit_code != 0
        assert "No category matching" in result.output

    def test_query_category_top_level_warns(self, runner, patched_db):
        patched_db.upsert_categories(SAMPLE_CATEGORIES)
        result = runner.invoke(cli, ["query", "--category", "Resistors"])
        assert result.exit_code == 0  # still runs
        assert "top-level category" in result.output

    def test_query_category_no_sync_skips_validation(self, runner, patched_db):
        """Without synced categories, query should just run the substring match."""
        result = runner.invoke(cli, ["query", "--category", "Chip Resistor"])
        assert result.exit_code == 0


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
        assert (tmp_path / ".bomi" / "project.yaml").exists()

    def test_init_already_exists(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".bomi").mkdir()
        (tmp_path / ".bomi" / "project.yaml").write_text("name: existing\n")
        result = runner.invoke(cli, ["init", "--name", "test"])
        assert result.exit_code != 0
        assert "already exists" in result.output


class TestSelect:
    def test_select_cached_part(self, runner, patched_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ["init", "--name", "test"])
        monkeypatch.setattr(
            "bomi.project.get_db_path",
            lambda: patched_db.db_path,
        )
        result = runner.invoke(cli, ["select", "C8287", "--ref", "R1", "--qty", "2"])
        assert result.exit_code == 0
        assert "R1" in result.output

    def test_select_no_project(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("BOMI_PROJECT", raising=False)
        result = runner.invoke(cli, ["select", "C8287", "--ref", "R1"])
        assert result.exit_code != 0
        assert "No project" in result.output

    def test_select_range_quantity_mismatch(self, runner, patched_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ["init", "--name", "test"])
        monkeypatch.setattr("bomi.project.get_db_path", lambda: patched_db.db_path)
        result = runner.invoke(cli, ["select", "C8287", "--ref", "U2-U4", "--qty", "1"])
        assert result.exit_code != 0
        assert "must be 3" in result.output

    def test_select_overlapping_ref(self, runner, patched_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ["init", "--name", "test"])
        monkeypatch.setattr("bomi.project.get_db_path", lambda: patched_db.db_path)
        monkeypatch.setattr("bomi.cli.get_db", lambda: Database(patched_db.db_path))
        runner.invoke(cli, ["select", "C8287", "--ref", "U2-U4", "--qty", "3"])
        result = runner.invoke(cli, ["select", "C8287", "--ref", "U3"])
        assert result.exit_code != 0
        assert "overlaps existing" in result.output

    def test_select_duplicate_designator_rejected(self, runner, patched_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ["init", "--name", "test"])
        monkeypatch.setattr("bomi.project.get_db_path", lambda: patched_db.db_path)
        monkeypatch.setattr("bomi.cli.get_db", lambda: Database(patched_db.db_path))
        runner.invoke(cli, ["select", "C8287", "--ref", "R1"])
        result = runner.invoke(cli, ["select", "C8287", "--ref", "R1"])
        assert result.exit_code != 0
        assert "already exists" in result.output


class TestDeselect:
    def test_deselect(self, runner, patched_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ["init", "--name", "test"])
        monkeypatch.setattr(
            "bomi.project.get_db_path",
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
            "bomi.project.get_db_path",
            lambda: patched_db.db_path,
        )
        runner.invoke(cli, ["select", "C8287", "--ref", "R1"])
        result = runner.invoke(cli, ["relabel", "R1", "R2"])
        assert result.exit_code == 0
        assert "R2" in result.output

    def test_relabel_range(self, runner, patched_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ["init", "--name", "test"])
        monkeypatch.setattr("bomi.project.get_db_path", lambda: patched_db.db_path)
        runner.invoke(cli, ["select", "C8287", "--ref", "U2-U4", "--qty", "3"])
        result = runner.invoke(cli, ["relabel", "U2-U4", "U5-U7"])
        assert result.exit_code == 0
        assert "U5-U7" in result.output


class TestBom:
    def test_bom_table(self, runner, patched_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ["init", "--name", "test"])
        monkeypatch.setattr(
            "bomi.project.get_db_path",
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
            "bomi.project.get_db_path",
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
            "bomi.project.get_db_path",
            lambda: patched_db.db_path,
        )
        runner.invoke(cli, ["select", "C8287", "--ref", "R1"])
        result = runner.invoke(cli, ["bom", "--format", "csv"])
        assert result.exit_code == 0
        assert "Ref,LCSC" in result.output
        assert "C8287" in result.output

    def test_bom_no_project(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("BOMI_PROJECT", raising=False)
        result = runner.invoke(cli, ["bom"])
        assert result.exit_code != 0

    def test_list_command(self, runner, patched_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ["init", "--name", "test"])
        monkeypatch.setattr("bomi.project.get_db_path", lambda: patched_db.db_path)
        runner.invoke(cli, ["select", "C8287", "--ref", "R1"])
        result = runner.invoke(cli, ["list", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["command"] == "list"
        assert data["data"][0]["lcsc"] == "C8287"

    def test_bom_alias_still_works(self, runner, patched_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ["init", "--name", "test"])
        monkeypatch.setattr("bomi.project.get_db_path", lambda: patched_db.db_path)
        runner.invoke(cli, ["select", "C8287", "--ref", "R1"])
        result = runner.invoke(cli, ["bom", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["command"] == "bom"

    def test_bom_markdown_has_anchor_links(self, runner, patched_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ["init", "--name", "test"])
        monkeypatch.setattr("bomi.project.get_db_path", lambda: patched_db.db_path)
        runner.invoke(cli, ["select", "C8287", "--ref", "R1"])
        result = runner.invoke(cli, ["bom", "--format", "markdown"])
        assert result.exit_code == 0
        assert "[R1](#c8287)" in result.output
        assert '<a id="c8287"></a>' in result.output


class TestStatus:
    def test_status(self, runner, patched_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ["init", "--name", "test"])
        monkeypatch.setattr(
            "bomi.project.get_db_path",
            lambda: patched_db.db_path,
        )
        runner.invoke(cli, ["select", "C8287", "--ref", "R1"])
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "test" in result.output
        assert "Selections: 1" in result.output
        assert "Est. cost:" in result.output


class TestSearch:
    @patch("bomi.cli.JLCPCBClient")
    def test_search_calls_api(self, mock_client_cls, runner, patched_db,
                               sample_search_response):
        mock_client = MagicMock()
        mock_client.search.return_value = sample_search_response
        mock_client_cls.return_value = mock_client

        result = runner.invoke(cli, ["search", "10k resistor"])
        assert result.exit_code == 0
        mock_client.search.assert_called_once()
        assert "C8287" in result.output

    @patch("bomi.cli.JLCPCBClient")
    def test_search_json(self, mock_client_cls, runner, patched_db,
                          sample_search_response):
        mock_client = MagicMock()
        mock_client.search.return_value = sample_search_response
        mock_client_cls.return_value = mock_client

        result = runner.invoke(cli, ["search", "10k", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "ok"

    @patch("bomi.cli.JLCPCBClient")
    def test_search_invalid_attr_fails_before_api(self, mock_client_cls, runner, patched_db):
        result = runner.invoke(cli, ["search", "10k", "--attr", "Resistance maybe 10k"])
        assert result.exit_code != 0
        assert "Invalid attribute filter" in result.output
        mock_client_cls.assert_not_called()

    @patch("bomi.cli.JLCPCBClient")
    def test_search_api_error_translated(self, mock_client_cls, runner, patched_db):
        mock_client = MagicMock()
        mock_client.search.side_effect = requests.RequestException("boom")
        mock_client_cls.return_value = mock_client
        result = runner.invoke(cli, ["search", "10k"])
        assert result.exit_code != 0
        assert "JLCPCB search failed" in result.output


SAMPLE_CATEGORIES = [
    {"name": "Resistors", "parent": None, "sort_id": None, "part_count": 1000},
    {"name": "Chip Resistor - Surface Mount", "parent": "Resistors", "sort_id": 2980, "part_count": 500},
    {"name": "Through Hole Resistors", "parent": "Resistors", "sort_id": 2295, "part_count": 300},
    {"name": "Capacitors", "parent": None, "sort_id": None, "part_count": 2000},
    {"name": "MLCC - SMD/SMT", "parent": "Capacitors", "sort_id": 2929, "part_count": 1500},
]


class TestSync:
    @patch("bomi.scrape.fetch_jlcpcb_categories", return_value=SAMPLE_CATEGORIES)
    def test_sync_fetches_categories(self, mock_fetch, runner, patched_db):
        result = runner.invoke(cli, ["sync"])
        assert result.exit_code == 0
        assert "Synced 2 categories, 3 subcategories" in result.output
        mock_fetch.assert_called_once()

    @patch("bomi.scrape.fetch_jlcpcb_categories", return_value=SAMPLE_CATEGORIES)
    def test_sync_skips_when_fresh(self, mock_fetch, runner, patched_db):
        # Seed categories so sync_time is set
        patched_db.upsert_categories(SAMPLE_CATEGORIES)
        result = runner.invoke(cli, ["sync"])
        assert result.exit_code == 0
        assert "already synced" in result.output
        mock_fetch.assert_not_called()

    @patch("bomi.scrape.fetch_jlcpcb_categories", return_value=SAMPLE_CATEGORIES)
    def test_sync_force_refetches(self, mock_fetch, runner, patched_db):
        patched_db.upsert_categories(SAMPLE_CATEGORIES)
        result = runner.invoke(cli, ["sync", "--force"])
        assert result.exit_code == 0
        assert "Synced" in result.output
        mock_fetch.assert_called_once()

    @patch("bomi.scrape.fetch_jlcpcb_categories",
           side_effect=requests.RequestException("timeout"))
    def test_sync_network_error(self, mock_fetch, runner, patched_db):
        result = runner.invoke(cli, ["sync"])
        assert result.exit_code != 0
        assert "Failed to fetch categories" in result.output


class TestCategories:
    def test_categories_no_cache(self, runner, patched_db):
        result = runner.invoke(cli, ["categories"])
        assert result.exit_code != 0
        assert "Run 'bomi sync' first" in result.output

    def test_categories_list_all(self, runner, patched_db):
        patched_db.upsert_categories(SAMPLE_CATEGORIES)
        result = runner.invoke(cli, ["categories"])
        assert result.exit_code == 0
        assert "Resistors" in result.output
        assert "Capacitors" in result.output
        assert "Chip Resistor - Surface Mount" in result.output

    def test_categories_filter(self, runner, patched_db):
        patched_db.upsert_categories(SAMPLE_CATEGORIES)
        result = runner.invoke(cli, ["categories", "resistor"])
        assert result.exit_code == 0
        assert "Resistors" in result.output
        assert "Chip Resistor - Surface Mount" in result.output
        assert "Capacitors" not in result.output

    def test_categories_filter_no_match(self, runner, patched_db):
        patched_db.upsert_categories(SAMPLE_CATEGORIES)
        result = runner.invoke(cli, ["categories", "nonexistent"])
        assert result.exit_code == 0
        assert result.output.strip() == ""


class TestSearchCategory:
    @patch("bomi.cli.JLCPCBClient")
    def test_search_with_category(self, mock_client_cls, runner, patched_db,
                                   sample_search_response):
        patched_db.upsert_categories(SAMPLE_CATEGORIES)
        mock_client = MagicMock()
        mock_client.search.return_value = sample_search_response
        mock_client_cls.return_value = mock_client

        result = runner.invoke(cli, ["search", "10k", "--category", "Chip Resistor - Surface Mount"])
        assert result.exit_code == 0
        mock_client.search.assert_called_once()
        call_kwargs = mock_client.search.call_args
        assert call_kwargs.kwargs.get("component_type") == "Chip Resistor - Surface Mount"

    def test_search_category_no_cache(self, runner, patched_db):
        result = runner.invoke(cli, ["search", "10k", "--category", "Resistor"])
        assert result.exit_code != 0
        assert "Run 'bomi sync' first" in result.output

    def test_search_category_no_match(self, runner, patched_db):
        patched_db.upsert_categories(SAMPLE_CATEGORIES)
        result = runner.invoke(cli, ["search", "10k", "--category", "xyz"])
        assert result.exit_code != 0
        assert "No category matching" in result.output

    def test_search_category_top_level_shows_children(self, runner, patched_db):
        patched_db.upsert_categories(SAMPLE_CATEGORIES)
        result = runner.invoke(cli, ["search", "10k", "--category", "Resistors"])
        assert result.exit_code != 0
        assert "top-level category" in result.output
        assert "Chip Resistor - Surface Mount" in result.output

    @patch("bomi.cli.JLCPCBClient")
    def test_search_category_substring_unique(self, mock_client_cls, runner,
                                               patched_db, sample_search_response):
        patched_db.upsert_categories(SAMPLE_CATEGORIES)
        mock_client = MagicMock()
        mock_client.search.return_value = sample_search_response
        mock_client_cls.return_value = mock_client

        result = runner.invoke(cli, ["search", "10k", "--category", "MLCC"])
        assert result.exit_code == 0
        call_kwargs = mock_client.search.call_args
        assert call_kwargs.kwargs.get("component_type") == "MLCC - SMD/SMT"

    def test_search_category_ambiguous(self, runner, patched_db):
        patched_db.upsert_categories(SAMPLE_CATEGORIES)
        result = runner.invoke(cli, ["search", "10k", "--category", "Resistor"])
        assert result.exit_code != 0
        assert "matches multiple categories" in result.output


class TestFetch:
    @patch("bomi.cli.JLCPCBClient")
    def test_fetch_api_error_translated(self, mock_client_cls, runner, patched_db):
        mock_client = MagicMock()
        mock_client.search.side_effect = requests.RequestException("boom")
        mock_client_cls.return_value = mock_client
        result = runner.invoke(cli, ["fetch", "C8287", "--force"])
        assert result.exit_code != 0
        assert "Failed to fetch C8287" in result.output

    def test_fetch_no_detail_option(self, runner):
        result = runner.invoke(cli, ["fetch", "--help"])
        assert result.exit_code == 0
        assert "--detail" not in result.output

    @patch("bomi.cli.JLCPCBClient")
    def test_fetch_all_from_project(self, mock_client_cls, runner, patched_db, tmp_path, monkeypatch, sample_search_response):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ["init", "--name", "test"])
        monkeypatch.setattr("bomi.project.get_db_path", lambda: patched_db.db_path)
        monkeypatch.setattr("bomi.cli.get_db", lambda: Database(patched_db.db_path))
        runner.invoke(cli, ["select", "C8287", "--ref", "R1"])

        mock_client = MagicMock()
        mock_client.search.return_value = sample_search_response
        mock_client_cls.return_value = mock_client

        result = runner.invoke(cli, ["fetch", "--all", "--force"])
        assert result.exit_code == 0
        assert "Fetching 1 part(s)..." in result.output
        assert "[1/1] C8287" in result.output
        assert "C8287" in result.output
        mock_client.search.assert_called_once()


class TestDatasheet:
    def test_datasheet_help_has_force(self, runner):
        result = runner.invoke(cli, ["datasheet", "--help"])
        assert result.exit_code == 0
        assert "--force" in result.output
        assert "--summarize" in result.output

    @patch("bomi.analysis.download_pdf")
    def test_datasheet_all_force_redownloads(self, mock_download_pdf, runner, patched_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        output_dir = tmp_path / "datasheets"
        output_dir.mkdir(parents=True, exist_ok=True)

        runner.invoke(cli, ["init", "--name", "test"])
        monkeypatch.setattr("bomi.project.get_db_path", lambda: patched_db.db_path)
        monkeypatch.setattr("bomi.cli.get_db", lambda: Database(patched_db.db_path))
        runner.invoke(cli, ["select", "C8287", "--ref", "R1"])

        existing_pdf = output_dir / "RC0402FR-0710KL_C8287.pdf"
        existing_pdf.write_bytes(b"%PDF-1.4 existing")
        mock_download_pdf.return_value = b"%PDF-1.4 refreshed"

        result = runner.invoke(cli, ["datasheet", "--all", "--pdf", "--force", "-o", str(output_dir)])
        assert result.exit_code == 0
        assert "[1/1] C8287" in result.output
        mock_download_pdf.assert_called_once()
        assert existing_pdf.read_bytes() == b"%PDF-1.4 refreshed"

    @patch("bomi.analysis.analyze_part")
    @patch("bomi.analysis.download_pdf")
    def test_datasheet_all_summary_skips_existing_without_force(
        self, mock_download_pdf, mock_analyze_part, runner, patched_db, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        output_dir = tmp_path / "datasheets"
        output_dir.mkdir(parents=True, exist_ok=True)

        runner.invoke(cli, ["init", "--name", "test"])
        monkeypatch.setattr("bomi.project.get_db_path", lambda: patched_db.db_path)
        monkeypatch.setattr("bomi.cli.get_db", lambda: Database(patched_db.db_path))
        runner.invoke(cli, ["select", "C8287", "--ref", "R1"])

        existing_md = output_dir / "RC0402FR-0710KL_C8287.md"
        existing_md.write_text("# existing summary\n")

        result = runner.invoke(cli, ["datasheet", "--all", "--summarize", "-o", str(output_dir)])
        assert result.exit_code == 0
        assert "Summary exists" in result.output
        mock_download_pdf.assert_not_called()
        mock_analyze_part.assert_not_called()

    @patch("bomi.analysis.download_pdf")
    def test_datasheet_uses_configured_output_dir(self, mock_download_pdf, runner, patched_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("bomi.cli.get_db", lambda: Database(patched_db.db_path))
        monkeypatch.setattr(
            "bomi.cli.get_config",
            lambda key, default=None: "my-datasheets" if key == "datasheet_output_dir" else default,
        )
        mock_download_pdf.return_value = b"%PDF-1.4 configured-dir"

        result = runner.invoke(cli, ["datasheet", "C8287", "--pdf", "--force"])
        assert result.exit_code == 0

        pdf_path = tmp_path / "my-datasheets" / "RC0402FR-0710KL_C8287.pdf"
        assert pdf_path.exists()

"""Tests for project management: init, selections, BOM."""

import pytest
import yaml

from jlcpcb_tool.project import (
    Project,
    Selection,
    add_selection,
    init_project,
    load_project,
    relabel_selection,
    remove_selection,
    resolve_bom,
    save_project,
)


class TestInitProject:
    def test_creates_project_yaml(self, tmp_path):
        project = init_project(tmp_path, name="test-board", description="A test")
        yaml_path = tmp_path / ".jlcpcb" / "project.yaml"
        assert yaml_path.exists()
        data = yaml.safe_load(yaml_path.read_text())
        assert data["name"] == "test-board"
        assert data["description"] == "A test"
        assert data["selections"] == []

    def test_sets_created_date(self, tmp_path):
        project = init_project(tmp_path, name="test")
        assert project.created  # non-empty date string

    def test_returns_project(self, tmp_path):
        project = init_project(tmp_path, name="test")
        assert project.name == "test"
        assert project.path == tmp_path


class TestLoadSaveProject:
    def test_round_trip(self, tmp_path):
        original = init_project(tmp_path, name="roundtrip", description="desc")
        loaded = load_project(tmp_path)
        assert loaded.name == "roundtrip"
        assert loaded.description == "desc"
        assert loaded.selections == []

    def test_load_nonexistent(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_project(tmp_path)

    def test_save_with_selections(self, tmp_path):
        project = init_project(tmp_path, name="test")
        project.selections.append(
            Selection(ref="R1", lcsc="C8287", quantity=2, notes="pullup")
        )
        save_project(project)

        loaded = load_project(tmp_path)
        assert len(loaded.selections) == 1
        sel = loaded.selections[0]
        assert sel.ref == "R1"
        assert sel.lcsc == "C8287"
        assert sel.quantity == 2
        assert sel.notes == "pullup"


class TestAddSelection:
    def test_add(self, tmp_path):
        project = init_project(tmp_path, name="test")
        sel = add_selection(project, lcsc="C8287", ref="R1", quantity=2, notes="10k")
        assert sel.ref == "R1"
        assert sel.lcsc == "C8287"
        assert len(project.selections) == 1

        # Persisted to disk
        loaded = load_project(tmp_path)
        assert len(loaded.selections) == 1

    def test_duplicate_ref_rejected(self, tmp_path):
        project = init_project(tmp_path, name="test")
        add_selection(project, lcsc="C8287", ref="R1")
        with pytest.raises(ValueError, match="already in BOM"):
            add_selection(project, lcsc="C9999", ref="R1")

    def test_multiple_selections_sorted(self, tmp_path):
        project = init_project(tmp_path, name="test")
        add_selection(project, lcsc="C1111", ref="U1")
        add_selection(project, lcsc="C2222", ref="C1")
        add_selection(project, lcsc="C3333", ref="R1")

        loaded = load_project(tmp_path)
        refs = [s.ref for s in loaded.selections]
        assert refs == ["C1", "R1", "U1"]


class TestRemoveSelection:
    def test_remove(self, tmp_path):
        project = init_project(tmp_path, name="test")
        add_selection(project, lcsc="C8287", ref="R1")
        removed = remove_selection(project, "R1")
        assert removed.lcsc == "C8287"
        assert len(project.selections) == 0

    def test_remove_nonexistent(self, tmp_path):
        project = init_project(tmp_path, name="test")
        with pytest.raises(ValueError, match="not found"):
            remove_selection(project, "R99")


class TestRelabelSelection:
    def test_relabel(self, tmp_path):
        project = init_project(tmp_path, name="test")
        add_selection(project, lcsc="C8287", ref="R1")
        sel = relabel_selection(project, "R1", "R2")
        assert sel.ref == "R2"

        loaded = load_project(tmp_path)
        assert loaded.selections[0].ref == "R2"

    def test_relabel_conflict(self, tmp_path):
        project = init_project(tmp_path, name="test")
        add_selection(project, lcsc="C8287", ref="R1")
        add_selection(project, lcsc="C9999", ref="R2")
        with pytest.raises(ValueError, match="already exists"):
            relabel_selection(project, "R1", "R2")

    def test_relabel_nonexistent(self, tmp_path):
        project = init_project(tmp_path, name="test")
        with pytest.raises(ValueError, match="not found"):
            relabel_selection(project, "R99", "R100")


class TestResolveBom:
    def test_resolve_tbd(self, tmp_path, monkeypatch):
        """TBD parts get a warning."""
        monkeypatch.setattr("jlcpcb_tool.project.get_db_path", lambda: tmp_path / "parts.db")
        project = init_project(tmp_path, name="test")
        project.selections.append(Selection(ref="R1", lcsc=None))
        save_project(project)

        entries = resolve_bom(project)
        assert len(entries) == 1
        assert "TBD" in entries[0]["warnings"][0]

    def test_resolve_uncached(self, tmp_path, monkeypatch):
        """Parts not in DB get a warning."""
        monkeypatch.setattr("jlcpcb_tool.project.get_db_path", lambda: tmp_path / "parts.db")
        project = init_project(tmp_path, name="test")
        add_selection(project, lcsc="C8287", ref="R1")

        entries = resolve_bom(project)
        assert entries[0]["warnings"][0] == "Not in local cache — run fetch"

    def test_resolve_cached(self, tmp_path, monkeypatch, sample_part):
        """Cached parts are included in BOM."""
        db_path = tmp_path / "parts.db"
        monkeypatch.setattr("jlcpcb_tool.project.get_db_path", lambda: db_path)

        from jlcpcb_tool.db import Database
        db = Database(db_path)
        db.upsert_part(sample_part)
        db.close()

        project = init_project(tmp_path, name="test")
        add_selection(project, lcsc="C8287", ref="R1")

        entries = resolve_bom(project)
        assert entries[0]["part"] is not None
        assert entries[0]["part"].lcsc_code == "C8287"

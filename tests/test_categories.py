"""Unit tests for category validation and API resolution."""

import pytest

from bomi.categories import resolve_category_for_search, validate_category_for_query
from bomi.db import Database


def _seed_categories(db: Database) -> None:
    db.upsert_categories(
        [
            {"name": "Resistors", "parent": None, "sort_id": 1, "part_count": 1000},
            {"name": "Chip Resistor", "parent": "Resistors", "sort_id": 2, "part_count": 500},
            {"name": "Capacitors", "parent": None, "sort_id": 3, "part_count": 800},
            {
                "name": "Ceramic Capacitor",
                "parent": "Capacitors",
                "sort_id": 4,
                "part_count": 400,
            },
        ],
        provider="jlcpcb",
    )


def test_validate_skips_when_no_synced_categories(tmp_path):
    with Database(tmp_path / "t.db") as db:
        validate_category_for_query(db, "Anything")


def test_validate_exits_when_no_match(tmp_path):
    with Database(tmp_path / "t.db") as db:
        _seed_categories(db)
        with pytest.raises(SystemExit) as exc:
            validate_category_for_query(db, "xyznonexistent")
        assert exc.value.code == 1


def test_resolve_subcategory_single_match(tmp_path):
    with Database(tmp_path / "t.db") as db:
        _seed_categories(db)
        assert resolve_category_for_search(db, "Chip") == "Chip Resistor"


def test_resolve_ambiguous_exits(tmp_path):
    with Database(tmp_path / "t.db") as db:
        _seed_categories(db)
        db.upsert_categories(
            [
                {"name": "A", "parent": None, "sort_id": 1, "part_count": 1},
                {"name": "A1", "parent": "A", "sort_id": 2, "part_count": 1},
                {"name": "A2", "parent": "A", "sort_id": 3, "part_count": 1},
            ],
            provider="jlcpcb",
        )
        with pytest.raises(SystemExit) as exc:
            resolve_category_for_search(db, "A")
        assert exc.value.code == 1


def test_resolve_parent_exits_with_children(tmp_path):
    with Database(tmp_path / "t.db") as db:
        _seed_categories(db)
        with pytest.raises(SystemExit) as exc:
            resolve_category_for_search(db, "Resistors")
        assert exc.value.code == 1

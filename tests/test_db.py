"""Tests for database schema and CRUD operations."""

import pytest
from datetime import datetime, timezone

from jlcpcb_tool.db import Database
from jlcpcb_tool.models import Analysis, Attribute, Part, PriceTier


class TestSchema:
    def test_tables_created(self, tmp_db):
        tables = tmp_db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = [t["name"] for t in tables]
        assert "parts" in names
        assert "prices" in names
        assert "attributes" in names
        assert "analyses" in names

    def test_indexes_created(self, tmp_db):
        indexes = tmp_db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        ).fetchall()
        names = [i["name"] for i in indexes]
        assert "idx_parts_category" in names
        assert "idx_parts_package" in names
        assert "idx_parts_stock" in names
        assert "idx_attr_name_num" in names


class TestUpsertPart:
    def test_insert_and_retrieve(self, tmp_db, sample_part):
        tmp_db.upsert_part(sample_part)
        result = tmp_db.get_part("C8287")
        assert result is not None
        assert result.lcsc_code == "C8287"
        assert result.mfr_part == "RC0402FR-0710KL"
        assert result.manufacturer == "YAGEO"
        assert result.stock == 500000
        assert result.preferred is True
        assert result.library_type == "base"

    def test_prices_stored(self, tmp_db, sample_part):
        tmp_db.upsert_part(sample_part)
        result = tmp_db.get_part("C8287")
        assert len(result.prices) == 3
        assert result.prices[0].unit_price == 0.0037
        assert result.prices[2].qty_to is None

    def test_attributes_stored(self, tmp_db, sample_part):
        tmp_db.upsert_part(sample_part)
        result = tmp_db.get_part("C8287")
        assert len(result.attributes) == 3
        resistance = next(a for a in result.attributes if a.name == "Resistance")
        assert resistance.value_raw == "10kΩ"
        assert resistance.value_num == 10000.0
        assert resistance.unit == "ohm"

    def test_upsert_updates_existing(self, tmp_db, sample_part):
        tmp_db.upsert_part(sample_part)
        sample_part.stock = 999999
        sample_part.prices = [PriceTier(qty_from=1, qty_to=None, unit_price=0.001)]
        tmp_db.upsert_part(sample_part)
        result = tmp_db.get_part("C8287")
        assert result.stock == 999999
        assert len(result.prices) == 1

    def test_get_nonexistent(self, tmp_db):
        assert tmp_db.get_part("C99999") is None


class TestDeletePart:
    def test_delete(self, tmp_db, sample_part):
        tmp_db.upsert_part(sample_part)
        tmp_db.delete_part("C8287")
        assert tmp_db.get_part("C8287") is None

    def test_cascading_delete(self, tmp_db, sample_part):
        tmp_db.upsert_part(sample_part)
        tmp_db.delete_part("C8287")
        prices = tmp_db.conn.execute(
            "SELECT COUNT(*) FROM prices WHERE lcsc_code = 'C8287'"
        ).fetchone()[0]
        attrs = tmp_db.conn.execute(
            "SELECT COUNT(*) FROM attributes WHERE lcsc_code = 'C8287'"
        ).fetchone()[0]
        assert prices == 0
        assert attrs == 0


class TestAnalysis:
    def test_save_and_retrieve(self, tmp_db, sample_part):
        tmp_db.upsert_part(sample_part)
        analysis = Analysis(
            lcsc_code="C8287",
            method="openrouter",
            model="gemini-2.0-flash",
            prompt="What is the power rating?",
            response="The power rating is 1/16W (62.5mW).",
            extracted_json='{"power_rating": "0.0625W"}',
            cost_usd=0.001,
        )
        aid = tmp_db.save_analysis(analysis)
        assert aid is not None

        results = tmp_db.get_analyses("C8287")
        assert len(results) == 1
        assert results[0].method == "openrouter"
        assert results[0].response == "The power rating is 1/16W (62.5mW)."


class TestStats:
    def test_empty_db(self, tmp_db):
        s = tmp_db.stats()
        assert s["parts"] == 0
        assert s["attributes"] == 0

    def test_after_insert(self, tmp_db, sample_part):
        tmp_db.upsert_part(sample_part)
        s = tmp_db.stats()
        assert s["parts"] == 1
        assert s["attributes"] == 3


class TestQueryParts:
    def test_query_by_keyword(self, tmp_db, sample_part):
        tmp_db.upsert_part(sample_part)
        results = tmp_db.query_parts(keyword="10k")
        assert len(results) == 1
        assert results[0].lcsc_code == "C8287"

    def test_query_by_package(self, tmp_db, sample_part):
        tmp_db.upsert_part(sample_part)
        results = tmp_db.query_parts(package="0402")
        assert len(results) == 1

    def test_query_basic_only(self, tmp_db, sample_part):
        tmp_db.upsert_part(sample_part)
        results = tmp_db.query_parts(basic_only=True)
        assert len(results) == 1

        sample_part.lcsc_code = "C99999"
        sample_part.library_type = "expand"
        tmp_db.upsert_part(sample_part)
        results = tmp_db.query_parts(basic_only=True)
        assert len(results) == 1

    def test_query_min_stock(self, tmp_db, sample_part):
        tmp_db.upsert_part(sample_part)
        results = tmp_db.query_parts(min_stock=1000000)
        assert len(results) == 0

    def test_query_attr_filter(self, tmp_db, sample_part):
        tmp_db.upsert_part(sample_part)
        results = tmp_db.query_parts(
            attr_filters=[("Resistance", ">=", 5000.0)]
        )
        assert len(results) == 1
        results = tmp_db.query_parts(
            attr_filters=[("Resistance", ">=", 50000.0)]
        )
        assert len(results) == 0

    def test_query_no_results(self, tmp_db):
        results = tmp_db.query_parts(keyword="nonexistent")
        assert len(results) == 0

    def test_clear(self, tmp_db, sample_part):
        tmp_db.upsert_part(sample_part)
        tmp_db.clear()
        assert tmp_db.stats()["parts"] == 0

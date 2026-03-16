"""Tests for API response normalization."""

import json
import pytest

from jlcpcb_tool.normalize import normalize_search_response, get_search_metadata


class TestNormalizeSearchResponse:
    def test_basic_normalization(self, sample_search_response):
        parts = normalize_search_response(sample_search_response)
        assert len(parts) == 2

    def test_first_part_fields(self, sample_search_response):
        parts = normalize_search_response(sample_search_response)
        p = parts[0]
        assert p.lcsc_code == "C8287"
        assert p.mfr_part == "RC0402FR-0710KL"
        assert p.manufacturer == "YAGEO"
        assert p.package == "0402"
        assert p.category == "Chip Resistor - Surface Mount"
        assert p.subcategory == "Resistors"
        assert p.stock == 500000
        assert p.library_type == "base"
        assert p.preferred is True
        assert p.datasheet_url == "https://example.com/datasheet.pdf"
        assert "C8287" in p.jlcpcb_url

    def test_prices_normalized(self, sample_search_response):
        parts = normalize_search_response(sample_search_response)
        p = parts[0]
        assert len(p.prices) == 3
        assert p.prices[0].qty_from == 1
        assert p.prices[0].unit_price == 0.0037
        assert p.prices[2].qty_to is None  # -1 → None

    def test_attributes_parsed(self, sample_search_response):
        parts = normalize_search_response(sample_search_response)
        p = parts[0]
        assert len(p.attributes) == 3
        resistance = next(a for a in p.attributes if a.name == "Resistance")
        assert resistance.value_raw == "10kΩ"
        assert resistance.value_num == pytest.approx(10000.0)
        assert resistance.unit == "ohm"

        power = next(a for a in p.attributes if a.name == "Power(Watts)")
        assert power.value_num == pytest.approx(0.0625)
        assert power.unit == "watt"

    def test_raw_json_preserved(self, sample_search_response):
        parts = normalize_search_response(sample_search_response)
        raw = json.loads(parts[0].raw_json)
        assert raw["componentCode"] == "C8287"

    def test_null_datasheet_url(self, sample_search_response):
        parts = normalize_search_response(sample_search_response)
        assert parts[1].datasheet_url is None

    def test_second_part(self, sample_search_response):
        parts = normalize_search_response(sample_search_response)
        p = parts[1]
        assert p.lcsc_code == "C25900"
        assert p.preferred is False
        assert len(p.prices) == 2


class TestSearchMetadata:
    def test_metadata(self, sample_search_response):
        meta = get_search_metadata(sample_search_response)
        assert meta["total"] == 179
        assert meta["pages"] == 18
        assert meta["has_next_page"] is True

    def test_empty_response(self):
        meta = get_search_metadata({})
        assert meta["total"] == 0


class TestRoundTrip:
    """Test normalize → DB → retrieve round-trip."""

    def test_normalize_store_retrieve(self, tmp_db, sample_search_response):
        parts = normalize_search_response(sample_search_response)
        for part in parts:
            tmp_db.upsert_part(part)

        retrieved = tmp_db.get_part("C8287")
        assert retrieved is not None
        assert retrieved.mfr_part == "RC0402FR-0710KL"
        assert len(retrieved.prices) == 3
        assert len(retrieved.attributes) == 3

        resistance = next(a for a in retrieved.attributes if a.name == "Resistance")
        assert resistance.value_num == pytest.approx(10000.0)

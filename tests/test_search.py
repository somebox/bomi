"""Tests for local DB search with filters."""

import pytest

from jlcpcb_tool.models import Attribute, Part, PriceTier
from jlcpcb_tool.search import search_local


@pytest.fixture
def populated_db(tmp_db):
    """DB with several parts for search testing."""
    parts = [
        Part(
            lcsc_code="C8287",
            mfr_part="RC0402FR-0710KL",
            manufacturer="YAGEO",
            package="0402",
            category="Chip Resistor",
            description="10kΩ ±1% 1/16W 0402",
            stock=500000,
            library_type="base",
            preferred=True,
            prices=[PriceTier(1, 9, 0.0037), PriceTier(10, None, 0.0025)],
            attributes=[
                Attribute("Resistance", "10kΩ", 10000.0, "ohm"),
                Attribute("Power(Watts)", "1/16W", 0.0625, "watt"),
            ],
        ),
        Part(
            lcsc_code="C25900",
            mfr_part="0402WGF1002TCE",
            manufacturer="UNI-ROYAL",
            package="0402",
            category="Chip Resistor",
            description="10kΩ ±1% 1/16W 0402",
            stock=300000,
            library_type="base",
            preferred=False,
            prices=[PriceTier(1, None, 0.0020)],
            attributes=[
                Attribute("Resistance", "10kΩ", 10000.0, "ohm"),
            ],
        ),
        Part(
            lcsc_code="C12345",
            mfr_part="GRM155R71C104KA88D",
            manufacturer="Murata",
            package="0402",
            category="MLCC",
            description="100nF 16V 0402 Capacitor",
            stock=100000,
            library_type="expand",
            preferred=False,
            prices=[PriceTier(1, None, 0.0100)],
            attributes=[
                Attribute("Capacitance", "100nF", 1e-7, "farad"),
                Attribute("Voltage Rated", "16V", 16.0, "volt"),
            ],
        ),
        Part(
            lcsc_code="C99999",
            mfr_part="OUT-OF-STOCK",
            manufacturer="Test",
            package="0805",
            category="Chip Resistor",
            description="100kΩ 0805",
            stock=0,
            library_type="expand",
            prices=[PriceTier(1, None, 0.0500)],
            attributes=[
                Attribute("Resistance", "100kΩ", 100000.0, "ohm"),
            ],
        ),
    ]
    for p in parts:
        tmp_db.upsert_part(p)
    return tmp_db


class TestSearchLocal:
    def test_no_filters(self, populated_db):
        results = search_local(populated_db)
        assert len(results) == 4

    def test_keyword(self, populated_db):
        results = search_local(populated_db, keyword="Capacitor")
        assert len(results) == 1
        assert results[0].lcsc_code == "C12345"

    def test_package(self, populated_db):
        results = search_local(populated_db, package="0402")
        assert len(results) == 3

    def test_min_stock(self, populated_db):
        results = search_local(populated_db, min_stock=100000)
        assert len(results) == 3
        assert all(r.stock >= 100000 for r in results)

    def test_basic_only(self, populated_db):
        results = search_local(populated_db, basic_only=True)
        assert len(results) == 2
        assert all(r.library_type == "base" for r in results)

    def test_preferred_only(self, populated_db):
        results = search_local(populated_db, preferred_only=True)
        assert len(results) == 1
        assert results[0].lcsc_code == "C8287"

    def test_max_price(self, populated_db):
        results = search_local(populated_db, max_price=0.005)
        assert len(results) == 2  # C8287 and C25900

    def test_attr_filter_gte(self, populated_db):
        results = search_local(
            populated_db, attr_exprs=["Resistance >= 50k"]
        )
        assert len(results) == 1
        assert results[0].lcsc_code == "C99999"

    def test_attr_filter_lte(self, populated_db):
        results = search_local(
            populated_db, attr_exprs=["Resistance <= 10k"]
        )
        assert len(results) == 2

    def test_combined_filters(self, populated_db):
        results = search_local(
            populated_db,
            package="0402",
            basic_only=True,
            attr_exprs=["Resistance >= 10k"],
        )
        assert len(results) == 2

    def test_invalid_filter_expr(self, populated_db):
        with pytest.raises(ValueError, match="Invalid attribute filter"):
            search_local(populated_db, attr_exprs=["bad filter"])

    def test_limit(self, populated_db):
        results = search_local(populated_db, limit=2)
        assert len(results) == 2

    def test_keyword_lcsc_code(self, populated_db):
        results = search_local(populated_db, keyword="C8287")
        assert len(results) == 1

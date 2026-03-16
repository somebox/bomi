"""Shared test fixtures."""

import json
import tempfile
from pathlib import Path

import pytest

from jlcpcb_tool.db import Database
from jlcpcb_tool.models import Attribute, Part, PriceTier


@pytest.fixture
def tmp_db(tmp_path):
    """Create a temporary database."""
    db = Database(tmp_path / "test.db")
    yield db
    db.close()


@pytest.fixture
def sample_part():
    """A sample Part for testing."""
    return Part(
        lcsc_code="C8287",
        mfr_part="RC0402FR-0710KL",
        manufacturer="YAGEO",
        package="0402",
        category="Chip Resistor - Surface Mount",
        subcategory="Resistors",
        description="10kΩ ±1% 1/16W 0402 Chip Resistor",
        stock=500000,
        library_type="base",
        preferred=True,
        datasheet_url="https://example.com/datasheet.pdf",
        jlcpcb_url="https://jlcpcb.com/partdetail/C8287",
        prices=[
            PriceTier(qty_from=1, qty_to=9, unit_price=0.0037),
            PriceTier(qty_from=10, qty_to=99, unit_price=0.0025),
            PriceTier(qty_from=100, qty_to=None, unit_price=0.0019),
        ],
        attributes=[
            Attribute(name="Resistance", value_raw="10kΩ", value_num=10000.0, unit="ohm"),
            Attribute(name="Power(Watts)", value_raw="1/16W", value_num=0.0625, unit="watt"),
            Attribute(name="Tolerance", value_raw="±1%", value_num=1.0, unit="percent"),
        ],
    )


@pytest.fixture
def sample_search_response():
    """Sample JLCPCB search API response."""
    return json.loads(SAMPLE_SEARCH_JSON)


SAMPLE_SEARCH_JSON = """{
  "code": 200,
  "data": {
    "componentPageInfo": {
      "total": 179,
      "pages": 18,
      "hasNextPage": true,
      "list": [
        {
          "componentCode": "C8287",
          "componentModelEn": "RC0402FR-0710KL",
          "componentBrandEn": "YAGEO",
          "componentSpecificationEn": "0402",
          "componentTypeEn": "Chip Resistor - Surface Mount",
          "firstSortName": "Chip Resistor - Surface Mount",
          "secondSortName": "Resistors",
          "componentLibraryType": "base",
          "preferredComponentFlag": true,
          "stockCount": 500000,
          "describe": "10kΩ ±1% 1/16W 0402 Chip Resistor - Surface Mount ROHS",
          "componentPrices": [
            {"startNumber": 1, "endNumber": 9, "productPrice": 0.0037},
            {"startNumber": 10, "endNumber": 99, "productPrice": 0.0025},
            {"startNumber": 100, "endNumber": -1, "productPrice": 0.0019}
          ],
          "attributes": [
            {"attribute_name_en": "Resistance", "attribute_value_name": "10kΩ"},
            {"attribute_name_en": "Power(Watts)", "attribute_value_name": "1/16W"},
            {"attribute_name_en": "Tolerance", "attribute_value_name": "±1%"}
          ],
          "dataManualUrl": "https://example.com/datasheet.pdf",
          "lcscGoodsUrl": "https://lcsc.com/product-detail/C8287.html",
          "urlSuffix": "Yageo-RC0402FR-0710KL_C8287",
          "leastPatchNumber": 5,
          "lossNumber": 3,
          "minPurchaseNum": 5
        },
        {
          "componentCode": "C25900",
          "componentModelEn": "0402WGF1002TCE",
          "componentBrandEn": "UNI-ROYAL",
          "componentSpecificationEn": "0402",
          "componentTypeEn": "Chip Resistor - Surface Mount",
          "firstSortName": "Chip Resistor - Surface Mount",
          "secondSortName": "Resistors",
          "componentLibraryType": "base",
          "preferredComponentFlag": false,
          "stockCount": 300000,
          "describe": "10kΩ ±1% 1/16W 0402 Chip Resistor - Surface Mount ROHS",
          "componentPrices": [
            {"startNumber": 1, "endNumber": 9, "productPrice": 0.0020},
            {"startNumber": 10, "endNumber": -1, "productPrice": 0.0015}
          ],
          "attributes": [
            {"attribute_name_en": "Resistance", "attribute_value_name": "10kΩ"},
            {"attribute_name_en": "Power(Watts)", "attribute_value_name": "1/16W"},
            {"attribute_name_en": "Tolerance", "attribute_value_name": "±1%"}
          ],
          "dataManualUrl": null,
          "lcscGoodsUrl": null,
          "urlSuffix": "UNI-ROYAL-0402WGF1002TCE_C25900",
          "leastPatchNumber": 5,
          "lossNumber": 3,
          "minPurchaseNum": 5
        }
      ]
    }
  }
}"""

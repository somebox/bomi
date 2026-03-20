"""Tests for BOM output formatters."""

import json

from bomi.models import Attribute, Part, PriceTier
from bomi.output import format_bom_json, format_bom_markdown, format_bom_table
from bomi.project import Project


def _sample_part() -> Part:
    return Part(
        lcsc_code="C123",
        mfr_part="TEST-MFR",
        manufacturer="ACME",
        package="0805",
        category="R",
        subcategory="Chip",
        description="Test resistor",
        stock=5000,
        library_type="base",
        preferred=True,
        datasheet_url="https://example.com/ds",
        jlcpcb_url="https://jlcpcb.com/part/C123",
        prices=[PriceTier(1, None, 0.01)],
        attributes=[Attribute("Resistance", "10k", 10000.0, "Ω")],
    )


def test_format_bom_json_shape():
    p = _sample_part()
    proj = Project(name="demo", description="d", selections=[])
    entries = [
        {
            "ref": "R1",
            "lcsc": "C123",
            "quantity": 2,
            "notes": "nb",
            "warnings": [],
            "part": p,
        },
    ]
    out = format_bom_json(entries, command_name="list")
    data = json.loads(out)
    assert data["status"] == "ok"
    assert data["command"] == "list"
    assert len(data["data"]) == 1
    row = data["data"][0]
    assert row["ref"] == "R1"
    assert row["price"] == 0.01


def test_format_bom_table_warnings_stderr_pairs():
    p = _sample_part()
    entries = [
        {
            "ref": "R1",
            "lcsc": "C123",
            "quantity": 1,
            "notes": "",
            "warnings": ["Low stock"],
            "part": p,
        },
    ]
    text, warn_pairs = format_bom_table(entries)
    assert "R1" in text
    assert warn_pairs == [("R1", "Low stock")]


def test_format_bom_markdown_grouping():
    p = _sample_part()
    proj = Project(name="g", description="", selections=[])
    entries = [
        {
            "ref": "R1",
            "lcsc": "C123",
            "quantity": 1,
            "notes": "a",
            "warnings": [],
            "part": p,
        },
        {
            "ref": "R2",
            "lcsc": "C123",
            "quantity": 3,
            "notes": "b",
            "warnings": [],
            "part": p,
        },
    ]
    md = format_bom_markdown(proj, entries)
    assert "# g" in md
    assert "R1, R2" in md or "R2, R1" in md
    assert "2 line items (1 unique parts)" in md

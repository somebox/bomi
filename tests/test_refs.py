"""Tests for reference designator parsing."""

import pytest

from jlcpcb_tool.refs import normalize_ref, parse_ref, ref_count, refs_overlap


def test_parse_single_ref():
    parsed = parse_ref("r10")
    assert parsed.prefix == "R"
    assert parsed.start == 10
    assert parsed.end == 10
    assert parsed.canonical() == "R10"


def test_parse_range_ref():
    parsed = parse_ref("U2-U4")
    assert parsed.prefix == "U"
    assert parsed.start == 2
    assert parsed.end == 4
    assert parsed.count == 3


def test_normalize_ref():
    assert normalize_ref("u2-u4") == "U2-U4"


def test_ref_count():
    assert ref_count("U2-U4") == 3
    assert ref_count("R1") == 1


def test_refs_overlap():
    assert refs_overlap("U2-U4", "U3")
    assert refs_overlap("U2-U4", "U4-U6")
    assert not refs_overlap("U2-U4", "U5-U6")
    assert not refs_overlap("U2-U4", "R3")


def test_invalid_range_rejected():
    with pytest.raises(ValueError, match="Invalid reference designator"):
        parse_ref("U2-4")


def test_descending_range_rejected():
    with pytest.raises(ValueError, match=">= start"):
        parse_ref("U4-U2")

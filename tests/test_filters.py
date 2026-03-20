"""Parity tests: in-memory post-fetch filters vs SQL ``query_parts``."""

import pytest

from bomi.db import Database
from bomi.filters import apply_post_fetch_filters, numeric_compare, part_matches_one_attr
from bomi.models import Attribute, Part, PriceTier
from bomi.search import parse_attr_filters, search_local


def _part(**kwargs) -> Part:
    defaults = dict(
        lcsc_code="C1",
        mfr_part="X",
        manufacturer="Y",
        package="0805",
        category="Resistors",
        subcategory="Chip",
        description="desc",
        stock=5000,
        library_type="base",
        preferred=False,
        prices=[PriceTier(1, None, 0.02)],
        attributes=[],
    )
    defaults.update(kwargs)
    return Part(**defaults)


def test_numeric_compare():
    assert numeric_compare(10.0, ">=", 10.0)
    assert not numeric_compare(9.9, ">=", 10.0)


def test_part_matches_string_attr():
    p = _part(
        attributes=[Attribute("Circuit", "SP3T", None, None)],
    )
    assert part_matches_one_attr(p, "Circuit", "=", "SP3T")
    assert not part_matches_one_attr(p, "Circuit", "=", "SPDT")
    assert part_matches_one_attr(p, "Circuit", "!=", "SPDT")


@pytest.mark.parametrize(
    "attr_expr",
    ["Resistance >= 10k", "Resistance >= 10000"],
)
def test_attr_filter_parity_numeric(tmp_path, attr_expr):
    part = _part(
        lcsc_code="CR1",
        attributes=[Attribute("Resistance", "10k", 10000.0, "Ω")],
    )
    with Database(tmp_path / "p.db") as db:
        db.upsert_part(part)
        exprs = parse_attr_filters([attr_expr])
        sql_hits = search_local(db, attr_exprs=[attr_expr], limit=10)
        mem_hits = apply_post_fetch_filters([part], attr_filters=exprs)
        assert [x.lcsc_code for x in sql_hits] == [x.lcsc_code for x in mem_hits]


def test_attr_filter_parity_string(tmp_path):
    part = _part(
        lcsc_code="SW1",
        attributes=[Attribute("Circuit", "SP3T", None, None)],
    )
    with Database(tmp_path / "p.db") as db:
        db.upsert_part(part)
        expr = "Circuit = SP3T"
        exprs = parse_attr_filters([expr])
        sql_hits = search_local(db, attr_exprs=[expr], limit=10)
        mem_hits = apply_post_fetch_filters([part], attr_filters=exprs)
        assert len(sql_hits) == len(mem_hits) == 1


def test_package_and_stock_parity(tmp_path):
    part = _part(lcsc_code="P1", package="SMD-0402", stock=100)
    with Database(tmp_path / "p.db") as db:
        db.upsert_part(part)
        sql_hits = search_local(db, package="0402", min_stock=50, limit=10)
        mem_hits = apply_post_fetch_filters(
            [part], package="0402", min_stock=50,
        )
        assert [x.lcsc_code for x in sql_hits] == [x.lcsc_code for x in mem_hits]

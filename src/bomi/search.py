"""Local DB query builder with attribute filters."""

from .db import Database
from .models import Part
from .units import parse_filter_expr


def parse_attr_filters(
    attr_exprs: list[str] | None = None,
) -> list[tuple[str, str, float | str]]:
    """Parse raw --attr expressions into normalized filters."""
    attr_filters: list[tuple[str, str, float | str]] = []
    if not attr_exprs:
        return attr_filters

    for expr in attr_exprs:
        parsed = parse_filter_expr(expr)
        if parsed is None:
            raise ValueError(f"Invalid attribute filter: {expr}")
        attr_filters.append(parsed)
    return attr_filters


def search_local(
    db: Database,
    keyword: str | None = None,
    category: str | None = None,
    package: str | None = None,
    min_stock: int | None = None,
    basic_only: bool = False,
    preferred_only: bool = False,
    max_price: float | None = None,
    attr_exprs: list[str] | None = None,
    limit: int = 50,
) -> list[Part]:
    """Search local DB with parsed attribute filter expressions.

    attr_exprs: list of strings like "Resistance >= 10k"
    """
    attr_filters = parse_attr_filters(attr_exprs)

    return db.query_parts(
        keyword=keyword,
        category=category,
        package=package,
        min_stock=min_stock,
        basic_only=basic_only,
        preferred_only=preferred_only,
        max_price=max_price,
        attr_filters=attr_filters,
        limit=limit,
    )

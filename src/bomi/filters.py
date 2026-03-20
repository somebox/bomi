"""Shared filtering rules for local ``query`` (SQL) and post-API ``search``.

Intentional differences (not unified here):

- ``search``: ``--basic-only`` / ``--preferred-only`` are applied by the JLCPCB API
  only; results are not re-filtered locally for those flags.
- ``search --category``: resolves to an exact synced subcategory name for the API.
  ``query --category`` uses SQL ``LIKE`` on ``parts.category`` (substring).

Package, min stock, max price (qty-1 tier), and ``--attr`` handling are aligned
between :func:`apply_post_fetch_filters` and :func:`append_attr_filter_sql`.
"""

from __future__ import annotations

from .models import Part

# ---------------------------------------------------------------------------
# Post-fetch filtering (in-memory ``Part`` list after ``search`` API)
# ---------------------------------------------------------------------------


def numeric_compare(value: float, op: str, threshold: float) -> bool:
    ops = {
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
        "=": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
    }
    fn = ops.get(op)
    if fn is None:
        return False
    return fn(value, threshold)


def part_matches_one_attr(
    part: Part,
    attr_name: str,
    op: str,
    threshold: float | str,
) -> bool:
    attr = next((a for a in part.attributes if a.name == attr_name), None)
    if attr is None:
        return False
    if isinstance(threshold, str):
        if op == "=" and attr.value_raw == threshold:
            return True
        if op == "!=" and attr.value_raw != threshold:
            return True
        return False
    if attr.value_num is not None:
        return numeric_compare(attr.value_num, op, threshold)
    return False


def _part_matches_price_cap(part: Part, max_price: float) -> bool:
    return bool(part.prices and part.prices[0].unit_price <= max_price)


def apply_post_fetch_filters(
    parts: list[Part],
    package: str | None = None,
    min_stock: int | None = None,
    max_price: float | None = None,
    attr_filters: list[tuple[str, str, float | str]] | None = None,
) -> list[Part]:
    """Filter normalized parts after a live API search (local constraints)."""
    result = list(parts)

    if package:
        result = [p for p in result if package.lower() in p.package.lower()]

    if min_stock is not None:
        result = [p for p in result if p.stock >= min_stock]

    if max_price is not None:
        result = [p for p in result if _part_matches_price_cap(p, max_price)]

    if attr_filters:
        for attr_name, op, threshold in attr_filters:
            result = [
                p for p in result
                if part_matches_one_attr(p, attr_name, op, threshold)
            ]

    return result


# ---------------------------------------------------------------------------
# SQL fragments for ``Database.query_parts`` (must stay in sync with above)
# ---------------------------------------------------------------------------


def append_attr_filter_sql(
    conditions: list[str],
    params: list,
    attr_name: str,
    op: str,
    value: float | str,
) -> None:
    """Append one attribute EXISTS clause and bound parameters."""
    if isinstance(value, str):
        if op == "!=":
            conditions.append(
                "EXISTS (SELECT 1 FROM attributes a "
                "WHERE a.lcsc_code = p.lcsc_code "
                "AND a.attr_name = ? AND a.attr_value_raw != ?)"
            )
        else:
            conditions.append(
                "EXISTS (SELECT 1 FROM attributes a "
                "WHERE a.lcsc_code = p.lcsc_code "
                "AND a.attr_name = ? AND a.attr_value_raw = ?)"
            )
        params.extend([attr_name, value])
        return

    sql_op = op if op != "=" else "="
    conditions.append(
        f"EXISTS (SELECT 1 FROM attributes a "
        f"WHERE a.lcsc_code = p.lcsc_code "
        f"AND a.attr_name = ? AND a.attr_value_num {sql_op} ?)"
    )
    params.extend([attr_name, value])

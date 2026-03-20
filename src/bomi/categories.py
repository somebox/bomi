"""Category name resolution for search (API) vs query (local cache)."""

from __future__ import annotations

import click

from .db import Database


def validate_category_for_query(db: Database, category: str) -> None:
    """Validate ``category`` against synced categories (optional, for ``query``).

    Does not resolve to an exact name: ``query`` uses substring matching on
    the parts table. Exits the process on invalid input when categories exist.
    """
    cats = db.get_categories()
    if not cats:
        return

    matches = db.match_category(category)
    if not matches:
        click.echo(
            f"No category matching '{category}'. "
            "Run 'bomi categories' to see available categories.",
            err=True,
        )
        raise SystemExit(1)

    exact = [m for m in matches if m.lower() == category.lower()]
    resolved = exact[0] if len(exact) == 1 else (matches[0] if len(matches) == 1 else None)
    if resolved:
        children = db.get_categories(parent=resolved)
        if children:
            click.echo(
                f"Note: '{resolved}' is a top-level category. "
                "Use a subcategory for more specific results. "
                "Run 'bomi categories' to browse.",
                err=True,
            )


def resolve_category_for_search(db: Database, category: str) -> str:
    """Resolve substring to exact JLCPCB API subcategory name. Exits on error."""
    matches = db.match_category(category)

    if not matches:
        has_any = bool(db.get_categories())
        if not has_any:
            click.echo(
                "No categories cached. Run 'bomi sync' first.",
                err=True,
            )
        else:
            click.echo(
                f"No category matching '{category}'. "
                "Run 'bomi categories' to see available categories.",
                err=True,
            )
        raise SystemExit(1)

    resolved = None
    if len(matches) == 1:
        resolved = matches[0]
    else:
        exact = [m for m in matches if m.lower() == category.lower()]
        if len(exact) == 1:
            resolved = exact[0]

    if resolved:
        children = db.get_categories(parent=resolved)
        if children:
            click.echo(
                f"'{resolved}' is a top-level category. "
                "Pick a subcategory:",
                err=True,
            )
            for child in children:
                cc = (
                    f" ({child['part_count']:,})"
                    if child["part_count"]
                    else ""
                )
                click.echo(f"  {child['name']}{cc}", err=True)
            raise SystemExit(1)
        return resolved

    all_cats_map = {c["name"]: c for c in db.get_categories()}
    subcats = [
        m
        for m in matches
        if all_cats_map.get(m, {}).get("parent") is not None
    ]

    if len(subcats) == 1:
        return subcats[0]

    display = subcats if subcats else matches
    click.echo(
        f"'{category}' matches multiple categories:",
        err=True,
    )
    for m in display:
        click.echo(f"  {m}", err=True)
    click.echo(
        "\nBe more specific or use the exact name.",
        err=True,
    )
    raise SystemExit(1)

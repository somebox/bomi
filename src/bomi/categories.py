"""Category name resolution for search (API) vs query (local cache)."""

from __future__ import annotations

import click

from .db import Database


def _resolve_category(
    db: Database, category: str
) -> tuple[list[str], str | None, list[dict]]:
    """Shared substring-match + single-resolution step.

    Returns ``(matches, resolved, children)``:
      - ``matches``: raw substring matches from ``db.match_category``.
      - ``resolved``: the single unambiguous match (exact case-insensitive
        match among several, or the only match), or None if ambiguous/no
        matches.
      - ``children``: subcategories of ``resolved`` (empty list if
        ``resolved`` is None or has no children).

    Both ``validate_category_for_query`` and ``resolve_category_for_search``
    build on this; they differ only in what they do with an unresolved or
    top-level result (warn-and-continue vs. hard-exit-with-suggestions).
    """
    matches = db.match_category(category)

    resolved = None
    if len(matches) == 1:
        resolved = matches[0]
    else:
        exact = [m for m in matches if m.lower() == category.lower()]
        if len(exact) == 1:
            resolved = exact[0]

    children = db.get_categories(parent=resolved) if resolved else []
    return matches, resolved, children


def validate_category_for_query(db: Database, category: str) -> None:
    """Validate ``category`` against synced categories (optional, for ``query``).

    Does not resolve to an exact name: ``query`` uses substring matching on
    the parts table. Exits the process on invalid input when categories exist.
    """
    cats = db.get_categories()
    if not cats:
        return

    matches, resolved, children = _resolve_category(db, category)

    if not matches:
        click.echo(
            f"No category matching '{category}'. "
            "Run 'bomi categories' to see available categories.",
            err=True,
        )
        raise SystemExit(1)

    if resolved and children:
        click.echo(
            f"Note: '{resolved}' is a top-level category. "
            "Use a subcategory for more specific results. "
            "Run 'bomi categories' to browse.",
            err=True,
        )


def resolve_category_for_search(db: Database, category: str) -> str:
    """Resolve substring to exact JLCPCB API subcategory name. Exits on error."""
    matches, resolved, children = _resolve_category(db, category)

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

    if resolved:
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

    # Ambiguous: multiple matches, none an exact match. Prefer disambiguating
    # via subcategories (leaf categories are usually what the caller wants).
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

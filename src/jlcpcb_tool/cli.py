"""Click CLI commands."""

import sys

import click

from .api import JLCPCBClient
from .config import get_db_path
from .db import Database
from .normalize import get_search_metadata, normalize_search_response
from .output import format_compare, format_envelope, format_part_detail, format_parts
from .search import search_local
from .units import parse_value


def get_db() -> Database:
    return Database(get_db_path())


# Common options
_format_option = click.option(
    "--format", "fmt", type=click.Choice(["table", "json", "csv"]),
    default="table", help="Output format",
)
_attr_option = click.option(
    "--attr", "attrs", multiple=True,
    help='Attribute filter, e.g. "Resistance >= 10k"',
)


@click.group()
def cli():
    """JLCPCB/LCSC component research tool."""
    pass


@cli.command()
@click.argument("keyword")
@click.option("--package", help="Filter by package")
@click.option("--min-stock", type=int, help="Minimum stock")
@click.option("--basic-only", is_flag=True, help="Basic parts only")
@click.option("--preferred-only", is_flag=True, help="Preferred parts only")
@click.option("--max-price", type=float, help="Max unit price (qty 1)")
@_attr_option
@click.option("--limit", type=int, default=25, help="Results per page")
@click.option("--pages", type=int, default=1, help="Number of pages to fetch")
@_format_option
def search(keyword, package, min_stock, basic_only, preferred_only,
           max_price, attrs, limit, pages, fmt):
    """Search JLCPCB API for components."""
    client = JLCPCBClient()
    db = get_db()
    all_parts = []

    try:
        for page in range(1, pages + 1):
            response = client.search(
                keyword, page=page, page_size=limit,
                basic_only=basic_only, preferred_only=preferred_only,
            )
            parts = normalize_search_response(response)
            meta = get_search_metadata(response)

            for part in parts:
                db.upsert_part(part)
            all_parts.extend(parts)

            if not meta["has_next_page"]:
                break

        # Apply local filters
        filtered = _apply_local_filters(
            all_parts, package=package, min_stock=min_stock,
            max_price=max_price, attrs=list(attrs),
        )

        click.echo(format_parts(filtered, fmt, command="search"))
    finally:
        db.close()


@cli.command()
@click.argument("lcsc_codes", nargs=-1, required=True)
@click.option("--force", is_flag=True, help="Re-fetch even if cached")
@click.option("--detail", is_flag=True, help="Fetch extended LCSC detail")
@_format_option
def fetch(lcsc_codes, force, detail, fmt):
    """Fetch specific part(s) by LCSC code."""
    client = JLCPCBClient()
    db = get_db()
    fetched = []

    try:
        for code in lcsc_codes:
            code = code.upper()
            if not code.startswith("C"):
                code = f"C{code}"

            if not force:
                age = db.get_part_age_hours(code)
                if age is not None and age < 24:
                    part = db.get_part(code)
                    if part:
                        fetched.append(part)
                        continue

            # Search by exact LCSC code
            response = client.search(code, page_size=5)
            parts = normalize_search_response(response)
            match = next((p for p in parts if p.lcsc_code == code), None)

            if match:
                db.upsert_part(match)
                fetched.append(match)
            else:
                click.echo(f"Part {code} not found.", err=True)

        click.echo(format_parts(fetched, fmt, command="fetch"))
    finally:
        db.close()


@cli.command()
@click.argument("keyword", required=False, default=None)
@click.option("--package", help="Filter by package")
@click.option("--min-stock", type=int, help="Minimum stock")
@click.option("--basic-only", is_flag=True, help="Basic parts only")
@click.option("--preferred-only", is_flag=True, help="Preferred parts only")
@click.option("--max-price", type=float, help="Max unit price (qty 1)")
@_attr_option
@click.option("--limit", type=int, default=50, help="Max results")
@_format_option
def query(keyword, package, min_stock, basic_only, preferred_only,
          max_price, attrs, limit, fmt):
    """Query LOCAL database (no API calls)."""
    db = get_db()
    try:
        results = search_local(
            db, keyword=keyword, package=package, min_stock=min_stock,
            basic_only=basic_only, preferred_only=preferred_only,
            max_price=max_price, attr_exprs=list(attrs), limit=limit,
        )
        click.echo(format_parts(results, fmt, command="query"))
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    finally:
        db.close()


@cli.command()
@click.argument("lcsc_code")
@_format_option
def info(lcsc_code, fmt):
    """Show full detail of a cached part."""
    db = get_db()
    try:
        code = lcsc_code.upper()
        if not code.startswith("C"):
            code = f"C{code}"

        part = db.get_part(code)
        if not part:
            click.echo(f"Part {code} not found in local database. Run 'jlcpcb fetch {code}' first.", err=True)
            sys.exit(1)

        click.echo(format_part_detail(part, fmt))
    finally:
        db.close()


@cli.command()
@click.argument("lcsc_codes", nargs=-1, required=True)
@click.option("--use-case", help="Describe use case for LLM comparison")
@_format_option
def compare(lcsc_codes, use_case, fmt):
    """Compare parts side-by-side."""
    db = get_db()
    try:
        parts = []
        for code in lcsc_codes:
            code = code.upper()
            if not code.startswith("C"):
                code = f"C{code}"
            part = db.get_part(code)
            if part:
                parts.append(part)
            else:
                click.echo(f"Part {code} not found in local database.", err=True)

        if not parts:
            click.echo("No parts found to compare.", err=True)
            sys.exit(1)

        click.echo(format_compare(parts, fmt))
    finally:
        db.close()


@cli.command()
@click.argument("lcsc_code")
@click.option("--method", type=click.Choice(["openrouter", "llmlayer"]),
              default="openrouter", help="Analysis method")
@click.option("--prompt", default="Summarize the key specifications from this datasheet.",
              help="Analysis prompt")
@click.option("--model", default=None, help="Override model name")
@_format_option
def analyze(lcsc_code, method, prompt, model, fmt):
    """Analyze a part's datasheet using LLM."""
    from .analysis import analyze_part

    db = get_db()
    try:
        code = lcsc_code.upper()
        if not code.startswith("C"):
            code = f"C{code}"

        part = db.get_part(code)
        if not part:
            click.echo(f"Part {code} not found. Run 'jlcpcb fetch {code}' first.", err=True)
            sys.exit(1)

        result = analyze_part(db, part, method=method, prompt=prompt, model=model)

        if fmt == "json":
            click.echo(format_envelope("ok", "analyze", [result]))
        else:
            click.echo(f"Analysis of {code} ({method}):")
            click.echo(f"Model: {result.get('model', 'N/A')}")
            click.echo(f"Cost: ${result.get('cost_usd', 0):.4f}")
            click.echo("")
            click.echo(result.get("response", ""))
    finally:
        db.close()


@cli.group()
def db():
    """Database management commands."""
    pass


@db.command()
@_format_option
def stats(fmt):
    """Show database statistics."""
    database = get_db()
    try:
        s = database.stats()
        if fmt == "json":
            click.echo(format_envelope("ok", "db stats", [s]))
        else:
            click.echo(f"Parts:      {s['parts']:,}")
            click.echo(f"Attributes: {s['attributes']:,}")
            click.echo(f"Analyses:   {s['analyses']:,}")
            click.echo(f"Categories: {s['categories']:,}")
    finally:
        database.close()


@db.command()
@click.confirmation_option(prompt="Are you sure you want to clear all data?")
def clear():
    """Clear all data from the database."""
    database = get_db()
    try:
        database.clear()
        click.echo("Database cleared.")
    finally:
        database.close()


def _apply_local_filters(
    parts: list,
    package: str | None = None,
    min_stock: int | None = None,
    max_price: float | None = None,
    attrs: list[str] | None = None,
) -> list:
    """Apply local filters to a list of Part objects after API fetch."""
    result = parts

    if package:
        result = [p for p in result if package.lower() in p.package.lower()]

    if min_stock is not None:
        result = [p for p in result if p.stock >= min_stock]

    if max_price is not None:
        result = [
            p for p in result
            if p.prices and p.prices[0].unit_price <= max_price
        ]

    if attrs:
        for expr in attrs:
            from .units import parse_filter_expr
            parsed = parse_filter_expr(expr)
            if parsed is None:
                continue
            attr_name, op, threshold = parsed
            filtered = []
            for p in result:
                attr = next(
                    (a for a in p.attributes if a.name == attr_name), None
                )
                if attr and attr.value_num is not None:
                    if _compare(attr.value_num, op, threshold):
                        filtered.append(p)
            result = filtered

    return result


def _compare(value: float, op: str, threshold: float) -> bool:
    ops = {
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
        "=": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
    }
    return ops.get(op, lambda a, b: False)(value, threshold)

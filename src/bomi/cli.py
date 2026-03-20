"""Click CLI commands."""

import sys
from pathlib import Path

import click
import requests

from .api import JLCPCBClient
from .categories import resolve_category_for_search, validate_category_for_query
from .filters import apply_post_fetch_filters
from .config import find_project_dir, get_config, get_db_path
from .db import Database
from .normalize import get_search_metadata, normalize_search_response
from .output import (
    format_bom_csv,
    format_bom_json,
    format_bom_markdown,
    format_bom_table,
    format_compare,
    format_envelope,
    format_part_detail,
    format_parts,
)
from .search import parse_attr_filters, search_local


def get_db() -> Database:
    return Database(get_db_path())


# Common options
_format_option = click.option(
    "--format", "fmt", type=click.Choice(["table", "json", "csv", "markdown"]),
    default="table", help="Output format",
)
_attr_option = click.option(
    "--attr", "attrs", multiple=True,
    help='Attribute filter, e.g. "Resistance >= 10k"',
)


@click.group()
@click.option("--project", "project_path", default=None,
              help="Path to project directory (overrides auto-detection)")
@click.pass_context
def cli(ctx, project_path):
    """JLCPCB/LCSC component research tool."""
    ctx.ensure_object(dict)
    ctx.obj["project_path"] = project_path


def _require_project(ctx) -> "Project":
    """Load project from context, or error if not found."""
    from .project import load_project

    project_path = ctx.obj.get("project_path")
    project_dir = find_project_dir(override=project_path)
    if not project_dir:
        click.echo("No project found. Run 'bomi init' or use --project.", err=True)
        sys.exit(1)
    return load_project(project_dir)


# ── Existing commands (unchanged, work without project) ──────────────


@cli.command()
@click.argument("keyword")
@click.option("--category", help="Filter by category (substring match)")
@click.option("--package", help="Filter by package")
@click.option("--min-stock", type=int, help="Minimum stock")
@click.option("--basic-only", is_flag=True, help="Basic parts only")
@click.option("--preferred-only", is_flag=True, help="Preferred parts only")
@click.option("--max-price", type=float, help="Max unit price (qty 1)")
@_attr_option
@click.option("--limit", type=int, default=25, help="Results per page")
@click.option("--pages", type=int, default=1, help="Number of pages to fetch")
@_format_option
def search(keyword, category, package, min_stock, basic_only, preferred_only,
           max_price, attrs, limit, pages, fmt):
    """Search JLCPCB API for components."""
    try:
        attr_filters = parse_attr_filters(list(attrs))
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Resolve --category to an exact category name via the local cache.
    # The JLCPCB API only filters on subcategory-level names (those with a
    # parent).  If the user picks a top-level parent we show its children
    # so they can refine.
    client = JLCPCBClient()
    with get_db() as db:
        component_type = None
        if category:
            component_type = resolve_category_for_search(db, category)

        all_parts = []
        try:
            for page in range(1, pages + 1):
                response = client.search(
                    keyword, page=page, page_size=limit,
                    basic_only=basic_only, preferred_only=preferred_only,
                    component_type=component_type,
                )
                parts = normalize_search_response(response)
                meta = get_search_metadata(response)

                for part in parts:
                    db.upsert_part(part)
                all_parts.extend(parts)

                if not meta["has_next_page"]:
                    break
        except requests.RequestException as e:
            click.echo(f"Error: JLCPCB search failed: {e}", err=True)
            sys.exit(1)
        except (KeyError, TypeError, ValueError) as e:
            click.echo(f"Error: Invalid response from JLCPCB API: {e}", err=True)
            sys.exit(1)

        # Apply local filters
        filtered = apply_post_fetch_filters(
            all_parts, package=package, min_stock=min_stock,
            max_price=max_price, attr_filters=attr_filters,
        )

        if not filtered and all_parts:
            active = []
            if min_stock is not None:
                active.append(f"--min-stock {min_stock}")
            if package:
                active.append(f"--package {package}")
            if max_price is not None:
                active.append(f"--max-price {max_price}")
            if attrs:
                active.extend(f'--attr "{a}"' for a in attrs)
            hint = f"Fetched {len(all_parts)} result(s), none passed local filters ({', '.join(active)})."
            hints = []
            if pages == 1:
                hints.append("--pages N to fetch more before filtering")
            if attrs:
                hints.append("a more specific keyword")
            if hints:
                hint += " Try " + " or ".join(hints) + "."
            click.echo(hint, err=True)

        click.echo(format_parts(filtered, fmt, command="search"))


@cli.command()
@click.argument("lcsc_codes", nargs=-1, required=False)
@click.option("--all", "fetch_all", is_flag=True, help="Fetch all selected LCSC parts from the current project")
@click.option("--force", is_flag=True, help="Re-fetch even if cached")
@_format_option
@click.pass_context
def fetch(ctx, lcsc_codes, fetch_all, force, fmt):
    """Fetch specific part(s) by LCSC code, or all parts in the active project."""
    if fetch_all and lcsc_codes:
        click.echo("Error: Use either explicit LCSC codes or --all, not both.", err=True)
        sys.exit(1)

    if fetch_all:
        project = _require_project(ctx)
        resolved = []
        for sel in project.selections:
            if sel.lcsc and sel.lcsc not in resolved:
                resolved.append(sel.lcsc)
        if not resolved:
            click.echo("No selected LCSC parts found in project BOM.", err=True)
            sys.exit(1)
        lcsc_codes = tuple(resolved)
    elif not lcsc_codes:
        click.echo("Error: Provide one or more LCSC codes, or use --all.", err=True)
        sys.exit(1)

    total = len(lcsc_codes)
    batch_mode = fetch_all or total > 1
    if batch_mode:
        click.echo(f"Fetching {total} part(s)...", err=True)

    client = JLCPCBClient()
    fetched = []

    with get_db() as db:
        for idx, code in enumerate(lcsc_codes, start=1):
            code = code.upper()
            if not code.startswith("C"):
                code = f"C{code}"

            if batch_mode:
                click.echo(f"[{idx}/{total}] {code}", err=True, nl=False)

            if not force:
                age = db.get_part_age_hours(code)
                if age is not None and age < 24:
                    part = db.get_part(code)
                    if part:
                        fetched.append(part)
                        if batch_mode:
                            click.echo(" (cached)", err=True)
                        continue

            # Search by exact LCSC code
            try:
                response = client.search(code, page_size=5)
                parts = normalize_search_response(response)
            except requests.RequestException as e:
                click.echo(f"Error: Failed to fetch {code}: {e}", err=True)
                sys.exit(1)
            except (KeyError, TypeError, ValueError) as e:
                click.echo(f"Error: Invalid response while fetching {code}: {e}", err=True)
                sys.exit(1)
            match = next((p for p in parts if p.lcsc_code == code), None)

            if match:
                db.upsert_part(match)
                fetched.append(match)
                if batch_mode:
                    click.echo(" (updated)", err=True)
            else:
                if batch_mode:
                    click.echo(" (not found)", err=True)
                click.echo(f"Part {code} not found.", err=True)

        click.echo(format_parts(fetched, fmt, command="fetch"))


@cli.command()
@click.argument("keyword", required=False, default=None)
@click.option("--category", help="Filter by category (substring match)")
@click.option("--package", help="Filter by package")
@click.option("--min-stock", type=int, help="Minimum stock")
@click.option("--basic-only", is_flag=True, help="Basic parts only")
@click.option("--preferred-only", is_flag=True, help="Preferred parts only")
@click.option("--max-price", type=float, help="Max unit price (qty 1)")
@_attr_option
@click.option("--limit", type=int, default=50, help="Max results")
@_format_option
def query(keyword, category, package, min_stock, basic_only, preferred_only,
          max_price, attrs, limit, fmt):
    """Query LOCAL database (no API calls)."""
    with get_db() as db:
        if category:
            validate_category_for_query(db, category)

        try:
            results = search_local(
                db, keyword=keyword, category=category, package=package,
                min_stock=min_stock, basic_only=basic_only,
                preferred_only=preferred_only, max_price=max_price,
                attr_exprs=list(attrs), limit=limit,
            )
            click.echo(format_parts(results, fmt, command="query"))
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)


@cli.command()
@click.argument("part_ref")
@_format_option
@click.pass_context
def info(ctx, part_ref, fmt):
    """Show full detail of a cached part by designator or LCSC code."""
    from .project import load_project
    from .refs import normalize_ref

    with get_db() as db:
        code = None

        # Prefer a matching designator in the current project when available.
        project_path = ctx.obj.get("project_path")
        project_dir = find_project_dir(override=project_path)
        if project_dir:
            try:
                canonical_ref = normalize_ref(part_ref)
                project = load_project(project_dir)
                selection = next((s for s in project.selections if s.ref == canonical_ref), None)
                if selection:
                    if not selection.lcsc:
                        click.echo(f"Reference {canonical_ref} has no selected LCSC part yet.", err=True)
                        sys.exit(1)
                    code = selection.lcsc
            except ValueError:
                # Not a valid designator; treat as an LCSC code below.
                pass

        if code is None:
            code = part_ref.upper()
            if not code.startswith("C"):
                code = f"C{code}"

        part = db.get_part(code)
        if not part:
            click.echo(f"Part {code} not found in local database. Run 'bomi fetch {code}' first.", err=True)
            sys.exit(1)

        click.echo(format_part_detail(part, fmt))


@cli.command()
@click.argument("lcsc_codes", nargs=-1, required=True)
@_format_option
def compare(lcsc_codes, fmt):
    """Compare parts side-by-side."""
    with get_db() as db:
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


@cli.command()
@click.argument("lcsc_code")
@click.option("--prompt", default=(
                  "Provide a concise technical summary of this component. Include:\n"
                  "- Key specifications (voltage, current, frequency, temperature range)\n"
                  "- Pin descriptions with pin numbers\n"
                  "- Typical application circuit component values\n"
                  "- Important design notes and limitations\n"
                  "Format as markdown. Be precise with values and units."
              ), help="Analysis prompt")
@click.option("--model", default=None, help="Override model name")
@click.option("--pdf-engine", default="mistral-ocr",
              type=click.Choice(["mistral-ocr", "pdf-text", "native"]),
              help="PDF parsing engine")
@_format_option
def analyze(lcsc_code, prompt, model, pdf_engine, fmt):
    """Analyze a part's datasheet using LLM.

    Downloads the PDF first, then sends it to OpenRouter for analysis.
    """
    from .analysis import analyze_part

    with get_db() as db:
        code = lcsc_code.upper()
        if not code.startswith("C"):
            code = f"C{code}"

        part = db.get_part(code)
        if not part:
            click.echo(f"Part {code} not found. Run 'bomi fetch {code}' first.", err=True)
            sys.exit(1)

        try:
            result = analyze_part(db, part, prompt=prompt, model=model, pdf_engine=pdf_engine)
        except requests.RequestException as e:
            click.echo(f"Error: Datasheet analysis request failed: {e}", err=True)
            sys.exit(1)
        except (KeyError, TypeError, ValueError) as e:
            click.echo(f"Error: Invalid analysis response: {e}", err=True)
            sys.exit(1)

        if "error" in result:
            click.echo(result["error"], err=True)
            sys.exit(1)

        if fmt == "json":
            click.echo(format_envelope("ok", "analyze", [result]))
        else:
            chunks = result.get("chunks", 1)
            chunk_info = f" ({chunks} chunks)" if chunks > 1 else ""
            click.echo(f"Analysis of {code}{chunk_info}:")
            click.echo(f"Model: {result.get('model', 'N/A')}")
            click.echo(f"Cost: ${result.get('cost_usd', 0):.4f}")
            click.echo("")
            click.echo(result.get("response", ""))


@cli.command()
@click.argument("lcsc_codes", nargs=-1, required=False)
@click.option("--all", "fetch_all", is_flag=True, help="Process datasheets for all selected LCSC parts from the current project")
@click.option("--output", "-o", default=None,
              help="Output directory (default: docs/datasheets in project, else current dir)",
              type=click.Path())
@click.option("--force", is_flag=True, help="Re-download PDF even if a local copy exists")
@click.option("--pdf", "dl_pdf", is_flag=True, help="Download datasheet PDF")
@click.option("--summary", "--summarize", "dl_summary", is_flag=True, help="Generate markdown summary via LLM")
@click.option("--prompt", default=None, help="Custom analysis prompt for summary")
@click.option("--model", default=None, help="Override model name for summary")
@click.option("--pdf-engine", default="mistral-ocr",
              type=click.Choice(["mistral-ocr", "pdf-text", "native"]),
              help="PDF parsing engine (mistral-ocr for scanned/CJK, pdf-text for clean text, native for model-native)")
@click.pass_context
def datasheet(ctx, lcsc_codes, fetch_all, output, force, dl_pdf, dl_summary, prompt, model, pdf_engine):
    """Download datasheets as PDF and/or generate markdown summaries.

    Pipeline: download PDF → (optional) save to disk → send to LLM via
    OpenRouter file API → save markdown summary.

    When --summary is used, the PDF is always downloaded first (required
    for analysis). If --pdf is also set, the same download is saved to disk.

    Large PDFs (>1.5MB) are automatically split into chunks and analyzed
    in parts, then synthesized into a single summary.

    Examples:

        bomi datasheet C9864 --pdf -o docs/datasheets/

        bomi datasheet C9864 --summary --model openai/gpt-5.4

        bomi datasheet C9864 --pdf --summary --pdf-engine pdf-text
    """
    from .analysis import analyze_part, download_pdf

    if fetch_all and lcsc_codes:
        click.echo("Error: Use either explicit LCSC codes or --all, not both.", err=True)
        sys.exit(1)

    if fetch_all:
        project = _require_project(ctx)
        resolved = []
        for sel in project.selections:
            if sel.lcsc and sel.lcsc not in resolved:
                resolved.append(sel.lcsc)
        if not resolved:
            click.echo("No selected LCSC parts found in project BOM.", err=True)
            sys.exit(1)
        lcsc_codes = tuple(resolved)
    elif not lcsc_codes:
        click.echo("Error: Provide one or more LCSC codes, or use --all.", err=True)
        sys.exit(1)

    total = len(lcsc_codes)
    batch_mode = fetch_all or total > 1

    if not dl_pdf and not dl_summary:
        dl_pdf = True  # default to PDF download if neither specified

    if output is None:
        project_dir = find_project_dir(override=ctx.obj.get("project_path") if ctx.obj else None)
        configured_output = get_config("datasheet_output_dir")
        if configured_output:
            configured_path = Path(configured_output).expanduser()
            if configured_path.is_absolute():
                output = str(configured_path)
            elif project_dir:
                output = str(project_dir / configured_path)
            else:
                output = str(configured_path)
        elif project_dir:
            output = str(project_dir / "docs" / "datasheets")
        else:
            output = "."

    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    with get_db() as db:
        for idx, lcsc_code in enumerate(lcsc_codes, start=1):
            code = lcsc_code.upper()
            if not code.startswith("C"):
                code = f"C{code}"

            if batch_mode:
                click.echo(f"[{idx}/{total}] {code}", err=True)

            part = db.get_part(code)
            if not part:
                click.echo(f"Part {code} not found. Run 'bomi fetch {code}' first.", err=True)
                continue

            if not part.datasheet_url:
                click.echo(f"{code}: No datasheet URL available.", err=True)
                continue

            safe_name = part.mfr_part.replace("/", "_").replace(" ", "_")
            pdf_path = output_dir / f"{safe_name}_{code}.pdf"
            md_path = output_dir / f"{safe_name}_{code}.md"

            if dl_summary and md_path.exists() and not force:
                click.echo(f"{code}: Summary exists ({md_path.name}), skipping (use --force to refresh)")
                continue

            # Step 1: Get PDF bytes (download or load from disk)
            pdf_data = None

            # Use existing local PDF if present (may have been manually placed),
            # unless --force requests a fresh download.
            if pdf_path.exists() and not force:
                pdf_data = pdf_path.read_bytes()
                if pdf_data[:5] != b"%PDF-":
                    pdf_data = None  # not a valid PDF

            # Download if we don't have it yet
            if pdf_data is None:
                click.echo(f"Downloading {code} ({part.mfr_part})...", nl=False)
                pdf_data = download_pdf(part.datasheet_url)
                if pdf_data:
                    click.echo(f" {len(pdf_data) // 1024}KB")
                    # Always save when downloading (needed alongside summary)
                    if dl_pdf or dl_summary:
                        pdf_path.write_bytes(pdf_data)
                else:
                    click.echo(f" not directly downloadable", err=True)
                    click.echo(f"  Download manually: {part.datasheet_url}", err=True)
                    if dl_summary:
                        click.echo(f"  Place PDF at: {pdf_path}", err=True)
                    continue
            elif dl_pdf:
                click.echo(f"{code}: Using existing {pdf_path} ({len(pdf_data) // 1024}KB)")

            # Step 2: Generate summary
            if dl_summary:
                analysis_prompt = prompt or (
                    "Provide a concise technical summary of this component. Include:\n"
                    "- Key specifications (voltage, current, temperature range)\n"
                    "- Pin descriptions with pin numbers\n"
                    "- Typical application circuit component values\n"
                    "- Important design notes or limitations\n"
                    "Format as markdown. Be precise with pin numbers and specifications."
                )
                click.echo(f"Analyzing {code} ({part.mfr_part})...", nl=False)
                try:
                    result = analyze_part(
                        db, part, prompt=analysis_prompt, model=model,
                        pdf_data=pdf_data, pdf_engine=pdf_engine,
                    )
                except Exception as e:
                    click.echo(f" FAILED: {e}", err=True)
                    continue

                if "error" in result:
                    click.echo(f" FAILED: {result['error']}", err=True)
                    continue

                chunks = result.get("chunks", 1)
                chunk_info = f", {chunks} chunks" if chunks > 1 else ""
                header = (
                    f"# {part.mfr_part} ({code})\n\n"
                    f"**Manufacturer:** {part.manufacturer}  \n"
                    f"**Package:** {part.package}  \n"
                    f"**Category:** {part.category}  \n"
                    f"**Datasheet:** {part.datasheet_url}  \n"
                    f"**JLCPCB:** {part.jlcpcb_url}  \n\n"
                    f"---\n\n"
                )
                md_path.write_text(header + result.get("response", ""))
                cost = result.get("cost_usd", 0)
                click.echo(f" {md_path} (${cost:.4f}{chunk_info})")


@cli.group()
def db():
    """Database management commands."""
    pass


@db.command()
@_format_option
def stats(fmt):
    """Show database statistics."""
    with get_db() as database:
        s = database.stats()
        if fmt == "json":
            click.echo(format_envelope("ok", "db stats", [s]))
        else:
            click.echo(f"Parts:      {s['parts']:,}")
            click.echo(f"Attributes: {s['attributes']:,}")
            click.echo(f"Analyses:   {s['analyses']:,}")
            click.echo(f"Categories: {s['categories']:,}")


@db.command()
@click.confirmation_option(prompt="Are you sure you want to clear all data?")
def clear():
    """Clear all data from the database."""
    with get_db() as database:
        database.clear()
        click.echo("Database cleared.")


# ── About ────────────────────────────────────────────────────────────

_LOGO_ASCII = r"""\
                                [=][___]--.
                                            \
                   ___        ___            |
                  /   \      /   \           |
                 |     \____/     |          |
           ____.-'  .       .      \         |
        /                           |        /
        \_____                      \      /
             \                      |    /
              \                    |   /
          \|/  \           ______     |  /
        --[#]-- \         /      `----' /
          /|\  _(________/             /
                   /  / `-------------'
                  /  /
"""


@cli.command()
def about():
    """Show information about bomi."""
    click.echo(_LOGO_ASCII)
    click.echo()
    click.echo("  bomi — CLI for agent-assisted circuit design")
    click.echo()
    click.echo("  Built by Jeremy Seitz. Hardware hacker, software generalist,")
    click.echo("  living in Switzerland. More at https://swiss.social/@somebox")
    click.echo()
    click.echo("  Logo by fern__theplant")
    click.echo()
    click.echo("  Source: https://github.com/somebox/bomi")
    click.echo("  License: MIT")


# ── Sync and categories ──────────────────────────────────────────────


@cli.command()
@click.option("--force", is_flag=True, help="Re-fetch even if recently synced")
def sync(force):
    """Fetch and cache provider category data."""
    from .scrape import fetch_jlcpcb_categories

    with get_db() as db:
        if not force:
            last = db.get_sync_time("jlcpcb")
            if last is not None:
                from datetime import datetime, timezone

                age_hours = (
                    datetime.now(timezone.utc) - last
                ).total_seconds() / 3600
                if age_hours < 24:
                    click.echo(
                        f"Categories already synced {age_hours:.0f}h ago. "
                        "Use --force to refresh.",
                        err=True,
                    )
                    return

        click.echo("Fetching JLCPCB categories...", err=True)
        try:
            cats = fetch_jlcpcb_categories()
        except requests.RequestException as e:
            click.echo(f"Error: Failed to fetch categories: {e}", err=True)
            sys.exit(1)

        db.upsert_categories(cats, provider="jlcpcb")
        top = sum(1 for c in cats if c["parent"] is None)
        sub = len(cats) - top
        click.echo(f"Synced {top} categories, {sub} subcategories.")


@cli.command()
@click.argument("query", required=False, default=None)
def categories(query):
    """List cached categories. Optionally filter by name."""
    with get_db() as db:
        cats = db.get_categories()
        if not cats:
            click.echo(
                "No categories cached. Run 'bomi sync' first.", err=True
            )
            sys.exit(1)

        # Build hierarchy: parent -> children
        top_level = []
        children_by_parent: dict[str, list] = {}
        for c in cats:
            if c["parent"] is None:
                top_level.append(c)
            else:
                children_by_parent.setdefault(c["parent"], []).append(c)

        # Filter if query provided
        if query:
            query_lower = query.lower()
            filtered_parents = set()
            filtered_children: dict[str, list] = {}

            for c in cats:
                if query_lower in c["name"].lower():
                    if c["parent"] is None:
                        filtered_parents.add(c["name"])
                    else:
                        filtered_parents.add(c["parent"])
                        filtered_children.setdefault(
                            c["parent"], []
                        ).append(c)

            # Show matching parents with their matching children
            for parent in top_level:
                if parent["name"] not in filtered_parents:
                    continue
                count = f" ({parent['part_count']:,})" if parent["part_count"] else ""
                click.echo(f"{parent['name']}{count}")
                kids = filtered_children.get(
                    parent["name"],
                    # If parent matched directly, show all children
                    children_by_parent.get(parent["name"], [])
                    if query_lower in parent["name"].lower()
                    else [],
                )
                for child in kids:
                    cc = f" ({child['part_count']:,})" if child["part_count"] else ""
                    click.echo(f"  {child['name']}{cc}")
        else:
            for parent in top_level:
                count = f" ({parent['part_count']:,})" if parent["part_count"] else ""
                click.echo(f"{parent['name']}{count}")
                for child in children_by_parent.get(parent["name"], []):
                    cc = f" ({child['part_count']:,})" if child["part_count"] else ""
                    click.echo(f"  {child['name']}{cc}")


# ── New project commands ─────────────────────────────────────────────


@cli.command()
@click.option("--name", prompt="Project name", help="Project name")
@click.option("--description", "desc", default="", help="Project description")
@click.pass_context
def init(ctx, name, desc):
    """Initialize a new project in the current directory."""
    from .project import init_project

    directory = Path.cwd()
    project_yaml = directory / ".bomi" / "project.yaml"
    if project_yaml.exists():
        click.echo(f"Project already exists at {project_yaml}", err=True)
        sys.exit(1)

    project = init_project(directory, name=name, description=desc)
    click.echo(f"Created {project_yaml}")


@cli.command()
@click.argument("lcsc_code")
@click.option("--ref", required=True, help="Reference designator (e.g. R1, U2-U4)")
@click.option("--qty", type=int, default=1, help="Quantity")
@click.option("--notes", default="", help="Notes about this selection")
@click.pass_context
def select(ctx, lcsc_code, ref, qty, notes):
    """Add a component to the project BOM."""
    from .project import add_selection

    project = _require_project(ctx)

    code = lcsc_code.upper()
    if not code.startswith("C"):
        code = f"C{code}"

    # Ensure part is cached
    with get_db() as db:
        part = db.get_part(code)
        if not part:
            click.echo(f"Fetching {code}...", err=True)
            client = JLCPCBClient()
            try:
                response = client.search(code, page_size=5)
                parts = normalize_search_response(response)
            except requests.RequestException as e:
                click.echo(f"Error: Failed to fetch {code}: {e}", err=True)
                sys.exit(1)
            except (KeyError, TypeError, ValueError) as e:
                click.echo(f"Error: Invalid response while fetching {code}: {e}", err=True)
                sys.exit(1)
            match = next((p for p in parts if p.lcsc_code == code), None)
            if match:
                db.upsert_part(match)
                part = match
            else:
                click.echo(f"Part {code} not found on JLCPCB.", err=True)
                sys.exit(1)

    try:
        sel = add_selection(project, lcsc=code, ref=ref, quantity=qty, notes=notes)
        click.echo(f"Added {ref} → {code} ({part.description})")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("ref")
@click.pass_context
def deselect(ctx, ref):
    """Remove a component from the BOM by reference designator."""
    from .project import remove_selection

    project = _require_project(ctx)
    try:
        removed = remove_selection(project, ref)
        click.echo(f"Removed {ref} (was {removed.lcsc or 'TBD'})")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("old_ref")
@click.argument("new_ref")
@click.pass_context
def relabel(ctx, old_ref, new_ref):
    """Rename a reference designator."""
    from .project import relabel_selection

    project = _require_project(ctx)
    try:
        sel = relabel_selection(project, old_ref, new_ref)
        click.echo(f"Relabeled {old_ref} → {new_ref}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def _display_project_bom(ctx, check, fmt, command_name):
    """Display the project BOM for list/bom commands."""
    from .project import resolve_bom

    project = _require_project(ctx)

    if check:
        # Refresh all BOM parts from API
        client = JLCPCBClient()
        with get_db() as db:
            for sel in project.selections:
                if sel.lcsc:
                    try:
                        response = client.search(sel.lcsc, page_size=5)
                        parts = normalize_search_response(response)
                    except requests.RequestException as e:
                        click.echo(f"Error: BOM refresh failed for {sel.lcsc}: {e}", err=True)
                        sys.exit(1)
                    except (KeyError, TypeError, ValueError) as e:
                        click.echo(f"Error: Invalid API data while refreshing {sel.lcsc}: {e}", err=True)
                        sys.exit(1)
                    match = next((p for p in parts if p.lcsc_code == sel.lcsc), None)
                    if match:
                        db.upsert_part(match)

    bom_entries = resolve_bom(project)

    if fmt == "json":
        click.echo(format_bom_json(bom_entries, command_name))

    elif fmt == "csv":
        click.echo(format_bom_csv(bom_entries))

    elif fmt == "markdown":
        click.echo(format_bom_markdown(project, bom_entries))

    else:
        table_text, warn_pairs = format_bom_table(bom_entries)
        click.echo(table_text)
        for ref, w in warn_pairs:
            click.echo(f"  ⚠ {ref}: {w}", err=True)


@cli.command(name="list")
@click.option("--check", is_flag=True, help="Refresh BOM parts from API, flag issues")
@_format_option
@click.pass_context
def list_bom(ctx, check, fmt):
    """Display the project BOM (preferred command; bom is an alias)."""
    _display_project_bom(ctx, check, fmt, command_name="list")


@cli.command(name="bom")
@click.option("--check", is_flag=True, help="Refresh BOM parts from API, flag issues")
@_format_option
@click.pass_context
def bom(ctx, check, fmt):
    """Display the project BOM (alias for list)."""
    _display_project_bom(ctx, check, fmt, command_name="bom")


@cli.command()
@click.pass_context
def status(ctx):
    """Show project overview and warnings."""
    from .project import resolve_bom

    project = _require_project(ctx)
    bom_entries = resolve_bom(project)

    click.echo(f"Project: {project.name}")
    if project.description:
        click.echo(f"  {project.description}")
    click.echo(f"Selections: {len(project.selections)}")

    # Cost estimate
    total_cost = 0.0
    warnings = []
    for entry in bom_entries:
        part = entry["part"]
        if part and part.prices:
            total_cost += part.prices[0].unit_price * entry["quantity"]
        for w in entry["warnings"]:
            warnings.append(f"{entry['ref']}: {w}")

    click.echo(f"Est. cost:  ${total_cost:.4f} (qty 1 pricing)")

    if warnings:
        click.echo(f"Warnings:   {len(warnings)}")
        for w in warnings:
            click.echo(f"  ⚠ {w}")
    else:
        click.echo("Warnings:   none")

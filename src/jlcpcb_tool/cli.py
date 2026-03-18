"""Click CLI commands."""

import json
import sys
from pathlib import Path

import click

from .api import JLCPCBClient
from .config import find_project_dir, get_db_path
from .db import Database
from .normalize import get_search_metadata, normalize_search_response
from .output import format_compare, format_envelope, format_part_detail, format_parts
from .search import search_local
from .units import parse_value


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
        click.echo("No project found. Run 'jlcpcb init' or use --project.", err=True)
        sys.exit(1)
    return load_project(project_dir)


# ── Existing commands (unchanged, work without project) ──────────────


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
@_format_option
def compare(lcsc_codes, fmt):
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
@click.option("--prompt", default="Summarize the key specifications from this datasheet.",
              help="Analysis prompt")
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

    db = get_db()
    try:
        code = lcsc_code.upper()
        if not code.startswith("C"):
            code = f"C{code}"

        part = db.get_part(code)
        if not part:
            click.echo(f"Part {code} not found. Run 'jlcpcb fetch {code}' first.", err=True)
            sys.exit(1)

        result = analyze_part(db, part, prompt=prompt, model=model, pdf_engine=pdf_engine)

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
    finally:
        db.close()


@cli.command()
@click.argument("lcsc_codes", nargs=-1, required=True)
@click.option("--output", "-o", default=".", help="Output directory", type=click.Path())
@click.option("--pdf", "dl_pdf", is_flag=True, help="Download datasheet PDF")
@click.option("--summary", "dl_summary", is_flag=True, help="Generate markdown summary via LLM")
@click.option("--prompt", default=None, help="Custom analysis prompt for summary")
@click.option("--model", default=None, help="Override model name for summary")
@click.option("--pdf-engine", default="mistral-ocr",
              type=click.Choice(["mistral-ocr", "pdf-text", "native"]),
              help="PDF parsing engine (mistral-ocr for scanned/CJK, pdf-text for clean text, native for model-native)")
def datasheet(lcsc_codes, output, dl_pdf, dl_summary, prompt, model, pdf_engine):
    """Download datasheets as PDF and/or generate markdown summaries.

    Pipeline: download PDF → (optional) save to disk → send to LLM via
    OpenRouter file API → save markdown summary.

    When --summary is used, the PDF is always downloaded first (required
    for analysis). If --pdf is also set, the same download is saved to disk.

    Large PDFs (>1.5MB) are automatically split into chunks and analyzed
    in parts, then synthesized into a single summary.

    Examples:

        jlcpcb datasheet C9864 --pdf -o docs/datasheets/

        jlcpcb datasheet C9864 --summary --model openai/gpt-5.4

        jlcpcb datasheet C9864 --pdf --summary --pdf-engine pdf-text
    """
    from .analysis import analyze_part, download_pdf

    if not dl_pdf and not dl_summary:
        dl_pdf = True  # default to PDF download if neither specified

    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    db = get_db()
    try:
        for lcsc_code in lcsc_codes:
            code = lcsc_code.upper()
            if not code.startswith("C"):
                code = f"C{code}"

            part = db.get_part(code)
            if not part:
                click.echo(f"Part {code} not found. Run 'jlcpcb fetch {code}' first.", err=True)
                continue

            if not part.datasheet_url:
                click.echo(f"{code}: No datasheet URL available.", err=True)
                continue

            safe_name = part.mfr_part.replace("/", "_").replace(" ", "_")
            pdf_path = output_dir / f"{safe_name}_{code}.pdf"

            # Step 1: Get PDF bytes (download or load from disk)
            pdf_data = None

            # Use existing local PDF if present (may have been manually placed)
            if pdf_path.exists():
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
                md_path = output_dir / f"{safe_name}_{code}.md"
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


# ── New project commands ─────────────────────────────────────────────


@cli.command()
@click.option("--name", prompt="Project name", help="Project name")
@click.option("--description", "desc", default="", help="Project description")
@click.pass_context
def init(ctx, name, desc):
    """Initialize a new project in the current directory."""
    from .project import init_project

    directory = Path.cwd()
    project_yaml = directory / ".jlcpcb" / "project.yaml"
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
    db = get_db()
    try:
        part = db.get_part(code)
        if not part:
            click.echo(f"Fetching {code}...", err=True)
            client = JLCPCBClient()
            response = client.search(code, page_size=5)
            parts = normalize_search_response(response)
            match = next((p for p in parts if p.lcsc_code == code), None)
            if match:
                db.upsert_part(match)
                part = match
            else:
                click.echo(f"Part {code} not found on JLCPCB.", err=True)
                sys.exit(1)
    finally:
        db.close()

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


@cli.command()
@click.option("--check", is_flag=True, help="Refresh BOM parts from API, flag issues")
@_format_option
@click.pass_context
def bom(ctx, check, fmt):
    """Display the project BOM."""
    from .project import resolve_bom

    project = _require_project(ctx)

    if check:
        # Refresh all BOM parts from API
        client = JLCPCBClient()
        db = get_db()
        try:
            for sel in project.selections:
                if sel.lcsc:
                    response = client.search(sel.lcsc, page_size=5)
                    parts = normalize_search_response(response)
                    match = next((p for p in parts if p.lcsc_code == sel.lcsc), None)
                    if match:
                        db.upsert_part(match)
        finally:
            db.close()

    bom_entries = resolve_bom(project)

    if fmt == "json":
        rows = []
        for entry in bom_entries:
            row = {
                "ref": entry["ref"],
                "lcsc": entry["lcsc"],
                "quantity": entry["quantity"],
                "notes": entry["notes"],
                "warnings": entry["warnings"],
            }
            part = entry["part"]
            if part:
                row["description"] = part.description
                row["package"] = part.package
                row["stock"] = part.stock
                row["price"] = part.prices[0].unit_price if part.prices else None
            rows.append(row)
        click.echo(json.dumps({"status": "ok", "command": "bom", "data": rows}, indent=2))

    elif fmt == "csv":
        import csv
        import io
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "Ref", "LCSC", "Qty", "Part", "Manufacturer", "Package",
            "Description", "Price", "Stock", "Type", "Notes",
            "Datasheet", "JLCPCB URL",
        ])
        for entry in bom_entries:
            part = entry["part"]
            writer.writerow([
                entry["ref"],
                entry["lcsc"] or "TBD",
                entry["quantity"],
                part.mfr_part if part else "",
                part.manufacturer if part else "",
                part.package if part else "",
                part.description if part else "",
                f"{part.prices[0].unit_price:.4f}" if part and part.prices else "",
                part.stock if part else "",
                part.library_type if part else "",
                entry["notes"],
                part.datasheet_url or "" if part else "",
                part.jlcpcb_url or "" if part else "",
            ])
        click.echo(buf.getvalue().rstrip())

    elif fmt == "markdown":
        click.echo(_format_bom_markdown(project, bom_entries))

    else:
        # Table format
        from tabulate import tabulate
        rows = []
        for entry in bom_entries:
            part = entry["part"]
            price = f"${part.prices[0].unit_price:.4f}" if part and part.prices else "-"
            stock = f"{part.stock:,}" if part else "-"
            warn = " ⚠" if entry["warnings"] else ""
            notes = entry["notes"]
            if len(notes) > 50:
                notes = notes[:49] + "…"
            rows.append([
                entry["ref"],
                entry["lcsc"] or "TBD",
                entry["quantity"],
                notes or "-",
                part.package if part else "-",
                price,
                stock + warn,
            ])
        click.echo(tabulate(rows, headers=["Ref", "LCSC", "Qty", "Notes", "Pkg", "Price", "Stock"]))

        # Print warnings
        for entry in bom_entries:
            if entry["warnings"]:
                for w in entry["warnings"]:
                    click.echo(f"  ⚠ {entry['ref']}: {w}", err=True)


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


# ── BOM markdown formatter ──────────────────────────────────────────


def _humanize_stock(stock: int) -> str:
    """Format stock for display: 2137009 -> '2.14m', 22021 -> '22k', 3059 -> '3,059'."""
    if stock >= 1_000_000:
        return f"{stock / 1_000_000:.2f}m"
    if stock >= 10_000:
        return f"{stock // 1_000}k"
    return f"{stock:,}"


def _make_anchor(ref: str) -> str:
    """Create a markdown anchor ID from a ref designator."""
    return ref.lower().replace("-", "").replace(" ", "")


def _group_bom_entries(bom_entries: list[dict]) -> list[dict]:
    """Group BOM entries that share the same LCSC code.

    Returns a list of group dicts with:
      refs: list of ref strings
      ref_label: combined label like "D1, D2"
      total_qty: summed quantity
      lcsc, part, notes, warnings: from first entry
    """
    from collections import OrderedDict

    groups: OrderedDict[str, dict] = OrderedDict()
    for entry in bom_entries:
        key = entry["lcsc"] or entry["ref"]  # TBD entries keyed by ref
        if key in groups:
            g = groups[key]
            g["refs"].append(entry["ref"])
            g["total_qty"] += entry["quantity"]
            # Merge notes (skip duplicates)
            if entry["notes"] and entry["notes"] not in g["all_notes"]:
                g["all_notes"].append(entry["notes"])
            g["warnings"].extend(entry["warnings"])
        else:
            groups[key] = {
                "refs": [entry["ref"]],
                "total_qty": entry["quantity"],
                "lcsc": entry["lcsc"],
                "part": entry["part"],
                "notes": entry["notes"],
                "all_notes": [entry["notes"]] if entry["notes"] else [],
                "warnings": list(entry["warnings"]),
            }

    result = []
    for g in groups.values():
        g["ref_label"] = ", ".join(g["refs"])
        result.append(g)
    return result


def _format_bom_markdown(project, bom_entries: list[dict]) -> str:
    """Format BOM as rich markdown with summary table + detail sections."""
    lines = []
    groups = _group_bom_entries(bom_entries)

    # Header
    lines.append(f"# {project.name}")
    if project.description:
        lines.append(f"\n{project.description}")
    lines.append("")

    # Cost summary
    total_cost = sum(
        e["part"].prices[0].unit_price * e["quantity"]
        for e in bom_entries
        if e["part"] and e["part"].prices
    )
    lines.append(f"**{len(bom_entries)} line items ({len(groups)} unique parts), ~${total_cost:.2f} estimated (qty 1)**")
    lines.append("")

    # Summary table
    lines.append("## BOM")
    lines.append("")
    headers = ["Ref", "Qty", "LCSC", "Package", "Note", "Stock", "Price"]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for g in groups:
        part = g["part"]
        anchor = (g["lcsc"] or _make_anchor(g["refs"][0])).lower()
        pkg = part.package if part else ""
        price = f"${part.prices[0].unit_price:.4f}" if part and part.prices else ""
        stock = _humanize_stock(part.stock) if part else ""
        note = g["notes"]
        lines.append("| " + " | ".join([
            f"[{g['ref_label']}](#{anchor})",
            str(g["total_qty"]),
            (g["lcsc"] or "TBD"),
            pkg,
            note,
            stock,
            price,
        ]) + " |")

    # Detail sections
    lines.append("")
    lines.append("## Details")

    for g in groups:
        part = g["part"]
        ref_label = g["ref_label"]
        anchor = _make_anchor(g["refs"][0])

        lcsc_id = g["lcsc"] or ref_label
        lines.append("")
        lines.append(f"### {lcsc_id}")
        lines.append("")

        if not part:
            lines.append(f"**Status:** TBD — no part selected")
            if g["notes"]:
                lines.append(f"**Notes:** {g['notes']}")
            continue

        # Detail table — no empty separator rows
        lines.append("| | |")
        lines.append("|---|---|")
        lines.append(f"| **Designator** | {ref_label} |")
        lines.append(f"| **Part** | {part.mfr_part} |")
        lines.append(f"| **LCSC** | {g['lcsc']} |")
        lines.append(f"| **Manufacturer** | {part.manufacturer} |")
        lines.append(f"| **Package** | {part.package} |")
        lib_label = "Basic (no extra fee)" if part.library_type == "base" else "Extended"
        lines.append(f"| **Type** | {lib_label} |")
        lines.append(f"| **Quantity** | {g['total_qty']} |")
        lines.append(f"| **Description** | {part.description} |")

        # Notes — show all unique notes for grouped entries
        for note in g["all_notes"]:
            lines.append(f"| **Notes** | {note} |")

        # Stock & pricing
        lines.append(f"| **Stock** | {part.stock:,} |")
        if part.prices:
            price_str = ", ".join(
                f"${p.unit_price:.4f} (≥{p.qty_from})"
                for p in part.prices
            )
            lines.append(f"| **Pricing** | {price_str} |")

        # Attributes
        for a in part.attributes:
            lines.append(f"| **{a.name}** | {a.value_raw} |")

        # Links
        if part.datasheet_url:
            lines.append(f"| **Datasheet** | {part.datasheet_url} |")
        if part.jlcpcb_url:
            lines.append(f"| **JLCPCB** | {part.jlcpcb_url} |")

    lines.append("")
    return "\n".join(lines)


# ── Helpers ──────────────────────────────────────────────────────────


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

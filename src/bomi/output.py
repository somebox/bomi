"""Output formatters: table, json, csv, BOM views."""

from __future__ import annotations

import csv
import io
import json
from collections import OrderedDict
from typing import TYPE_CHECKING

from tabulate import tabulate

from .models import Part

if TYPE_CHECKING:
    from .project import Project


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max_len using trailing ellipsis."""
    s = str(text) if text is not None else ""
    s = s.replace("\r", " ").replace("\n", " ")
    if len(s) <= max_len:
        return s
    if max_len <= 3:
        return s[:max_len]
    return s[: max_len - 3] + "..."


def _escape_md_cell(text: str) -> str:
    """Escape markdown table cell delimiters."""
    return text.replace("|", "\\|")


def format_parts(parts: list[Part], fmt: str = "table", command: str = "") -> str:
    """Format a list of parts for output."""
    if fmt == "json":
        return _format_json(parts, command)
    elif fmt == "csv":
        return _format_csv(parts)
    elif fmt == "markdown":
        return _format_markdown(parts)
    else:
        return _format_table(parts)


def format_part_detail(part: Part, fmt: str = "table") -> str:
    """Format a single part with full detail."""
    if fmt == "json":
        return _format_json([part], "info")
    elif fmt == "csv":
        return _format_csv([part])
    else:
        return _format_detail_table(part)


def format_compare(parts: list[Part], fmt: str = "table") -> str:
    """Format parts for side-by-side comparison."""
    if fmt == "json":
        return _format_json(parts, "compare")
    elif fmt == "csv":
        return _format_csv(parts)
    elif fmt == "markdown":
        return _format_compare_markdown(parts)
    else:
        return _format_compare_table(parts)


def format_envelope(status: str, command: str, results: list, count: int | None = None) -> str:
    """Format a JSON envelope for agent consumption."""
    envelope = {
        "status": status,
        "command": command,
        "count": count if count is not None else len(results),
        "results": results,
    }
    return json.dumps(envelope, indent=2)


def _part_to_dict(part: Part) -> dict:
    """Convert Part to serializable dict."""
    d = {
        "lcsc_code": part.lcsc_code,
        "mfr_part": part.mfr_part,
        "manufacturer": part.manufacturer,
        "package": part.package,
        "category": part.category,
        "subcategory": part.subcategory,
        "description": part.description,
        "stock": part.stock,
        "library_type": part.library_type,
        "preferred": part.preferred,
        "datasheet_url": part.datasheet_url,
        "jlcpcb_url": part.jlcpcb_url,
    }
    if part.prices:
        d["prices"] = [
            {"qty_from": p.qty_from, "qty_to": p.qty_to, "unit_price": p.unit_price}
            for p in part.prices
        ]
        d["price_qty1"] = part.prices[0].unit_price
    if part.attributes:
        d["attributes"] = {
            a.name: {"raw": a.value_raw, "num": a.value_num, "unit": a.unit}
            for a in part.attributes
        }
    return d


def _format_json(parts: list[Part], command: str) -> str:
    return format_envelope(
        status="ok",
        command=command,
        results=[_part_to_dict(p) for p in parts],
    )


def _format_table(parts: list[Part]) -> str:
    if not parts:
        return "No results found."
    rows = []
    for p in parts:
        price = f"${p.prices[0].unit_price:.4f}" if p.prices else "-"
        lib = "Basic" if p.library_type == "base" else "Ext"
        if p.preferred:
            lib += "*"
        rows.append([
            p.lcsc_code, p.mfr_part[:30], p.manufacturer[:15],
            p.package, p.stock, price, lib,
        ])
    headers = ["LCSC", "MFR Part", "Manufacturer", "Package", "Stock", "Price", "Type"]
    return tabulate(rows, headers=headers, tablefmt="simple")


def _format_detail_table(part: Part) -> str:
    lines = [
        f"{'LCSC Code:':<20} {part.lcsc_code}",
        f"{'MFR Part:':<20} {part.mfr_part}",
        f"{'Manufacturer:':<20} {part.manufacturer}",
        f"{'Package:':<20} {part.package}",
        f"{'Category:':<20} {part.category}",
        f"{'Subcategory:':<20} {part.subcategory}",
        f"{'Description:':<20} {part.description}",
        f"{'Stock:':<20} {part.stock:,}",
        f"{'Library Type:':<20} {part.library_type}",
        f"{'Preferred:':<20} {'Yes' if part.preferred else 'No'}",
        f"{'Datasheet:':<20} {part.datasheet_url or 'N/A'}",
        f"{'JLCPCB URL:':<20} {part.jlcpcb_url or 'N/A'}",
    ]

    if part.prices:
        lines.append("")
        lines.append("Pricing:")
        for p in part.prices:
            qty_to = f"{p.qty_to}" if p.qty_to else "∞"
            lines.append(f"  {p.qty_from:>6} - {qty_to:<6}  ${p.unit_price:.4f}")

    if part.attributes:
        lines.append("")
        lines.append("Attributes:")
        for a in part.attributes:
            num_str = f" ({a.value_num} {a.unit or ''})" if a.value_num is not None else ""
            lines.append(f"  {a.name:<30} {a.value_raw}{num_str}")

    return "\n".join(lines)


def _format_compare_table(parts: list[Part]) -> str:
    if not parts:
        return "No parts to compare."

    # Collect all attribute names
    all_attrs = []
    seen = set()
    for p in parts:
        for a in p.attributes:
            if a.name not in seen:
                all_attrs.append(a.name)
                seen.add(a.name)

    # Build comparison table
    headers = ["Field"] + [p.lcsc_code for p in parts]
    rows = [
        ["MFR Part"] + [_truncate(p.mfr_part, 24) for p in parts],
        ["Manufacturer"] + [_truncate(p.manufacturer, 24) for p in parts],
        ["Package"] + [_truncate(p.package, 24) for p in parts],
        ["Stock"] + [str(p.stock) for p in parts],
        ["Price (qty 1)"] + [
            f"${p.prices[0].unit_price:.4f}" if p.prices else "-"
            for p in parts
        ],
        ["Type"] + [p.library_type for p in parts],
    ]

    for attr_name in all_attrs:
        values = []
        for p in parts:
            attr = next((a for a in p.attributes if a.name == attr_name), None)
            values.append(_truncate(attr.value_raw, 24) if attr else "-")
        rows.append([_truncate(attr_name, 28)] + values)

    return tabulate(rows, headers=headers, tablefmt="simple")


def _format_csv(parts: list[Part]) -> str:
    if not parts:
        return ""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "lcsc_code", "mfr_part", "manufacturer", "package",
        "stock", "price_qty1", "library_type", "preferred", "description",
    ])
    for p in parts:
        price = p.prices[0].unit_price if p.prices else ""
        writer.writerow([
            p.lcsc_code, p.mfr_part, p.manufacturer, p.package,
            p.stock, price, p.library_type, p.preferred, p.description,
        ])
    return output.getvalue()


def _format_markdown(parts: list[Part]) -> str:
    if not parts:
        return "No results found."
    headers = ["LCSC", "MFR Part", "Manufacturer", "Package", "Stock", "Price", "Type"]
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for p in parts:
        price = f"${p.prices[0].unit_price:.4f}" if p.prices else ""
        lib = "Basic" if p.library_type == "base" else "Ext"
        if p.preferred:
            lib += "*"
        lines.append("| " + " | ".join([
            p.lcsc_code,
            p.mfr_part,
            p.manufacturer,
            p.package,
            f"{p.stock:,}",
            price,
            lib,
        ]) + " |")
    return "\n".join(lines)


def _format_compare_markdown(parts: list[Part]) -> str:
    if not parts:
        return "No parts to compare."

    all_attrs = []
    seen = set()
    for p in parts:
        for a in p.attributes:
            if a.name not in seen:
                all_attrs.append(a.name)
                seen.add(a.name)

    headers = ["Field"] + [p.lcsc_code for p in parts]
    rows = [
        ["MFR Part"] + [_truncate(p.mfr_part, 24) for p in parts],
        ["Manufacturer"] + [_truncate(p.manufacturer, 24) for p in parts],
        ["Package"] + [_truncate(p.package, 24) for p in parts],
        ["Stock"] + [str(p.stock) for p in parts],
        ["Price (qty 1)"] + [
            f"${p.prices[0].unit_price:.4f}" if p.prices else "-"
            for p in parts
        ],
        ["Type"] + [p.library_type for p in parts],
    ]
    for attr_name in all_attrs:
        values = []
        for p in parts:
            attr = next((a for a in p.attributes if a.name == attr_name), None)
            values.append(_truncate(attr.value_raw, 24) if attr else "-")
        rows.append([_truncate(attr_name, 28)] + values)

    lines = ["| " + " | ".join(_escape_md_cell(h) for h in headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        lines.append("| " + " | ".join(_escape_md_cell(str(cell)) for cell in row) + " |")
    return "\n".join(lines)


# ── BOM (project list / bom commands) ─────────────────────────────────


def _humanize_stock(stock: int) -> str:
    """Format stock: 2137009 -> '2.14m', 22021 -> '22k', 3059 -> '3,059'."""
    if stock >= 1_000_000:
        return f"{stock / 1_000_000:.2f}m"
    if stock >= 10_000:
        return f"{stock // 1_000}k"
    return f"{stock:,}"


def _make_anchor(ref: str) -> str:
    return ref.lower().replace("-", "").replace(" ", "")


def _group_anchor(group: dict) -> str:
    return (group["lcsc"] or _make_anchor(group["refs"][0])).lower()


def _group_bom_entries(bom_entries: list[dict]) -> list[dict]:
    """Group BOM entries that share the same LCSC code."""
    groups: OrderedDict[str, dict] = OrderedDict()
    for entry in bom_entries:
        key = entry["lcsc"] or entry["ref"]
        if key in groups:
            g = groups[key]
            g["refs"].append(entry["ref"])
            g["total_qty"] += entry["quantity"]
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


def format_bom_json(bom_entries: list[dict], command_name: str) -> str:
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
    return json.dumps(
        {"status": "ok", "command": command_name, "data": rows},
        indent=2,
    )


def format_bom_csv(bom_entries: list[dict]) -> str:
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
    return buf.getvalue().rstrip()


def format_bom_markdown(project: Project, bom_entries: list[dict]) -> str:
    lines = []
    groups = _group_bom_entries(bom_entries)

    lines.append(f"# {project.name}")
    if project.description:
        lines.append(f"\n{project.description}")
    lines.append("")

    total_cost = sum(
        e["part"].prices[0].unit_price * e["quantity"]
        for e in bom_entries
        if e["part"] and e["part"].prices
    )
    lines.append(
        f"**{len(bom_entries)} line items ({len(groups)} unique parts), "
        f"~${total_cost:.2f} estimated (qty 1)**"
    )
    lines.append("")

    lines.append("## BOM")
    lines.append("")
    headers = ["Ref", "Qty", "LCSC", "Package", "Note", "Stock", "Price"]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for g in groups:
        part = g["part"]
        anchor = _group_anchor(g)
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

    lines.append("")
    lines.append("## Details")

    for g in groups:
        part = g["part"]
        ref_label = g["ref_label"]
        anchor = _group_anchor(g)

        lcsc_id = g["lcsc"] or ref_label
        lines.append("")
        lines.append(f'<a id="{anchor}"></a>')
        lines.append(f"### {lcsc_id}")
        lines.append("")

        if not part:
            lines.append("**Status:** TBD — no part selected")
            if g["notes"]:
                lines.append(f"**Notes:** {g['notes']}")
            continue

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

        for note in g["all_notes"]:
            lines.append(f"| **Notes** | {note} |")

        lines.append(f"| **Stock** | {part.stock:,} |")
        if part.prices:
            price_str = ", ".join(
                f"${p.unit_price:.4f} (≥{p.qty_from})"
                for p in part.prices
            )
            lines.append(f"| **Pricing** | {price_str} |")

        for a in part.attributes:
            lines.append(f"| **{a.name}** | {a.value_raw} |")

        if part.datasheet_url:
            lines.append(f"| **Datasheet** | {part.datasheet_url} |")
        if part.jlcpcb_url:
            lines.append(f"| **JLCPCB** | {part.jlcpcb_url} |")

    lines.append("")
    return "\n".join(lines)


def format_bom_table(bom_entries: list[dict]) -> tuple[str, list[tuple[str, str]]]:
    """Return tabulate text and (ref, warning) pairs for stderr."""
    rows = []
    for entry in bom_entries:
        part = entry["part"]
        price = f"${part.prices[0].unit_price:.4f}" if part and part.prices else "-"
        stock = f"{part.stock:,}" if part else "-"
        warn = " ⚠" if entry["warnings"] else ""
        notes = entry["notes"]
        if len(notes) > 40:
            notes = notes[:39] + "…"
        rows.append([
            entry["ref"],
            entry["lcsc"] or "TBD",
            entry["quantity"],
            notes or "-",
            part.package if part else "-",
            price,
            stock + warn,
        ])
    text = tabulate(
        rows,
        headers=["Ref", "LCSC", "Qty", "Notes", "Pkg", "Price", "Stock"],
    )
    warn_lines: list[tuple[str, str]] = []
    for entry in bom_entries:
        if entry["warnings"]:
            for w in entry["warnings"]:
                warn_lines.append((entry["ref"], w))
    return text, warn_lines

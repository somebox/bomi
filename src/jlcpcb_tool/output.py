"""Output formatters: table, json, csv."""

import csv
import io
import json

from tabulate import tabulate

from .models import Part


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
        ["MFR Part"] + [p.mfr_part for p in parts],
        ["Manufacturer"] + [p.manufacturer for p in parts],
        ["Package"] + [p.package for p in parts],
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
            values.append(attr.value_raw if attr else "-")
        rows.append([attr_name] + values)

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
        ["MFR Part"] + [p.mfr_part for p in parts],
        ["Manufacturer"] + [p.manufacturer for p in parts],
        ["Package"] + [p.package for p in parts],
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
            values.append(attr.value_raw if attr else "-")
        rows.append([attr_name] + values)

    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)

"""KiCad BOM import: read LCSC part numbers from a KiCad project or BOM CSV.

KiCad keeps the LCSC number as a symbol field (commonly ``LCSC``, but plugins
and templates use other names). This module turns a schematic, project file or
exported BOM CSV into bomi selections: one entry per LCSC code and contiguous
reference range (``R211-R218``), ready to merge into ``.bomi/project.yaml``.

Schematics are exported with ``kicad-cli sch export bom`` (KiCad 7+), so
hierarchical sheets, multi-unit symbols, power symbols and "exclude from BOM"
are handled by KiCad itself. CSV input needs no KiCad install.
"""

from __future__ import annotations

import csv
import io
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .refs import compress_refs, expand_refs, parse_ref, ref_count

# Field names used for LCSC numbers by common KiCad workflows, in priority order.
LCSC_FIELD_ALIASES = (
    "LCSC",
    "LCSC Part",
    "LCSC Part #",
    "LCSC Part Number",
    "LCSC#",
    "JLCPCB Part #",
    "JLCPCB Part",
    "JLC",
    "JLCPCB",
)
REF_COLUMNS = ("Reference", "References", "Refs", "Ref", "Designator", "Designators")
VALUE_COLUMNS = ("Value", "Comment", "Val")
FOOTPRINT_COLUMNS = ("Footprint", "Package")
DNP_COLUMNS = ("DNP", "Do not populate", "Do Not Place")
_DNP_TRUE = {"dnp", "yes", "y", "true", "1", "x", "excluded"}
_LCSC_RE = re.compile(r"^C?(\d+)$", re.IGNORECASE)

# Standard kicad-cli locations when it is not on PATH.
_KICAD_CLI_CANDIDATES = (
    "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
    r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe",
    r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe",
    r"C:\Program Files\KiCad\8.0\bin\kicad-cli.exe",
)


class KicadImportError(Exception):
    """Raised when a KiCad source cannot be read."""


@dataclass
class KicadComponent:
    ref: str
    value: str = ""
    footprint: str = ""
    lcsc_raw: str = ""
    dnp: bool = False


@dataclass
class ImportRow:
    """One BOM entry derived from KiCad: a ref or contiguous range sharing one LCSC code."""

    ref: str
    lcsc: str | None
    quantity: int
    value: str = ""


@dataclass
class KicadBom:
    source: Path
    lcsc_field: str | None
    components: list[KicadComponent]
    rows: list[ImportRow] = field(default_factory=list)
    missing_lcsc: list[str] = field(default_factory=list)       # refs (compressed)
    invalid_lcsc: list[dict] = field(default_factory=list)      # [{ref, value}]
    skipped_dnp: list[str] = field(default_factory=list)        # refs (compressed)
    invalid_refs: list[str] = field(default_factory=list)       # designators bomi can't store


def normalize_lcsc(value: str) -> str | None:
    """Return a canonical LCSC code ("C1525") or None if the value is not one."""
    m = _LCSC_RE.match(value.strip())
    return f"C{int(m.group(1))}" if m else None


def find_kicad_cli(explicit: str | None = None) -> str | None:
    """Locate kicad-cli: explicit path, BOMI_KICAD_CLI, PATH, then standard installs."""
    for candidate in (explicit, os.environ.get("BOMI_KICAD_CLI")):
        if candidate:
            return candidate if Path(candidate).exists() else None
    found = shutil.which("kicad-cli")
    if found:
        return found
    for candidate in _KICAD_CLI_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return None


def resolve_schematic(source: Path) -> Path:
    """Map a .kicad_pro to its root .kicad_sch; pass schematics through."""
    if source.suffix == ".kicad_pro":
        sch = source.with_suffix(".kicad_sch")
        if not sch.exists():
            raise KicadImportError(f"No root schematic {sch.name} next to {source.name}")
        return sch
    return source


def export_bom_csv(schematic: Path, kicad_cli: str, lcsc_fields: tuple[str, ...]) -> str:
    """Run kicad-cli to export one BOM row per component with the LCSC field candidates."""
    fields = ["Reference", "Value", "Footprint", "${DNP}", *lcsc_fields]
    labels = ["Reference", "Value", "Footprint", "DNP", *lcsc_fields]
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "bom.csv"
        cmd = [
            kicad_cli, "sch", "export", "bom",
            "--fields", ",".join(fields),
            "--labels", ",".join(labels),
            "--group-by", "",
            "--ref-range-delimiter", "",
            "--output", str(out),
            str(schematic),
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise KicadImportError(f"Failed to run kicad-cli: {e}") from e
        if proc.returncode != 0 or not out.exists():
            detail = (proc.stderr or proc.stdout).strip()
            raise KicadImportError(f"kicad-cli BOM export failed: {detail}")
        return out.read_text(encoding="utf-8")


def _pick(header: dict[str, str], names: tuple[str, ...]) -> str | None:
    for name in names:
        if name.lower() in header:
            return header[name.lower()]
    return None


def parse_bom_csv(text: str, lcsc_field: str | None = None) -> tuple[list[KicadComponent], str | None]:
    """Parse a KiCad BOM CSV (one row per component, or grouped with ref lists/ranges).

    Returns the components and the name of the column the LCSC numbers came from
    (None when no row has one). With ``lcsc_field`` set, only that column is used.
    """
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise KicadImportError("BOM CSV has no header row")
    header = {name.strip().lower(): name for name in reader.fieldnames}

    ref_col = _pick(header, REF_COLUMNS)
    if not ref_col:
        raise KicadImportError(
            f"BOM CSV has no reference column (looked for {', '.join(REF_COLUMNS)})"
        )
    value_col = _pick(header, VALUE_COLUMNS)
    fp_col = _pick(header, FOOTPRINT_COLUMNS)
    dnp_col = _pick(header, DNP_COLUMNS)

    if lcsc_field:
        col = header.get(lcsc_field.strip().lower())
        if not col:
            raise KicadImportError(f"BOM CSV has no column named '{lcsc_field}'")
        lcsc_cols = [col]
    else:
        lcsc_cols = [header[a.lower()] for a in LCSC_FIELD_ALIASES if a.lower() in header]

    components: list[KicadComponent] = []
    used_field: str | None = None
    for row in reader:
        refs_cell = (row.get(ref_col) or "").strip()
        if not refs_cell:
            continue
        lcsc_raw = ""
        for col in lcsc_cols:
            v = (row.get(col) or "").strip()
            if v:
                lcsc_raw = v
                used_field = used_field or col
                break
        dnp = (row.get(dnp_col) or "").strip().lower() in _DNP_TRUE if dnp_col else False
        for ref in expand_refs(refs_cell):
            components.append(KicadComponent(
                ref=ref,
                value=(row.get(value_col) or "").strip() if value_col else "",
                footprint=(row.get(fp_col) or "").strip() if fp_col else "",
                lcsc_raw=lcsc_raw,
                dnp=dnp,
            ))
    return components, used_field


def _range_values(ref: str, values: dict[str, str]) -> str:
    """Distinct KiCad values across a ref range, in reference order ("BUS_IN / BUS_OUT")."""
    spec = parse_ref(ref)
    seen: list[str] = []
    for n in range(spec.start, spec.end + 1):
        v = values.get(f"{spec.prefix}{n}", "")
        if v and v not in seen:
            seen.append(v)
    return " / ".join(seen)


def group_components(bom: KicadBom, include_missing: bool = False, include_dnp: bool = False) -> KicadBom:
    """Group components into ImportRows: one per LCSC code and contiguous ref range."""
    by_lcsc: dict[str, list[str]] = {}
    values: dict[str, str] = {}  # ref -> KiCad value
    missing: dict[str, list[str]] = {}  # value -> refs, for TBD rows
    dnp_refs: list[str] = []
    seen: set[str] = set()

    for comp in bom.components:
        try:
            parse_ref(comp.ref)
        except ValueError:
            bom.invalid_refs.append(comp.ref)
            continue
        if comp.ref.upper() in seen:
            continue  # multi-unit symbols can appear once per unit in some exports
        seen.add(comp.ref.upper())
        if comp.dnp and not include_dnp:
            dnp_refs.append(comp.ref)
            continue
        if not comp.lcsc_raw:
            missing.setdefault(comp.value, []).append(comp.ref)
            continue
        code = normalize_lcsc(comp.lcsc_raw)
        if not code:
            bom.invalid_lcsc.append({"ref": comp.ref, "value": comp.lcsc_raw})
            continue
        by_lcsc.setdefault(code, []).append(comp.ref)
        values[comp.ref.upper()] = comp.value

    rows = [
        ImportRow(ref=r, lcsc=code, quantity=ref_count(r), value=_range_values(r, values))
        for code, refs in by_lcsc.items()
        for r in compress_refs(refs)
    ]
    all_missing = [ref for refs in missing.values() for ref in refs]
    bom.missing_lcsc = compress_refs(all_missing) if all_missing else []
    if include_missing:
        rows += [
            ImportRow(ref=r, lcsc=None, quantity=ref_count(r), value=value)
            for value, refs in missing.items()
            for r in compress_refs(refs)
        ]
    bom.skipped_dnp = compress_refs(dnp_refs) if dnp_refs else []
    bom.rows = rows
    return bom


def read_kicad_bom(
    source: Path,
    lcsc_field: str | None = None,
    kicad_cli: str | None = None,
    include_missing: bool = False,
    include_dnp: bool = False,
) -> KicadBom:
    """Read a .kicad_sch, .kicad_pro or BOM .csv and return grouped import rows."""
    source = Path(source)
    if not source.exists():
        raise KicadImportError(f"{source} does not exist")

    if source.suffix in (".kicad_sch", ".kicad_pro"):
        schematic = resolve_schematic(source)
        cli = find_kicad_cli(kicad_cli)
        if not cli:
            raise KicadImportError(
                "kicad-cli not found. Install KiCad 7+, pass --kicad-cli, set BOMI_KICAD_CLI, "
                "or export a BOM CSV from KiCad and import that instead."
            )
        fields = (lcsc_field,) if lcsc_field else LCSC_FIELD_ALIASES
        text = export_bom_csv(schematic, cli, fields)
    elif source.suffix.lower() in (".csv", ".tsv", ".txt"):
        text = source.read_text(encoding="utf-8-sig")
    else:
        raise KicadImportError(
            f"Unsupported file type '{source.suffix}': use .kicad_sch, .kicad_pro or a BOM .csv"
        )

    components, used_field = parse_bom_csv(text, lcsc_field)
    bom = KicadBom(source=source, lcsc_field=used_field, components=components)
    return group_components(bom, include_missing=include_missing, include_dnp=include_dnp)

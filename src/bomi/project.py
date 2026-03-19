"""Project management: init, selections CRUD, BOM generation."""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from .config import get_db_path
from .db import Database
from .refs import normalize_ref, ref_count, ref_sort_key, refs_overlap


@dataclass
class Alternative:
    lcsc: str
    reason: str = ""


@dataclass
class Selection:
    ref: str
    lcsc: str | None = None
    quantity: int = 1
    notes: str = ""
    alternatives: list[Alternative] = field(default_factory=list)


@dataclass
class Project:
    name: str
    description: str = ""
    created: str = ""
    selections: list[Selection] = field(default_factory=list)
    path: Path | None = None  # directory containing .bomi/

    @property
    def project_yaml_path(self) -> Path | None:
        if self.path:
            return self.path / ".bomi" / "project.yaml"
        return None


def _selection_to_dict(sel: Selection) -> dict:
    d: dict = {"ref": sel.ref, "lcsc": sel.lcsc, "quantity": sel.quantity}
    if sel.notes:
        d["notes"] = sel.notes
    if sel.alternatives:
        d["alternatives"] = [
            {"lcsc": a.lcsc, "reason": a.reason} for a in sel.alternatives
        ]
    return d


def _selection_from_dict(d: dict) -> Selection:
    alts = [
        Alternative(lcsc=a["lcsc"], reason=a.get("reason", ""))
        for a in d.get("alternatives", [])
    ]
    raw_ref = d["ref"]
    try:
        canonical_ref = normalize_ref(raw_ref)
    except ValueError:
        canonical_ref = raw_ref

    return Selection(
        ref=canonical_ref,
        lcsc=d.get("lcsc"),
        quantity=d.get("quantity", 1),
        notes=d.get("notes", ""),
        alternatives=alts,
    )


def _ref_sort_key(ref: str) -> tuple:
    """Sort key for reference designators: alpha prefix, then numeric."""
    try:
        return ref_sort_key(ref)
    except ValueError:
        return (ref.upper(), 0, 0)


def init_project(directory: Path, name: str, description: str = "") -> Project:
    """Create .bomi/project.yaml for a project."""
    jlcpcb_dir = directory / ".bomi"
    jlcpcb_dir.mkdir(parents=True, exist_ok=True)

    project = Project(
        name=name,
        description=description,
        created=date.today().isoformat(),
        selections=[],
        path=directory,
    )
    save_project(project)

    # Append datasheet PDF gitignore rule if .gitignore exists or create it
    gitignore_path = directory / ".gitignore"
    pdf_rule = "docs/datasheets/*.pdf"
    needs_rule = True
    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8")
        if pdf_rule in content:
            needs_rule = False
    if needs_rule:
        with open(gitignore_path, "a", encoding="utf-8") as f:
            f.write(
                "\n# Datasheet PDFs are large — regenerate with: "
                "bomi datasheet CXXXXX --pdf -o docs/datasheets/\n"
                "docs/datasheets/*.pdf\n"
                "docs/datasheets/*.PDF\n"
            )

    return project


def load_project(project_dir: Path) -> Project:
    """Load project from .bomi/project.yaml."""
    yaml_path = project_dir / ".bomi" / "project.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"No project.yaml at {yaml_path}")

    with open(yaml_path) as f:
        data = yaml.safe_load(f) or {}

    selections = [_selection_from_dict(s) for s in data.get("selections", [])]

    return Project(
        name=data.get("name", ""),
        description=data.get("description", ""),
        created=data.get("created", ""),
        selections=selections,
        path=project_dir,
    )


def save_project(project: Project):
    """Write project to .bomi/project.yaml."""
    if not project.path:
        raise ValueError("Project has no path set")

    # Sort selections by ref for clean diffs
    project.selections.sort(key=lambda s: _ref_sort_key(s.ref))

    data: dict = {"name": project.name}
    if project.description:
        data["description"] = project.description
    if project.created:
        data["created"] = project.created

    if project.selections:
        data["selections"] = [_selection_to_dict(s) for s in project.selections]
    else:
        data["selections"] = []

    yaml_path = project.path / ".bomi" / "project.yaml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    with open(yaml_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def add_selection(
    project: Project,
    lcsc: str,
    ref: str,
    quantity: int = 1,
    notes: str = "",
) -> Selection:
    """Add a component selection to the project BOM."""
    canonical_ref = normalize_ref(ref)
    if quantity < 1:
        raise ValueError("Quantity must be >= 1")

    expected_qty = ref_count(canonical_ref)
    if expected_qty > 1 and quantity != expected_qty:
        raise ValueError(
            f"Quantity for range {canonical_ref} must be {expected_qty}, got {quantity}"
        )

    # Check overlap against existing refs/ranges.
    for existing in project.selections:
        if existing.ref == canonical_ref:
            raise ValueError(
                f"Reference {canonical_ref} already exists (LCSC: {existing.lcsc})"
            )
        if refs_overlap(existing.ref, canonical_ref):
            raise ValueError(
                f"Reference {canonical_ref} overlaps existing {existing.ref} (LCSC: {existing.lcsc})"
            )

    sel = Selection(ref=canonical_ref, lcsc=lcsc, quantity=quantity, notes=notes)
    project.selections.append(sel)
    save_project(project)
    return sel


def remove_selection(project: Project, ref: str) -> Selection:
    """Remove a selection by reference designator."""
    canonical_ref = normalize_ref(ref)
    for i, sel in enumerate(project.selections):
        if sel.ref == canonical_ref:
            removed = project.selections.pop(i)
            save_project(project)
            return removed
    raise ValueError(f"Reference {canonical_ref} not found in BOM")


def relabel_selection(project: Project, old_ref: str, new_ref: str) -> Selection:
    """Rename a reference designator."""
    canonical_old = normalize_ref(old_ref)
    canonical_new = normalize_ref(new_ref)

    for sel in project.selections:
        if sel.ref == canonical_old:
            expected_qty = ref_count(canonical_new)
            if expected_qty > 1 and sel.quantity != expected_qty:
                raise ValueError(
                    f"Quantity for range {canonical_new} must be {expected_qty}, got {sel.quantity}"
                )

            # Check new ref doesn't overlap other selections.
            for existing in project.selections:
                if existing is sel:
                    continue
                if refs_overlap(existing.ref, canonical_new):
                    raise ValueError(
                        f"Reference {canonical_new} overlaps existing {existing.ref}"
                    )

            sel.ref = canonical_new
            save_project(project)
            return sel
    raise ValueError(f"Reference {canonical_old} not found in BOM")


def resolve_bom(project: Project) -> list[dict]:
    """Resolve BOM: enrich selections with cached part data from global DB.

    Returns list of dicts with selection info + part data merged.
    """
    db = Database(get_db_path())
    try:
        results = []
        for sel in project.selections:
            entry = {
                "ref": sel.ref,
                "lcsc": sel.lcsc,
                "quantity": sel.quantity,
                "notes": sel.notes,
                "part": None,
                "warnings": [],
            }

            if sel.lcsc:
                part = db.get_part(sel.lcsc)
                if part:
                    entry["part"] = part
                    if part.stock < 1000:
                        entry["warnings"].append(f"Low stock: {part.stock}")
                else:
                    entry["warnings"].append("Not in local cache — run fetch")
            else:
                entry["warnings"].append("TBD — no part selected")

            results.append(entry)
        return results
    finally:
        db.close()

"""Tests for KiCad BOM import (bomi.kicad) and the import planner in bomi.project."""

import subprocess
from pathlib import Path

import pytest

from bomi.kicad import (
    KicadImportError,
    export_bom_csv,
    find_kicad_cli,
    normalize_lcsc,
    parse_bom_csv,
    read_kicad_bom,
    resolve_schematic,
)
from bomi.project import apply_import, init_project, load_project, plan_import
from bomi.refs import compress_refs, expand_refs

FIXTURES = Path(__file__).parent / "fixtures" / "kicad"


class TestRefHelpers:
    def test_expand_mixed_separators_and_ranges(self):
        assert expand_refs("R1, R2 R5-R7;C3-5") == ["R1", "R2", "R5", "R6", "R7", "C3", "C4", "C5"]

    def test_expand_keeps_invalid_items(self):
        assert expand_refs("R1,J_PWR1") == ["R1", "J_PWR1"]

    def test_compress_contiguous_runs(self):
        assert compress_refs(["D3", "D1", "D2", "D5", "R10", "R9", "D2"]) == ["D1-D3", "D5", "R9-R10"]

    def test_compress_single(self):
        assert compress_refs(["U1"]) == ["U1"]


class TestNormalizeLcsc:
    @pytest.mark.parametrize("raw,expected", [
        ("C1525", "C1525"), ("c1525", "C1525"), (" 1525 ", "C1525"), ("C001525", "C1525"),
        ("see notes", None), ("", None), ("C12x", None),
    ])
    def test_normalize(self, raw, expected):
        assert normalize_lcsc(raw) == expected


class TestParseCsv:
    def test_per_component_export(self):
        comps, field = parse_bom_csv((FIXTURES / "bom_per_component.csv").read_text())
        assert field == "LCSC"
        by_ref = {c.ref: c for c in comps}
        assert by_ref["C1"].lcsc_raw == "C1525"
        assert by_ref["C3"].lcsc_raw == "C19702"  # falls back to the JLCPCB Part # column
        assert by_ref["R5"].dnp is True
        assert by_ref["TP1"].lcsc_raw == ""

    def test_grouped_export_with_ranges(self):
        comps, field = parse_bom_csv((FIXTURES / "bom_grouped.csv").read_text())
        assert field == "LCSC Part #"
        assert [c.ref for c in comps if c.lcsc_raw == "C25744"] == ["R1", "R2", "R3", "R7"]
        assert {c.ref for c in comps if c.lcsc_raw == "C1525"} == {"C1", "C2"}

    def test_explicit_field(self):
        comps, field = parse_bom_csv((FIXTURES / "bom_per_component.csv").read_text(),
                                     lcsc_field="JLCPCB Part #")
        assert field == "JLCPCB Part #"
        assert [c.ref for c in comps if c.lcsc_raw] == ["C3"]

    def test_explicit_field_missing(self):
        with pytest.raises(KicadImportError, match="no column named"):
            parse_bom_csv((FIXTURES / "bom_grouped.csv").read_text(), lcsc_field="MPN")

    def test_no_reference_column(self):
        with pytest.raises(KicadImportError, match="no reference column"):
            parse_bom_csv("Value,LCSC\n10k,C25744\n")

    def test_semicolon_delimited(self):
        comps, field = parse_bom_csv("Reference;Value;LCSC\nR1;10k;C25744\nR2;10k;C25744\n")
        assert field == "LCSC"
        assert [c.ref for c in comps] == ["R1", "R2"]


class TestReadKicadBom:
    def test_groups_by_lcsc_into_ranges(self):
        bom = read_kicad_bom(FIXTURES / "bom_per_component.csv")
        rows = {r.ref: r for r in bom.rows}
        assert rows["C1-C2"].lcsc == "C1525" and rows["C1-C2"].quantity == 2
        assert rows["D1-D3"].quantity == 3
        assert rows["R1-R2"].lcsc == "C25744"   # "c25744" normalized
        assert rows["R4"].lcsc == "C25744"      # "25744" normalized, not contiguous with R1-R2
        assert rows["J1-J2"].value == "BUS_IN / BUS_OUT"
        assert bom.skipped_dnp == ["R5"]
        assert bom.missing_lcsc == ["TP1-TP2"]
        assert bom.invalid_lcsc == [{"ref": "U1", "value": "see notes"}]
        assert bom.invalid_refs == ["J_PWR1"]

    def test_include_missing_and_dnp(self):
        bom = read_kicad_bom(FIXTURES / "bom_per_component.csv", include_missing=True, include_dnp=True)
        rows = {r.ref: r for r in bom.rows}
        assert rows["R5"].lcsc == "C25900"
        assert rows["TP1"].lcsc is None and rows["TP1"].value == "SWCLK"
        assert rows["TP2"].lcsc is None

    def test_unsupported_suffix(self, tmp_path):
        f = tmp_path / "board.kicad_pcb"
        f.write_text("")
        with pytest.raises(KicadImportError, match="Unsupported file type"):
            read_kicad_bom(f)

    def test_schematic_without_kicad_cli(self, monkeypatch):
        monkeypatch.setattr("bomi.kicad.find_kicad_cli", lambda explicit=None: None)
        with pytest.raises(KicadImportError, match="kicad-cli not found"):
            read_kicad_bom(FIXTURES / "mini" / "mini.kicad_sch")


class TestKicadCli:
    def test_explicit_path_must_exist(self, tmp_path):
        assert find_kicad_cli(str(tmp_path / "nope")) is None
        exe = tmp_path / "kicad-cli"
        exe.write_text("")
        assert find_kicad_cli(str(exe)) == str(exe)

    def test_env_var(self, tmp_path, monkeypatch):
        exe = tmp_path / "kicad-cli"
        exe.write_text("")
        monkeypatch.setenv("BOMI_KICAD_CLI", str(exe))
        assert find_kicad_cli() == str(exe)

    def test_project_file_resolves_to_root_schematic(self):
        assert resolve_schematic(FIXTURES / "mini" / "mini.kicad_pro").name == "mini.kicad_sch"

    def test_project_without_schematic(self, tmp_path):
        pro = tmp_path / "x.kicad_pro"
        pro.write_text("{}")
        with pytest.raises(KicadImportError, match="No root schematic"):
            resolve_schematic(pro)

    def test_export_invokes_kicad_cli(self, monkeypatch, tmp_path):
        calls = []

        def fake_run(cmd, capture_output, text, timeout):
            calls.append(cmd)
            Path(cmd[cmd.index("--output") + 1]).write_text('"Reference","LCSC"\n"R1","C25744"\n')
            return subprocess.CompletedProcess(cmd, 0, "", "")

        monkeypatch.setattr("bomi.kicad.subprocess.run", fake_run)
        text = export_bom_csv(tmp_path / "a.kicad_sch", "/bin/kicad-cli", ("LCSC",))
        assert "C25744" in text
        cmd = calls[0]
        assert cmd[:4] == ["/bin/kicad-cli", "sch", "export", "bom"]
        assert "Reference,Value,Footprint,${DNP},LCSC" in cmd
        assert cmd[cmd.index("--ref-range-delimiter") + 1] == ""

    def test_export_failure(self, monkeypatch, tmp_path):
        monkeypatch.setattr("bomi.kicad.subprocess.run",
                            lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, "", "bad schematic"))
        with pytest.raises(KicadImportError, match="bad schematic"):
            export_bom_csv(tmp_path / "a.kicad_sch", "/bin/kicad-cli", ("LCSC",))

    @pytest.mark.skipif(find_kicad_cli() is None, reason="kicad-cli not installed")
    def test_real_schematic_export(self):
        bom = read_kicad_bom(FIXTURES / "mini" / "mini.kicad_pro")
        rows = {r.ref: (r.lcsc, r.quantity) for r in bom.rows}
        assert rows == {"R1-R2": ("C25744", 2), "C1": ("C1525", 1)}
        assert bom.lcsc_field == "LCSC"
        assert bom.missing_lcsc == ["R3"]


class TestImportPlan:
    @pytest.fixture
    def project(self, tmp_path):
        return init_project(tmp_path, name="t")

    @pytest.fixture
    def rows(self):
        return read_kicad_bom(FIXTURES / "bom_grouped.csv").rows  # R1-R3, R7, C1-C2, U1

    def test_first_import_adds_everything(self, project, rows):
        plan = plan_import(project, rows)
        assert sorted(s.ref for s in plan.added) == ["C1-C2", "R1-R3", "R7", "U1"]
        apply_import(project, plan)
        saved = load_project(project.path)
        by_ref = {s.ref: s for s in saved.selections}
        assert by_ref["R1-R3"].quantity == 3 and by_ref["R1-R3"].notes == "10k"

    def test_reimport_is_idempotent(self, project, rows):
        apply_import(project, plan_import(project, rows))
        plan = plan_import(load_project(project.path), rows)
        assert plan.added == [] and plan.updated == [] and len(plan.unchanged) == 4

    def test_changed_part_updates_and_keeps_notes(self, project, rows):
        apply_import(project, plan_import(project, rows))
        project = load_project(project.path)
        project.selections[0].notes = "hand-written note"
        ref = project.selections[0].ref
        changed = [type(r)(r.ref, "C99999" if r.ref == ref else r.lcsc, r.quantity, r.value) for r in rows]
        plan = plan_import(project, changed)
        assert [(b.ref, a.lcsc) for b, a in plan.updated] == [(ref, "C99999")]
        apply_import(project, plan)
        updated = {s.ref: s for s in load_project(project.path).selections}[ref]
        assert updated.lcsc == "C99999" and updated.notes == "hand-written note"

    def test_partial_overlap_is_a_conflict(self, project, rows):
        from bomi.project import add_selection
        add_selection(project, "C25744", "R1-R2", quantity=2)
        plan = plan_import(project, rows)
        assert [(i.ref, e.ref) for i, e in plan.conflicts] == [("R1-R3", "R1-R2")]
        assert "R1-R3" not in [s.ref for s in plan.added]

    def test_stale_entries_kept_by_merge_removed_by_replace(self, project, rows):
        from bomi.project import add_selection
        add_selection(project, "C25744", "R99")
        add_selection(project, "C25744", "R1-R2", quantity=2)
        merge = plan_import(project, rows)
        assert [s.ref for s in merge.stale] == ["R99"]
        replace = plan_import(project, rows, replace=True)
        assert sorted(s.ref for s in replace.stale) == ["R1-R2", "R99"]
        assert replace.conflicts == []
        apply_import(project, replace)
        refs = sorted(s.ref for s in load_project(project.path).selections)
        assert refs == ["C1-C2", "R1-R3", "R7", "U1"]

    def test_unparseable_existing_ref_does_not_crash(self, project, rows):
        from bomi.project import Selection, save_project
        project.selections.append(Selection(ref="J_PWR1", lcsc="C8465"))
        save_project(project)
        plan = plan_import(load_project(project.path), rows)
        assert [s.ref for s in plan.stale] == ["J_PWR1"]
        assert len(plan.added) == 4

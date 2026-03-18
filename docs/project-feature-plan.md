# Historical Plan: Project-Aware CLI Tool with Shared Part Cache

This file is an implementation-era planning note. Parts of it have been implemented, parts have drifted, and it should not be treated as the current user guide. For current behavior, use `README.md`. For open follow-up work, use `docs/review-issues.md`.

## Context

The repo is a JLCPCB CLI tool. The user wants to restructure so that:
- The tool repo has no user data — it's a clean installable package
- Part data is cached globally and shared across all projects (fetch once, use everywhere)
- Projects are separate directories where the user works on a PCB design
- The tool detects project context from cwd, `--project`, or `BOMI_PROJECT`
- Components can be "selected" for a project, forming the BOM
- Reference designators can be changed without re-selecting parts

## Data Architecture

### Global (shared across all projects)

Location: `~/.local/share/bomi/` (Linux) or `~/Library/Application Support/bomi/` (macOS)

```
~/.local/share/bomi/
  parts.db              # SQLite cache — all fetched parts, prices, attributes, analyses
  config.yaml           # Global tool config (API keys, defaults)
```

**The parts DB is shared.** When any project triggers a fetch or search, the results go into this single DB. All projects benefit — if project A fetched C114581 yesterday, project B sees it immediately. The `--force` flag on fetch still refreshes stale data.

### Per-project (checked into the project's git repo)

Location: `.bomi/` inside the project directory. The user decides what to gitignore (datasheets, etc.).

```
my-pcb-project/
  .bomi/
    project.yaml        # Project metadata + selected components (the BOM)
  docs/                  # User's own files — tool doesn't manage these
  datasheets/            # User's choice whether to gitignore
```

**Only one file: `project.yaml`.** It holds both project metadata and selections. No separate selections file — keeps it simple, one file to commit.

## `project.yaml` Format

```yaml
name: rgb-spotlight
description: "50mm circular chainable RGB spotlight pixel"
created: "2026-03-16"

# Selected components — this IS the BOM
selections:
  - ref: U1
    lcsc: C114581
    quantity: 1
    notes: "WS2811 pixel controller, SET pin floated for 800kHz"

  - ref: U2-U4
    lcsc: C347356
    quantity: 3
    notes: "PT4115 buck LED driver, one per RGB channel"
    alternatives:
      - lcsc: C12345
        reason: "Backup if out of stock"

  - ref: LED1
    lcsc: C49237857
    quantity: 1
    notes: "HD2525 Red LED 625nm"

  - ref: R4-R6
    lcsc: null
    quantity: 3
    notes: "4.7k pull-up, any basic 0402 — TBD"
```

Key points:
- `ref` is the reference designator — can be renamed freely with `bomi relabel`
- `lcsc: null` for TBD/unresolved parts
- `alternatives` is optional per selection
- File is the single source of truth for what's in the BOM
- Sorted by ref for clean git diffs

## Global Config (`~/.local/share/bomi/config.yaml`)

```yaml
# API keys (migrated from secrets.yaml in repo root)
openrouter_api_key: sk-or-v1-...
llmlayer_api_key: llm_...

# Optional defaults
default_stock_warning: 1000
cache_max_age_hours: 24
```

Fallback chain for config: env vars → global config.yaml → defaults.

## Project Resolution

The tool finds project context in order:
1. `--project <path>` CLI option
2. `BOMI_PROJECT` env var
3. Walk up from cwd looking for `.bomi/project.yaml`
4. No project (search/fetch/query/info/compare still work without one)

## CLI Commands

### Existing (unchanged, work without project context)
```
bomi search <keyword>       # Search JLCPCB API
bomi fetch <codes>...       # Fetch specific parts
bomi query [keyword]        # Query local DB
bomi info <code>            # Full part detail
bomi compare <codes>...     # Side-by-side comparison
bomi analyze <code>         # LLM datasheet analysis
bomi db stats               # Database statistics
bomi db clear               # Clear cache
```

### New project commands
```
bomi init [--name NAME] [--description DESC]
    Create .bomi/project.yaml in current directory.

bomi select <lcsc_code> --ref <REF> [--qty N] [--notes TEXT]
    Add a component to the project BOM. Fetches part if not cached.
    Requires project context.

bomi deselect <ref>
    Remove a component from the BOM by reference designator.

bomi relabel <old_ref> <new_ref>
    Rename a reference designator (e.g. after schematic changes).
    Updates the selection in place — no re-fetch needed.

bomi bom [--format table|json|csv] [--output FILE] [--check]
    Display the project BOM, enriched with cached part data.
    --check: refresh all BOM parts from API, flag stock/price issues.

bomi status
    Project overview: name, # selections, total cost estimate,
    warnings (low stock, stale cache, TBD parts, missing refs).
```

## Typical Workflow

### Starting a new PCB project
```bash
mkdir my-board && cd my-board
git init
bomi init --name "my-board" --description "Motor driver board"
# Creates .bomi/project.yaml
git add .bomi/project.yaml
```

### Finding and selecting components
```bash
# Research phase — no project context needed
bomi search "100nF 0402 X7R"
bomi compare C1525 C2345 C6789
bomi info C1525

# Select for this project
bomi select C1525 --ref C1-C4 --qty 4 --notes "Bypass caps"
bomi select C347356 --ref U2-U4 --qty 3 --notes "PT4115 LED driver"
git commit -am "Add bypass caps and LED drivers to BOM"
```

### Checking BOM health
```bash
bomi bom                    # Table view of current BOM
bomi bom --check            # Refresh prices/stock, flag issues
bomi bom --format csv > bom.csv  # Export for JLCPCB order
bomi status                 # Quick overview
```

### Schematic changed — relabel parts
```bash
bomi relabel C1-C4 C1-C3   # Removed one cap
bomi relabel U2-U4 U3-U5   # Shifted IC numbering
git commit -am "Updated refs after schematic revision"
```

### Using with Claude Code
```bash
# Claude can read project.yaml and use the tool
claude "check if any BOM parts are low stock"
# Claude runs: bomi bom --check --format json
# Claude interprets results and reports

claude "find a cheaper alternative to U1"
# Claude runs: bomi info C114581, then bomi search "WS2811"
# Claude compares options and suggests a swap
```

## File Changes

| File | Action | Purpose |
|------|--------|---------|
| `src/bomi/config.py` | **Modify** | XDG data dir, global config, `find_project_dir()` |
| `src/bomi/project.py` | **Create** | Project init, selections CRUD, BOM generation, relabel |
| `src/bomi/cli.py` | **Modify** | `--project` global opt, new commands: init/select/deselect/relabel/bom/status |
| `tests/test_project.py` | **Create** | Tests for project module |
| `.gitignore` | **Modify** | Remove `data/` references (no longer in repo) |
| `data/` | **Remove** | DB moves to user home dir |
| `docs/rgb-spotlight-bom.md` | **Move** | → `examples/rgb-spotlight/docs/bom.md` |
| `examples/rgb-spotlight/.bomi/` | **Create** | Sample project.yaml with selections from existing BOM |
| `README.md` | **Modify** | Document project workflow, new commands, data locations |

## Implementation Order

1. **config.py** — XDG data dir, global config loading, `find_project_dir()`
2. **project.py** — `init_project`, `load_project`, `save_project`
3. **cli.py** — `--project` global option + `init` command
4. **project.py** — `add_selection`, `remove_selection`, `relabel_selection`
5. **cli.py** — `select`, `deselect`, `relabel` commands
6. **project.py** — `resolve_bom`, `generate_bom_output`, `check_bom_stock`
7. **cli.py** — `bom`, `status` commands
8. Migrate RGB spotlight to `examples/rgb-spotlight/`
9. Cleanup: remove `data/`, update `.gitignore`, migrate `secrets.yaml` handling
10. **tests/test_project.py** + update **README.md**

## Verification

1. `pip install -e .` — clean install
2. Verify DB at `~/Library/Application Support/bomi/parts.db` (macOS)
3. `cd /tmp && mkdir test-pcb && cd test-pcb && bomi init --name test` — creates `.bomi/`
4. `bomi search "10k 0402"` — works, caches to global DB
5. `bomi select C8287 --ref R1 --qty 2` — adds to project
6. `bomi bom` — shows enriched BOM
7. `bomi relabel R1 R1-R2` — renames ref
8. `bomi bom --format csv` — CSV export
9. `bomi bom --check` — refreshes from API
10. `bomi deselect R1-R2` — removes
11. `bomi status` — overview
12. `cd /tmp && BOMI_PROJECT=/tmp/test-pcb bomi bom` — works from outside project
13. `bomi --project /tmp/test-pcb bom` — also works
14. `pytest tests/ -v` — all pass

# Plan: Project-Aware CLI Tool with Shared Part Cache

## Context

The repo is a JLCPCB CLI tool. The user wants to restructure so that:
- The tool repo has no user data — it's a clean installable package
- Part data is cached globally and shared across all projects (fetch once, use everywhere)
- Projects are separate directories where the user works on a PCB design
- The tool detects project context from cwd, `--project`, or `JLCPCB_PROJECT`
- Components can be "selected" for a project, forming the BOM
- Reference designators can be changed without re-selecting parts

## Data Architecture

### Global (shared across all projects)

Location: `~/.local/share/jlcpcb/` (Linux) or `~/Library/Application Support/jlcpcb/` (macOS)

```
~/.local/share/jlcpcb/
  parts.db              # SQLite cache — all fetched parts, prices, attributes, analyses
  config.yaml           # Global tool config (API keys, defaults)
```

**The parts DB is shared.** When any project triggers a fetch or search, the results go into this single DB. All projects benefit — if project A fetched C114581 yesterday, project B sees it immediately. The `--force` flag on fetch still refreshes stale data.

### Per-project (checked into the project's git repo)

Location: `.jlcpcb/` inside the project directory. The user decides what to gitignore (datasheets, etc.).

```
my-pcb-project/
  .jlcpcb/
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
- `ref` is the reference designator — can be renamed freely with `jlcpcb relabel`
- `lcsc: null` for TBD/unresolved parts
- `alternatives` is optional per selection
- File is the single source of truth for what's in the BOM
- Sorted by ref for clean git diffs

## Global Config (`~/.local/share/jlcpcb/config.yaml`)

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
2. `JLCPCB_PROJECT` env var
3. Walk up from cwd looking for `.jlcpcb/project.yaml`
4. No project (search/fetch/query/info/compare still work without one)

## CLI Commands

### Existing (unchanged, work without project context)
```
jlcpcb search <keyword>       # Search JLCPCB API
jlcpcb fetch <codes>...       # Fetch specific parts
jlcpcb query [keyword]        # Query local DB
jlcpcb info <code>            # Full part detail
jlcpcb compare <codes>...     # Side-by-side comparison
jlcpcb analyze <code>         # LLM datasheet analysis
jlcpcb db stats               # Database statistics
jlcpcb db clear               # Clear cache
```

### New project commands
```
jlcpcb init [--name NAME] [--description DESC]
    Create .jlcpcb/project.yaml in current directory.

jlcpcb select <lcsc_code> --ref <REF> [--qty N] [--notes TEXT]
    Add a component to the project BOM. Fetches part if not cached.
    Requires project context.

jlcpcb deselect <ref>
    Remove a component from the BOM by reference designator.

jlcpcb relabel <old_ref> <new_ref>
    Rename a reference designator (e.g. after schematic changes).
    Updates the selection in place — no re-fetch needed.

jlcpcb bom [--format table|json|csv] [--output FILE] [--check]
    Display the project BOM, enriched with cached part data.
    --check: refresh all BOM parts from API, flag stock/price issues.

jlcpcb status
    Project overview: name, # selections, total cost estimate,
    warnings (low stock, stale cache, TBD parts, missing refs).
```

## Typical Workflow

### Starting a new PCB project
```bash
mkdir my-board && cd my-board
git init
jlcpcb init --name "my-board" --description "Motor driver board"
# Creates .jlcpcb/project.yaml
git add .jlcpcb/project.yaml
```

### Finding and selecting components
```bash
# Research phase — no project context needed
jlcpcb search "100nF 0402 X7R"
jlcpcb compare C1525 C2345 C6789
jlcpcb info C1525

# Select for this project
jlcpcb select C1525 --ref C1-C4 --qty 4 --notes "Bypass caps"
jlcpcb select C347356 --ref U2-U4 --qty 3 --notes "PT4115 LED driver"
git commit -am "Add bypass caps and LED drivers to BOM"
```

### Checking BOM health
```bash
jlcpcb bom                    # Table view of current BOM
jlcpcb bom --check            # Refresh prices/stock, flag issues
jlcpcb bom --format csv > bom.csv  # Export for JLCPCB order
jlcpcb status                 # Quick overview
```

### Schematic changed — relabel parts
```bash
jlcpcb relabel C1-C4 C1-C3   # Removed one cap
jlcpcb relabel U2-U4 U3-U5   # Shifted IC numbering
git commit -am "Updated refs after schematic revision"
```

### Using with Claude Code
```bash
# Claude can read project.yaml and use the tool
claude "check if any BOM parts are low stock"
# Claude runs: jlcpcb bom --check --format json
# Claude interprets results and reports

claude "find a cheaper alternative to U1"
# Claude runs: jlcpcb info C114581, then jlcpcb search "WS2811"
# Claude compares options and suggests a swap
```

## File Changes

| File | Action | Purpose |
|------|--------|---------|
| `src/jlcpcb_tool/config.py` | **Modify** | XDG data dir, global config, `find_project_dir()` |
| `src/jlcpcb_tool/project.py` | **Create** | Project init, selections CRUD, BOM generation, relabel |
| `src/jlcpcb_tool/cli.py` | **Modify** | `--project` global opt, new commands: init/select/deselect/relabel/bom/status |
| `tests/test_project.py` | **Create** | Tests for project module |
| `.gitignore` | **Modify** | Remove `data/` references (no longer in repo) |
| `data/` | **Remove** | DB moves to user home dir |
| `docs/rgb-spotlight-bom.md` | **Move** | → `examples/rgb-spotlight/docs/bom.md` |
| `examples/rgb-spotlight/.jlcpcb/` | **Create** | Sample project.yaml with selections from existing BOM |
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
2. Verify DB at `~/Library/Application Support/jlcpcb/parts.db` (macOS)
3. `cd /tmp && mkdir test-pcb && cd test-pcb && jlcpcb init --name test` — creates `.jlcpcb/`
4. `jlcpcb search "10k 0402"` — works, caches to global DB
5. `jlcpcb select C8287 --ref R1 --qty 2` — adds to project
6. `jlcpcb bom` — shows enriched BOM
7. `jlcpcb relabel R1 R1-R2` — renames ref
8. `jlcpcb bom --format csv` — CSV export
9. `jlcpcb bom --check` — refreshes from API
10. `jlcpcb deselect R1-R2` — removes
11. `jlcpcb status` — overview
12. `cd /tmp && JLCPCB_PROJECT=/tmp/test-pcb jlcpcb bom` — works from outside project
13. `jlcpcb --project /tmp/test-pcb bom` — also works
14. `pytest tests/ -v` — all pass

# bomi — Agent Guide

Use `bomi` for JLCPCB/LCSC part research and project BOM updates. Prefer it over manual website searches when you want repeatable, local-cache-backed results.

> This guide is also available at [somebox.github.io/bomi/guide.html](https://somebox.github.io/bomi/guide.html).

## Quick Rules

- `sync` fetches the JLCPCB category tree and caches it locally (skips if <24h old).
- `search` is live and also updates the local cache. Use `--category` to filter by category (requires `sync` first).
- `query` is local-cache only — fast and offline.
- `info`, `compare`, `analyze`, and `datasheet` need the part in the local cache first — run `fetch` if needed.
- `select` fetches the part automatically if it is not already cached.
- `select`, `list`/`bom`, `status`, `deselect`, and `relabel` need project context (a `.bomi/project.yaml` in the tree).
- `fetch --all` and `datasheet --all` use selected parts from the active project BOM.
- `status` is text-only. `list --format json` (and `bom --format json`) uses a different JSON shape than most other commands.

## Quick Reference

| Command | Purpose |
|---------|---------|
| `bomi sync` | Fetch and cache JLCPCB category tree |
| `bomi categories` | List cached categories |
| `bomi categories "filter"` | Filter categories by name |
| `bomi search "keyword"` | Search the live JLCPCB catalog |
| `bomi search "keyword" --category "name"` | Search within a specific category |
| `bomi fetch CXXXXX` | Cache a specific part by LCSC code |
| `bomi fetch --all` | Cache all selected LCSC parts from the active project BOM |
| `bomi query "keyword"` | Search the local cache only |
| `bomi query --category "name"` | Filter local cache by category |
| `bomi info R1` | Show full details for the part selected at a designator |
| `bomi info CXXXXX` | Show full details for one cached part by LCSC code |
| `bomi compare CXXXXX CYYYYY` | Compare cached parts side-by-side |
| `bomi analyze CXXXXX` | Analyze a cached datasheet with OpenRouter |
| `bomi datasheet CXXXXX --pdf --summary -o dir/` | Download PDF and write a markdown summary |
| `bomi datasheet --all --pdf --summary` | Process datasheets for all selected LCSC parts in the active project |
| `bomi init` | Create `.bomi/project.yaml` in the current directory |
| `bomi select CXXXXX --ref U1` | Add a BOM entry (fetches if not cached) |
| `bomi deselect U1` | Remove a BOM entry by reference |
| `bomi relabel R1 R3` | Rename a BOM reference |
| `bomi list` | Show the full BOM with pricing and stock (`bom` is an alias) |
| `bomi list --check` | Refresh BOM stock and pricing from live catalog |
| `bomi list --format json` | Export BOM as JSON |
| `bomi status` | Show project summary with cost estimate and warnings |
| `bomi db stats` | Show local cache statistics |

## Common Flows

### Sync categories and search

```bash
bomi sync
bomi categories mosfet
bomi search "N-Channel" --category "MOSFETs"
```

### Search and inspect

```bash
bomi search "buck converter 3.3V"
bomi fetch C9865
bomi info C9865
bomi info U3
bomi compare C9865 C28023
```

### Filter by attributes

```bash
bomi search "0402 resistor" --attr "Resistance >= 10k"
bomi search "MOSFET SOT-23" --attr "Drain Source Voltage (Vdss) >= 30"
bomi query --category "Chip Resistor" --basic-only --attr "Resistance >= 10k"
bomi query --basic-only --attr "Capacitance <= 100n"
```

Attribute operators: `>=` `<=` `>` `<` `=`.
Values support SI prefixes: `10k`, `100n`, `4.7u`.
Non-numeric values use exact string matching with `=`: `"Circuit = SP3T"`.
Multiple `--attr` flags are ANDed together.

### Work in a project

```bash
cd my-project
bomi init --name "My Board" --description "Description here"

bomi select C9865 --ref U3 --qty 1 --notes "3.3V buck, chosen for low quiescent current"
bomi select C8678 --ref D3 --qty 1 --notes "catch diode"

bomi list
bomi list --check
bomi status
```

### Work with datasheets

```bash
bomi fetch C9865
bomi analyze C9865
bomi analyze C9865 --prompt "What is the enable pin threshold voltage?"
bomi fetch --all --force
bomi datasheet --all --pdf --summary --force -o docs/datasheets/
bomi datasheet C9865 --pdf --summary -o docs/datasheets/
```

The `analyze` command sends the datasheet PDF to OpenRouter and returns structured markdown covering key specs, pin descriptions, application circuit values, and design notes. Pass `--prompt` only when you need something specific beyond that. Requires an OpenRouter API key in config.

The `datasheet` command writes files to disk: a PDF and (with `--summary`) a `.md` alongside it. The markdown summary is useful as context for subsequent agent queries.

## Output Notes

Most commands support `--format table|json|csv|markdown`. JSON uses this envelope:

```json
{
  "status": "ok",
  "command": "search",
  "count": 1,
  "results": []
}
```

`list --format json` (and `bom --format json`) is different — it uses `data` instead of `results`:

```json
{
  "status": "ok",
  "command": "bom",
  "data": []
}
```

`status` is text-only and does not support `--format`.

## Project Context

Project context is resolved in this order:

1. `--project <path>`
2. `BOMI_PROJECT` environment variable
3. Walk up from the current directory until `.bomi/project.yaml` is found

`bomi init` also appends datasheet PDF ignore rules to `.gitignore`.

If running from outside the project tree (e.g. via `uv run --directory`), set `BOMI_PROJECT` to avoid needing `--project` on every command.

## Configuration (project.yaml + global options)

### Project file: `.bomi/project.yaml`

`project.yaml` is project-local and should usually be committed to git. It stores project metadata and selected parts:

```yaml
name: my-board
description: Motor driver board
created: "2026-03-19"
selections:
  - ref: U3
    lcsc: C9865
    quantity: 1
    notes: 3.3V buck regulator
```

Core fields:
- `name`, `description`, `created`
- `selections[]` entries with `ref`, `lcsc`, `quantity`, `notes` (and optional `alternatives`)

### Global config: `config.yaml`

Global config lives at:
- macOS: `~/Library/Application Support/bomi/config.yaml`
- Linux: `~/.local/share/bomi/config.yaml`

Relevant keys:

```yaml
openrouter_api_key: sk-or-v1-...
default_model: anthropic/claude-sonnet-4.6
datasheet_output_dir: docs/datasheets
```

How they are used:
- `openrouter_api_key`: required for `analyze` and `datasheet --summary/--summarize`
- `default_model`: default model for summaries/analyze when `--model` is not provided
- `datasheet_output_dir`: default output directory for `bomi datasheet` when `-o/--output` is not provided

Env vars override config values:
- `BOMI_OPENROUTER_API_KEY`
- `BOMI_DEFAULT_MODEL`
- `BOMI_DATASHEET_OUTPUT_DIR`

## Good Defaults

- Run `sync` once before using `--category` on search.
- Run `fetch` before `info`, `compare`, `analyze`, or `datasheet`.
- Use `query` when you want fast, offline, reproducible filtering from the local cache.
- Use `list --check` before ordering to refresh stock and pricing from the live catalog.
- Use one reference per BOM line when possible (`R1`, `U2`, etc.).
- Add `--notes` to selections to record why a part was chosen — this context persists in the project file.
- Commit `.bomi/project.yaml` with every BOM change so decisions are tracked in git.

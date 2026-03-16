# jlcpcb-tool

CLI tool for researching JLCPCB/LCSC electronic components and managing PCB project BOMs. Search the catalog, cache parts locally, filter by parametric attributes, analyze datasheets with LLMs, and track component selections per project.

## Install

```bash
# Development (from repo)
uv sync

# Global install (available everywhere as `jlcpcb`)
uv tool install -e .
```

## Setup

API keys and settings go in the global config file:

- **macOS:** `~/Library/Application Support/jlcpcb/config.yaml`
- **Linux:** `~/.local/share/jlcpcb/config.yaml`

```yaml
openrouter_api_key: sk-or-v1-...
llmlayer_api_key: llm_...
```

Environment variables override config.yaml (prefix with `JLCPCB_`):
```bash
export JLCPCB_OPENROUTER_API_KEY=sk-or-v1-...
```

The parts database (`parts.db`) is stored in the same directory. It's shared across all projects — fetch once, use everywhere.

## Quick Start

```bash
# Search for components
jlcpcb search "10k 0402 resistor"

# Fetch specific parts into cache
jlcpcb fetch C8287 C25900

# Query local cache with filters
jlcpcb query --package 0402 --basic-only --attr "Resistance >= 10k"

# View full part details
jlcpcb info C8287

# Compare parts side-by-side
jlcpcb compare C8287 C25900

# Analyze datasheet with LLM
jlcpcb analyze C8287 --prompt "What is the max power rating?"
```

## Project Workflow

Projects track component selections (the BOM) in a `.jlcpcb/project.yaml` file inside your PCB project directory. This file is meant to be committed to git.

```bash
# Initialize a project
cd my-pcb-project
jlcpcb init --name "my-board" --description "Motor driver board"

# Select components into the BOM (auto-fetches if not cached)
jlcpcb select C8287 --ref R1 --qty 2 --notes "10k pull-up"
jlcpcb select C1525 --ref C1-C4 --qty 4 --notes "100nF bypass"

# View the BOM
jlcpcb bom                     # table
jlcpcb bom --format json       # for agents
jlcpcb bom --format csv        # for export
jlcpcb bom --check             # refresh stock/prices from API

# Project overview with warnings
jlcpcb status

# Schematic changed — rename refs without re-selecting
jlcpcb relabel R1 R1-R2

# Remove a selection
jlcpcb deselect C1-C4
```

### Project Resolution

The tool finds project context in order:
1. `--project <path>` CLI option
2. `JLCPCB_PROJECT` environment variable
3. Walk up from cwd looking for `.jlcpcb/project.yaml`

Commands that don't need a project (`search`, `fetch`, `query`, `info`, `compare`, `analyze`, `db`) work from anywhere.

## Commands

### Research (no project needed)

| Command | Description |
|---------|-------------|
| `search <keyword>` | Search JLCPCB API, cache + display results |
| `fetch <codes>...` | Fetch specific part(s) by LCSC code |
| `query [keyword]` | Query local DB only (no API calls) |
| `info <code>` | Full detail view of a cached part |
| `compare <codes>...` | Side-by-side comparison table |
| `analyze <code>` | LLM datasheet analysis |
| `db stats` | Database statistics |
| `db clear` | Clear all cached data |

### Project (requires `.jlcpcb/project.yaml`)

| Command | Description |
|---------|-------------|
| `init` | Create `.jlcpcb/project.yaml` in current directory |
| `select <code> --ref REF` | Add component to BOM (auto-fetches if needed) |
| `deselect <ref>` | Remove component by reference designator |
| `relabel <old> <new>` | Rename a reference designator |
| `bom` | Display BOM enriched with cached part data |
| `status` | Project overview with cost estimate and warnings |

## Common Options

- `--format table|json|csv` — Output format (default: table)
- `--project <path>` — Override project directory
- `--package` — Filter by package (e.g., 0402, SOT-23)
- `--min-stock N` — Minimum stock count
- `--basic-only` — Basic parts only (no extra assembly fee)
- `--preferred-only` — JLCPCB preferred parts only
- `--max-price N` — Maximum unit price at qty 1
- `--attr "Name op Value"` — Attribute filter (repeatable)

## Attribute Filters

Filter syntax: `--attr "AttributeName operator value"`

Operators: `>=`, `<=`, `>`, `<`, `=`, `!=`

Values support SI prefixes: `10k` = 10000, `100n` = 1e-7, `4.7u` = 4.7e-6

```bash
--attr "Resistance >= 10k"
--attr "Capacitance <= 100n"
--attr "Forward Current >= 100mA"
```

## Agent Integration

All commands support `--format json` for machine consumption. JSON output uses a consistent envelope:

```json
{
  "status": "ok",
  "command": "search",
  "count": 5,
  "results": [...]
}
```

Project commands also output JSON:
```bash
jlcpcb bom --format json       # BOM with part data, stock, prices, warnings
jlcpcb status                  # text summary (no JSON yet)
```

The `bom --check` flag refreshes all BOM parts from the API before display — useful for pre-order verification.

## Data Locations

| What | Where |
|------|-------|
| Parts cache (SQLite) | `~/Library/Application Support/jlcpcb/parts.db` (macOS) |
| Global config | `~/Library/Application Support/jlcpcb/config.yaml` |
| Project BOM | `.jlcpcb/project.yaml` (in your project dir) |

## Development

```bash
uv sync
uv run pytest tests/ -v
```

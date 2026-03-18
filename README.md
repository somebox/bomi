# bomi

[![CI](https://github.com/somebox/bomi/actions/workflows/ci.yml/badge.svg)](https://github.com/somebox/bomi/actions/workflows/ci.yml)

<img src="site/assets/logo.png" alt="bomi logo" width="120" align="right">

**Bill of Materials Integration** — applying DevOps-style tooling to electronics projects.

`bomi` is a Python CLI for researching JLCPCB/LCSC parts and keeping a per-project BOM in version control. It caches part data in a shared local SQLite database and stores project selections in `.bomi/project.yaml`.

AI agents (Claude Code, Cursor, GitHub Copilot, etc.) can drive it directly — searching the catalog, comparing parts, updating the BOM, and pulling datasheet analysis without touching a browser. After a lot of iteration and many PCBs made, bomi proved to be a significant time saver: easier to track decisions, catch stock issues early, and keep BOM costs under control across revisions.

**[somebox.github.io/bomi](https://somebox.github.io/bomi)** — demos, examples, and getting-started guide

## Requirements

- Python `3.11+`
- [`uv`](https://docs.astral.sh/uv/) for install and development
- Network access for live catalog search
- An OpenRouter API key only if you want datasheet analysis or summaries

## Install

```bash
git clone https://github.com/somebox/bomi.git
cd bomi

# Install the CLI globally as `bomi`
uv tool install -e .

# Or, to work on the repo
uv sync
```

> **Note for asdf users:** `uv tool install` installs into uv's own tool environment, which may not be on `PATH` under all asdf-managed Python shims. If you get "No preset version installed for command bomi", run directly with:
> ```bash
> uv run --directory /path/to/bomi bomi <command>
> ```
> Set `BOMI_PROJECT` (see [Project Resolution](#project-resolution)) to avoid needing `--project` on every command.

## Configuration

Global config lives here:

- macOS: `~/Library/Application Support/bomi/config.yaml`
- Linux: `~/.local/share/bomi/config.yaml`

Minimal config (see `secrets.yaml.example` in the repo):

```yaml
openrouter_api_key: sk-or-v1-...
```

Environment variables override config values:

```bash
export BOMI_OPENROUTER_API_KEY=sk-or-v1-...
```

The shared cache database is stored alongside the config as `parts.db`.

## First Use

```bash
# 1. Search the live catalog
bomi search "10k 0402 resistor"

# 2. Cache one or more exact parts
bomi fetch C8287 C25900

# 3. Query the local cache offline
bomi query --package 0402 --basic-only --attr "Resistance >= 10k"

# 4. Inspect or compare cached parts
bomi info C8287
bomi compare C8287 C25900

# 5. Analyze a cached part's datasheet with OpenRouter (default prompt covers key specs)
bomi analyze C8287
```

`info`, `compare`, `analyze`, and `datasheet` all work from the local cache. If a part is missing, run `bomi fetch <code>` first.

## Project Workflow

Projects store their BOM in `.bomi/project.yaml`, which is meant to be committed with the rest of the design files.

```bash
cd my-pcb-project
bomi init --name "my-board" --description "Motor driver board"

# Add parts to the BOM (fetches from catalog if not already cached)
bomi select C8287 --ref R1 --qty 2 --notes "10k pull-up"
bomi select C1525 --ref C1 --qty 1 --notes "100nF bypass"
bomi select C1525 --ref C2 --qty 1 --notes "100nF bypass"

# Review the BOM
bomi bom
bomi bom --format json
bomi bom --format csv
bomi bom --check

# Project summary
bomi status

# Edit selections
bomi relabel R1 R3
bomi deselect C2
```

`bomi init` currently:

- creates `.bomi/project.yaml`
- appends datasheet PDF ignore rules to `.gitignore`

### Project Resolution

Project context is resolved in this order:

1. `--project <path>`
2. `BOMI_PROJECT` env var
3. walking up from the current directory to find `.bomi/project.yaml`

If you're running `bomi` from outside the project directory (e.g. via `uv run --directory`), set `BOMI_PROJECT` so project commands work without `--project` on every call:

```bash
export BOMI_PROJECT=/path/to/my-pcb-project
```

## Commands

### Research commands

| Command | Notes |
|---------|-------|
| `search <keyword>` | Live JLCPCB search, results are cached locally |
| `fetch <codes>...` | Cache exact LCSC codes |
| `query [keyword]` | Search the local cache only |
| `info <code>` | Show one cached part |
| `compare <codes>...` | Compare cached parts |
| `analyze <code>` | Analyze one cached datasheet with OpenRouter |
| `datasheet <codes>...` | Download PDFs and optionally generate markdown summaries |
| `db stats` | Show cache statistics |
| `db clear` | Clear the local cache |

### Project commands

| Command | Notes |
|---------|-------|
| `init` | Create `.bomi/project.yaml` in the current directory |
| `select <code> --ref REF` | Add a BOM entry, fetching the part if needed |
| `deselect <ref>` | Remove a BOM entry by reference |
| `relabel <old> <new>` | Rename a BOM entry reference |
| `bom` | Show the BOM with cached part data |
| `status` | Show project summary, cost estimate, and warnings |

## Output Formats

Most research commands support `--format table|json|csv|markdown`.

Commands that currently support `--format`:

- `search`
- `fetch`
- `query`
- `info`
- `compare`
- `analyze`
- `bom`
- `db stats`

Most JSON output uses this envelope:

```json
{
  "status": "ok",
  "command": "search",
  "count": 5,
  "results": []
}
```

`bom --format json` is different. It returns `{ "status": "ok", "command": "bom", "data": [...] }`.

`status` is text-only today.

## Attribute Filters

Filter syntax:

```bash
--attr "AttributeName operator value"
```

Supported operators: `>=`, `<=`, `>`, `<`, `=`, `!=`

Examples:

```bash
bomi search "0402 resistor" --attr "Resistance >= 10k"
bomi query --attr "Capacitance <= 100n"
bomi search "RGB LED" --attr "Forward Current >= 100mA"
```

Values support SI prefixes such as `10k`, `100n`, and `4.7u`.

## Data Locations

| What | Location |
|------|----------|
| Global config | `~/Library/Application Support/bomi/config.yaml` on macOS, `~/.local/share/bomi/config.yaml` on Linux |
| Shared cache database | `parts.db` in the same global data directory |
| Project BOM | `.bomi/project.yaml` inside a PCB project |
| Optional project docs | `docs/` inside your project |

## Project Structure

```text
src/bomi/
  api.py        HTTP client for JLCPCB search and detail endpoints
  analysis.py   datasheet download and OpenRouter analysis
  cli.py        Click command definitions and output orchestration
  config.py     config and path handling
  db.py         SQLite schema and persistence
  output.py     table/json/csv/markdown formatters
  project.py    project file and BOM handling
  search.py     local cache query helpers
```

## Documentation

- `docs/bomi-guide.md`: short agent-oriented usage guide (also at [somebox.github.io/bomi/guide.html](https://somebox.github.io/bomi/guide.html))
- `docs/examples.md`: command examples
- `docs/bomi-api-internals.md`: current API notes and implementation boundaries
- `docs/sqlite-database-guide.md`: local cache schema and query examples

## Development

```bash
uv sync
uv run pytest -v
```

## Contributing

PRs are welcome. A good starting point is:

1. run `uv sync`
2. read `README.md` and the docs linked above
3. run `uv run pytest -v`
4. keep behavior changes reflected in the docs

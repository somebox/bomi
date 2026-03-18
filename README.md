# jlcpcb-tool

`jlcpcb-tool` is a Python CLI for researching JLCPCB/LCSC parts and keeping a per-project BOM in version control. It solves two common problems: repeated part lookups and ad-hoc BOM notes. It does that by caching part data in a shared local SQLite database and storing project selections in `.jlcpcb/project.yaml`.

## Requirements

- Python `3.11+`
- [`uv`](https://docs.astral.sh/uv/) for install and development
- Network access for live catalog search
- An OpenRouter API key only if you want datasheet analysis or summaries

## Install

```bash
# Work on the repo
uv sync

# Install the CLI globally as `jlcpcb`
uv tool install -e .
```

> **Note for asdf users:** `uv tool install` installs into uv's own tool environment, which may not be on `PATH` under all asdf-managed Python shims. If you get "No preset version installed for command jlcpcb", run directly with:
> ```bash
> uv run --directory /path/to/jlcpcb-tool jlcpcb <command>
> ```
> Set `JLCPCB_PROJECT` (see [Project Resolution](#project-resolution)) to avoid needing `--project` on every command.

## Configuration

Global config lives here:

- macOS: `~/Library/Application Support/jlcpcb/config.yaml`
- Linux: `~/.local/share/jlcpcb/config.yaml`

Minimal config:

```yaml
openrouter_api_key: sk-or-v1-...
```

Environment variables override config values:

```bash
export JLCPCB_OPENROUTER_API_KEY=sk-or-v1-...
```

The shared cache database is stored alongside the config as `parts.db`.

## First Use

```bash
# 1. Search the live catalog
jlcpcb search "10k 0402 resistor"

# 2. Cache one or more exact parts
jlcpcb fetch C8287 C25900

# 3. Query the local cache offline
jlcpcb query --package 0402 --basic-only --attr "Resistance >= 10k"

# 4. Inspect or compare cached parts
jlcpcb info C8287
jlcpcb compare C8287 C25900

# 5. Analyze a cached part's datasheet with OpenRouter
jlcpcb analyze C8287 --prompt "Summarize key ratings and limits"
```

`info`, `compare`, `analyze`, and `datasheet` all work from the local cache. If a part is missing, run `jlcpcb fetch <code>` first.

## Project Workflow

Projects store their BOM in `.jlcpcb/project.yaml`, which is meant to be committed with the rest of the design files.

```bash
cd my-pcb-project
jlcpcb init --name "my-board" --description "Motor driver board"

# Add parts to the BOM
jlcpcb select C8287 --ref R1 --qty 2 --notes "10k pull-up"
jlcpcb select C1525 --ref C1 --qty 1 --notes "100nF bypass"
jlcpcb select C1525 --ref C2 --qty 1 --notes "100nF bypass"

# Review the BOM
jlcpcb bom
jlcpcb bom --format json
jlcpcb bom --format csv
jlcpcb bom --check

# Project summary
jlcpcb status

# Edit selections
jlcpcb relabel R1 R3
jlcpcb deselect C2
```

`jlcpcb init` currently:

- creates `.jlcpcb/project.yaml`
- appends datasheet PDF ignore rules to `.gitignore`

### Project Resolution

Project context is resolved in this order:

1. `--project <path>`
2. `JLCPCB_PROJECT` env var
3. walking up from the current directory to find `.jlcpcb/project.yaml`

If you're running `jlcpcb` from outside the project directory (e.g. via `uv run --directory`), set `JLCPCB_PROJECT` so project commands work without `--project` on every call:

```bash
export JLCPCB_PROJECT=/path/to/my-pcb-project
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
| `init` | Create `.jlcpcb/project.yaml` in the current directory |
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
jlcpcb search "0402 resistor" --attr "Resistance >= 10k"
jlcpcb query --attr "Capacitance <= 100n"
jlcpcb search "RGB LED" --attr "Forward Current >= 100mA"
```

Values support SI prefixes such as `10k`, `100n`, and `4.7u`.

## Data Locations

| What | Location |
|------|----------|
| Global config | `~/Library/Application Support/jlcpcb/config.yaml` on macOS, `~/.local/share/jlcpcb/config.yaml` on Linux |
| Shared cache database | `parts.db` in the same global data directory |
| Project BOM | `.jlcpcb/project.yaml` inside a PCB project |
| Optional project docs | `docs/` inside your project |

## Project Structure

```text
src/jlcpcb_tool/
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

- `docs/jlcpcb-tool-guide.md`: short agent-oriented usage guide
- `docs/examples.md`: command examples
- `docs/jlcpcb-api-internals.md`: current API notes and implementation boundaries
- `docs/sqlite-database-guide.md`: local cache schema and query examples
- `docs/review-issues.md`: review findings and next-step issue list

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

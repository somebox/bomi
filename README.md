# jlcpcb-tool

CLI tool for researching JLCPCB/LCSC electronic components. Search the catalog, cache parts locally, filter by parametric attributes, and analyze datasheets with LLMs.

## Install

```bash
uv sync
```

## Quick Start

```bash
# Search for components
jlcpcb search "10k 0402 resistor"

# Fetch specific parts
jlcpcb fetch C8287 C25900

# Query local cache with filters
jlcpcb query --package 0402 --basic-only --attr "Resistance >= 10k"

# View full part details
jlcpcb info C8287

# Compare parts side-by-side
jlcpcb compare C8287 C25900

# Analyze datasheet with LLM
jlcpcb analyze C8287 --prompt "What is the max power rating?"

# Database management
jlcpcb db stats
```

## Commands

| Command | Description |
|---------|-------------|
| `search <keyword>` | Search JLCPCB API, store + display results |
| `fetch <codes>...` | Fetch specific part(s) by LCSC code |
| `query [keyword]` | Query local DB only (no API calls) |
| `info <code>` | Full detail view of a cached part |
| `compare <codes>...` | Side-by-side comparison table |
| `analyze <code>` | LLM datasheet analysis |
| `db stats` | Database statistics |
| `db clear` | Clear all cached data |

## Common Options

- `--format table|json|csv` — Output format (default: table)
- `--package` — Filter by package (e.g., 0402, SOT-23)
- `--min-stock N` — Minimum stock count
- `--basic-only` — Basic parts only (no extra assembly fee)
- `--preferred-only` — JLCPCB preferred parts only
- `--max-price N` — Maximum unit price at qty 1
- `--attr "Name op Value"` — Attribute filter (repeatable)

## Attribute Filters

Filter syntax: `--attr "AttributeName operator value"`

Operators: `>=`, `<=`, `>`, `<`, `=`, `!=`

Values support SI prefixes: `10k` = 10000, `100n` = 1e-7, `4.7µ` = 4.7e-6

Examples:
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

## Configuration

API keys for LLM analysis go in `secrets.yaml`:

```yaml
openrouter_api_key: sk-or-v1-...
llmlayer_api_key: llm_...
```

## Development

```bash
uv sync
uv run pytest tests/ -v
```

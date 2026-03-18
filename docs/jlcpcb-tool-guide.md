# jlcpcb-tool — Agent Guide

Use `jlcpcb` for JLCPCB/LCSC part research and project BOM updates. Prefer it over manual website searches when you want repeatable, local-cache-backed results.

## Quick Rules

- `search` is live and also updates the local cache.
- `query` is local-cache only.
- `info`, `compare`, `analyze`, and `datasheet` need the part in the local cache first.
- `select`, `bom`, `status`, `deselect`, and `relabel` need project context.
- `status` is text-only. `bom --format json` uses a different JSON shape than most other commands.

## Quick Reference

| Command | Purpose |
|---------|---------|
| `jlcpcb search "keyword"` | Search the live JLCPCB catalog |
| `jlcpcb fetch CXXXXX` | Cache a specific part |
| `jlcpcb query "keyword"` | Query the local cache |
| `jlcpcb info CXXXXX` | Show one cached part |
| `jlcpcb compare CXXXXX CYYYYY` | Compare cached parts |
| `jlcpcb analyze CXXXXX` | Analyze one cached datasheet with OpenRouter |
| `jlcpcb datasheet CXXXXX --pdf --summary -o dir/` | Download a PDF and optionally write a markdown summary |
| `jlcpcb init` | Create `.jlcpcb/project.yaml` in the current directory |
| `jlcpcb select CXXXXX --ref U1` | Add a BOM entry |
| `jlcpcb bom --format json` | Export the current BOM |
| `jlcpcb status` | Show cost and warning summary |

## Common Flows

### Search and inspect

```bash
jlcpcb search "buck converter 3.3V"
jlcpcb fetch C9865
jlcpcb info C9865
jlcpcb compare C9865 C28023
```

### Filter by attributes

```bash
jlcpcb search "0402 resistor" --attr "Resistance >= 10k"
jlcpcb search "MOSFET SOT-23" --attr "Drain Source Voltage (Vdss) >= 30"
jlcpcb query --basic-only --attr "Capacitance <= 100n"
```

### Work in a project

```bash
cd my-project
jlcpcb init --name "My Board" --description "Description here"

jlcpcb select C9865 --ref U3 --qty 1 --notes "3.3V buck"
jlcpcb select C8678 --ref D3 --qty 1 --notes "catch diode"

jlcpcb bom
jlcpcb bom --check
jlcpcb status
```

### Work with datasheets

```bash
jlcpcb fetch C9865
jlcpcb analyze C9865 --prompt "Summarize ratings and pin functions"
jlcpcb datasheet C9865 --pdf --summary -o docs/datasheets/
```

## Output Notes

Most JSON output uses:

```json
{
  "status": "ok",
  "command": "search",
  "count": 1,
  "results": []
}
```

`bom --format json` uses:

```json
{
  "status": "ok",
  "command": "bom",
  "data": []
}
```

## Project Context

Project context is resolved in this order:

1. `--project <path>`
2. `JLCPCB_PROJECT`
3. walk up from the current directory until `.jlcpcb/project.yaml` is found

`jlcpcb init` appends datasheet PDF ignore rules to `.gitignore`.

## Good Defaults

- Use `fetch` before `info`, `compare`, `analyze`, or `datasheet`.
- Use `query` when you want offline, reproducible filtering from the local cache.
- Use `bom --check` before ordering to refresh stock and pricing.
- Use one ref per BOM line when possible. Range-like refs are accepted by the CLI but are not deeply modeled yet.

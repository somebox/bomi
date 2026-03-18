# bomi — Agent Guide

Use `jlcpcb` for JLCPCB/LCSC part research and project BOM updates. Prefer it over manual website searches when you want repeatable, local-cache-backed results.

> This guide is also available at [somebox.github.io/bomi/guide.html](https://somebox.github.io/bomi/guide.html).

## Quick Rules

- `search` is live and also updates the local cache.
- `query` is local-cache only — fast and offline.
- `info`, `compare`, `analyze`, and `datasheet` need the part in the local cache first — run `fetch` if needed.
- `select` fetches the part automatically if it is not already cached.
- `select`, `bom`, `status`, `deselect`, and `relabel` need project context (a `.bomi/project.yaml` in the tree).
- `status` is text-only. `bom --format json` uses a different JSON shape than most other commands.

## Quick Reference

| Command | Purpose |
|---------|---------|
| `bomi search "keyword"` | Search the live JLCPCB catalog |
| `bomi fetch CXXXXX` | Cache a specific part by LCSC code |
| `bomi query "keyword"` | Search the local cache only |
| `bomi info CXXXXX` | Show full details for one cached part |
| `bomi compare CXXXXX CYYYYY` | Compare cached parts side-by-side |
| `bomi analyze CXXXXX` | Analyze a cached datasheet with OpenRouter |
| `bomi datasheet CXXXXX --pdf --summary -o dir/` | Download PDF and write a markdown summary |
| `bomi init` | Create `.bomi/project.yaml` in the current directory |
| `bomi select CXXXXX --ref U1` | Add a BOM entry (fetches if not cached) |
| `bomi deselect U1` | Remove a BOM entry by reference |
| `bomi relabel R1 R3` | Rename a BOM reference |
| `bomi bom` | Show the full BOM with pricing and stock |
| `bomi bom --check` | Refresh BOM stock and pricing from live catalog |
| `bomi bom --format json` | Export BOM as JSON |
| `bomi status` | Show project summary with cost estimate and warnings |
| `bomi db stats` | Show local cache statistics |

## Common Flows

### Search and inspect

```bash
bomi search "buck converter 3.3V"
bomi fetch C9865
bomi info C9865
bomi compare C9865 C28023
```

### Filter by attributes

```bash
bomi search "0402 resistor" --attr "Resistance >= 10k"
bomi search "MOSFET SOT-23" --attr "Drain Source Voltage (Vdss) >= 30"
bomi query --basic-only --attr "Capacitance <= 100n"
```

Attribute operators: `>=` `<=` `>` `<` `=` `!=`.
Values support SI prefixes: `10k`, `100n`, `4.7u`.
Multiple `--attr` flags are ANDed together.

### Work in a project

```bash
cd my-project
bomi init --name "My Board" --description "Description here"

bomi select C9865 --ref U3 --qty 1 --notes "3.3V buck, chosen for low quiescent current"
bomi select C8678 --ref D3 --qty 1 --notes "catch diode"

bomi bom
bomi bom --check
bomi status
```

### Work with datasheets

```bash
bomi fetch C9865
bomi analyze C9865
bomi analyze C9865 --prompt "What is the enable pin threshold voltage?"
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

`bom --format json` is different — it uses `data` instead of `results`:

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

## Good Defaults

- Run `fetch` before `info`, `compare`, `analyze`, or `datasheet`.
- Use `query` when you want fast, offline, reproducible filtering from the local cache.
- Use `bom --check` before ordering to refresh stock and pricing from the live catalog.
- Use one reference per BOM line when possible (`R1`, `U2`, etc.).
- Add `--notes` to selections to record why a part was chosen — this context persists in the project file.
- Commit `.bomi/project.yaml` with every BOM change so decisions are tracked in git.

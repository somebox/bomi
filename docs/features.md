# Future features & ideas

This note captures **possible directions** for `bomi`. Nothing here is a roadmap or commitment; it exists so design discussions and “we talked about this once” items have a single place to live.

For what the tool does today, see the [README](../README.md) and [Agent guide](bomi-guide.md).

## Design anchors (from project intent)

- **Components first** — catalog search, BOM state in git, datasheets/analysis; not a full EDA or layout workflow.
- **EDA-agnostic** — works alongside KiCad, Altium, or other flows; project truth stays in `.bomi/project.yaml` under the same folder as the rest of the design.
- **Agent-friendly** — JSON/CSV/markdown, small CLI surface, suitable for automation (terminals, CI, coding agents).

## Under consideration

### Additional manufacturers & distributors

Today the live catalog path is **JLCPCB / LCSC**. Extending to other sources would imply:

- Separate APIs or scrapers, with clear attribution and rate limits.
- A stable notion of **part identity** across vendors (MPN, distributor SKUs, or explicit “same part” links).
- Cache/schema implications: whether `parts.db` stays one table per “provider” or a unified part model with multiple offers.

Open questions: which distributors matter most for your users (prototype vs production), and whether multi-source belongs in core `bomi` vs separate tooling.

### BOM import

**Import** could mean:

- **From EDA** — KiCad BOM CSV, Altium pick-and-place / BOM export, generic CSV with ref, MPN, LCSC, quantity, etc.
- **From spreadsheets** — reconciling designator ↔ LCSC (or MPN) columns into `select`-equivalent rows.

Challenges: mapping columns reliably, handling duplicate refs, merge vs replace semantics for `project.yaml`, and validation (missing LCSC, stale stock) after import.

### Skills (agent packaging)

[GitHub — kicad-happy](https://github.com/aklofas/kicad-happy) packages **Claude Code skills** around KiCad-centric workflows. A parallel for `bomi` might be:

- Curated **skill / plugin** bundles: prompts, short docs, and command recipes aligned with `bomi`’s CLI.
- Keeping the **CLI the contract** so skills stay thin wrappers rather than a second source of truth.

This fits the “agents drive the terminal” story without requiring `bomi` to ship inside a single vendor’s skill format only.

## Smaller or maintenance-adjacent ideas

- **Site build** — optional step to assemble shared `<nav>` / footer from one template when the static pages drift.
- **Presentation deck** — extra scenes or slides when new commands deserve a recorded walkthrough (see `demo/` and `build_site.py`).
- **Testing / fixtures** — more golden tests for table/markdown/JSON output as formatters evolve.

## Adding to this list

When you close a discussion with a concrete idea, add a short bullet here with enough context that a future reader knows *what problem* it solves, not just a feature name. Remove or move items to the real README/changelog when they ship.

# Contributing

Contributions are welcome. This document covers expectations for issues, pull requests, and code quality.

## Issues

Open an issue before starting work on any significant change. This avoids wasted effort and keeps the project moving in a coherent direction. A brief description of what you want to change and why is enough to start.

**Open an issue for:**
- Bug reports
- New features or significant changes to existing behavior
- Changes to CLI commands, output format, or data schema
- Changes to catalog search, part fetching, or caching behavior

**For small fixes** (typos, obvious bugs with clear fixes), a PR without a prior issue is fine.

## Pull Requests

- PRs are more likely to be reviewed and merged if there's been prior discussion in an issue
- Large PRs without an associated issue may be closed or left unreviewed
- All tests must pass before a PR will be considered
- CI runs against Python 3.11 and 3.12 — make sure your changes work on both
- PRs that affect CLI behavior, data schema, or architecture should update the relevant docs in `docs/`

### What counts as "affecting docs"

| Change | Docs to update |
|--------|----------------|
| New or changed CLI commands or output | `docs/bomi-guide.md`, `docs/examples.md` |
| Changes to part fetching, search, or caching | `docs/bomi-guide.md` |
| Schema changes (project.yaml, parts.db structure) | `docs/sqlite-database-guide.md` |
| API or internal architecture changes | `docs/bomi-api-internals.md` |
| New usage examples | `docs/examples.md` |

## Tests

Tests live in `tests/`. Run them with:

```bash
uv run pytest
```

New features and bug fixes are expected to include tests. PRs without tests for new behavior will be asked to add them before merging.

Some tests use recorded HTTP fixtures (via `pytest-recording`). If your change touches network calls to the JLCPCB/LCSC API, you may need to record new cassettes or update existing ones.

## Development Setup

```bash
git clone https://github.com/somebox/bomi.git
cd bomi
uv sync --dev
```

See [README.md](README.md) for full setup, configuration, and usage details.

## AI-assisted Code

AI-assisted contributions are welcome. However:

- Be transparent in your PR description about how the code was written (e.g. "generated with X, reviewed manually", "AI-drafted, tested and edited")
- All AI-generated code is held to the same quality and test standards as hand-written code

**Docs and issues should be human-written and reviewed.**

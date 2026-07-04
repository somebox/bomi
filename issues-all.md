# Technical Debt / Housekeeping Findings — Bomi Project

This file records the findings from a focused housekeeping review of the
`bomi` source tree.  Scope: all packages under `src/bomi/` plus top-level
scripts and tests.  No code was changed; this is a structured inventory.

## Summary

| Category                 | Count | Notes                                       |
|--------------------------|-------|---------------------------------------------|
| Undocumented debug print | 0     | No `print(`, `pdb.set_trace()`, `console.log` or `logger.debug` in production code. |
| TODO/FIXME/XXX markers   | 0     | None in Python source or tests.             |
| Redundant/duplicated helpers | 3 | Identified below.                           |
| Dead/unreachable code    | 1     | Extracted/structured analysis field not wired up. |
| Temporary/build files    | 0 tracked | `__pycache__` and `.venv` are git-ignored, not staged. |
| Other observations       | 6     | See detailed list below.                    |

---

## 1. Undocumented Debug Output

**Status: clean**

A project-wide search (`grep -R`) found zero `print(`, `pdb.set_trace()`,
`console.log()`, or `logger.debug()` calls inside `src/bomi/`.

The only `print()` calls live in non-production files:

- `tests/test_models.py` — exploratory model-comparison harness; prints are part
  of its CLI output.
- `build_site.py` and `demo/generator/*.py` — site-build scripts that report
  progress to the terminal.

No action required for production code.

---

## 2. TODO / FIXME / Dead / Temporary Markers

**Status: clean in source**

- No `TODO`, `FIXME`, `XXX`, or `HACK` markers exist in `src/bomi/` or the
  test suite.
- The single literal match from the marker search is inside a gitignore comment
  in `src/bomi/project.py:109` ("bomi datasheet CXXXXX --pdf ..."), which is
  user-facing documentation text, not a code TODO.

**Untracked / temporary files:**

- This review used `uv run pytest`, which created `.venv/` and
  `src/bomi/__pycache__/` / `tests/__pycache__/`.
- These artifacts are already listed in `.gitignore` and are **not staged**.
- No stray `*.tmp`, `*.bak`, `*~`, or `.DS_Store` files were found.

---

## 3. Redundant / Duplicated Helper Functions

### 3.1 PDF download logic is duplicated

- **Primary implementation:** `src/bomi/analysis.py:58` — `download_pdf()`
  with URL resolution, fallback, and user-agent handling.
- **Duplicate implementation:** `tests/test_models.py:59` — `download_pdf()`
  re-implements the same LCSC URL regex fallback.

**Impact:** The test harness duplicates production logic, so if the direct-PDF
URL template changes, both files must be updated.

**Recommendation:** Export or expose the core download logic from
`analysis.py` (e.g. a public `download_pdf` helper) and import it in the test
harness, or move URL resolution to a small public helper.

### 3.2 Category matching helper code is duplicated

- `src/bomi/categories.py:10` — `validate_category_for_query()`
- `src/bomi/categories.py:42` — `resolve_category_for_search()`

Both functions call `db.match_category(category)` and then:

1. look for single/exact matches,
2. check whether a resolved name is a top-level parent (has children),
3. emit a similar warning to stderr.

The shared logic is not extracted into a common helper.

**Recommendation:** Extract a `_resolve_or_suggest(db, category, require_leaf=True)`
helper that returns `(resolved_name, is_leaf, alternatives)`; then implement the
CLI-specific `raise SystemExit(1)` behavior in each wrapper.

### 3.3 BOM display code is duplicated

- `src/bomi/cli.py:827` — `_display_project_bom()` handles the `list` and
  `bom` commands.
- `src/bomi/cli.py:874` — `list_bom()` simply forwards.
- `src/bomi/cli.py:883` — `bom()` simply forwards.

This is an intentional alias implementation and is currently the cleanest way
to expose both command names.  The duplication is minimal (two one-line
function bodies), so it is **low priority**.  The alternative is Click's
`aliases=` feature, which would add complexity.

**Recommendation:** Leave as-is unless a third alias is added; then consolidate
into a single command with explicit aliases.

---

## 4. Dead / Unwired Code

### 4.1 `extracted_json` column is never populated

- `src/bomi/models.py:50` — `Analysis.extracted_json: str | None = None`
- `src/bomi/db.py:55` — `analyses.extracted_json TEXT`
- `src/bomi/db.py:240-245` — `save_analysis()` writes the field, but callers
  never set it.
- `docs/sqlite-database-guide.md:78` documents it as "Reserved for structured
  extraction".

No code path parses the LLM response into structured JSON and stores it here.
The field is effectively dead schema.

**Recommendation:** Either remove the column until structured extraction is
implemented, or add a minimal JSON extraction pass.  Keeping an empty column
increases schema weight without benefit.

---

## 5. Other Observations (Not Strictly Dead Code)

### 5.1 `_format_markdown` is unused for part lists

- `src/bomi/output.py:223` — `_format_markdown(parts)` exists, but
  `format_parts()` only calls `_format_csv`, `_format_table`, or (for
  `fmt == "markdown"`) `_format_markdown`.

Wait — it **is** used by `format_parts`.  The earlier grep confirms
`format_parts()` dispatches to it.  No issue here.

### 5.2 Cost estimation uses hard-coded token prices

- `src/bomi/analysis.py:334-338` — `_estimate_cost()` multiplies prompt and
  completion tokens by fixed rates (`0.075` and `0.30` per million).

These rates are not documented near the function and will drift when model
pricing changes.  This is a maintenance risk, not dead code.

**Recommendation:** Move rates to config or constants named
`OPENROUTER_COST_PROMPT_PER_1M` / `OPENROUTER_COST_COMPLETION_PER_1M`.

### 5.3 Cache-age literals are repeated

- `src/bomi/cli.py:197` — part fetch cache TTL hard-coded as `24` hours.
- `src/bomi/cli.py:643` — category sync cache TTL also hard-coded as `24`
  hours.

These are the same domain concept ("one day") but not shared as a constant.

**Recommendation:** Add a module-level constant, e.g.
`CACHE_TTL_HOURS = 24`, and reference it in both places.

### 5.4 `JLCPCBClient` only exposes `search()`

- `src/bomi/api.py` mentions "LCSC Detail API clients" in the module docstring,
  but only `JLCPCBClient.search()` is implemented.

This is consistent with the `docs/bomi-api-internals.md` note that detail
endpoints exist but are not used.  No action unless detail lookup is adopted.

### 5.5 Category page parser relies on minified JS structure

- `src/bomi/scrape.py:22` — `_parse_jlcpcb_categories()` uses regexes against
  a Nuxt.js IIFE.  Any upstream HTML/JS change will break it.

This is a known fragility, not dead code.  Existing tests use recorded
fixtures.

### 5.6 `units.py` has a `pass` statement after an unreachable fallback

- `src/bomi/units.py:155` — `pass` follows the string-value fallback, but is
  harmless.

---

## 6. File-by-File Clean/Findings Map

| File          | Debug prints | TODOs | Redundant helpers | Dead code |
|---------------|--------------|-------|-------------------|-----------|
| `api.py`      | 0            | 0     | 0                 | 0         |
| `analysis.py` | 0            | 0     | 0*                | 1 (see 4.1) |
| `categories.py`| 0           | 0     | 1 (3.2)           | 0         |
| `cli.py`      | 0            | 0     | 1 minor (3.3)     | 0         |
| `config.py`   | 0            | 0     | 0                 | 0         |
| `db.py`       | 0            | 0     | 0                 | 0         |
| `filters.py`  | 0            | 0     | 0                 | 0         |
| `models.py`   | 0            | 0     | 0                 | 0         |
| `normalize.py`| 0            | 0     | 0                 | 0         |
| `output.py`   | 0            | 0     | 0                 | 0         |
| `project.py`  | 0            | 0     | 0                 | 0         |
| `refs.py`     | 0            | 0     | 0                 | 0         |
| `scrape.py`   | 0            | 0     | 0                 | 0         |
| `search.py`   | 0            | 0     | 0                 | 0         |
| `units.py`    | 0            | 0     | 0                 | 0         |
| `__init__.py` | 0            | 0     | 0                 | 0         |

*Potential external duplication: `tests/test_models.py` duplicates PDF download
logic from `analysis.py`.

---

## 7. Recommended Next Steps (Prioritised)

1. **Low effort / high consistency:** extract a shared `CACHE_TTL_HOURS`
   constant in `cli.py`.
2. **Low effort / high consistency:** document or externalize the hard-coded
   OpenRouter cost factors in `analysis.py`.
3. **Medium effort:** unify the category-matching logic in `categories.py`
   into one internal helper.
4. **Medium effort:** decide the fate of `extracted_json` — implement
   structured extraction or drop the column.
5. **Low effort / test hygiene:** make `tests/test_models.py` reuse the
   production `download_pdf` helper instead of re-implementing it.


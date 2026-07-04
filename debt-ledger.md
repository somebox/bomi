# Project Technical-Debt Ledger — Bomi

> **Purpose.** A single, canonical registry of technical-debt items in the
> `bomi` repository. Each entry is normalized with a stable ID, category,
> severity, locations, the cross-referenced *pattern* it belongs to, and a
> recommendation. New items should be appended with the next free ID.

**Sources cross-referenced:** `inventory.md` (file-layout & review-area
partition) and `issues-all.md` (housekeeping findings). Both were read in
full; line references below were re-verified against source at ledger-creation
time.

**Convention.** Severity is `low` / `medium` / `high`. Status is `open`
(unaddressed), `decided` (a deliberate choice was made to leave it), or
`resolved` (no longer applies). Effort is a coarse `S` / `M` / `L` estimate.

---

## Cross-Reference Summary: Recurring Patterns

Before the per-item ledger, the following *patterns* recur across multiple
items and are the most useful lens for triage:

| Pattern | Items | Synthesis |
|---|---|---|
| **Repeated hard-coded literals** | DEBT-002, DEBT-003 | The same domain concept ("one day", "OpenRouter unit price") is inlined at each call site instead of named. Cheap to fix; high consistency payoff. |
| **Duplicated helpers** | DEBT-004, DEBT-005, DEBT-006 | Three independent duplications: production↔test (PDF download), within-file (category matching), and across-commands (BOM aliases). The first two are real maintenance risk; the third is intentional and low-priority. |
| **Half-finished / unwired scaffolding** | DEBT-007 | The `extracted_json` column is the only item in this pattern, but it is the clearest "scaffolded then abandoned" signal in the tree — schema, persistence, and docs all exist for a feature that has no producer. |
| **Fragile external coupling** | DEBT-008 | The category-page parser regexes against a minified Nuxt.js IIFE. Not strictly debt (it works, with fixtures), but flagged here because it shares the "single point of silent breakage" shape with the duplication items. |
| **Repeated debug logging** | *(none)* | Cross-check: both source documents report **zero** `print`, `pdb`, `logger.debug`, or `console.log` calls in production code (`issues-all.md` §1; `inventory.md` Found Markers). **No debt item created** — the pattern is clean. The only `print()` calls are in `tests/test_models.py`, `build_site.py`, and `demo/generator/*.py`, which is acceptable for CLI/script output. |
| **Half-finished error handling** | DEBT-009 | The `units.py` `pass` after a `ValueError` fallback is the closest analogue. It is harmless and reachable as a no-op terminal branch; documented for completeness only. |

---

## Debt Items

### DEBT-001 — No `TODO`/`FIXME`/`XXX`/`HACK` markers in source
- **Category:** marker hygiene
- **Severity:** low
- **Status:** decided (clean — no action)
- **Locations:** none in `src/bomi/` or tests
- **Cross-ref:** `inventory.md` "Found Markers"; `issues-all.md` §2
- **Notes:** A project-wide search found zero code markers. The only literal
  match is `src/bomi/project.py:109`, which is user-facing documentation text
  (`bomi datasheet CXXXXX --pdf ...`) inside a gitignore comment — not a code
  marker. No item to act on; recorded so future audits have a baseline.

---

### DEBT-002 — Cache TTL `24` hours hard-coded in two places
- **Category:** repeated hard-coded literal
- **Severity:** low
- **Status:** open
- **Effort:** S
- **Locations:**
  - `src/bomi/cli.py:197` — part-fetch cache TTL (`if age is not None and age < 24:`)
  - `src/bomi/cli.py:643` — category-sync cache TTL (`if age_hours < 24:`)
- **Cross-ref:** `issues-all.md` §5.3; review Area 4 (Utilities) in
  `inventory.md`
- **Pattern:** Same domain concept ("one day") inlined twice; if one drifts,
  behavior silently diverges.
- **Recommendation:** Add a module-level constant
  `CACHE_TTL_HOURS = 24` in `cli.py` (or in `config.py` if it should be
  tunable) and reference it from both sites. Pair with DEBT-003 since both are
  "named constant" cleanups.

---

### DEBT-003 — OpenRouter token prices hard-coded & undocumented
- **Category:** repeated hard-coded literal
- **Severity:** low
- **Status:** open
- **Effort:** S
- **Locations:**
  - `src/bomi/analysis.py:334-338` — `_estimate_cost()` returns
    `(prompt_tokens * 0.075 + completion_tokens * 0.30) / 1_000_000`
- **Cross-ref:** `issues-all.md` §5.2; review Area 1 (API/Scraper/Analysis
  Core) in `inventory.md`
- **Pattern:** Magic numbers without a named constant or a comment near the
  function. Pricing will drift as models change; there is no single source of
  truth.
- **Recommendation:** Promote to named constants
  `OPENROUTER_COST_PROMPT_PER_1M` / `OPENROUTER_COST_COMPLETION_PER_1M`, with
  a short comment naming the model the rates were calibrated against and the
  date. Consider moving to `config.py` if pricing is expected to vary per run.

---

### DEBT-004 — PDF download logic duplicated (production ↔ test)
- **Category:** duplicated helper
- **Severity:** medium
- **Status:** open
- **Effort:** S
- **Locations:**
  - `src/bomi/analysis.py:58` — `download_pdf()` with URL resolution, fallback,
    user-agent handling (production)
  - `tests/test_models.py:59` — `download_pdf()` re-implements the LCSC URL
    regex fallback (test harness)
- **Cross-ref:** `issues-all.md` §3.1; the file-by-file map at `issues-all.md`
  §6 (analysis.py row footnote)
- **Pattern:** Production↔test duplication. If the direct-PDF URL template
  changes, both files must be updated in lockstep or the test silently
  exercises a stale path.
- **Recommendation:** Expose the production `download_pdf` (or a smaller
  `_resolve_pdf_url` helper) as importable from `analysis.py`, and have the
  test harness import it. Keep test-only concerns (mocking the HTTP layer) in
  the test, not the URL logic.

---

### DEBT-005 — Category-matching logic duplicated within `categories.py`
- **Category:** duplicated helper
- **Severity:** medium
- **Status:** open
- **Effort:** M
- **Locations:**
  - `src/bomi/categories.py:10` — `validate_category_for_query()`
  - `src/bomi/categories.py:42` — `resolve_category_for_search()`
  - Both call `db.match_category(category)` and then perform:
    (1) single/exact-match detection, (2) top-level-parent (has-children)
    check, (3) a "similar" warning to stderr.
- **Cross-ref:** `issues-all.md` §3.2; review Area 3 (Data Store & Models) in
  `inventory.md`
- **Pattern:** Within-file duplication of a three-step resolve-and-suggest
  flow. The two wrappers differ only in their terminal behavior
  (`SystemExit(1)` vs. return-with-warning).
- **Recommendation:** Extract
  `_resolve_or_suggest(db, category, require_leaf=True) ->
  (resolved_name, is_leaf, alternatives)`; keep the CLI-specific
  `raise SystemExit(1)` in each public wrapper.

---

### DEBT-006 — BOM `list`/`bom` commands are alias forwards
- **Category:** duplicated helper
- **Severity:** low
- **Status:** decided (intentional, low priority)
- **Effort:** S
- **Locations:**
  - `src/bomi/cli.py:827` — `_display_project_bom()` (real implementation)
  - `src/bomi/cli.py:874` — `list_bom()` forwards
  - `src/bomi/cli.py:883` — `bom()` forwards
- **Cross-ref:** `issues-all.md` §3.3
- **Pattern:** Three functions where two are one-line forwards. Currently the
  cleanest way to expose both command names; Click's `aliases=` would add
  complexity.
- **Recommendation:** Leave as-is. Consolidate into a single command with
  explicit aliases **only if** a third alias is added — otherwise the
  cure is worse than the disease. Recorded so this is a deliberate, not
  accidental, choice.

---

### DEBT-007 — `extracted_json` column is scaffolded but never populated
- **Category:** half-finished / unwired scaffolding
- **Severity:** medium
- **Status:** resolved — decision (b) taken: dropped. Removed
  `Analysis.extracted_json` (`models.py`), the `extracted_json` column from
  the `analyses` schema and from `save_analysis`/`get_analyses` (`db.py`),
  and the docs entry (`docs/sqlite-database-guide.md`). Existing on-disk
  databases created before this change keep the legacy column (SQLite
  doesn't retroactively alter existing tables), but it is no longer read or
  written — verified backward-compatible against a simulated pre-existing
  DB with the column present.
- **Effort:** M (S to remove; the decision itself was the real cost)
- **Former locations:**
  - `src/bomi/models.py` — `Analysis.extracted_json: str | None = None`
  - `src/bomi/db.py` — `analyses.extracted_json TEXT` (schema),
    `save_analysis()` / `get_analyses()`
  - `docs/sqlite-database-guide.md` — documented it as "Reserved for
    structured extraction"
- **Cross-ref:** `issues-all.md` §4.1; review Area 3 (Data Store & Models) in
  `inventory.md`
- **Rationale:** No code path ever populated the column, and nothing in the
  current roadmap calls for LLM-structured-extraction output; keeping a
  permanently-NULL column with a "reserved for" doc note misled readers into
  thinking the feature existed. If/when structured extraction is actually
  built, re-add the column at that point, fully wired (schema + producer in
  the same change), rather than resurrecting a dormant placeholder.

---

### DEBT-008 — Category-page parser regexes against minified Nuxt.js IIFE
- **Category:** fragile external coupling
- **Severity:** medium
- **Status:** decided (known fragility, fixture-backed)
- **Effort:** L
- **Locations:**
  - `src/bomi/scrape.py:22` — `_parse_jlcpcb_categories()` uses regexes
    against a Nuxt.js IIFE
- **Cross-ref:** `issues-all.md` §5.5; review Area 1 (API/Scraper/Analysis
  Core) in `inventory.md`; `docs/bomi-api-internals.md`
- **Pattern:** Single point of silent breakage — any upstream HTML/JS change
  from JLCPCB breaks parsing with no in-process signal. Mitigated by recorded
  fixtures, so failures surface in CI rather than in prod runs.
- **Recommendation:** No immediate action. Track as a known risk; if category
  sync starts failing, this is the first place to look. If detail-endpoint
  adoption (DEBT-010) proceeds, consider switching category enumeration to a
  more stable source.

---

### DEBT-009 — `units.py` has a `pass` after a `ValueError` fallback
- **Category:** minor unreachable / no-op branch
- **Severity:** low
- **Status:** decided (harmless)
- **Effort:** S
- **Locations:**
  - `src/bomi/units.py:155` — `pass` follows the string-value fallback
- **Cross-ref:** `issues-all.md` §5.6; review Area 4 (Utilities & Filters) in
  `inventory.md`
- **Pattern:** Closest analogue to "half-finished error handling" in the
  tree — a terminal `pass` that reads as a placeholder. It is actually
  reachable and harmless (the surrounding control flow falls through to the
  string-value branch below it).
- **Recommendation:** Optional cleanup only. If touched for another reason,
  remove the redundant `pass` or replace with an explicit comment. Not worth
  a dedicated commit.

---

### DEBT-010 — `JLCPCBClient` only exposes `search()` despite detail-API docstring
- **Category:** documented-but-unimplemented surface
- **Severity:** low
- **Status:** decided (consistent with docs)
- **Effort:** L
- **Locations:**
  - `src/bomi/api.py` module docstring mentions "LCSC Detail API clients"
  - Only `JLCPCBClient.search()` is implemented
- **Cross-ref:** `issues-all.md` §5.4; `docs/bomi-api-internals.md`
- **Pattern:** Docstring advertises a surface that the module does not
  provide. Not dead code — the search client is used — but the docstring is
  aspirational.
- **Recommendation:** Either trim the docstring to match the implemented
  surface, or add a `# TODO: detail client` marker (the project currently has
  zero such markers, so this would be a deliberate exception). No action
  unless detail lookup is adopted.

---

## Priority Triage

Ordered by effort-to-consistency payoff, mirroring `issues-all.md` §7 but
normalized to this ledger's IDs. **Status as of this pass: DEBT-002 through
DEBT-005 and DEBT-007 are resolved** (see entries above); remaining items
are deliberate no-actions or tracked risks.

1. ~~**DEBT-002** (S) — extract `CACHE_TTL_HOURS`.~~ Resolved.
2. ~~**DEBT-003** (S→M) — real/live cost accounting, superseding the
   original "name the constants" recommendation.~~ Resolved.
3. ~~**DEBT-004** (S) — have `tests/test_models.py` import the production
   `download_pdf` helper.~~ Resolved.
4. ~~**DEBT-005** (M) — unify category-matching in `categories.py`.~~
   Resolved.
5. ~~**DEBT-007** (M) — decide the fate of `extracted_json`.~~ Resolved:
   decision (b), column dropped.
6. **DEBT-008 / DEBT-010** (L) — leave open as tracked risks; revisit if
   detail-endpoint adoption or category-sync breakage forces it.
7. **DEBT-001 / DEBT-006 / DEBT-009** — no action; recorded as deliberate.

All resolved items were additionally verified live against a real project
([somebox/rgb-spotlight](https://github.com/somebox/rgb-spotlight), which
is set up to use bomi): live JLCPCB category sync, part fetch/cache,
category resolution (ambiguous and leaf-match paths), a real LCSC datasheet
PDF download, and OpenRouter's live `/models` pricing endpoint (340 models)
with DB-cached fallback cost resolution. The one path not exercised live
was OpenRouter's actual billed `usage.cost` on a real chat completion,
since no OpenRouter API key was available in the review sandbox — recommend
a follow-up live run with a real key before considering DEBT-003 fully
closed end-to-end.

---

## Items Considered But Not Created

- **Repeated debug logging:** both source documents report zero debug
  output in production code. No debt item — the pattern is clean.
- **Stray temporary/build files:** `issues-all.md` §2 confirms
  `__pycache__/`, `.venv/` are git-ignored and not staged; no `.tmp`,
  `.bak`, `*~`, or `.DS_Store` found. `inventory.md` "Unstaged or Untracked
  Files" independently confirms a clean working tree. No debt item.
- **`_format_markdown` unused:** `issues-all.md` §5.1 initially suspected
  this but self-corrected — `format_parts()` does dispatch to it. No debt
  item.

# Review Issue List

This file captures the follow-up work found during a documentation, test, and design review of the current repository. It is meant to be turned into a concrete implementation plan later.

## High Priority

### 1. Normalize CLI failure handling

- `search`, `fetch`, `select`, `bom --check`, `analyze`, and `datasheet` can surface raw network exceptions instead of stable CLI errors.
- Goal: convert transport and API failures into clear user-facing messages with non-zero exits.
- Suggested next step: add a small error-handling layer around JLCPCB and OpenRouter calls.

### 2. Remove or implement dead CLI surfaces

- `fetch --detail` is exposed but does not change behavior.
- `JLCPCBClient.fetch_detail()` exists but is not used by the CLI.
- `analysis.analyze_part(method=...)` accepts a method argument but always stores `openrouter`.
- Goal: either implement these surfaces or remove them from the public interface.

### 3. Unify filter validation

- `query --attr` rejects invalid filters.
- `search --attr` silently ignores invalid filters after the live API call.
- Goal: invalid filters should fail fast and behave the same in live and local workflows.

### 4. Split `cli.py` into smaller modules

- `src/jlcpcb_tool/cli.py` currently mixes command definitions, fetch logic, formatting, BOM markdown generation, and some business rules.
- Goal: separate commands, services, and renderers so behavior is easier to test and change.

## Medium Priority

### 5. Fix BOM markdown anchor behavior

- Summary table links point at anchors that are not actually emitted in the detail sections.
- Goal: make markdown exports navigable and predictable.

### 6. Decide how reference ranges should work

- The CLI accepts range-like refs such as `U2-U4`, but most sorting, validation, relabeling, and markdown behavior treats refs as plain strings.
- Goal: either support structured ref ranges properly or document and enforce a simpler one-ref-per-entry model.

### 7. Reduce duplicated filtering and rendering logic

- Filtering logic is split across `cli.py`, `search.py`, and `db.py`.
- Formatting logic is split between `output.py` and BOM-specific helpers in `cli.py`.
- Goal: move shared behavior into one parsing/filter layer and one rendering layer.

### 8. Avoid N+1 lookups in `Database.query_parts()`

- `query_parts()` selects matching `lcsc_code` values and then calls `get_part()` for each match.
- Goal: reduce query count and simplify the return path.

### 9. Clarify cache freshness and exact-part fetch behavior

- `fetch` currently resolves exact parts through the search endpoint rather than the detail endpoint.
- Goal: decide whether exact fetches should remain search-based or use a dedicated detail flow.

## Low Priority

### 10. Rename or move `test_models.py`

- `test_models.py` is a manual benchmark script, not part of the pytest suite.
- Goal: move it under a clearer location such as `scripts/` or rename it to reflect its purpose.

## Test Gaps

### 11. Add CLI workflow coverage

- Missing or thin coverage for:
- `fetch`
- `analyze`
- `datasheet`
- `bom --check`
- BOM markdown rendering
- Goal: cover the main user workflows, not just the smaller helpers.

### 12. Add failure-path tests

- Missing tests for:
- network errors
- malformed API payloads
- malformed OpenRouter responses
- YAML parse failures
- datasheet download failures
- Goal: make error handling safe to refactor.

### 13. Add tests for the current no-op or edge surfaces

- Add tests that would catch:
- `fetch --detail` doing nothing
- broken markdown anchors
- ambiguous or overlapping ref inputs
- Goal: stop these behaviors from drifting silently.

### 14. Repair the recorded API integration test

- `tests/test_api.py::TestJLCPCBClient::test_search_live` currently fails because the VCR cassette no longer matches the request/response shape being produced.
- Goal: either refresh the cassette intentionally or adjust the matching setup so this test remains useful and reproducible.

## Documentation Follow-Up

### 15. Keep implementation notes separate from user docs

- User-facing docs are now closer to the current implementation, but design-history notes still live beside operational docs.
- Goal: keep `README.md` and user docs focused on current behavior, and move planning/history material into a clearly marked area if it grows further.

# JLCPCB API Notes For This Repo

This file documents the HTTP surfaces and external services used by the current `bomi` implementation. It is not a general survey of every upstream data source around JLCPCB or LCSC.

## What The Tool Uses Today

| Area | Used by this repo | Notes |
|------|-------------------|-------|
| JLCPCB search API | Yes | Primary catalog lookup path |
| JLCPCB detail API | Partly | Client code exists, but current CLI does not rely on it |
| OpenRouter chat completions | Yes | Used for datasheet analysis and markdown summaries |
| EasyEDA APIs | No | Not used in the current implementation |
| Upstream bulk databases | No | Not used by the CLI runtime |

## JLCPCB Search API

This is the main live catalog endpoint used by `search`, and it is also the lookup path behind `fetch`, `select`, and `bom --check`.

### Endpoint

```text
POST https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList
```

### Request headers

The client sets browser-like headers and forwards an `XSRF-TOKEN` cookie as `X-XSRF-TOKEN` on later requests.

### Request body

```json
{
  "keyword": "STM32F103",
  "currentPage": 1,
  "pageSize": 25
}
```

Supported request fields in the current client:

| Field | Purpose |
|-------|---------|
| `keyword` | search text or LCSC code |
| `currentPage` | 1-based page number |
| `pageSize` | results per page |
| `componentLibraryType` | `"base"` when `basic_only=True` |
| `preferredComponentFlag` | `true` when `preferred_only=True` |
| `componentType` | subcategory name for server-side category filtering (e.g. `"Chip Resistor - Surface Mount"`) |

### Response fields used by the tool

The normalizer reads these fields from each component object:

- `componentCode`
- `componentModelEn`
- `componentBrandEn`
- `componentSpecificationEn`
- `firstSortName`
- `secondSortName`
- `describe`
- `stockCount`
- `componentLibraryType`
- `preferredComponentFlag`
- `componentPrices`
- `attributes`
- `dataManualUrl`
- `urlSuffix` or `lcscGoodsUrl`

The CLI stores normalized results in `parts.db`.

## JLCPCB Detail API

The implementation currently does not call a dedicated detail endpoint in normal CLI workflows. Exact-part fetches still resolve through search + local matching.

## OpenRouter Integration

Datasheet analysis goes through OpenRouter in `src/bomi/analysis.py`.

### Endpoint

```text
POST https://openrouter.ai/api/v1/chat/completions
```

### What the tool sends

- a text prompt with part context
- a PDF as OpenRouter `file` content
- the `file-parser` plugin with a selected PDF engine

Supported PDF engines in the CLI:

- `mistral-ocr`
- `pdf-text`
- `native`

### Required config

```yaml
openrouter_api_key: sk-or-v1-...
```

Environment override:

```bash
export BOMI_OPENROUTER_API_KEY=sk-or-v1-...
```

### Large PDF handling

Large PDFs are split into chunks before upload. Each chunk is analyzed separately, then a synthesis request combines the chunk summaries into one markdown response.

## JLCPCB Category Page

The `sync` command scrapes the category tree from:

```text
GET https://jlcpcb.com/parts/all-electronic-components
```

The page is a Nuxt.js app that embeds an `allPartsList` array in an IIFE. Each top-level entry has `sortName`, `componentCount`, and a `childSortList` array of subcategories with `componentSortKeyId` fields. The scraper (`src/bomi/scrape.py`) parses this structure with regex and stores the results in the `categories` and `sync_meta` tables.

Category names from this page correspond to the `componentType` API filter and the `firstSortName` / `componentTypeEn` fields in search results. Top-level parent names (e.g. "Capacitors") are not valid `componentType` values — only subcategory-level names work for API filtering.

## Python module layout (CLI implementation)

| Module | Role |
|--------|------|
| `cli.py` | Click entrypoint; orchestrates all commands. |
| `api.py` | `JLCPCBClient` — HTTP requests to the JLCPCB search API. |
| `normalize.py` | Converts raw API response objects into `Part` model instances. |
| `models.py` | Dataclasses: `Part`, `PriceBreak`, `Attribute`, `Selection`. |
| `db.py` | SQLite access; `Database` implements `__enter__` / `__exit__` for `with Database(path) as db`. |
| `search.py` | Search orchestration: calls API client, normalizes, applies filters, stores results. |
| `categories.py` | Category validation for `query`; substring resolution to exact API subcategory name for `search`. |
| `filters.py` | Shared logic for package/stock/max-price/`--attr` between post-API filtering (`apply_post_fetch_filters`) and `Database.query_parts` (via `append_attr_filter_sql`). |
| `scrape.py` | Scrapes the JLCPCB category tree page and populates the `categories` and `sync_meta` tables. |
| `analysis.py` | Datasheet analysis via OpenRouter: PDF upload, chunking, synthesis. |
| `output.py` | Part formatters; BOM JSON/CSV/markdown/table for `list` / `bom`. |
| `project.py` | Load, save, and mutate `.bomi/project.yaml` (selections, relabeling). |
| `refs.py` | Reference designator parsing and expansion (e.g. `R1-R4` → individual refs). |
| `config.py` | Config loading from `config.yaml` and env var overrides; OS data directory resolution. |
| `units.py` | SI prefix parsing and numeric value normalization for attribute filtering. |

## Implementation Boundaries

The current implementation does not do these things:

- it does not use EasyEDA endpoints
- it does not require LCSC signing credentials
- it does not use an upstream full-catalog SQLite download at runtime
- it does not provide a stable public API beyond the CLI itself

## Practical Notes

- The search API is the only live catalog source the CLI depends on today.
- The local cache is the source of truth for `query`, `info`, `compare`, and project BOM enrichment.
- Datasheet analysis depends on both a cached part entry and a working datasheet URL.
- Network failures are not handled consistently yet.

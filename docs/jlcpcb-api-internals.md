# JLCPCB API Notes For This Repo

This file documents the HTTP surfaces and external services used by the current `jlcpcb-tool` implementation. It is not a general survey of every upstream data source around JLCPCB or LCSC.

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

### OpenRouter endpoint

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

The codebase includes a client method for a detail endpoint:

```text
POST https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentDetail
```

Current status:

- `src/jlcpcb_tool/api.py` implements `fetch_detail()`
- the public CLI exposes `fetch --detail`
- the current `fetch` command does not actually use the detail endpoint yet

This means the detail API is currently a maintenance item, not a documented core workflow.

## OpenRouter Integration

Datasheet analysis goes through OpenRouter in `src/jlcpcb_tool/analysis.py`.

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
export JLCPCB_OPENROUTER_API_KEY=sk-or-v1-...
```

### Large PDF handling

Large PDFs are split into chunks before upload. Each chunk is analyzed separately, then a synthesis request combines the chunk summaries into one markdown response.

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
- Network failures are not handled consistently yet; see `docs/review-issues.md` for follow-up work.

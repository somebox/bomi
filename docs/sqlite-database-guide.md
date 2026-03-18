# Local SQLite Database Guide

This document describes the `parts.db` database used by `bomi`. It is the shared local cache for fetched parts, prices, attributes, and saved datasheet analyses.

## Location

The database is created automatically in the global data directory:

- macOS: `~/Library/Application Support/bomi/parts.db`
- Linux: `~/.local/share/bomi/parts.db`

The cache is shared across all projects.

## Schema Overview

The current schema lives in `src/bomi/db.py`.

### Table: `parts`

One row per cached LCSC part.

| Column | Type | Notes |
|--------|------|-------|
| `lcsc_code` | TEXT PK | `C8287`, `C25900`, and so on |
| `mfr_part` | TEXT | Manufacturer part number |
| `manufacturer` | TEXT | Manufacturer name |
| `package` | TEXT | Package string |
| `category` | TEXT | Top-level category |
| `subcategory` | TEXT | Subcategory |
| `description` | TEXT | Human-readable description |
| `stock` | INTEGER | Last cached stock count |
| `library_type` | TEXT | JLCPCB library type such as `base` or `expand` |
| `preferred` | INTEGER | Stored as `0` or `1` |
| `datasheet_url` | TEXT | Datasheet URL if present |
| `jlcpcb_url` | TEXT | JLCPCB part page URL if present |
| `fetched_at` | TEXT | ISO timestamp |
| `raw_json` | TEXT | Raw normalized source payload |

### Table: `prices`

Tiered pricing for each cached part.

| Column | Type | Notes |
|--------|------|-------|
| `lcsc_code` | TEXT | FK to `parts.lcsc_code` |
| `qty_from` | INTEGER | Minimum quantity for the tier |
| `qty_to` | INTEGER | Maximum quantity, nullable |
| `unit_price` | REAL | Unit price in USD |

Primary key: `(lcsc_code, qty_from)`

### Table: `attributes`

Parsed parametric attributes for each cached part.

| Column | Type | Notes |
|--------|------|-------|
| `lcsc_code` | TEXT | FK to `parts.lcsc_code` |
| `attr_name` | TEXT | Attribute name such as `Resistance` |
| `attr_value_raw` | TEXT | Original string value |
| `attr_value_num` | REAL | Parsed numeric value when available |
| `attr_unit` | TEXT | Parsed unit when available |

Primary key: `(lcsc_code, attr_name)`

### Table: `analyses`

Saved datasheet analysis results.

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Autoincrement row id |
| `lcsc_code` | TEXT | FK to `parts.lcsc_code` |
| `method` | TEXT | Current implementation stores `openrouter` |
| `model` | TEXT | OpenRouter model name |
| `prompt` | TEXT | User prompt |
| `response` | TEXT | Markdown or plain text response |
| `extracted_json` | TEXT | Reserved for structured extraction |
| `created_at` | TEXT | ISO timestamp |
| `cost_usd` | REAL | Estimated OpenRouter cost |

## Indexes

The current schema creates these indexes:

- `idx_parts_category` on `parts(category)`
- `idx_parts_package` on `parts(package)`
- `idx_parts_stock` on `parts(stock)`
- `idx_attr_name_num` on `attributes(attr_name, attr_value_num)`

## Example Queries

### Look up one part

```sql
SELECT *
FROM parts
WHERE lcsc_code = 'C8287';
```

### Show the first pricing tier

```sql
SELECT p.lcsc_code, p.mfr_part, pr.unit_price
FROM parts p
LEFT JOIN prices pr
  ON pr.lcsc_code = p.lcsc_code
WHERE p.lcsc_code = 'C8287'
  AND pr.qty_from = (
    SELECT MIN(qty_from)
    FROM prices
    WHERE lcsc_code = p.lcsc_code
  );
```

### Find in-stock basic 0402 resistors

```sql
SELECT lcsc_code, mfr_part, description, stock
FROM parts
WHERE package LIKE '%0402%'
  AND library_type = 'base'
  AND stock > 0
ORDER BY stock DESC
LIMIT 20;
```

### Filter on parsed attributes

```sql
SELECT p.lcsc_code, p.mfr_part, a.attr_value_raw
FROM parts p
JOIN attributes a ON a.lcsc_code = p.lcsc_code
WHERE a.attr_name = 'Resistance'
  AND a.attr_value_num >= 10000
ORDER BY p.stock DESC
LIMIT 20;
```

### List recent analyses

```sql
SELECT lcsc_code, method, model, created_at, cost_usd
FROM analyses
ORDER BY created_at DESC
LIMIT 20;
```

### Summary statistics

```sql
SELECT
  (SELECT COUNT(*) FROM parts) AS parts,
  (SELECT COUNT(*) FROM attributes) AS attributes,
  (SELECT COUNT(*) FROM analyses) AS analyses,
  (SELECT COUNT(DISTINCT category) FROM parts) AS categories;
```

## Using It From Python

```python
import sqlite3

db = sqlite3.connect("parts.db")
db.row_factory = sqlite3.Row

row = db.execute(
    "SELECT lcsc_code, mfr_part, manufacturer, stock FROM parts WHERE lcsc_code = ?",
    ("C8287",),
).fetchone()

if row:
    print(f"{row['lcsc_code']} {row['mfr_part']} by {row['manufacturer']}")
    print(f"Stock: {row['stock']}")
```

## Notes

- This database is a cache, not a canonical source of truth.
- `query`, `info`, `compare`, and project BOM enrichment all depend on it.
- The CLI currently loads full part objects by joining through `parts`, `prices`, and `attributes` in Python rather than through SQL views.
- See `docs/review-issues.md` for open design and performance follow-ups around query behavior.

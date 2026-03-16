# JLC PCB Parts SQLite Database Guide

This document describes the SQLite database (`cache.sqlite3`) used by jlcparts. It covers the schema, field meanings, data formats, and example queries. This is intended as a reference for querying the database directly for offline analysis.

## Getting the Database

The pre-built SQLite database is hosted as a split zip archive on the upstream GitHub Pages site. To download and reassemble it:

```bash
# Download all split volumes (each is 50 MB)
for i in $(seq -w 01 18); do
  wget -q "https://yaqwsx.github.io/jlcparts/data/cache.z$i"
done
wget -q "https://yaqwsx.github.io/jlcparts/data/cache.zip"

# Concatenate and fix the split-zip structure
cat cache.z* cache.zip > cache-combined-bad.zip
echo -e 'z\r\n' | zip -FF cache-combined-bad.zip -O cache-combined.zip
rm cache-combined-bad.zip cache.z* cache.zip

# Extract
unzip cache-combined.zip
# Result: cache.sqlite3 (~930 MB)
```

Note: The upstream SQLite cache may be stale (months old). The processed JSONL data at `https://dougy83.github.io/jlcparts/data/all.jsonlines.tar` is rebuilt daily but is in a different format (gzip-compressed JSONL, not SQLite).

## Database Schema

The database has three tables and one convenience view.

### Table: `components`

The main table. Each row is one component from the JLC PCB catalog.

| Column | Type | Description |
|---|---|---|
| `lcsc` | INTEGER (PK) | LCSC part number as integer (e.g., `7063` for `C7063`). To get the LCSC code string, prepend `C`. |
| `category_id` | INTEGER (FK) | References `categories.id`. |
| `mfr` | TEXT | Manufacturer's part number (e.g., `RC0402FR-0710KL`). |
| `package` | TEXT | Package type (e.g., `0402`, `SOT-23`, `SOIC-8`). |
| `joints` | INTEGER | Number of solder joints (pads) for the component. |
| `manufacturer_id` | INTEGER (FK) | References `manufacturers.id`. |
| `basic` | INTEGER | `1` if this is a JLC PCB "basic" part (no extra fee), `0` if "extended". |
| `preferred` | INTEGER | `1` if this is a JLC PCB "preferred" part, `0` otherwise. |
| `description` | TEXT | Short text description of the component. |
| `datasheet` | TEXT | URL to the component's datasheet (PDF). |
| `stock` | INTEGER | Current stock quantity at JLC PCB. |
| `price` | TEXT | JSON string encoding tiered pricing (see [Price Format](#price-format)). |
| `last_update` | INTEGER | Unix timestamp of when this component was last fetched/updated. |
| `extra` | TEXT | JSON string with extended data from LCSC API (see [Extra Field](#extra-field)). |
| `flag` | INTEGER | Internal processing flag (used during database updates, not useful for analysis). |
| `last_on_stock` | INTEGER | Unix timestamp of when the component was last known to be in stock. `0` if never recorded. |

### Table: `categories`

Lookup table for component categories.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER (PK) | Category ID. |
| `category` | TEXT | Top-level category name (e.g., `Resistors`, `Capacitors`, `Integrated Circuits (ICs)`). |
| `subcategory` | TEXT | Subcategory name (e.g., `Chip Resistor - Surface Mount`, `Multilayer Ceramic Capacitors MLCC`). |

### Table: `manufacturers`

Lookup table for manufacturer names.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER (PK) | Manufacturer ID. |
| `name` | TEXT | Manufacturer name (e.g., `YAGEO`, `Samsung Electro-Mechanics`, `Texas Instruments`). |

### View: `v_components`

A pre-joined view that resolves the foreign keys, making queries simpler. Returns all useful fields with human-readable category and manufacturer names.

| Column | Source |
|---|---|
| `lcsc` | `components.lcsc` (integer, prepend `C` for the LCSC code) |
| `category_id` | `components.category_id` |
| `category` | `categories.category` |
| `subcategory` | `categories.subcategory` |
| `mfr` | `components.mfr` |
| `package` | `components.package` |
| `joints` | `components.joints` |
| `manufacturer` | `manufacturers.name` |
| `basic` | `components.basic` |
| `preferred` | `components.preferred` |
| `description` | `components.description` |
| `datasheet` | `components.datasheet` |
| `stock` | `components.stock` |
| `last_on_stock` | `components.last_on_stock` |
| `price` | `components.price` (JSON string) |
| `extra` | `components.extra` (JSON string) |

## Data Formats

### Price Format

The `price` column is a JSON array of price tiers. Each tier is an object:

```json
[
  {"qFrom": 1, "qTo": 9, "price": 0.0037},
  {"qFrom": 10, "qTo": 99, "price": 0.0025},
  {"qFrom": 100, "qTo": 499, "price": 0.0019},
  {"qFrom": 500, "qTo": null, "price": 0.0016}
]
```

- `qFrom`: minimum order quantity for this tier
- `qTo`: maximum order quantity (`null` means unlimited)
- `price`: unit price in USD

### Extra Field

The `extra` column is a JSON string containing extended component data fetched from the LCSC API. It can be an empty object `{}` (meaning LCSC had no data, often for discontinued parts) or a rich object. Common keys include:

| Key | Type | Description |
|---|---|---|
| `attributes` | object | Key-value pairs of component parameters (e.g., `"Resistance": "10kΩ"`, `"Capacitance": "100nF"`). This is the most useful field for parametric analysis. |
| `images` | array | Product images from LCSC. |
| `url` | string | Full LCSC product page URL. |
| `datasheet` | string | Datasheet URL (from LCSC, may differ from JLC PCB's). |
| `manufacturer` | object | `{"name": "YAGEO"}` |
| `number` | string | LCSC product number. |
| `title` | string | Product title from LCSC. |
| `prices` | array | LCSC pricing (may differ from JLC PCB pricing). |

The `attributes` object varies by component type. Common attribute keys:

- **Resistors**: `Resistance`, `Power`, `Tolerance`
- **Capacitors**: `Capacitance`, `Allowable Voltage`, `Tolerance`
- **Inductors**: `Inductance`, `Rated current`, `DC Resistance`
- **MOSFETs**: `Drain Source Voltage (Vdss)`, `Continuous Drain Current (Id)`, `Rds On (Max) @ Id, Vgs`
- **ICs**: `Supply Voltage (Max)`, `Supply Voltage (Min)`, `Operating Temperature (Max/Min)`
- **General**: `Package`, `Basic/Extended`, `Status`, `Manufacturer`

### LCSC Code Conversion

The `lcsc` column stores the numeric part only. To convert:
- **Database to display**: prepend `C` to the integer (e.g., `7063` becomes `C7063`)
- **Display to query**: strip the `C` prefix and cast to integer

## Example Queries

### Basic lookups

```sql
-- Count total components
SELECT COUNT(*) FROM components;

-- Look up a specific part by LCSC code (e.g., C7063)
SELECT * FROM v_components WHERE lcsc = 7063;

-- List all categories and subcategories
SELECT category, subcategory, COUNT(*) as part_count
FROM v_components
GROUP BY category, subcategory
ORDER BY category, subcategory;
```

### Filtering by category and stock

```sql
-- All in-stock 0402 chip resistors
SELECT 'C' || lcsc AS lcsc_code, mfr, description, stock, price
FROM v_components
WHERE subcategory = 'Chip Resistor - Surface Mount'
  AND package = '0402'
  AND stock > 0
ORDER BY stock DESC;

-- Basic parts only (no extra assembly fee)
SELECT 'C' || lcsc AS lcsc_code, category, subcategory, mfr, description
FROM v_components
WHERE basic = 1
  AND stock > 0;

-- Preferred parts (JLC PCB preferred, subset of basic)
SELECT 'C' || lcsc AS lcsc_code, mfr, description, stock
FROM v_components
WHERE preferred = 1
  AND stock > 0
ORDER BY category, subcategory;
```

### Working with JSON fields

SQLite's `json_extract()` function can query the JSON columns directly.

```sql
-- Get the unit price at qty 1 for a part
SELECT 'C' || lcsc AS lcsc_code, mfr,
       json_extract(price, '$[0].price') AS unit_price
FROM v_components
WHERE lcsc = 7063;

-- Find 10kΩ resistors using the extra.attributes field
SELECT 'C' || lcsc AS lcsc_code, mfr, package, stock,
       json_extract(extra, '$.attributes.Resistance') AS resistance
FROM v_components
WHERE subcategory = 'Chip Resistor - Surface Mount'
  AND json_extract(extra, '$.attributes.Resistance') LIKE '%10k%'
  AND stock > 0
ORDER BY stock DESC
LIMIT 20;

-- Find capacitors rated above a certain voltage
SELECT 'C' || lcsc AS lcsc_code, mfr, description, package, stock
FROM v_components
WHERE category = 'Capacitors'
  AND json_extract(extra, '$.attributes') IS NOT NULL
  AND stock > 0
LIMIT 50;
```

### Price analysis

```sql
-- Cheapest basic parts by unit price (qty 1), in stock
SELECT 'C' || lcsc AS lcsc_code, category, subcategory, mfr, description,
       json_extract(price, '$[0].price') AS unit_price,
       stock
FROM v_components
WHERE basic = 1
  AND stock > 0
  AND json_extract(price, '$[0].price') IS NOT NULL
ORDER BY CAST(json_extract(price, '$[0].price') AS REAL) ASC
LIMIT 50;

-- Parts with deepest volume discount
SELECT 'C' || lcsc AS lcsc_code, mfr, description,
       json_extract(price, '$[0].price') AS price_qty1,
       json_extract(price, '$[-1].price') AS price_bulk,
       ROUND(json_extract(price, '$[0].price') / json_extract(price, '$[-1].price'), 2) AS discount_ratio
FROM v_components
WHERE stock > 0
  AND json_extract(price, '$[0].price') > 0
  AND json_extract(price, '$[-1].price') > 0
ORDER BY discount_ratio DESC
LIMIT 20;
```

### Staleness and update tracking

```sql
-- When was the database last updated?
SELECT datetime(MAX(last_update), 'unixepoch') AS newest_update,
       datetime(MIN(last_update), 'unixepoch') AS oldest_update
FROM components;

-- Components that have been out of stock for a long time
SELECT 'C' || lcsc AS lcsc_code, mfr, description, stock,
       datetime(last_on_stock, 'unixepoch') AS last_in_stock
FROM v_components
WHERE stock = 0
  AND last_on_stock > 0
ORDER BY last_on_stock ASC
LIMIT 20;
```

### Summary statistics

```sql
-- Parts per top-level category
SELECT category, COUNT(*) AS total,
       SUM(CASE WHEN stock > 0 THEN 1 ELSE 0 END) AS in_stock,
       SUM(CASE WHEN basic = 1 THEN 1 ELSE 0 END) AS basic_parts
FROM v_components
GROUP BY category
ORDER BY total DESC;

-- Manufacturer market share (by number of listed parts)
SELECT manufacturer, COUNT(*) AS parts
FROM v_components
GROUP BY manufacturer
ORDER BY parts DESC
LIMIT 30;
```

## Using with Python

```python
import sqlite3
import json

db = sqlite3.connect("cache.sqlite3")
db.row_factory = sqlite3.Row

# Query a specific part
row = db.execute("SELECT * FROM v_components WHERE lcsc = ?", (7063,)).fetchone()
print(f"C{row['lcsc']}: {row['mfr']} - {row['description']}")
print(f"  Category: {row['category']} > {row['subcategory']}")
print(f"  Stock: {row['stock']}, Basic: {bool(row['basic'])}")
print(f"  Price tiers: {json.loads(row['price'])}")

extra = json.loads(row["extra"])
if "attributes" in extra:
    for key, val in extra["attributes"].items():
        print(f"  {key}: {val}")

# Bulk analysis example: export all in-stock basic resistors to CSV
import csv
cursor = db.execute("""
    SELECT 'C' || lcsc AS lcsc, mfr, package, description, stock, price, extra
    FROM v_components
    WHERE subcategory = 'Chip Resistor - Surface Mount'
      AND basic = 1 AND stock > 0
""")
with open("basic_resistors.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["LCSC", "MFR Part", "Package", "Description", "Stock", "Price_Qty1"])
    for row in cursor:
        prices = json.loads(row["price"])
        price1 = prices[0]["price"] if prices else None
        writer.writerow([row["lcsc"], row["mfr"], row["package"],
                         row["description"], row["stock"], price1])
```

## Indexes

The database has two indexes for faster queries:
- `components_category` on `components.category_id` -- speeds up category-based filtering
- `components_manufacturer` on `components.manufacturer_id` -- speeds up manufacturer lookups

For best performance when doing full-text searches on `description` or `mfr`, consider creating additional indexes or using SQLite FTS5.

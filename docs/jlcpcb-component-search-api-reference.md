# JLC PCB Component Data: API Reference for Agent-Based Tools

This document describes the available APIs and data sources for building automated tools that search, filter, and analyze JLC PCB's electronic component catalog (~7.1 million parts). It is intended for developers building AI agent integrations, MCP servers, or programmatic component selection tools.

## Data Sources Overview

| Source | Auth Required | Data Freshness | Best For |
|--------|--------------|----------------|----------|
| JLCPCB Search API | No | Real-time | On-demand search, filtering, pricing, stock |
| LCSC Product API | No | Real-time | Detailed attributes for a known part |
| EasyEDA API | No | Real-time | Schematic symbols, footprints, 3D models |
| SQLite Database (upstream) | No | Stale (Nov 2025) | Bulk offline analysis of full catalog |
| Processed JSONL (fork) | No | Daily rebuild | Browser-based frontend |

---

## 1. JLCPCB Search API (Primary)

The main catalog search endpoint. This is the same API the jlcpcb.com website uses. No authentication or API keys required.

### Endpoint

```
POST https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList
```

### Required Headers

```
Content-Type: application/json
Origin: https://jlcpcb.com
Referer: https://jlcpcb.com/parts
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36
```

### Request Body

```json
{
  "keyword": "STM32F103",
  "currentPage": 1,
  "pageSize": 25
}
```

#### Supported Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `keyword` | string | Yes | Search query. Supports part numbers, descriptions, values (e.g., `"10k 0402"`, `"STM32F103"`, `"LDO 3.3V"`). Empty string returns all parts. |
| `currentPage` | int | Yes | Page number (1-indexed). |
| `pageSize` | int | Yes | Results per page (max observed: 100). |
| `componentLibraryType` | string | No | Filter by part type: `"base"` (basic, no extra fee), `"expand"` (extended). Omit for all. |
| `preferredComponentFlag` | bool | No | Set `true` to return only JLC PCB preferred parts. |

### Response Structure

```json
{
  "code": 200,
  "data": {
    "componentPageInfo": {
      "total": 179,
      "pages": 18,
      "hasNextPage": true,
      "list": [ /* array of component objects */ ]
    }
  }
}
```

### Component Object Fields

| Field | Type | Description |
|-------|------|-------------|
| `componentCode` | string | LCSC part number (e.g., `"C8287"`). The primary identifier. |
| `componentModelEn` | string | Manufacturer part number (e.g., `"STM32F103ZET6"`). |
| `componentBrandEn` | string | Manufacturer name. |
| `componentSpecificationEn` | string | Package (e.g., `"LQFP-144"`, `"0402"`). |
| `componentTypeEn` | string | Subcategory (e.g., `"Microcontrollers (MCU/MPU/SOC)"`). |
| `firstSortName` | string | Subcategory name (same as componentTypeEn in most cases). |
| `secondSortName` | string | Top-level category (e.g., `"Embedded Processors & Controllers"`). |
| `componentLibraryType` | string | `"base"` (basic) or `"expand"` (extended). |
| `preferredComponentFlag` | bool | Whether this is a JLC PCB preferred part. |
| `stockCount` | int | Current stock at JLC PCB. |
| `describe` | string | Full description string (e.g., `"-55℃~+155℃ 10kΩ 50V 62.5mW Thick Film Resistor ±1% ±200ppm/℃ 0402 Chip Resistor - Surface Mount ROHS"`). |
| `componentPrices` | array | SMT assembly pricing tiers (see below). |
| `attributes` | array | Structured parametric attributes (see below). |
| `dataManualUrl` | string\|null | Datasheet URL. |
| `lcscGoodsUrl` | string\|null | LCSC product page URL. |
| `urlSuffix` | string | URL slug for constructing `https://jlcpcb.com/partdetail/{urlSuffix}`. |
| `leastPatchNumber` | int | Minimum placement quantity for SMT. |
| `lossNumber` | int | Attrition/waste parts added per placement. |
| `minPurchaseNum` | int | Minimum purchase quantity. |

### Pricing Tiers

```json
"componentPrices": [
  {"startNumber": 1, "endNumber": 9, "productPrice": 6.7509},
  {"startNumber": 10, "endNumber": 29, "productPrice": 6.0611},
  {"startNumber": 30, "endNumber": 99, "productPrice": 5.6192},
  {"startNumber": 100, "endNumber": -1, "productPrice": 5.193}
]
```

- `endNumber: -1` means unlimited (highest tier).
- Prices are in USD.

### Structured Attributes

The `attributes` array contains parsed parametric data. Each entry:

```json
{
  "attribute_name_en": "Resistance",
  "attribute_value_name": "10kΩ"
}
```

Common attribute names by component type:

| Component Type | Common Attributes |
|---------------|-------------------|
| Resistors | `Resistance`, `Power(Watts)`, `Tolerance`, `Temperature Coefficient`, `Type` |
| Capacitors | `Capacitance`, `Voltage Rated`, `Tolerance`, `Temperature Coefficient`, `Dielectric Material` |
| Inductors | `Inductance`, `Rated Current`, `DC Resistance`, `Saturation Current` |
| MOSFETs | `Drain Source Voltage (Vdss)`, `Continuous Drain Current (Id)`, `Rds On (Max)`, `Gate Threshold Voltage` |
| Linear Regulators | `Output Voltage`, `Output Current`, `Input Voltage`, `Dropout Voltage` |
| MCUs | `Program Memory Size`, `RAM Size`, `Max Clock Frequency`, `Number of I/Os`, `Supply Voltage` |
| LEDs | `Emitted Color`, `Forward Voltage`, `Luminous Intensity` |
| General (all) | `Operating Temperature`, `Package`, `Voltage-Supply(Max)` |

### Catalog Scale

| Filter | Count (as of March 2026) |
|--------|--------------------------|
| All parts | ~7,100,000 |
| Preferred parts | ~1,234 |
| Basic parts | ~351 |

---

## 2. LCSC Product Detail API

For fetching rich detail on a specific part by LCSC number. Returns extended attributes, images, and product metadata.

### Endpoint

```
GET https://ips.lcsc.com/rest/wmsc2agent/product/info/{lcsc_number}
```

Example: `https://ips.lcsc.com/rest/wmsc2agent/product/info/C7063`

### Authentication

Requires LCSC API credentials (`LCSC_KEY`, `LCSC_SECRET`) for the signed request variant used by jlcparts. The request is signed with SHA1:

```python
payload = {
    "key": LCSC_KEY,
    "nonce": random_string(16),
    "secret": LCSC_SECRET,
    "timestamp": str(int(time.time())),
}
payload["signature"] = sha1(urlencode(payload)).hexdigest()
requests.get(url, params=payload)
```

### Response

Returns a JSON object with:
- `attributes`: Key-value pairs of all parametric data
- `images`: Product photos
- `datasheet`: PDF URL
- `url`: Product page URL
- `manufacturer`: Manufacturer info
- `prices`: LCSC pricing (may differ from JLC PCB pricing)

### When to Use

Use the JLCPCB Search API (Section 1) as the primary source — it includes `attributes` inline and requires no authentication. Use this LCSC endpoint only when you need extended detail beyond what the search API provides.

---

## 3. EasyEDA Component API

For retrieving schematic symbols, PCB footprints, and 3D models. Useful if building tools that need to generate or validate PCB designs.

### Endpoints

```
GET https://easyeda.com/api/products/{lcsc_id}/svgs    → returns component UUIDs
GET https://easyeda.com/api/components/{uuid}           → returns shape/pin data
```

### No authentication required.

### Data Returned

- Pin names, numbers, electrical types, positions
- Pad shapes, sizes, positions, layers
- 3D model references (STEP/WRL files)
- Component parameters (`c_para`: prefix, package, manufacturer, datasheet)

---

## 4. SQLite Database (Offline Bulk Access)

A pre-built SQLite database containing the full catalog is available as a split zip from the upstream project.

### Download

```bash
for i in $(seq -w 01 18); do
  wget -q "https://yaqwsx.github.io/jlcparts/data/cache.z$i"
done
wget -q "https://yaqwsx.github.io/jlcparts/data/cache.zip"
7z x cache.zip   # produces cache.sqlite3 (~930 MB)
```

### Staleness Warning

The upstream database was last updated **November 2025**. Stock counts, pricing, and new parts will be out of date. For real-time data, use the JLCPCB Search API.

### Schema

See `docs/sqlite-database-guide.md` for full schema, example queries, and Python usage.

**Tables**: `components`, `categories`, `manufacturers`
**View**: `v_components` (pre-joined)

Key columns: `lcsc` (int PK), `mfr`, `package`, `description`, `stock`, `price` (JSON), `extra` (JSON with `attributes` object), `basic`, `preferred`.

---

## 5. Design Considerations for Agent Tools

### Recommended Architecture

```
User Query (natural language)
    ↓
AI Agent (interprets intent, selects parameters)
    ↓
JLCPCB Search API (real-time search)
    ↓
Structured Results (filtered, ranked, compared)
    ↓
Agent Response (recommendations with rationale)
```

### Search Strategy

1. **Keyword search**: The JLCPCB API supports natural queries like `"10k 0402 resistor"` or `"LDO 3.3V 500mA"`. Start here.

2. **Filter by part type**: Use `componentLibraryType: "base"` to restrict to basic parts (no extra fee, recommended for cost-sensitive designs).

3. **Paginate for completeness**: For broad searches, paginate through results. The API returns `total` count and `hasNextPage` flag.

4. **Parse attributes**: The `attributes` array in search results provides structured parametric data. Use these for numeric comparisons rather than parsing the `describe` string.

5. **Cross-reference with LCSC**: For parts where the search API's attributes are insufficient, fetch extended detail from the LCSC product API.

### Attribute Value Parsing

Component attribute values use SI prefixes and unit strings that need parsing for numeric comparison:

| Raw Value | Parsed | Unit |
|-----------|--------|------|
| `10kΩ` | 10000 | ohms |
| `100nF` | 1e-7 | farads |
| `4.7µH` | 4.7e-6 | henries |
| `3.3V` | 3.3 | volts |
| `500mA` | 0.5 | amperes |
| `1/16W` | 0.0625 | watts |
| `±1%` | 1.0 | percent |

SI prefix table:

| Prefix | Multiplier |
|--------|-----------|
| `p` | 1e-12 |
| `n` | 1e-9 |
| `u`, `µ`, `μ` | 1e-6 |
| `m` | 1e-3 |
| `k`, `K` | 1e3 |
| `M` | 1e6 |
| `G` | 1e9 |

The `jlcparts` Python package includes robust parsers for these in `jlcparts/attributes.py`. These handle edge cases like fractions (`1/16W`), typos (`?` instead of `m`), compound values (`2.5Ω@VGS=10V`), and dual-value components (dual MOSFETs).

### Rate Limiting

No explicit rate limits have been documented for the JLCPCB Search API, but as a public web API:

- Add delays between requests (1-2 seconds recommended for bulk operations)
- Use browser-like headers (User-Agent, Origin, Referer)
- Cache results aggressively — component data changes infrequently (stock and pricing update daily)
- For bulk catalog download, consider using the SQLite database instead

### Example Agent Workflows

#### Find a component by requirements

```
Input:  "I need a 100nF 0402 capacitor rated for at least 16V, basic part preferred"
Action: Search API with keyword="100nF 0402 capacitor", componentLibraryType="base"
Filter: Parse attributes for Voltage Rated >= 16V
Output: Ranked list by stock and price
```

#### Compare alternatives

```
Input:  "Compare STM32F103 variants available at JLCPCB"
Action: Search API with keyword="STM32F103"
Filter: stock > 0
Output: Table of variants with package, RAM, flash, price, stock
```

#### BOM validation

```
Input:  BOM with LCSC part numbers
Action: For each part, search by componentCode
Check:  Stock >= required quantity, pricing at target quantity
Output: Availability report, flag out-of-stock or discontinued parts
```

#### Parametric selection

```
Input:  "Find the cheapest N-channel MOSFET with Vds >= 30V, Id >= 5A, Rds < 50mΩ, in SOT-23"
Action: Search API with keyword="N-channel MOSFET SOT-23"
Filter: Parse attributes for Vds, Id, Rds thresholds
Rank:   By unit price ascending
Output: Top candidates with full specs
```

### Cost Awareness

JLC PCB charges differently based on part type:

| Type | Extra Fee | Count |
|------|-----------|-------|
| Basic | None | ~351 parts |
| Preferred | Small fee | ~1,234 parts |
| Extended | $3 per unique part per board | ~7.1M parts |

For cost-optimized designs, prefer basic/preferred parts. The `componentLibraryType` and `preferredComponentFlag` fields enable filtering.

---

## 6. Quick Start: Minimal Search Tool

```python
import requests
import json

JLCPCB_SEARCH_URL = (
    "https://jlcpcb.com/api/overseas-pcb-order/v1/"
    "shoppingCart/smtGood/selectSmtComponentList"
)

HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://jlcpcb.com",
    "Referer": "https://jlcpcb.com/parts",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36"
    ),
}


def search_jlcpcb(keyword, page=1, page_size=25, basic_only=False):
    """Search JLC PCB catalog. Returns (total, components)."""
    body = {
        "keyword": keyword,
        "currentPage": page,
        "pageSize": page_size,
    }
    if basic_only:
        body["componentLibraryType"] = "base"

    resp = requests.post(JLCPCB_SEARCH_URL, json=body, headers=HEADERS)
    data = resp.json()["data"]["componentPageInfo"]

    components = []
    for c in data["list"]:
        attrs = {
            a["attribute_name_en"]: a["attribute_value_name"]
            for a in (c.get("attributes") or [])
        }
        components.append({
            "lcsc": c["componentCode"],
            "mfr_part": c["componentModelEn"],
            "manufacturer": c["componentBrandEn"],
            "package": c["componentSpecificationEn"],
            "category": c["componentTypeEn"],
            "description": c["describe"],
            "stock": c["stockCount"],
            "basic": c["componentLibraryType"] == "base",
            "preferred": c["preferredComponentFlag"],
            "price_qty1": (
                c["componentPrices"][0]["productPrice"]
                if c.get("componentPrices")
                else None
            ),
            "attributes": attrs,
            "datasheet": c.get("dataManualUrl"),
            "url": (
                f"https://jlcpcb.com/partdetail/{c['urlSuffix']}"
                if c.get("urlSuffix")
                else None
            ),
        })

    return data["total"], components


# Example usage
if __name__ == "__main__":
    total, parts = search_jlcpcb("10k 0402 resistor", page_size=5)
    print(f"Found {total} results\n")
    for p in parts:
        print(f"  {p['lcsc']}  {p['mfr_part']:<30}  "
              f"stock={p['stock']:>6}  ${p['price_qty1']}")
        for k, v in p["attributes"].items():
            print(f"    {k}: {v}")
        print()
```

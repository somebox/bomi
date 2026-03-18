# jlcpcb-tool — Agent Guide

CLI tool for searching, selecting, and managing JLCPCB/LCSC electronic
components. Use this tool via the `jlcpcb` command for all component
research instead of web searches or manual API calls.

## Quick Reference

| Command | Purpose |
|---------|---------|
| `jlcpcb search "keyword"` | Search JLCPCB catalog (live API) |
| `jlcpcb fetch CXXXXX` | Fetch and cache a specific part by LCSC code |
| `jlcpcb compare CXXXXX CYYYYY` | Side-by-side part comparison |
| `jlcpcb info CXXXXX` | Show full cached detail for a part |
| `jlcpcb select CXXXXX --ref U1 --notes "..."` | Add part to project BOM |
| `jlcpcb deselect U1` | Remove part from BOM by ref designator |
| `jlcpcb relabel U1 U3` | Rename a ref designator |
| `jlcpcb bom` | Display project BOM (table) |
| `jlcpcb bom --format csv` | Export BOM as CSV (all columns) |
| `jlcpcb bom --format markdown` | Export BOM as rich markdown with detail sections |
| `jlcpcb bom --format json` | Export BOM as JSON (for programmatic use) |
| `jlcpcb bom --check` | Refresh all BOM parts from API, flag issues |
| `jlcpcb status` | Project overview: selection count, cost, warnings |
| `jlcpcb datasheet CXXXXX --pdf --summary -o dir/` | Download PDF + generate markdown summary |
| `jlcpcb init` | Initialize a new project in current directory |

## Searching for Parts

```bash
# Natural language search
jlcpcb search "buck converter 3.3V wide input"
jlcpcb search "10k 0402 resistor"
jlcpcb search "N-channel MOSFET SOT-23"

# Filter options
jlcpcb search "LDO 3.3V" --basic-only          # basic parts only (no extra fee)
jlcpcb search "ESP32" --min-stock 1000          # minimum stock
jlcpcb search "capacitor 100nF" --max-price 0.01

# Parametric filtering
jlcpcb search "MOSFET SOT-23" --attr "Drain Source Voltage (Vdss) >= 30"
jlcpcb search "resistor 0402" --attr "Resistance = 10k"

# Output formats
jlcpcb search "SS54" --format json              # structured JSON for parsing
jlcpcb search "TPS54331" --format table         # default terminal table
```

### Parsing JSON Output

For programmatic filtering of search results:

```bash
jlcpcb search "keyword" --format json | python3 -c "
import sys, json
d = json.load(sys.stdin)
for r in d['results']:
    attrs = {k: v.get('raw','') for k,v in r.get('attributes',{}).items()}
    print(f\"{r['lcsc_code']}  {r['mfr_part']:<30}  stock={r['stock']:>8}  \${r['price_qty1']:.2f}  {r['library_type']}\")
"
```

### Fetching Specific Parts

```bash
# Fetch by LCSC code (caches locally for 24h)
jlcpcb fetch C9865 C22452

# Force re-fetch from API
jlcpcb fetch C9865 --force

# Show full cached detail
jlcpcb info C9865
```

## Project BOM Management

### Initialization

```bash
cd my-project
jlcpcb init --name "My Board" --description "Description here"
```

Creates `.jlcpcb/project.yaml` in the project directory.

### Selecting Components

```bash
# Add a part to the BOM
jlcpcb select C9865 --ref U3 --qty 1 --notes "TPS54331 3.3V logic buck"

# Multiple refs for identical parts
jlcpcb select C8678 --ref D3 --notes "SS34 catch diode for U3"
jlcpcb select C8678 --ref D4 --notes "SS34 catch diode for U4"

# Grouped refs
jlcpcb select C20917 --ref Q1-Q3 --qty 3 --notes "AO3400A MOSFETs for PWM"
```

### Modifying Selections

```bash
# Remove a component
jlcpcb deselect U5

# Rename a designator
jlcpcb relabel C4 C4a

# Replace: deselect old, select new
jlcpcb deselect U3
jlcpcb select C9865 --ref U3 --notes "Upgraded to TPS54331"
```

### Viewing the BOM

```bash
# Terminal table (shows notes column, truncated)
jlcpcb bom

# CSV with all columns (Ref, LCSC, Qty, Part, Manufacturer, Package,
# Description, Price, Stock, Type, Notes, Datasheet, JLCPCB URL)
jlcpcb bom --format csv > docs/BOM.csv

# Rich markdown with summary table + per-component detail sheets
jlcpcb bom --format markdown > docs/BOM.md

# Refresh stock/pricing from API and flag issues
jlcpcb bom --check
```

### Datasheets

```bash
# Download PDF only
jlcpcb datasheet C9865 --pdf -o docs/datasheets/

# Download PDF + generate LLM markdown summary
jlcpcb datasheet C9865 --pdf --summary -o docs/datasheets/

# Multiple parts at once
jlcpcb datasheet C9865 C22452 C8678 --pdf --summary -o docs/datasheets/
```

## JLCPCB Cost Awareness

| Type | Extra Fee | Catalog Size |
|------|-----------|-------------|
| Basic | None | ~351 parts |
| Preferred | Small fee | ~1,234 parts |
| Extended | $3 per unique extended part per board | ~7.1M parts |

Prefer basic parts where possible. The `--basic-only` flag and
`library_type` field in results help identify them.

## Common Attribute Names

Use these with `--attr` filters:

| Component Type | Attributes |
|---------------|------------|
| Resistors | `Resistance`, `Power(Watts)`, `Tolerance` |
| Capacitors | `Capacitance`, `Voltage Rated`, `Tolerance`, `Dielectric Material` |
| Inductors | `Inductance`, `Rated Current`, `DC Resistance`, `Saturation Current` |
| MOSFETs | `Drain Source Voltage (Vdss)`, `Continuous Drain Current (Id)`, `Rds On (Max)` |
| Regulators | `Output Voltage`, `Output Current`, `Voltage - Supply` |
| LEDs | `Emitted Color`, `Forward Voltage`, `Luminous Intensity` |

## Typical Agent Workflows

### Find a replacement part

1. `jlcpcb search "TPS54331"` — find the part
2. `jlcpcb fetch C9865` — cache it
3. `jlcpcb info C9865` — review specs
4. `jlcpcb select C9865 --ref U3 --notes "3.3V logic buck"` — add to BOM

### Compare alternatives

1. `jlcpcb search "buck converter 3.3V"` — broad search
2. Pick candidates from results
3. `jlcpcb compare C9865 C28023 C141841` — side-by-side comparison
4. Select the winner

### Validate and export BOM

1. `jlcpcb bom --check` — refresh all parts, flag stock/price issues
2. `jlcpcb bom --format csv > docs/BOM.csv` — export for ordering
3. `jlcpcb bom --format markdown > docs/BOM.md` — export for documentation

### Research with datasheets

1. `jlcpcb datasheet C9865 --pdf --summary -o docs/datasheets/`
2. Read the generated `.md` summary for key specs, pin descriptions,
   application circuits, and design notes

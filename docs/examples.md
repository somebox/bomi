# Usage Examples

This file focuses on commands that are implemented in the current CLI. For a structured agent reference, see `docs/jlcpcb-tool-guide.md` or [somebox.github.io/jlcpcb-tool/examples.html](https://somebox.github.io/jlcpcb-tool/examples.html).

## Basic Search

```bash
# Search for 10k resistors in 0402
jlcpcb search "10k 0402 resistor"

# Restrict to basic parts
jlcpcb search "100nF capacitor" --basic-only

# Preferred parts with minimum stock
jlcpcb search "LED" --preferred-only --min-stock 1000

# Fetch more than one results page
jlcpcb search "STM32" --pages 3 --limit 50
```

## Attribute Filtering

```bash
# Find resistors >= 10k
jlcpcb search "0402 resistor" --attr "Resistance >= 10k"

# Find capacitors rated for at least 25V
jlcpcb search "0402 capacitor" --attr "Voltage Rated >= 25"

# AND multiple attribute filters together
jlcpcb search "MOSFET SOT-23" \
  --attr "Drain Source Voltage (Vdss) >= 30" \
  --attr "Continuous Drain Current (Id) >= 5"

# Add a price cap
jlcpcb search "LDO 3.3V" --max-price 0.50 --basic-only
```

## Output Formats

### Search as JSON

```bash
jlcpcb search "10k resistor" --format json
```

```json
{
  "status": "ok",
  "command": "search",
  "count": 2,
  "results": [
    {
      "lcsc_code": "C8287",
      "mfr_part": "RC0402FR-0710KL",
      "manufacturer": "YAGEO",
      "package": "0402",
      "stock": 500000,
      "price_qty1": 0.0037
    }
  ]
}
```

### BOM as JSON

```bash
jlcpcb bom --format json
```

```json
{
  "status": "ok",
  "command": "bom",
  "data": [
    {
      "ref": "R1",
      "lcsc": "C8287",
      "quantity": 2,
      "warnings": []
    }
  ]
}
```

## Local Cache Queries

```bash
# Query all cached parts
jlcpcb query

# Query by keyword
jlcpcb query "resistor" --package 0402

# Query by attributes
jlcpcb query --attr "Resistance >= 1k" --attr "Resistance <= 100k" --basic-only
```

## Cached Part Inspection

```bash
# Cache a part, then inspect it
jlcpcb fetch C8287
jlcpcb info C8287

# Compare cached parts
jlcpcb compare C8287 C25900

# Force a refresh even if the part is recent
jlcpcb fetch C8287 --force
```

## Datasheets

```bash
# Analyze one cached datasheet with OpenRouter
# Default prompt covers: key specs, pin descriptions, application circuit values, design notes
jlcpcb fetch C8287
jlcpcb analyze C8287

# Pass --prompt only when you need something specific
jlcpcb analyze C8287 --prompt "What is the enable pin threshold voltage?"

# Use a specific model
jlcpcb analyze C8287 --model "anthropic/claude-sonnet-4.6"

# Download PDF only
jlcpcb datasheet C8287 --pdf -o docs/datasheets/

# Download PDF and generate a markdown summary (useful as agent context)
jlcpcb datasheet C8287 --pdf --summary -o docs/datasheets/
```

## Project Workflow

### Start a new PCB project

```bash
mkdir my-board && cd my-board
git init
jlcpcb init --name "my-board" --description "Motor driver board"
```

### Research and select components

```bash
# Research phase
jlcpcb search "100nF 0402 X7R"
jlcpcb fetch C1525
jlcpcb info C1525

# Add BOM entries (select fetches automatically if not already cached)
jlcpcb select C1525 --ref C1 --qty 1 --notes "Bypass cap"
jlcpcb select C1525 --ref C2 --qty 1 --notes "Bypass cap"
jlcpcb select C347356 --ref U2 --qty 1 --notes "LED driver, constant current"
```

### BOM review

```bash
jlcpcb bom
jlcpcb bom --check
jlcpcb bom --format csv
jlcpcb bom --format markdown
jlcpcb status
```

### Work from outside the project directory

```bash
# Via CLI flag
jlcpcb --project ~/Projects/my-board bom

# Via environment variable
export JLCPCB_PROJECT=~/Projects/my-board
jlcpcb status
```

## Database Commands

```bash
jlcpcb db stats
jlcpcb db clear
```

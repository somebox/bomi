# Usage Examples

## Basic Search

```bash
# Search for 10k resistors in 0402 package
jlcpcb search "10k 0402 resistor"

# Search for basic parts only (no extra assembly fee)
jlcpcb search "100nF capacitor" --basic-only

# Search preferred parts with minimum stock
jlcpcb search "LED" --preferred-only --min-stock 1000

# Fetch multiple pages
jlcpcb search "STM32" --pages 3 --limit 50
```

## Attribute Filtering

```bash
# Find resistors >= 10kΩ
jlcpcb search "0402 resistor" --attr "Resistance >= 10k"

# Find capacitors rated for at least 25V
jlcpcb search "0402 capacitor" --attr "Voltage Rated >= 25"

# Multiple attribute filters (AND logic)
jlcpcb search "MOSFET SOT-23" \
  --attr "Drain Source Voltage (Vdss) >= 30" \
  --attr "Continuous Drain Current (Id) >= 5"

# Find LEDs with specific forward current
jlcpcb search "RGB LED" --attr "Forward Current >= 100mA"

# Budget-constrained search
jlcpcb search "LDO 3.3V" --max-price 0.50 --basic-only
```

## Output Formats

### Table (default)
```bash
jlcpcb search "10k resistor" --limit 5
```
```
LCSC     MFR Part                        Manufacturer     Package    Stock   Price   Type
-------  ------------------------------  ---------------  ---------  ------  ------  ------
C8287    RC0402FR-0710KL                 YAGEO            0402       500000  $0.0037 Basic*
C25900   0402WGF1002TCE                  UNI-ROYAL        0402       300000  $0.0020 Basic
```

### JSON (for agents)
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
      "price_qty1": 0.0037,
      "attributes": {
        "Resistance": {"raw": "10kΩ", "num": 10000.0, "unit": "ohm"}
      }
    }
  ]
}
```

### CSV
```bash
jlcpcb search "10k resistor" --format csv > resistors.csv
```

## Local Database Queries

After fetching parts, query the local cache without API calls:

```bash
# Query all cached parts
jlcpcb query

# Query with keyword
jlcpcb query "resistor" --package 0402

# Query with attribute filters
jlcpcb query --attr "Resistance >= 1k" --attr "Resistance <= 100k" --basic-only
```

## Part Details

```bash
# Fetch and view a specific part
jlcpcb fetch C8287
jlcpcb info C8287

# Force re-fetch (ignore 24h cache)
jlcpcb fetch C8287 --force
```

## Comparing Parts

```bash
# Side-by-side comparison
jlcpcb compare C8287 C25900

# JSON output for programmatic comparison
jlcpcb compare C8287 C25900 --format json
```

## Datasheet Analysis

```bash
# Analyze with OpenRouter (vision model)
jlcpcb analyze C8287 --method openrouter \
  --prompt "What is the maximum power rating and operating temperature range?"

# Analyze with LLMLayer (text extraction + text model)
jlcpcb analyze C8287 --method llmlayer \
  --prompt "Extract all electrical specifications as a structured list"

# Use a specific model
jlcpcb analyze C8287 --method openrouter --model "anthropic/claude-sonnet-4"
```

## Agent Workflow Examples

### Find RGB LEDs for a project
```bash
# Step 1: Search for RGB LEDs
jlcpcb search "RGB LED SMD" --format json --limit 20

# Step 2: Filter by brightness
jlcpcb query --attr "Luminous Intensity >= 500" --format json

# Step 3: Compare top candidates
jlcpcb compare C2843 C2844 C2845 --format json
```

### Find an LED driver
```bash
# Search for LED drivers with specific output current
jlcpcb search "LED driver constant current" \
  --attr "Output Current >= 350mA" \
  --basic-only --format json
```

### Find connectors
```bash
# Search for USB-C connectors in stock
jlcpcb search "USB Type-C connector" --min-stock 100 --format json

# Search for push buttons
jlcpcb search "tactile switch SMD" --basic-only --format json
```

## Database Management

```bash
# View statistics
jlcpcb db stats

# Clear all cached data
jlcpcb db clear
```

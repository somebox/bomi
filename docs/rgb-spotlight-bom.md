# RGB Spotlight PCB — Bill of Materials

30mm circular chainable RGB spotlight. WS2811 pixel controller + 74HC04 inverter + 3× PT4115 buck LED drivers + XINGLIGHT HD2525 high-power LEDs. Input: 12V / DIN / GND (3-wire chain). ~4.73W per pixel at 450mA/channel.

> All LCSC part numbers verified in stock as of 2026-03-05.

## ICs

| Ref | Part | Manufacturer | LCSC | Package | Qty | Price (1+) | Type | Stock |
|-----|------|-------------|------|---------|-----|------------|------|-------|
| U1 | WS2811 | Worldsemi | [C114581](https://jlcpcb.com/partdetail/Worldsemi-WS2811/C114581) | SOP-8 | 1 | $0.0325 | Extended | 282,006 |
| U2–U4 | PT4115 | UMW | [C347356](https://jlcpcb.com/partdetail/324016-PT4115/C347356) | SOT-89-5 | 3 | $0.0895 | Extended | 203,331 |
| U5 | 78L05G-AB3-R | UTC | [C71136](https://jlcpcb.com/partdetail/UTC_Unisonic_Tech-78L05G_AB3R/C71136) | SOT-89-3 | 1 | $0.0702 | **Basic** | 68,740 |
| U6 | 74HC04D,653 | Nexperia | [C5590](https://jlcpcb.com/partdetail/Nexperia-74HC04D653/C5590) | SOIC-14 | 1 | $0.1707 | Extended | 96,842 |
| U7 | SN74AHCT1G125DCKR | Texas Instruments | [C350557](https://jlcpcb.com/partdetail/TexasInstruments-SN74AHCT1G125DCKR/C350557) | SC-70-5 | 1 | $0.1095 | Extended | 4,034 |

## LEDs

| Ref | Part | Color | λ | Vf | LCSC | Qty | Price (1+) | Stock |
|-----|------|-------|---|-----|------|-----|------------|-------|
| LED1 | XL-HD2525SURC-A4 | Red | 625nm | 2.4V | [C49237857](https://jlcpcb.com/partdetail/XINGLIGHT-XL_HD2525SURCA4/C49237857) | 1 | $0.2630 | 1,213 |
| LED2 | XL-HD2525UGC-A4 | Green | 525nm | 3.4V | [C49237859](https://jlcpcb.com/partdetail/XINGLIGHT-XL_HD2525UGCA4/C49237859) | 1 | $0.2846 | 2,144 |
| LED3 | XL-HD2525UBC-A4 | Blue | 455nm | 3.4V | [C49237860](https://jlcpcb.com/partdetail/XINGLIGHT-XL_HD2525UBCA4/C49237860) | 1 | $0.2024 | 2,011 |

All HD2525 series: 3W max, 700mA max, 120° viewing angle, 2.5×2.5mm. Red LED stock is low — order early or identify alternates for large runs.

## Inductors & Diodes

| Ref | Part | LCSC | Package | Qty | Price (1+) | Stock |
|-----|------|------|---------|-----|------------|-------|
| L1–L3 | FNR6045S101MT (100µH, 1A, shielded) | [C168095](https://jlcpcb.com/partdetail/179478-FNR6045S101MT/C168095) | 6×6mm | 3 | $0.0673 | 232,734 |
| D1–D3 | B5819W (40V/1A Schottky) | [C64885](https://jlcpcb.com/partdetail/MDD_Microdiode_Semiconductor-B5819W/C64885) | SOD-123 | 3 | $0.0165 | 1,192,640 |

## Connectors

| Ref | Part | Manufacturer | LCSC | Package | Qty | Price (1+) | Type | Stock |
|-----|------|-------------|------|---------|-----|------------|------|-------|
| J1, J2 | S3B-PH-SM4-TB(LF)(SN) | JST | [C265101](https://jlcpcb.com/partdetail/JstSalesAmerica-S3B_PH_SM4_TB_LF_SN/C265101) | PH 2.0mm 3P SMT RA | 2 | $0.25 | Extended | 22,600 |

JST PH 2.0mm, 3-pin, right-angle (side entry), surface mount. SM4 variant with reinforcement tabs for peel strength. J1 = input (12V/DIN/GND), J2 = output (GND/DOUT/12V).

## Resistors & Capacitors

| Ref | Value | LCSC | Package | Qty | Price (1+) | Type |
|-----|-------|------|---------|-----|------------|------|
| R1–R3 | 0.22Ω ±1% (current sense) | [C247160](https://jlcpcb.com/partdetail/244368-0805W8F220LT5E/C247160) | 0805 | 3 | $0.0044 | Extended |
| R4–R6 | 4.7kΩ (pull-up) | TBD (any basic 0402) | 0402 | 3 | ~$0.001 | **Basic** |
| R7 | 10kΩ (OE pull-down) | TBD (any basic 0402) | 0402 | 1 | ~$0.001 | **Basic** |
| C1–C4 | 100nF X7R 16V | [C1525](https://jlcpcb.com/partdetail/1877-CL05B104KO5NNNC/C1525) | 0402 | 4 | $0.0013 | **Basic** |
| C5–C8 | 10µF X5R 25V | [C15850](https://jlcpcb.com/partdetail/16532-CL21A106KAYNNNE/C15850) | 0805 | 4 | $0.0188 | **Basic** |

## Unit Cost Summary

| Category | Parts | Subtotal |
|----------|-------|----------|
| ICs | WS2811 + 3× PT4115 + 78L05 + 74HC04 + 74AHCT1G125 | $0.65 |
| LEDs | Red + Green + Blue | $0.75 |
| Inductors | 3× 100µH | $0.20 |
| Schottky diodes | 3× B5819W | $0.05 |
| Connectors | 2× JST PH 3P SMT RA | $0.50 |
| Resistors + Caps | 3× sense + 3× pull-up + 1× pull-down + 8× caps | $0.10 |
| **Total BOM** | | **~$2.25/unit** |

Extended part fee: 10 unique extended parts × $3 = **$30/order** (one-time).

## Component Selection Rationale

### U1 — WS2811 (pixel controller)

3-channel PWM controller with single-wire NeoPixel-compatible protocol. Outputs are **open-drain** (sink-only). SET pin floated for 800kHz mode. PWM frequency ~2kHz (within PT4115 DIM range).

### U6 — 74HC04 (hex inverter) — why it's needed

The WS2811 open-drain outputs and PT4115 active-high DIM create an **inversion problem**: data 0xFF → WS2811 sinks → DIM LOW → LED OFF (wrong). Without correction, software must send `255 - brightness`, breaking compatibility with WLED, Art-Net, FastLED, and all standard NeoPixel software.

The 74HC04 inverts the signal between the pull-up node and the PT4115 DIM pin:
- Data 0xFF → WS2811 sinks → pull-up node LOW → inverter outputs HIGH → DIM HIGH → LED ON (correct)
- Data 0x00 → WS2811 floats → pull-up node HIGH → inverter outputs LOW → DIM LOW → LED OFF (correct)

Uses 3 of 6 available gates. Remaining 3 inputs should be tied to VCC or GND to prevent floating. SOIC-14 fits on the bottom side. Adds $0.17/unit but eliminates all software workarounds.

### U7 — SN74AHCT1G125 (3.3V→5V level shifter on DIN)

Single-gate bus buffer in SC-70-5 (tiny). The **AHCT** family accepts 3.3V logic as valid high (VIH = 2.0V) while outputting 5V levels, solving the WS2811 input threshold problem (VIH = 0.7 × VDD = 3.5V). Placed on the first pixel's DIN input so 3.3V controllers (ESP32, RP2040, STM32) can drive the chain directly. Subsequent pixels don't need level shifting — each WS2811 regenerates DOUT at 5V.

**OE pin handling (from datasheet):** TI recommends tying OE to VCC through a pull-up resistor so the output stays Hi-Z during power-up/power-down, preventing garbage from being driven onto the data bus. In our circuit, OE is tied to GND via R7 (10kΩ) to enable the buffer during normal operation. The pull-up is omitted because brief transients on the WS2811 DIN line during power-up are harmless — the WS2811 requires a >50µs reset pulse before accepting data. If clean power-up behavior is needed, add a 10kΩ pull-up from OE to VCC (the pull-down will win once supply rails are stable).

**Bypass:** 100nF (C3) close to VCC pin, per datasheet recommendation.

### U2–U4 — PT4115 (buck LED drivers)

Constant-current buck converters, one per LED channel.

- **High-side current sensing:** Rs between 12V rail and CSN pin. VIN connects directly to 12V. IC regulates 100mV across Rs.
- **DIM pin:** Active-high (>2.5V = on, <0.3V = off). Internal 200kΩ pull-up. PWM range 100Hz–20kHz.
- **Exposed pad** is GND — solder for thermal relief.

### U5 — 78L05 (5V regulator)

Selected over AMS1117-5.0: **basic part** (no $3 fee), smaller (SOT-89 vs SOT-223), and 100mA output is ample for the ~17mA load (WS2811 + 74HC04). Dissipation: (12V − 5V) × 17mA ≈ 0.12W → ~24°C rise. A switcher would be overkill for this load.

### R1–R3 — 0.22Ω sense resistors

Iout = 0.1V / 0.22Ω ≈ **454mA** (64% of LED max, leaves thermal margin). Alternatives: 0.33Ω → 300mA, 0.15Ω → 667mA. Power dissipation: 45mW (0805 rated 125mW).

### R4–R6 — 4.7kΩ pull-ups

Pull WS2811 open-drain outputs to 5V for the inverter input. The PT4115 internal 200kΩ pull-up alone is too weak against switching noise. 4.7kΩ limits WS2811 sink current to ~1mA (trivial).

### L1–L3 — 100µH inductors

PT4115 datasheet value for Vin > 8V. 1A saturation > 454mA operating. Shielded 6×6mm package for EMI.

### D1–D3 — B5819W Schottky

Freewheeling diodes: 40V/1A, SOD-123, 600mV Vf. JLCPCB preferred part with massive stock.

### LED1–LED3 — HD2525 LEDs

Matched RGB set from XINGLIGHT, same 2525 footprint. Driven at 454mA (64% of 700mA max). Red Vf=2.4V, Green/Blue Vf=3.4V.

### Capacitors

- **C1–C4** (100nF): Bypass for WS2811, 74HC04, 74AHCT1G125, and 78L05 output respectively.
- **C5** (10µF): 78L05 input bulk.
- **C6, C7, C8** (10µF): Dedicated input bulk for each PT4115 channel (Red, Green, Blue). Place close to each PT4115 VIN pin.

## Connection Table

### U1 — WS2811 (SOP-8)
| Pin | Name | Net | Connects to |
|-----|------|-----|-------------|
| 1 | OUTR | DIM_R_RAW | R4 (4.7kΩ to 5V), U6 3A |
| 2 | OUTG | DIM_G_RAW | R5 (4.7kΩ to 5V), U6 2A |
| 3 | OUTB | DIM_B_RAW | R6 (4.7kΩ to 5V), U6 1A |
| 4 | GND | GND | Ground plane |
| 5 | DOUT | DOUT | J2 pin 2 |
| 6 | DIN | DIN_5V | U7 Y (pin 4) |
| 7 | SET | NC | Float (800kHz mode) |
| 8 | VDD | 5V | U5 VOUT, U6 VCC, C1 (100nF to GND) |

### U7 — SN74AHCT1G125 (SC-70-5, level shifter)
| Pin | Name | Net | Connects to |
|-----|------|-----|-------------|
| 1 | OE (active low) | OE_DIN | R7 (10kΩ to GND) — always enabled |
| 2 | A | DIN | J1 pin 2 |
| 3 | GND | GND | Ground plane |
| 4 | Y | DIN_5V | U1 DIN (pin 6) |
| 5 | VCC | 5V | U5 VOUT, C3 (100nF to GND) |

### U6 — 74HC04D (SOIC-14, hex inverter)
| Pin | Net | Connects to |
|-----|-----|-------------|
| 1A | DIM_B_RAW | U1 OUTB (pin 3), R6 |
| 1Y | DIM_B | U4 DIM (pin 3) |
| 2A | DIM_G_RAW | U1 OUTG (pin 2), R5 |
| 2Y | DIM_G | U3 DIM (pin 3) |
| 3A | DIM_R_RAW | U1 OUTR (pin 1), R4 |
| 3Y | DIM_R | U2 DIM (pin 3) |
| GND | GND | Ground plane |
| 4Y | — | Unused (output, leave floating) |
| 4A | GND | Tie to GND |
| 5Y | — | Unused (output, leave floating) |
| 5A | GND | Tie to GND |
| 6Y | — | Unused (output, leave floating) |
| 6A | GND | Tie to GND |
| VCC | 5V | U5 VOUT, U1 VDD, C2 (100nF to GND) |

### U2 — PT4115 (SOT-89-5) — Red channel
| Pin | Name | Net | Connects to |
|-----|------|-----|-------------|
| 1 | SW | SW_R | L1 (100µH), D1 cathode |
| 2 | GND | GND | Ground plane (+ exposed pad) |
| 3 | DIM | DIM_R | U6 3Y |
| 4 | CSN | CSN_R | R1 (0.22Ω to 12V) |
| 5 | VIN | 12V | 12V rail, C6 (10µF to GND) |

### U3 — PT4115 (SOT-89-5) — Green channel
| Pin | Name | Net | Connects to |
|-----|------|-----|-------------|
| 1 | SW | SW_G | L2 (100µH), D2 cathode |
| 2 | GND | GND | Ground plane (+ exposed pad) |
| 3 | DIM | DIM_G | U6 2Y |
| 4 | CSN | CSN_G | R2 (0.22Ω to 12V) |
| 5 | VIN | 12V | 12V rail, C7 (10µF to GND) |

### U4 — PT4115 (SOT-89-5) — Blue channel
| Pin | Name | Net | Connects to |
|-----|------|-----|-------------|
| 1 | SW | SW_B | L3 (100µH), D3 cathode |
| 2 | GND | GND | Ground plane (+ exposed pad) |
| 3 | DIM | DIM_B | U6 1Y |
| 4 | CSN | CSN_B | R3 (0.22Ω to 12V) |
| 5 | VIN | 12V | 12V rail, C8 (10µF to GND) |

### U5 — 78L05 (SOT-89-3)
| Pin | Name | Net | Connects to |
|-----|------|-----|-------------|
| 1 | GND | GND | Ground plane (+ tab) |
| 2 | VIN | 12V | 12V rail, C5 (10µF to GND) |
| 3 | VOUT | 5V | U1 VDD, U6 VCC, C4 (100nF to GND) |

### Passives
| Ref | Value | From | To | Purpose |
|-----|-------|------|----|---------|
| R1 | 0.22Ω | 12V | U2 CSN | Current sense Red (454mA) |
| R2 | 0.22Ω | 12V | U3 CSN | Current sense Green |
| R3 | 0.22Ω | 12V | U4 CSN | Current sense Blue |
| R4 | 4.7kΩ | 5V | DIM_R_RAW | Pull-up for WS2811 OUTR |
| R5 | 4.7kΩ | 5V | DIM_G_RAW | Pull-up for WS2811 OUTG |
| R6 | 4.7kΩ | 5V | DIM_B_RAW | Pull-up for WS2811 OUTB |
| R7 | 10kΩ | U7 OE (pin 1) | GND | Pull-down to enable U7 |
| L1 | 100µH | U2 SW | LED1 anode | Buck inductor Red |
| L2 | 100µH | U3 SW | LED2 anode | Buck inductor Green |
| L3 | 100µH | U4 SW | LED3 anode | Buck inductor Blue |
| D1 | B5819W | GND (anode) | SW_R (cathode) | Freewheeling diode Red |
| D2 | B5819W | GND (anode) | SW_G (cathode) | Freewheeling diode Green |
| D3 | B5819W | GND (anode) | SW_B (cathode) | Freewheeling diode Blue |
| LED1 | HD2525 Red | L1 (anode) | GND (cathode) | Red LED |
| LED2 | HD2525 Green | L2 (anode) | GND (cathode) | Green LED |
| LED3 | HD2525 Blue | L3 (anode) | GND (cathode) | Blue LED |
| C1 | 100nF | 5V | GND | WS2811 bypass |
| C2 | 100nF | 5V (U6 VCC) | GND | 74HC04 bypass |
| C3 | 100nF | 5V (U7 VCC) | GND | 74AHCT1G125 bypass |
| C4 | 100nF | 5V | GND | 78L05 output bypass |
| C5 | 10µF | 12V | GND | 78L05 input bulk |
| C6 | 10µF | 12V (U2 VIN) | GND | PT4115 Red input bulk |
| C7 | 10µF | 12V (U3 VIN) | GND | PT4115 Green input bulk |
| C8 | 10µF | 12V (U4 VIN) | GND | PT4115 Blue input bulk |

### J1 — JST PH 3P (input connector)
| Pin | Net | Connects to |
|-----|-----|-------------|
| 1 | 12V | 12V rail |
| 2 | DIN | U7 A (pin 2) |
| 3 | GND | Ground plane |

### J2 — JST PH 3P (output connector)
| Pin | Net | Connects to |
|-----|-----|-------------|
| 1 | GND | Ground plane (passthrough) |
| 2 | DOUT | U1 DOUT (pin 5) |
| 3 | 12V | 12V rail (passthrough) |

## Assembly & Layout Notes

- **PCB:** 50mm diameter, 2-layer, 1.6mm FR4. Consider aluminum-core for thermal performance.
- **Top side:** 3× LEDs in tight triangle (centered), JST PH connectors at edges for chain in/out.
- **Bottom side:** 3× PT4115 groups (IC + inductor + Schottky) at 120° spacing, WS2811 + 74HC04 center, 78L05 near edge.
- **Thermal vias** adjacent to LED pads (not directly under) to bottom ground pour — avoids solder wicking during reflow.
- Keep Rs (0.22Ω) traces short — high-current path between 12V and CSN.
- Tie unused 74HC04 inputs (4A, 5A, 6A) to GND.
- Standard NeoPixel/WS2812 data protocol — no software inversion needed.

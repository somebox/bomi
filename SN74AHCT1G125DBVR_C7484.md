# SN74AHCT1G125DBVR (C7484)

**Manufacturer:** Texas Instruments  
**Package:** SOT-23-5  
**Category:** Buffers, Drivers, Receivers, Transceivers  
**Datasheet:** https://www.lcsc.com/datasheet/lcsc_datasheet_1809192136_Texas-Instruments-SN74AHCT1G125DBVR_C7484.pdf  
**JLCPCB:** https://jlcpcb.com/partdetail/TexasInstruments-SN74AHCT1G125DBVR/C7484  

---

# SN74AHCT1G125DBVR — Single Bus Buffer Gate with 3-State Output

## Key Specifications

| Parameter | Value |
|-----------|-------|
| Supply Voltage (V_CC) | 4.5 V – 5.5 V |
| Operating Temperature | −40°C to +85°C (datasheet); listed as −40°C to +125°C in part description — verify application range |
| Quiescent Current (I_CC) | 10 µA max |
| Output Drive (I_OH / I_OL) | ±8 mA at 5 V |
| Propagation Delay (t_PLH/t_PHL) | 5.5 ns typ / 6.5 ns max @ 5 V, 15 pF |
| Enable/Disable Delay (t_PZH/t_PZL) | 5.1 ns typ / 6 ns max |
| Disable Delay (t_PHZ/t_PLZ) | 6.8 ns typ / 8 ns max |
| Input Logic Family | TTL-compatible (V_IH ≥ 2.0 V, V_IL ≤ 0.8 V) |
| Output Voltage High (V_OH) | ≥ 3.94 V @ −8 mA |
| Output Voltage Low (V_OL) | ≤ 0.44 V @ 8 mA |
| Input Capacitance (C_i) | 4 pF typ, 10 pF max |
| Power Dissipation Capacitance (C_pd) | 14 pF typ @ 1 MHz |
| Package | SOT-23-5 (DBV) |
| Latch-Up Immunity | >250 mA per JESD 17 |

---

## Pin Descriptions (SOT-23-5 / DBV Package)

| Pin # | Name | Type | Description |
|-------|------|------|-------------|
| 1 | /OE | Input | Active-LOW output enable; HIGH forces output to high-impedance |
| 2 | A | Input | Data input (TTL-compatible) |
| 3 | GND | Power | Ground reference |
| 4 | Y | Output | 3-state buffered output |
| 5 | V_CC | Power | Supply voltage (4.5 V – 5.5 V) |

---

## Function Table

| /OE | A | Y |
|-----|---|---|
| L | H | H |
| L | L | L |
| H | X | **Z** (High-Z) |

---

## Typical Application Circuit

```
        VCC (5V)
          |
         R1          C1
          |     VCC --||-- GND
        [10kΩ]       100nF (bypass, place close to pin 5)
          |
Pin 1 (/OE) ──── Control Signal (or tie to GND to always enable)
Pin 2 (A)  ──── Input Data Signal
Pin 3 (GND) ─── GND
Pin 4 (Y)  ──── Output (load ≤ 8 mA, C_L ≤ 50 pF for rated speed)
Pin 5 (VCC) ─── VCC
```

### Recommended Component Values
- **V_CC bypass capacitor (C1):** 100 nF ceramic, placed as close as possible to pin 5
- **OE pull-up resistor (R1):** 10 kΩ to V_CC (ensures high-Z during power-up/power-down)
- **Load capacitance:** ≤15 pF for best speed; derating applies up to 50 pF

---

## Important Design Notes

1. **OE pull-up required at power-up:** Connect /OE to V_CC through a pull-up resistor (≥10 kΩ typical) to guarantee high-impedance state during power-up or power-down sequences.

2. **Operating temperature discrepancy:** The datasheet specifies −40°C to +85°C for standard operation. The part description lists +125°C — use the automotive-qualified variant **SN74AHCT1G125-Q1** if extended temperature is required.

3. **Input voltage range:** Accepts 0 V to 5.5 V on inputs but TTL thresholds apply (V_IH ≥ 2.0 V). **Not directly compatible with 3.3 V CMOS logic** without level consideration (3.3 V V_OH ≈ 2.4–3.3 V; marginal but often works).

4. **All unused inputs must be tied** to V_CC or GND — floating CMOS inputs cause excessive I_CC and potential oscillation.

5. **Input slew rate limit:** Input transition rate must not exceed **20 ns/V** to ensure correct switching behavior.

6. **Absolute maximum V_CC:** 7 V; exceeding this causes permanent damage. Normal operation is 4.5 V–5.5 V only.

7. **Output current:** Continuous output current is ±25 mA max (absolute); recommended operating limit is ±8 mA for guaranteed V_OH/V_OL specs.

8. **MSL Rating:** Level-1-260°C-UNLIM — no moisture precautions required before soldering.
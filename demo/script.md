
# Demo Script: bomi USB Flashlight Project

## Audience and Goal

This demo shows how `bomi` is used to research parts, make BOM decisions, and keep project selections in version control.

Project example: a USB-powered LED flashlight board with adjustable brightness controls.

## Runtime Notes

- Presenter pace: calm, technical, concise.
- Keep each terminal recording under 45-60 seconds.
- Pause after key commands so viewers can read outputs.
- Highlight one idea per scene.

## Chapter 1 - Introduction

### Scene 1.1 - Title Card (no terminal)

Narration:

"This walkthrough introduces bomi, a command-line workflow for researching JLCPCB parts and maintaining a project BOM as code. We will build a sample USB LED flashlight design and validate part decisions step by step."

### Scene 1.2 - What We Will Build (no terminal)

Narration:

"The board takes USB-C input, drives an LED through a PT4115 current driver, and includes two switch inputs for brightness control behavior. The goal is not full EE design depth; it is a practical BOM workflow from search to validation."

## Chapter 2 - Project Setup

### Scene 2.1 - Create Project Folder and Git Repo

Working directory: `~/Documents/projects`

Commands:

```bash
mkdir -p usb-led-flashlight
cd usb-led-flashlight
git init
```

Narration:

"We begin with a normal project folder and initialize git so BOM changes can be reviewed and tracked."

### Scene 2.2 - Initialize bomi Project Metadata

Working directory: `~/Documents/projects/usb-led-flashlight`

Commands:

```bash
bomi init --name "usb-led-flashlight" --description "USB-C powered LED flashlight with brightness buttons"
```

Narration:

"`bomi init` creates `.bomi/project.yaml`, which becomes the source of truth for part selections."

## Chapter 3 - Search and Inspect Parts

### Scene 3.1 - Find USB-C Power Connector

Commands:

```bash
bomi search "USB Type-C connector SMD" --limit 5
```

Narration:

"Live search returns candidates with package, stock, and pricing in one table."

### Scene 3.2 - Find LED Driver

Commands:

```bash
bomi search "PT4115 LED driver" --limit 5
```

Narration:

"For the flashlight we use PT4115, a buck LED driver suitable for USB-level input."

### Scene 3.3 - Inspect Driver Datasheet Metadata

Commands:

```bash
bomi fetch C347356
bomi info C347356
```

Narration:

"`fetch` caches the exact part, and `info` shows detailed specs, links, and attributes for review."

### Scene 3.4 - Find Supporting Power Parts

Commands:

```bash
bomi search "Schottky diode SOD-123" --basic-only --limit 5
bomi search "inductor 47uH SMD" --limit 5
```

Narration:

"We source the catch diode and inductor needed by the buck stage, checking stock and package fit."

## Chapter 4 - Compare and Decide

### Scene 4.1 - Compare a Decision Candidate

Commands:

```bash
bomi fetch C145837
bomi compare C49023761 C145837
```

Narration:

"Here we compare the chosen tactile switch against a slide-switch alternative to demonstrate decision-making. The example shows how requirements can outweigh a single metric like datasheet availability."

### Scene 4.2 - Capture Known Constraints

Commands:

```bash
bomi info C49023761
bomi search "white LED 2835" --limit 10
```

Narration:

"Some catalog entries have gaps, like missing datasheet URLs or limited stock. We explicitly record these constraints in project notes."

## Chapter 5 - Build the BOM

### Scene 5.1 - Add Selected Parts

Commands:

```bash
# (baseline parts are pre-seeded for demo pacing)
bomi select C456012 --ref J1 --qty 1 --notes "USB-C 6-pin power input"
bomi select C347356 --ref U1 --qty 1 --notes "PT4115 LED driver"
bomi select C3015100 --ref LED1 --qty 1 --notes "White high-power LED placeholder"
bomi select C49023761 --ref SW2 --qty 1 --notes "Brightness down button"
```

Narration:

"Selections map real components to design references. For demo pacing, we show a few adds on top of a prepared baseline BOM."

### Scene 5.2 - Review BOM and Status

Commands:

```bash
bomi list
bomi status
```

Narration:

"`list` gives a detailed table and `status` gives an overview with warnings and rough cost."

## Chapter 6 - Refine and Validate

### Scene 6.1 - Edit BOM References

Commands:

```bash
bomi relabel C1 C99
bomi relabel C2 C1
bomi relabel C99 C2
```

Narration:

"Reference updates can be applied without re-selecting parts, which keeps changes small and traceable."

### Scene 6.2 - Health Check and Export

Commands:

```bash
bomi list --check
bomi list --format csv
bomi list --format json
```

Narration:

"`list --check` refreshes stock and pricing. CSV and JSON exports support downstream review and automation."

### Scene 6.3 - Download Datasheet Artifacts

Commands:

```bash
bomi datasheet C347356 C456012 --pdf -o artifacts/datasheets
```

Narration:

"We save datasheet PDFs as traceable project artifacts for later review."

## Chapter 7 - Wrap-up

### Scene 7.1 - Version-Control the Result

Commands:

```bash
git status
git add .bomi/project.yaml artifacts
git commit -m "Add initial flashlight BOM selections and validation artifacts"
```

Narration:

"The final step is normal git workflow: commit BOM state and validation outputs so design decisions remain reproducible."

### Scene 7.2 - Closing Card (no terminal)

Narration:

"This workflow scales from quick prototypes to larger boards: search, inspect, compare, select, validate, and commit."

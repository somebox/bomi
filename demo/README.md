# Demo Video Assets

This directory contains everything needed to produce the demo presentation for `jlcpcb-tool`.

The demo walks through a sample USB LED flashlight project and shows how to:

- initialize project metadata
- search and inspect parts
- compare alternatives
- select and validate a BOM
- export artifacts for review

## Structure

```text
demo/
  README.md
  script.md                     # scene-by-scene presenter script
  generator/
    cast_generator.py           # generates asciinema .cast files from scenes.yaml
    record_all.py               # one-command generator + verification runner
    scenes.yaml                 # scene definitions and commands
  presentation/
    index.html                  # reveal.js deck with embedded asciinema players
    recordings/                 # generated .cast files
    demo-project/               # throwaway workspace used during recording generation
```

## Requirements

- `uv` (for running Python in project env)
- `asciinema` 3.x
- network access (live `jlcpcb search/fetch` calls)

## Generate Recordings

From repo root:

```bash
python demo/generator/record_all.py
```

This command:

1. runs all scenes from `demo/generator/scenes.yaml`
2. writes `.cast` files to `demo/presentation/recordings/`
3. verifies each `.cast` by converting it to plain text (`asciinema convert`)

Notes:

- `asciinema play` needs a TTY; CI or non-interactive shells may fail. `record_all.py` uses conversion-based verification for reliability.
- Scene generation resets `demo/presentation/demo-project/usb-led-flashlight` so reruns are deterministic.

## Generate Single Scene

```bash
uv run python demo/generator/cast_generator.py \
  --scenes demo/generator/scenes.yaml \
  --scene scene-search-core-parts \
  --output-dir demo/presentation/recordings
```

## Run Presentation

Use any static server from repo root. Example:

```bash
python -m http.server 8000
```

Open:

- `http://localhost:8000/demo/presentation/`

## Editing Workflow

1. Update narration and flow in `demo/script.md`.
2. Update scene commands and timing in `demo/generator/scenes.yaml`.
3. Regenerate recordings with `demo/generator/record_all.py`.
4. Adjust slide text/layout in `demo/presentation/index.html`.
5. Re-run generation if slide references or scenes changed.

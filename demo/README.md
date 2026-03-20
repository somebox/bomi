# Demo Video Assets

This directory contains everything needed to produce the demo presentation for `bomi`.

The demo walks through a sample USB LED flashlight project and shows how to:

- initialize project metadata
- search and inspect parts
- compare alternatives
- select and validate a BOM
- export artifacts for review

## Structure

```text
build_site.py                   # repo root: regen site/presentation/ (wraps record_all)

demo/
  README.md
  script.md                     # scene-by-scene presenter script
  generator/
    cast_generator.py           # generates asciinema .cast files from scenes.yaml
    record_all.py               # implementation of build_site (casts + verify + deck copy)
    make_agent_demo.py          # synthetic agent-terminal cast
    scenes.yaml                 # scene definitions and commands
  presentation/
    index.html                  # Reveal.js source (copied to site/ on regen)
    demo-project/               # empty placeholder; scenes create usb-led-flashlight here when recording

site/presentation/              # GitHub Pages path /presentation/ (generated, commit with repo)
  index.html                    # copy of demo/presentation/index.html
  recordings/*.cast              # all terminal recordings (CLI + agent)
```

## Requirements

- `uv` (for running Python in project env)
- `asciinema` 3.x
- network access (live `bomi search/fetch` calls)

## Generate recordings (build site demo assets)

From repo root, use the single entrypoint (wraps `demo/generator/record_all.py`):

```bash
python build_site.py
```

This command:

1. runs all scenes from `demo/generator/scenes.yaml`
2. writes CLI `.cast` files to `site/presentation/recordings/`
3. verifies each CLI `.cast` via `asciinema convert`
4. writes `scene-agent-bom-review.cast` (scripted agent demo)
5. copies `demo/presentation/index.html` → `site/presentation/index.html`

Notes:

- **Commit** updated `site/presentation/` (`.cast` files and `index.html`) after a successful regen. GitHub Pages deploy uploads the committed `site/` tree only; it does not run `build_site.py` (avoids network flakiness in CI).
- `asciinema play` needs a TTY; CI or non-interactive shells may fail. `build_site.py` / `record_all.py` use conversion-based verification for reliability.
- The first scene removes and recreates `demo/presentation/demo-project/usb-led-flashlight` so reruns are deterministic (that tree is not tracked in git).

## Generate Single Scene

```bash
uv run python demo/generator/cast_generator.py \
  --scenes demo/generator/scenes.yaml \
  --scene scene-search-core-parts \
  --output-dir site/presentation/recordings
```

## Run Presentation

Serve the `site/` directory as the document root (matches GitHub Pages, where `site/` is published at `/`):

```bash
cd site && python -m http.server 8000
```

Open:

- `http://localhost:8000/presentation/` — Reveal deck; casts load from `presentation/recordings/`

## Editing Workflow

1. Update narration and flow in `demo/script.md`.
2. Update scene commands and timing in `demo/generator/scenes.yaml`.
3. Regenerate with `python build_site.py`, then **commit** `site/presentation/`.
4. Adjust slide text/layout in `demo/presentation/index.html`, then re-run `build_site.py` to refresh `site/presentation/index.html`.
5. Re-run generation if slide references or scenes changed.

## Maintenance Notes

For ongoing maintenance, tuning, and troubleshooting details, see:

- `demo/dev-notes.md`

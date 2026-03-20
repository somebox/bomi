# Demo Site and Video Maintenance Notes

This document is for maintainers of the demo slide deck and generated terminal recordings.

## What Is Source vs Generated

- Source files:
  - `demo/script.md` (story flow and narration)
  - `demo/generator/scenes.yaml` (recording scenario definitions)
  - `demo/generator/cast_generator.py` (cast generation logic)
  - `demo/generator/make_agent_demo.py` (synthetic agent cast)
  - `demo/presentation/index.html` (slide deck source; copied into `site/` on regen)
- Generated files:
  - `site/presentation/recordings/*.cast` (CLI scenes + `scene-agent-bom-review.cast`)
  - `site/presentation/index.html` (copy of demo deck for `/presentation/` on Pages)
  - `/tmp/bomi-cast-verify/*.txt` (verification artifacts, ephemeral)

Treat `site/presentation/*.cast` and `site/presentation/index.html` as **committed build outputs**: regenerate locally when scenes or generators change, then commit. The Pages workflow does not regenerate them.

## Standard Maintenance Workflow

1. Update scene flow in `demo/script.md` and `demo/generator/scenes.yaml`.
2. If needed, update generator behavior in `demo/generator/cast_generator.py`.
3. Regenerate all casts:

```bash
python build_site.py
```

4. Run and review the deck:

```bash
cd site && python -m http.server 8000
# open http://localhost:8000/presentation/
```

5. Verify that command summaries, timings, and table wrapping still look correct.
6. Commit changes under `site/presentation/` (and any related HTML) before pushing—deploy expects pre-built casts.

## When You Must Regenerate Videos

Regenerate casts when you change:

- `demo/generator/scenes.yaml` (commands, cols/rows, pauses, visibility)
- `demo/generator/cast_generator.py` (typing speed, cursor behavior, output handling)
- `demo/generator/make_agent_demo.py` (agent narrative / layout)
- CLI output formatting that appears in recordings (for example `src/bomi/output.py`)

Pure slide/CSS edits only require updating `site/presentation/index.html` (copy from `demo/presentation/index.html`, or run `build_site.py`, which recopies and also regenerates all casts).

## Scene Authoring Rules

### Keep demo pace practical

- Use short visible command sequences per slide.
- If a scene needs preconditions, use hidden setup commands:

```yaml
- cmd: "bomi select C8598 --ref D1 --qty 1 --notes \"...\""
  hidden: true
```

Hidden commands execute, but do not appear in the recorded playback.

### Avoid fragile commands

- Prefer deterministic commands and known-good search phrases.
- If a command can fail transiently, either stabilize it or mark it with `allow_failure: true` only when the failure is acceptable in narrative context.

### Keep output width aligned with slide layout

- Scene terminal size is controlled by `cols` / `rows` in `demo/generator/scenes.yaml`.
- Current target is tuned for deck readability (for example `cols: 75`).
- If lines clip or wrap poorly, adjust `cols` first, then player font sizing.

## Site Runtime Behavior (index.html)

The slide deck uses reveal.js with asciinema-player. Key behavior:

- players auto-initialize on slide load
- click on terminal area toggles play/pause
- control-strip interactions are excluded from the click-toggle handler
- terminal font is computed from panel width and recording columns
- deck content is top-aligned (`center: false`) to avoid vertical jump artifacts

### Font sizing model

`computeTerminalFontSize()` in `index.html` derives a font size from:

- terminal panel pixel width
- cast `cols`
- monospace width factor (`charWidthFactor`)

If text feels too large/small:

1. tune `cols` in `scenes.yaml`
2. tune `charWidthFactor` and clamps in `computeTerminalFontSize()`
3. re-check across at least two viewport sizes

## Compare Table Width Control

Wide compare rows are constrained in `src/bomi/output.py` via truncation helpers:

- `_truncate()`
- `_format_compare_table()`
- `_format_compare_markdown()`

If compare output overflows again, adjust truncation limits there first.

## Troubleshooting

### Recordings don’t play in browser

- Ensure you are using HTTP server mode, not `file://`.
- Open (with `site/` as cwd):
  - `http://localhost:8000/presentation/`

### `asciinema play` fails in non-interactive environment

- Expected in some environments due to TTY requirements.
- Use `build_site.py` / `record_all.py` verification (`asciinema convert -f txt`) instead.

### Scene fails during generation

- Re-run a single scene for faster debugging:

```bash
uv run python demo/generator/cast_generator.py \
  --scenes demo/generator/scenes.yaml \
  --scene scene-refine-validate \
  --output-dir site/presentation/recordings
```

Then inspect command validity in that scene.

## Review Checklist Before Sharing Demo

- Slide flow is coherent and concise.
- Each demo slide has:
  - concept bullets
  - key command block
  - matching recording
- Compare/BOM tables are readable at target viewport.
- End-of-scene cursor state looks intentional and not duplicated.
- No stale casts after scene or formatter changes.

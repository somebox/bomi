# Rename Plan: `jlcpcb-tool` → `bomi`

Rename the tool's own identity everywhere. JLCPCB and LCSC remain as vendor names in prose, URLs, and the API client. Only the tool's name, paths, env vars, and module name change.

## Scope

**Changes:** tool name, CLI command, Python module path, hidden project dir (`.jlcpcb/` → `.bomi/`), app data dir, env var prefix, docs filenames, site content, demo content.

**No changes:**
- `jlcpcb_url` data field — vendor URL column; renaming breaks the DB schema
- `JLCPCBClient` class — it is the JLCPCB vendor API client; other sources may be added later
- `JLCPCB_SEARCH_URL` constant — it is the vendor's API endpoint URL
- All `jlcpcb.com` URLs — real external endpoints
- All prose references to "JLCPCB" and "LCSC" as vendor names

---

## Execution Order

Steps are sequenced so the test suite can validate each phase before proceeding.

### Phase 1 — Python package (foundation)

**1a. Rename the source directory**

```bash
git mv src/jlcpcb_tool src/bomi
```

**1b. Update `pyproject.toml`** (4 changes):
- `name = "jlcpcb-tool"` → `"bomi"`
- `description` — update wording
- `jlcpcb = "jlcpcb_tool.cli:cli"` → `bomi = "bomi.cli:cli"`
- `packages = ["src/jlcpcb_tool"]` → `["src/bomi"]`

**1c. Fix all internal imports** across `src/bomi/*.py`:
- `from jlcpcb_tool.X` → `from bomi.X`
- `import jlcpcb_tool.X` → `import bomi.X`

**1d. Reinstall and smoke-test:**

```bash
uv sync
bomi --help
```

`uv.lock` is regenerated automatically by `uv sync`.

---

### Phase 2 — Runtime identity

**`src/bomi/config.py`** (~10 changes):
- `return base / "jlcpcb"` → `return base / "bomi"` (app data dir)
- `f"JLCPCB_{key.upper()}"` → `f"BOMI_{key.upper()}"` (env var prefix)
- `.jlcpcb/` → `.bomi/` (project dir path strings)
- `.jlcpcb/project.yaml` → `.bomi/project.yaml`
- Module docstring paths

**`src/bomi/cli.py`** (~10 changes):
- Error messages: `"Run 'jlcpcb init'"` → `"Run 'bomi init'"`
- Docstring examples: `jlcpcb datasheet ...` → `bomi datasheet ...`
- Any remaining `.jlcpcb/` path strings

**`src/bomi/project.py`** (~3 changes):
- Generated `project.yaml` comment: `jlcpcb datasheet CXXXXX` → `bomi datasheet CXXXXX`
- `.jlcpcb/` path strings

---

### Phase 3 — Tests

Move the misplaced root-level test file into the test suite:

```bash
git mv test_models.py tests/test_models.py
```

Then update `tests/test_models.py`:
- `JLCPCB_OPENROUTER_API_KEY` → `BOMI_OPENROUTER_API_KEY`
- `"jlcpcb"` in config path string → `"bomi"`
- `~/Library/Application Support/jlcpcb/` → `~/Library/Application Support/bomi/`

Sweep all test files for these patterns:

| Pattern | Replacement |
|---|---|
| `from jlcpcb_tool.X` | `from bomi.X` |
| `import jlcpcb_tool.X` | `import bomi.X` |
| `patch("jlcpcb_tool.X")` | `patch("bomi.X")` |
| `.jlcpcb/` | `.bomi/` |
| `JLCPCB_PROJECT` | `BOMI_PROJECT` |
| `JLCPCB_MY_SETTING` (test fixture) | `BOMI_MY_SETTING` |
| `d.name == "jlcpcb"` | `d.name == "bomi"` |
| `"jlcpcb" in str(d)` | `"bomi" in str(d)` |
| `".local/share/jlcpcb"` | `".local/share/bomi"` |
| `"jlcpcb-tool-guide.md"` | `"bomi-guide.md"` |

Run full test suite — should be green before proceeding:

```bash
uv run pytest
```

---

### Phase 4 — Root files

**`README.md`** (~50 changes):
- Title, badges, install instructions
- All CLI examples: `jlcpcb <cmd>` → `bomi <cmd>`
- Config paths: `.jlcpcb/` → `.bomi/`, data dir paths
- Env vars: `JLCPCB_*` → `BOMI_*`
- Project structure table: `src/jlcpcb_tool/` → `src/bomi/`
- Doc links: `jlcpcb-tool-guide.md` → `bomi-guide.md`, `jlcpcb-api-internals.md` → `bomi-api-internals.md`
- GitHub URL: `somebox/jlcpcb-tool` → `somebox/bomi` (update after repo rename in phase 8)

**`secrets.yaml.example`** (~5 changes):
- Header comment, config path comments
- Env var pattern `JLCPCB_<KEY>` → `BOMI_<KEY>`
- Command examples: `jlcpcb analyze` → `bomi analyze`, `jlcpcb datasheet` → `bomi datasheet`

---

### Phase 5 — Docs

| File | Operation | Notes |
|---|---|---|
| `docs/jlcpcb-tool-guide.md` | **RENAME** to `docs/bomi-guide.md` + edit | Title, all `jlcpcb <cmd>` examples, `.jlcpcb/` paths, env vars |
| `docs/jlcpcb-api-internals.md` | **RENAME** to `docs/bomi-api-internals.md` + edit | Keep JLCPCB/LCSC vendor prose; update `jlcpcb-tool` name refs, `src/jlcpcb_tool/` paths, `JLCPCB_OPENROUTER_API_KEY` |
| `docs/examples.md` | EDIT | All `jlcpcb <cmd>` → `bomi <cmd>`, env vars, paths, doc links |
| `docs/sqlite-database-guide.md` | EDIT | Title, data dir paths, `src/jlcpcb_tool/db.py` path |
| `docs/project-feature-plan.md` | EDIT | Tool name, CLI examples, `.jlcpcb/` paths, env vars, `src/jlcpcb_tool/` paths |

```bash
git mv docs/jlcpcb-tool-guide.md docs/bomi-guide.md
git mv docs/jlcpcb-api-internals.md docs/bomi-api-internals.md
```

---

### Phase 6 — Static site

All 4 HTML files share the same nav logo and footer pattern. Sweep each for:

| Pattern | Replacement |
|---|---|
| `jlcpcb<span>-tool</span>` (nav logo) | `bomi` |
| `jlcpcb-tool v__BUILD_VERSION__` (footer) | `bomi v__BUILD_VERSION__` |
| `jlcpcb <cmd>` in code blocks | `bomi <cmd>` |
| `.jlcpcb/project.yaml` | `.bomi/project.yaml` |
| `JLCPCB_PROJECT` | `BOMI_PROJECT` |
| `JLCPCB_OPENROUTER_API_KEY` | `BOMI_OPENROUTER_API_KEY` |
| GitHub URL `somebox/jlcpcb-tool` | `somebox/bomi` |
| Site URL `somebox.github.io/jlcpcb-tool` | `somebox.github.io/bomi` |
| `<title>jlcpcb-tool` | `<title>bomi` |

Files: `site/index.html`, `site/guide.html`, `site/examples.html`, `site/vibe.html`

---

### Phase 7 — Demo text files

**`demo/generator/scenes.yaml`** (~50 changes):
- Scene id `scene-init-jlcpcb` → `scene-init-bomi`
- Scene title `"Initialize jlcpcb Project"` → `"Initialize bomi Project"`
- All `cmd: "jlcpcb <cmd>"` entries → `cmd: "bomi <cmd>"`
- `ls -la .jlcpcb` → `ls -la .bomi`
- `working_dir` paths containing `jlcpcb-tool` → update to new repo path (if folder is renamed before re-recording)

**`demo/presentation/index.html`** (~25 changes):
- Title, heading
- `scene-init-jlcpcb.cast` reference → `scene-init-bomi.cast`
- All `jlcpcb <cmd>` code blocks
- `.jlcpcb/` path strings

**`demo/generator/make_agent_demo.py`** (~6 changes):
- Module docstring
- All `jlcpcb <cmd>` strings in `s.tool("Bash", ...)` calls

**`demo/generator/record_all.py`** (~2 changes):
- Help text: `"jlcpcb-tool repository root"` → `"bomi repository root"`
- Temp dir: `/tmp/jlcpcb-cast-verify` → `/tmp/bomi-cast-verify`

**`demo/generator/dev-notes.md`** (~3 changes):
- `jlcpcb-tool` name references
- `src/jlcpcb_tool/output.py` path → `src/bomi/output.py`
- `/tmp/jlcpcb-cast-verify/` path

**`demo/README.md`** (~3 changes):
- Tool name in intro
- `jlcpcb search/fetch` CLI references → `bomi search/fetch`
- `network access (live jlcpcb search/fetch calls)` → `bomi search/fetch`

**`demo/script.md`** (~35 changes):
- Title, all CLI examples, `.jlcpcb/` paths, `jlcpcb init` → `bomi init`

**Demo project fixture:**

```bash
git mv demo/presentation/demo-project/usb-led-flashlight/.jlcpcb \
       demo/presentation/demo-project/usb-led-flashlight/.bomi
```

The `project.yaml` inside has no `jlcpcb` strings — no content edit needed.

**`demo/presentation/demo-project/usb-led-flashlight/.gitignore`** (1 change):
- Comment `jlcpcb datasheet CXXXXX` → `bomi datasheet CXXXXX`

---

### Phase 8 — `.claude/settings.local.json`

This file controls Claude's tool permissions for the project. Update the `jlcpcb` CLI allow-list entries. Run this script from the repo root:

```bash
python3 - <<'EOF'
import json, re
from pathlib import Path

p = Path(".claude/settings.local.json")
text = p.read_text()

# Replace Bash allow entries for the CLI command
text = re.sub(r'"Bash\(jlcpcb([ :])', r'"Bash(bomi\1', text)

# Replace git log grep path if present
text = text.replace(
    'git -C /Users/foz/src/jlcpcb-tool',
    'git -C /Users/foz/src/bomi'
)

p.write_text(text)
print("Updated .claude/settings.local.json")
print(p.read_text())
EOF
```

Verify the result looks correct before saving. The `WebFetch(domain:jlcpcb.com)` entry stays — it is the vendor domain.

---

### Phase 9 — Cast recordings (rebuild)

Cast files are binary terminal recordings. The `jlcpcb` command strings baked into them cannot be text-edited — they must be regenerated after the rename is complete and `bomi` is installed.

**Rename the one file that also needs a filename change:**

```bash
git mv demo/presentation/recordings/scene-init-jlcpcb.cast \
       demo/presentation/recordings/scene-init-bomi.cast
```

**Rebuild all recordings:**

```bash
uv sync                          # ensure bomi is installed in the env
python demo/generator/record_all.py
```

This regenerates all `.cast` files in `demo/presentation/recordings/`. The `site/recordings/` directory (used by the public site) also needs rebuilding if it exists separately — check whether it is a copy or symlink of the demo recordings.

Single-scene rebuild for faster iteration:

```bash
uv run python demo/generator/cast_generator.py \
  --scenes demo/generator/scenes.yaml \
  --scene scene-init-bomi \
  --output-dir demo/presentation/recordings
```

---

### Phase 10 — GitHub repo rename (manual, last step)

After all code changes are committed and pushed:

1. Rename repo on GitHub: Settings → Repository name → `bomi`
2. Update the remote in your local clone:
   ```bash
   git remote set-url origin https://github.com/somebox/bomi.git
   ```
3. Optionally rename the local folder:
   ```bash
   cd .. && mv jlcpcb-tool bomi && cd bomi
   ```
4. GitHub Pages URL changes from `somebox.github.io/jlcpcb-tool` → `somebox.github.io/bomi` — already handled in phases 4–6 above.

---

## Dark corners to check

These are easy to miss in a bulk find-replace pass:

- **`demo/generator/scenes.yaml` `working_dir` paths** — these are absolute paths to the local repo. They contain `jlcpcb-tool` in the path. They need updating if the repo folder is renamed (phase 10), or they will break recording generation. Consider making these relative or parameterised.
- **`test_models.py` at repo root** — this file is outside `tests/` and is not picked up by `pytest` by default (check `pyproject.toml` `testpaths`). Move it to `tests/test_models.py` in phase 3.
- **`site/recordings/` vs `demo/presentation/recordings/`** — verify whether these are the same files, a copy, or a symlink. The site build may copy them. Check `.github/workflows/pages.yml` to understand the build pipeline.
- **`uv.lock`** — regenerated by `uv sync`, but if the lock file is committed, commit it after phase 1d.
- **`__pycache__` directories** — will contain stale `.pyc` files referencing `jlcpcb_tool`. These are gitignored and will be rebuilt automatically; no action needed.
- **Any shell scripts or Makefiles** — check for `jlcpcb` command invocations. (None found in current inventory, but worth a final `rg 'jlcpcb' --type sh` sweep.)
- **`demo/generator/cast_generator.py`** — the generator itself may reference the working dir or tool name in log messages. Check before re-recording.
- **`demo/generator/record_all.py` temp dir** — `/tmp/jlcpcb-cast-verify` is used for verification artifacts. Update to `/tmp/bomi-cast-verify` in phase 7 so post-rename verification output is not confusingly named.
- **Existing user data** — any project using `.jlcpcb/` will silently stop working after install. Consider adding a one-time migration check in `cli.py`: if `.jlcpcb/` exists and `.bomi/` does not, print a migration hint.

---

## Final verification checklist

```bash
# No tool-identity jlcpcb refs remain in source or docs
rg -i 'jlcpcb.tool|jlcpcb_tool|\.jlcpcb|JLCPCB_PROJECT|JLCPCB_OPENROUTER' \
  --type py --type md --type html --type toml --type yaml

# Package installs and CLI works
uv sync && bomi --help

# Full test suite passes
uv run pytest

# Demo recordings build cleanly
python demo/generator/record_all.py
```

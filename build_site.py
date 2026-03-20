#!/usr/bin/env python3
"""Regenerate GitHub Pages demo assets under site/presentation/.

Runs the full pipeline (terminal casts, agent cast, Reveal deck copy). This is a
thin wrapper around demo/generator/record_all.py so there is one obvious command
from the repo root.

  python build_site.py                # default: verify casts with asciinema
  python build_site.py --skip-verify  # faster iteration

Requires: uv, asciinema (unless --skip-verify), network for live bomi commands.
Commit site/presentation/ after a successful run. See demo/README.md.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
_RECORD_ALL = _REPO_ROOT / "demo" / "generator" / "record_all.py"


def main() -> int:
    if not _RECORD_ALL.is_file():
        print(f"Missing {_RECORD_ALL}", file=sys.stderr)
        return 1
    cmd = [sys.executable, str(_RECORD_ALL), *sys.argv[1:]]
    return subprocess.call(cmd, cwd=str(_REPO_ROOT))


if __name__ == "__main__":
    raise SystemExit(main())

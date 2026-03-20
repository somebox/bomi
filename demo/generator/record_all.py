#!/usr/bin/env python3
"""Run all demo recording scenes, agent cast, Reveal deck sync; verify .cast files.

Prefer invoking from the repo root (same behavior):

  python build_site.py

Default output layout matches GitHub Pages (site/ artifact):

  site/presentation/index.html          <- copied from demo/presentation/index.html
  site/presentation/recordings/*.cast    <- CLI scenes + scene-agent-bom-review.cast
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd), check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Path to bomi repository root",
    )
    parser.add_argument(
        "--scenes",
        default="demo/generator/scenes.yaml",
        help="Scene YAML path (relative to repo root by default)",
    )
    parser.add_argument(
        "--output-dir",
        default="site/presentation/recordings",
        help="Output directory for generated CLI cast files",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip cast verification via asciinema convert",
    )
    parser.add_argument(
        "--no-copy-deck",
        action="store_true",
        help="Do not copy demo/presentation/index.html -> site/presentation/index.html",
    )
    parser.add_argument(
        "--skip-agent-demo",
        action="store_true",
        help="Do not run make_agent_demo.py (synthetic agent cast)",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve()
    scenes = Path(args.scenes)
    output_dir = Path(args.output_dir)
    if not scenes.is_absolute():
        scenes = repo_root / scenes
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir

    output_dir.mkdir(parents=True, exist_ok=True)

    run(
        [
            "uv",
            "run",
            "python",
            "demo/generator/cast_generator.py",
            "--scenes",
            str(scenes),
            "--output-dir",
            str(output_dir),
        ],
        cwd=repo_root,
    )

    if not args.skip_verify:
        verify_dir = Path("/tmp/bomi-cast-verify")
        verify_dir.mkdir(parents=True, exist_ok=True)
        for cast_file in sorted(output_dir.glob("*.cast")):
            txt_out = verify_dir / f"{cast_file.stem}.txt"
            run(
                [
                    "asciinema",
                    "convert",
                    "-f",
                    "txt",
                    str(cast_file),
                    str(txt_out),
                    "--overwrite",
                ],
                cwd=repo_root,
            )
        print(f"verified: {len(list(output_dir.glob('*.cast')))} cast files")

    if not args.skip_agent_demo:
        agent_out = output_dir / "scene-agent-bom-review.cast"
        run(
            [
                "uv",
                "run",
                "python",
                "demo/generator/make_agent_demo.py",
                "--output",
                str(agent_out),
            ],
            cwd=repo_root,
        )

    if not args.no_copy_deck:
        src = repo_root / "demo" / "presentation" / "index.html"
        dst_dir = repo_root / "site" / "presentation"
        dst = dst_dir / "index.html"
        if not src.is_file():
            raise SystemExit(f"Reveal deck not found: {src}")
        dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"copied deck: {dst}")

    print("done.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"Command failed with exit code {exc.returncode}", file=sys.stderr)
        raise SystemExit(exc.returncode)

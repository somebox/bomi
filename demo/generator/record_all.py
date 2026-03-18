#!/usr/bin/env python3
"""Run all demo recording scenes and verify resulting .cast files."""

from __future__ import annotations

import argparse
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
        help="Path to jlcpcb-tool repository root",
    )
    parser.add_argument(
        "--scenes",
        default="demo/generator/scenes.yaml",
        help="Scene YAML path (relative to repo root by default)",
    )
    parser.add_argument(
        "--output-dir",
        default="demo/presentation/recordings",
        help="Output directory for generated cast files",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip cast verification via asciinema convert",
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
        verify_dir = Path("/tmp/jlcpcb-cast-verify")
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

    print("done.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"Command failed with exit code {exc.returncode}", file=sys.stderr)
        raise SystemExit(exc.returncode)

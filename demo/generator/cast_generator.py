#!/usr/bin/env python3
"""Generate asciinema v3 .cast recordings from scene definitions."""

from __future__ import annotations

import argparse
import json
import os
import pty
import random
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class EventStream:
    """Collect asciicast events as interval-coded tuples."""

    events: list[list[Any]]
    elapsed: float = 0.0

    def wait(self, seconds: float) -> None:
        if seconds > 0:
            self.elapsed += seconds

    def output(self, text: str, delay: float = 0.0) -> None:
        self.events.append([round(max(0.0, self.elapsed + delay), 3), "o", text])
        self.elapsed = 0.0

    def marker(self, label: str = "", delay: float = 0.0) -> None:
        self.events.append([round(max(0.0, self.elapsed + delay), 3), "m", label])
        self.elapsed = 0.0

    def exit(self, code: int = 0, delay: float = 0.0) -> None:
        self.events.append([round(max(0.0, self.elapsed + delay), 3), "x", str(code)])
        self.elapsed = 0.0


def _expand_path(path_text: str) -> Path:
    return Path(path_text).expanduser().resolve()


def _prompt_for(cwd: Path) -> str:
    # Keep a colorful prompt so recordings are easier to scan.
    return f"\x1b[1;34m{cwd.name}\x1b[0m \x1b[1;32m$\x1b[0m "


def _is_simple_cd(cmd: str) -> bool:
    stripped = cmd.strip()
    return stripped.startswith("cd ") and "&&" not in stripped and ";" not in stripped


def _run_command(command: str, cwd: Path, env: dict[str, str]) -> tuple[int, str]:
    master_fd, slave_fd = pty.openpty()
    chunks: list[bytes] = []
    try:
        proc = subprocess.Popen(
            command,
            cwd=str(cwd),
            shell=True,
            stdin=subprocess.DEVNULL,
            stdout=slave_fd,
            stderr=slave_fd,
            env=env,
        )
        os.close(slave_fd)

        os.set_blocking(master_fd, False)
        while True:
            try:
                data = os.read(master_fd, 65536)
                if data:
                    chunks.append(data)
            except BlockingIOError:
                pass
            except OSError:
                break

            if proc.poll() is not None:
                while True:
                    try:
                        data = os.read(master_fd, 65536)
                        if not data:
                            break
                        chunks.append(data)
                    except (BlockingIOError, OSError):
                        break
                break
            time.sleep(0.01)

        return_code = proc.wait()
        output_text = b"".join(chunks).decode("utf-8", errors="replace")
        return return_code, output_text
    finally:
        try:
            os.close(master_fd)
        except OSError:
            pass


def _type_command(
    stream: EventStream,
    prompt: str,
    command: str,
    rng: random.Random,
    type_min: float,
    type_max: float,
) -> None:
    stream.output(prompt)
    for ch in command:
        stream.wait(rng.uniform(type_min, type_max))
        stream.output(ch)
    stream.wait(rng.uniform(type_min, type_max))
    stream.output("\r\n")


def _emit_command_spacing(stream: EventStream) -> None:
    """Insert one blank line after each command block."""
    stream.output("\r\n")


def _emit_idle_prompt_with_cursor_blink(
    stream: EventStream,
    prompt: str,
    blink_cycles: int = 3,
    on_time: float = 0.62,
    off_time: float = 0.56,
) -> None:
    """Finish scene on idle prompt with slower terminal cursor blink."""
    # Make sure cursor is visible before drawing final prompt.
    stream.output("\x1b[?25h")
    stream.output(prompt)
    for _ in range(blink_cycles):
        stream.wait(off_time)
        stream.output("\x1b[?25l")
        stream.wait(on_time)
        stream.output("\x1b[?25h")


def _load_scene_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict) or "scenes" not in data or not isinstance(data["scenes"], list):
        raise ValueError(f"Invalid scenes file: {path}")
    return data


def generate_scene(scene: dict[str, Any], output_dir: Path, dry_run: bool = False) -> Path:
    scene_id = scene["id"]
    title = scene.get("title", scene_id)
    cols = int(scene.get("cols", 120))
    rows = int(scene.get("rows", 30))
    shell_type = scene.get("shell", "/bin/zsh")
    type_min = float(scene.get("typing_delay_min", 0.018))
    type_max = float(scene.get("typing_delay_max", 0.055))
    line_delay = float(scene.get("line_delay", 0.07))
    command_delay = float(scene.get("command_delay", 0.35))
    initial_pause = float(scene.get("initial_pause", 0.35))

    working_dir = _expand_path(scene.get("working_dir", "."))
    if not working_dir.exists():
        raise FileNotFoundError(f"Scene working_dir does not exist: {working_dir}")

    stream = EventStream(events=[])
    rng = random.Random(scene.get("seed", scene_id))
    env = dict(os.environ)
    env["PATH"] = f"{Path.home() / '.local/bin'}:{env.get('PATH', '')}"
    env.setdefault("TERM", "xterm-256color")
    env.setdefault("CLICOLOR_FORCE", "1")
    env.setdefault("FORCE_COLOR", "1")

    commands = scene.get("commands", [])
    if not commands:
        raise ValueError(f"Scene has no commands: {scene_id}")

    stream.wait(initial_pause)
    stream.marker(scene_id)

    current_dir = working_dir
    for item in commands:
        if not isinstance(item, dict) or "cmd" not in item:
            raise ValueError(f"Scene '{scene_id}' has invalid command entry: {item!r}")
        cmd = str(item["cmd"])
        hidden = bool(item.get("hidden", False))
        # Keep readable spacing, but allow faster command-heavy scenes.
        min_pause_after = float(scene.get("min_pause_after", 0.35))
        pause_after = max(float(item.get("pause_after", 0.7)), min_pause_after)
        allow_failure = bool(item.get("allow_failure", False))

        if not hidden:
            _type_command(stream, _prompt_for(current_dir), cmd, rng, type_min, type_max)
            stream.wait(command_delay)

        if _is_simple_cd(cmd):
            target = cmd.strip()[3:].strip()
            next_dir = _expand_path(target if target.startswith("/") else str(current_dir / target))
            if next_dir.exists():
                current_dir = next_dir
            else:
                if not hidden:
                    stream.output(f"cd: no such file or directory: {target}\r\n", delay=line_delay)
        else:
            if dry_run:
                if not hidden:
                    stream.output("[dry-run] command output skipped\r\n", delay=line_delay)
                return_code = 0
            else:
                return_code, output_text = _run_command(cmd, current_dir, env)
                if output_text and not hidden:
                    # Emit command output line-by-line to keep replay readable.
                    for line in output_text.splitlines(keepends=True):
                        stream.wait(line_delay)
                        stream.output(line.replace("\n", "\r\n"))
                if return_code != 0 and not hidden:
                    stream.wait(line_delay)
                    stream.output(f"[exit {return_code}] {cmd}\r\n")
                if return_code != 0 and not allow_failure:
                    raise RuntimeError(
                        f"Scene '{scene_id}' command failed (exit {return_code}): {cmd}"
                    )

        if not hidden:
            _emit_command_spacing(stream)
        stream.wait(pause_after)

    stream.wait(0.35)
    _emit_idle_prompt_with_cursor_blink(stream, _prompt_for(current_dir))
    stream.wait(0.25)

    header = {
        "version": 3,
        "term": {"cols": cols, "rows": rows, "type": "xterm-256color"},
        "timestamp": int(time.time()),
        "title": title,
        "command": shell_type,
        "env": {"SHELL": shell_type},
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{scene_id}.cast"
    with out_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(header) + "\n")
        for event in stream.events:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenes",
        default=str(Path(__file__).with_name("scenes.yaml")),
        help="Path to scenes YAML file",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).parents[1] / "presentation" / "recordings"),
        help="Directory for generated .cast files",
    )
    parser.add_argument("--scene", help="Generate only one scene by id")
    parser.add_argument("--dry-run", action="store_true", help="Skip command execution")
    args = parser.parse_args()

    scenes_file = Path(args.scenes).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    data = _load_scene_file(scenes_file)

    scenes = data["scenes"]
    if args.scene:
        scenes = [s for s in scenes if s.get("id") == args.scene]
        if not scenes:
            raise SystemExit(f"Scene id not found: {args.scene}")

    generated: list[Path] = []
    for scene in scenes:
        out_path = generate_scene(scene, output_dir=output_dir, dry_run=args.dry_run)
        generated.append(out_path)
        print(f"generated: {out_path}")

    print(f"done: {len(generated)} scene(s)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130)

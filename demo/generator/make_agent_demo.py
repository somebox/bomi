#!/usr/bin/env python3
"""Generate a scripted agent-chat demo cast file.

Simulates an AI agent session running bomi tool calls for a BOM stock review.
Default output: site/presentation/recordings/scene-agent-bom-review.cast

All timing is in whole milliseconds. Asciinema v3 uses *relative* timestamps
(delta from the previous event), not absolute offsets from the start.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

COLS = 90
ROWS = 28

# ── ANSI ─────────────────────────────────────────────────────────────────────
RST   = "\x1b[0m"
BOLD  = "\x1b[1m"
DIM   = "\x1b[2m"
GREEN = "\x1b[32m"
BGRN  = "\x1b[92m"   # bright green
BLUE  = "\x1b[94m"
CYAN  = "\x1b[96m"
RED   = "\x1b[91m"
YEL   = "\x1b[93m"
GREY  = "\x1b[90m"
WHT   = "\x1b[97m"

HIDE = "\x1b[?25l"
SHOW = "\x1b[?25h"
CLR  = "\r\x1b[2K"

# UI chrome
PROMPT = f"{BLUE}❯{RST} "
BULLET = f"{BGRN}⏺{RST}"


# ── Stream ────────────────────────────────────────────────────────────────────

class Stream:
    """Accumulates cast events. All timing in whole milliseconds.
    Asciinema v3 timestamps are deltas from the previous event.
    """

    def __init__(self) -> None:
        self.events: list[list] = []
        self._ms: int = 0
        self._last_ms: int = 0

    def wait(self, ms: int) -> None:
        self._ms += ms

    def out(self, text: str) -> None:
        delta = self._ms - self._last_ms
        self.events.append([round(delta / 1000, 3), "o", text])
        self._last_ms = self._ms

    def ln(self, text: str = "", wait_ms: int = 0) -> None:
        self.wait(wait_ms)
        self.out(text + "\r\n")

    def type(self, text: str, char_ms: int = 35, jitter_ms: int = 12) -> None:
        """Emit text char-by-char. Each char waits char_ms + rand(0..jitter_ms)."""
        rng = random.Random(42)
        for ch in text:
            self.wait(char_ms + rng.randint(0, jitter_ms))
            self.out(ch)

    def tool(self, name: str, args: str) -> None:
        """Emit a tool-call line."""
        self.out(f"\r\n{BULLET} {BOLD}{name}{RST}({GREY}{args}{RST})\r\n")

    def output_block(self, lines: list[str], delay_ms: int = 80) -> None:
        """Emit indented output lines; first gets the corner bracket."""
        for i, line in enumerate(lines):
            self.wait(delay_ms)
            pfx = f"  {GREY}⎿{RST}  " if i == 0 else "     "
            self.out(pfx + line + "\r\n")

    def dots(self, n: int = 3, interval_ms: int = 380) -> None:
        for _ in range(n):
            self.wait(interval_ms)
            self.out(".")

    def dumps(self) -> str:
        header = {
            "version": 3,
            "term": {"cols": COLS, "rows": ROWS, "type": "xterm-256color"},
            "timestamp": 1740000000,
            "title": "Agent: multi-project stock review",
        }
        lines = [json.dumps(header)]
        for e in self.events:
            lines.append(json.dumps(e))
        return "\n".join(lines) + "\n"


# ── Table helpers ─────────────────────────────────────────────────────────────
# Column widths: Project(22), Ref(8), Part(27), Stock(7), Risk(4)
_W = (22, 8, 27, 7, 4)

def _border(left: str, mid: str, right: str) -> str:
    segs = ["─" * (w + 2) for w in _W]
    return "  " + left + mid.join(segs) + right

T_TOP = _border("┌", "┬", "┐")
T_SEP = _border("├", "┼", "┤")
T_BOT = _border("└", "┴", "┘")
T_HDR = (f"  │ {'Project':<{_W[0]}} │ {'Ref':<{_W[1]}} │ {'Part':<{_W[2]}} │"
         f" {'Stock':>{_W[3]}} │ {'Risk':<{_W[4]}} │")

def trow(proj: str, ref: str, part: str, stock: str, risk: str) -> str:
    rc = RED if risk == "HIGH" else YEL
    return (f"  │ {proj:<{_W[0]}} │ {ref:<{_W[1]}} │ {part:<{_W[2]}} │"
            f" {rc}{stock:>{_W[3]}}{RST} │ {rc}{risk:<{_W[4]}}{RST} │")


# ── Scene ─────────────────────────────────────────────────────────────────────

def build() -> Stream:
    s = Stream()

    # ── Start already inside the agent ───────────────────────────────────────
    s.wait(300)
    s.out(SHOW)
    s.out(f"{BULLET} How can I help?\r\n\r\n")
    s.wait(200)
    s.out(PROMPT)

    # ── User types request ────────────────────────────────────────────────────
    s.wait(400)
    s.type("check my rgb-spotlight BOM stock levels, suggest replacements where needed")
    s.wait(500)
    s.out("\r\n")

    # ── Agent acknowledges ────────────────────────────────────────────────────
    s.wait(350)
    s.out(f"\r\n{BULLET} Let me check the rgb-spotlight BOM and stock levels.\r\n")

    # ── Tool: list (rgb-spotlight) ────────────────────────────────────────────
    s.wait(400)
    s.tool("Bash", "bomi --project ~/pcb/rgb-spotlight list --check")
    s.wait(650)
    s.output_block([
        f"  Ref   LCSC         Qty  Part                          Stock    Price",
        f"  ----  -----------  ---  ----------------------------  -------  ------",
        f"  LED1  C49237857      3  HD2525 RGB Red 625nm          {RED}  1,100{RST}  $0.031  {RED}⚠{RST}",
        f"  LED2  C49237859      3  HD2525 RGB Green 525nm        {RED}  2,085{RST}  $0.028  {RED}⚠{RST}",
        f"  LED3  C49237860      3  HD2525 RGB Blue 455nm         {RED}  2,001{RST}  $0.027  {RED}⚠{RST}",
        f"  U7    C350557        1  SN74AHCT1G125 SC-70-5         {RED}  2,837{RST}  $0.071  {RED}⚠{RST}",
        f"  {DIM}… +9 lines (ctrl+o to expand){RST}",
    ])

    # ── Tool: list (esphome-dimmer) ───────────────────────────────────────────
    s.wait(300)
    s.tool("Bash", "bomi --project ~/pcb/esphome-dimmer list --check")
    s.wait(650)
    s.output_block([
        f"  Ref    LCSC         Qty  Part                          Stock    Price",
        f"  -----  -----------  ---  ----------------------------  -------  ------",
        f"  C2/C3  C49326690      2  47µF 6.3V X5R 0805           {YEL}  3,221{RST}  $0.042  {YEL}⚠{RST}",
        f"  SW1    C361165        1  EC11E rotary encoder          {YEL}  3,059{RST}  $0.342  {YEL}⚠{RST}",
        f"  {DIM}… +14 lines (ctrl+o to expand){RST}",
    ])

    # ── Tool: list (usb-led-flashlight) ───────────────────────────────────────
    s.wait(300)
    s.tool("Bash", "bomi --project ~/pcb/usb-led-flashlight list --check")
    s.wait(650)
    s.output_block([
        f"  Ref      LCSC        Qty  Part                      Stock    Price",
        f"  -------  ----------  ---  ------------------------  -------  ------",
        f"  L1       C354577       1  47µH inductor 4030        {RED}  2,710{RST}  $0.049  {RED}⚠{RST}",
        f"  SW1/SW2  C49023761     2  tact switch 3×4mm         {YEL}  4,433{RST}  $0.018  {YEL}⚠{RST}",
        f"  {DIM}… +6 lines (ctrl+o to expand){RST}",
    ])

    # ── Stock summary table ───────────────────────────────────────────────────
    s.wait(400)
    s.out(f"\r\n{BULLET} 5 items with low stock across 3 projects:\r\n\r\n")

    for row in [
        T_TOP, T_HDR, T_SEP,
        trow("rgb-spotlight",       "LED1-3", "HD2525 RGB LEDs",                "1,100", "HIGH"),
        trow("rgb-spotlight",       "U7",     "SN74AHCT1G125 SC-70-5",          "2,837", "HIGH"),
        trow("usb-led-flashlight",  "L1",     "47µH inductor 4030",             "2,710", "HIGH"),
        trow("esphome-dimmer",      "C2/C3",  "47µF 6.3V X5R 0805",            "3,221", "MED"),
        trow("esphome-dimmer",      "SW1",    "EC11E rotary encoder",           "3,059", "MED"),
        T_BOT,
    ]:
        s.wait(150)
        s.out(row + "\r\n")

    # ── Search for inductor replacement ──────────────────────────────────────
    s.wait(1200)
    s.out(f"\r\n{BULLET} Searching for replacements...\r\n")
    s.wait(400)
    s.tool("Bash", "bomi search \"47uH inductor SMD 4030\" --limit 5")
    s.wait(700)
    s.output_block([
        f"  LCSC       MFR Part               Package    Stock    Price   Type",
        f"  C167888    FNR4030S470MT          4030     {GREEN}147,733{RST}  $0.049  Basic",
        f"  C408330    SWPA4030S470MT         4030      {GREEN}82,451{RST}  $0.038  Basic",
        f"  {DIM}… +5 lines (ctrl+o to expand){RST}",
    ])

    # ── Search for level shifter replacement ─────────────────────────────────
    s.wait(1400)
    s.tool("Bash", "bomi search \"SN74AHCT1G125 SOT-23-5\" --limit 5")
    s.wait(700)
    s.output_block([
        f"  LCSC      MFR Part                 Package      Stock   Price   Type",
        f"  C7484     SN74AHCT1G125DBVR         SOT-23-5  {GREEN}15,677{RST}  $0.096  Basic",
        f"  {DIM}… +4 lines (ctrl+o to expand){RST}",
    ])

    # ── Recommendations ───────────────────────────────────────────────────────
    s.wait(450)
    recs = [
        (0,   f"\r\n{BULLET} Recommendations:\r\n"),
        (200, f"\r\n  {BOLD}usb-led-flashlight{RST} · L1 (47µH inductor)"),
        (120, f"  Swap {GREY}C354577{RST} → {BOLD}C167888{RST} FNR4030S470MT"
              f"  {DIM}same 4030 footprint · 147k in stock{RST}"),
        (200, f"\r\n  {BOLD}rgb-spotlight{RST} · U7 (level shifter)"),
        (120, f"  Swap {GREY}C350557{RST} → {BOLD}C7484{RST} SN74AHCT1G125DBVR"
              f"  {DIM}SOT-23-5 · 15k in stock · footprint swap needed{RST}"),
        (200, f"\r\n  {BOLD}rgb-spotlight{RST} · LED1-3 (HD2525 RGB)"),
        (120, f"  No same-footprint alternatives in stock. Order before these run out."),
        (200, f"\r\n  {DIM}esphome-dimmer C2/C3 and SW1: moderate risk, monitor but not urgent.{RST}"),
    ]
    for ms, line in recs:
        s.wait(ms)
        s.out(line + "\r\n")

    # ── Final question + waiting prompt ──────────────────────────────────────
    s.wait(350)
    s.out(f"\r\n  Want me to update any of the BOMs with these swaps?\r\n")
    s.wait(700)
    s.out(f"\r\n{PROMPT}")

    # Hold on final frame
    for _ in range(7):
        s.wait(650)
        s.out(HIDE)
        s.wait(600)
        s.out(SHOW)

    return s


# ── Main ──────────────────────────────────────────────────────────────────────

def _avg_ms_per_char(events: list) -> float:
    typed = [e for e in events if e[1] == "o" and len(e[2]) == 1
             and e[2] not in ("\r", "\n") and e[2].isprintable() and e[0] < 0.1]
    return sum(e[0] for e in typed) / len(typed) * 1000 if typed else 0


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    default_out = repo_root / "site" / "presentation" / "recordings" / "scene-agent-bom-review.cast"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=default_out,
        help="Path for generated .cast file",
    )
    args = parser.parse_args()
    out_path = args.output.expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    stream = build()
    out_path.write_text(stream.dumps(), encoding="utf-8")
    total_s = sum(e[0] for e in stream.events)
    print(f"wrote {out_path}  ({len(stream.events)} events)")
    print(f"avg typing: {_avg_ms_per_char(stream.events):.0f}ms/char")
    print(f"total duration: {total_s:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

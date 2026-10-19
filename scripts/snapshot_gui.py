"""Render the main window off-screen to a PNG for design review (docs/design-guide.md §4).

    uv run python scripts/snapshot_gui.py --out docs/design/snapshots/main-window.png
    uv run python scripts/snapshot_gui.py --out /tmp/w.png --width 1600 --height 1000

Needs the [gui] extra (``uv sync --extra dev --extra gui``). Sets QT_QPA_PLATFORM=offscreen
unless you already chose a platform, so it works on headless machines and in CI.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out", default=str(REPO_ROOT / "docs/design/snapshots/main-window.png"))
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=800)
    args = parser.parse_args(argv)

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from opentcad.gui.app import snapshot

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        path = snapshot(str(out), args.width, args.height)
    except SystemExit as exc:  # raised by gui.app when PySide6 is missing
        print(exc, file=sys.stderr)
        return 1
    print(f"wrote {path} ({os.path.getsize(path)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

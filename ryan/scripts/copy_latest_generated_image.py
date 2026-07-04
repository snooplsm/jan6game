#!/usr/bin/env python3
"""Copy the newest Codex-generated image into the synthetic people set."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CODEX_HOME = Path.home() / ".codex"


def latest_generated_png(codex_home: Path) -> Path:
    generated_root = codex_home / "generated_images"
    candidates = list(generated_root.glob("*/*.png"))
    if not candidates:
        raise FileNotFoundError(f"No generated PNG files found under {generated_root}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("person_id")
    parser.add_argument(
        "--view",
        choices=["front", "side", "back", "none"],
        default="front",
        help="Image view suffix to write. Use 'none' for the legacy person_id.png filename.",
    )
    parser.add_argument(
        "--codex-home",
        default=os.environ.get("CODEX_HOME", str(DEFAULT_CODEX_HOME)),
        type=Path,
    )
    args = parser.parse_args()

    source = latest_generated_png(args.codex_home)
    out_dir = ROOT / "generated_people_corrected" / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = "" if args.view == "none" else f"_{args.view}"
    target = out_dir / f"{args.person_id}{suffix}.png"
    shutil.copy2(source, target)
    print(f"Copied {source} -> {target}")


if __name__ == "__main__":
    main()

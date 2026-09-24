#!/usr/bin/env python3
"""Fetch the official Inochi2D sample puppets used as the regression corpus.

Sources (both BSD-2-Clause, from the official inochi2d repository):

    examples/empty08.inx   702 B      minimal 0.8 puppet — the schema truth for "empty"
    examples/ada-static.inx 7.1 MB    single-part puppet carrying a real texture

Run:  python tools/fetch_examples.py [--out examples]

The samples are downloaded rather than committed so the repository stays
source-only; CI and local tests skip when they are absent.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/Inochi2D/inochi2d/main/examples/"
FILES = {
    "empty08.inx": {
        "bytes": 702,
        "sha256": "b56a0377034fed6bf658820b1a009252605c1c47ffbb58168d011dc129d330fd",
    },
    "ada-static.inx": {
        "bytes": 7123901,
        "sha256": "8821f5d8de9f225cbafa3d496de93633d77c84dd95e6bc702a3d23739e238f93",
    },
}


def fetch(name: str, out_dir: Path) -> Path:
    target = out_dir / name
    if target.exists():
        data = target.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        expected = FILES[name]["sha256"]
        note = "ok" if digest == expected else f"HASH CHANGED (expected {expected})"
        print(f"{target} already present ({len(data)} bytes, {note})")
        return target
    url = BASE + name
    print(f"downloading {url}")
    with urllib.request.urlopen(url, timeout=120) as response:
        data = response.read()
    target.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    expected_bytes = FILES[name]["bytes"]
    expected_hash = FILES[name]["sha256"]
    problems = []
    if len(data) != expected_bytes:
        problems.append(f"size {len(data)} != expected {expected_bytes}")
    if digest != expected_hash:
        problems.append("sha256 differs from the recorded one")
    print(f"{target}  {len(data)} bytes  sha256={digest}  {'ok' if not problems else '; '.join(problems)}")
    if problems:
        print(
            "  note: the upstream sample changed — update FILES in this script deliberately, "
            "and re-check that the byte-for-byte test still holds",
            file=sys.stderr,
        )
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="examples", help="destination directory")
    args = parser.parse_args(argv)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        try:
            fetch(name, out_dir)
        except Exception as exc:  # noqa: BLE001 - report and continue with the rest
            print(f"failed to fetch {name}: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Command line interface.

The CLI is the primary surface: every capability is implemented here first and
the MCP server (``mcp_server.py``) is a thin wrapper over the same functions.
That ordering keeps the tool usable by a human, by a shell script, and by an
agent without three divergent implementations.

Capabilities not implemented yet are reported as such instead of being faked —
see ``inochi2d status``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

from . import build, inp, puppet as puppet_mod

__version__ = "0.1.0"

# name -> (status, one-line description); status is one of
# "implemented" | "planned". Update together with the code, never ahead of it.
CAPABILITIES: dict[str, tuple[str, str]] = {
    "new": ("implemented", "write a minimal puppet from scratch"),
    "inspect": ("implemented", "read a puppet and print its structure"),
    "verify": ("implemented", "round-trip + structural validation"),
    "textures": ("implemented", "extract embedded textures"),
    "from-layers": ("planned", "build a rigged puppet from layered art (mesh + bindings)"),
    "render": ("planned", "headless render of a puppet to PNG (needs the Creator bridge)"),
    "bridge": ("planned", "install/refresh the Creator CLI bridge on a workstation"),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #


def cmd_new(args: argparse.Namespace) -> int:
    rng = random.Random(args.seed) if args.seed is not None else None
    doc = build.minimal_puppet(args.name, seed=rng)
    out = Path(args.out)
    inp.save(doc, out, json_indent=args.indent)
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    doc = inp.load(args.file)
    summary = puppet_mod.summarise(doc)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    print(f"file       {summary['source']}  sha256={_sha256(Path(args.file))[:16]}…")
    print(f"name       {summary['name']!r}   format {summary['version']}")
    print(f"nodes      {summary['nodes']}  {summary['node_types']}")
    print(f"parameters {len(summary['parameters'])}   animations {summary['animations']}")
    print(f"textures   {len(summary['textures'])}  {summary['textures'][:6]}")
    if summary["parameters"]:
        print("param list")
        for entry in summary["parameters"]:
            print(
                f"  - {entry['name']:<24} range[{entry['min']}, {entry['max']}] "
                f"points={entry['points']} bindings={entry['bindings']}"
            )
    if args.tree:
        print("node tree")
        for depth, node in doc.walk():
            ty = node.get("type", "?")
            print(f"  {'  ' * depth}- {node.get('name') or '<unnamed>'} [{ty}] uuid={node.get('uuid')}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Prove a file survives a read → write → read cycle unchanged."""
    path = Path(args.file)
    original = inp.load(path)
    rewritten = inp.parse(inp.dumps(original))

    failures: list[str] = []
    if rewritten.payload != original.payload:
        failures.append("JSON payload changed across round-trip")
    if len(rewritten.textures) != len(original.textures):
        failures.append(
            f"texture count changed: {len(original.textures)} -> {len(rewritten.textures)}"
        )
    for index, (a, b) in enumerate(zip(original.textures, rewritten.textures)):
        if a.encoding != b.encoding or a.data != b.data:
            failures.append(f"texture #{index} changed across round-trip")

    issues = puppet_mod.validate(original)
    errors = [i for i in issues if i.severity == puppet_mod.ERROR]
    warnings = [i for i in issues if i.severity == puppet_mod.WARNING]

    print(f"{path.name}: {original.node_count()} nodes, {len(original.textures)} textures")
    print(f"round-trip: {'FAIL' if failures else 'ok (payload + textures byte-identical in memory)'}")
    print(f"validation: {len(errors)} error(s), {len(warnings)} warning(s)")
    for item in errors:
        print(f"  {item}")
    if args.warnings:
        for item in warnings:
            print(f"  {item}")

    if failures:
        print("failures:")
        for line in failures:
            print(f"  - {line}")
        return 1
    return 1 if errors else 0


def cmd_textures(args: argparse.Namespace) -> int:
    doc = inp.load(args.file)
    written = inp.extract_textures(doc, args.out)
    if not written:
        print("no embedded textures")
        return 0
    for path in written:
        print(f"{path}  {path.stat().st_size} bytes")
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    width = max(len(name) for name in CAPABILITIES)
    print(f"inochi2d-toolkit {__version__}")
    for name, (status, description) in CAPABILITIES.items():
        print(f"  {name:<{width}}  {status:<11} {description}")
    print()
    print("Planned capabilities exit with a not-implemented error until they exist; keep this list in")
    print("sync with the code (tests enforce it).")
    return 0


# --------------------------------------------------------------------------- #
# argparse wiring
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inochi2d",
        description="Read, verify and (soon) build Inochi2D puppets.",
    )
    parser.add_argument("--version", action="version", version=f"inochi2d-toolkit {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("new", help=CAPABILITIES["new"][1])
    p.add_argument("out", help="output .inx/.inp path")
    p.add_argument("--name", default="New Puppet")
    p.add_argument("--seed", type=int, default=None, help="seed uuid allocation for reproducible files")
    p.add_argument("--indent", type=int, default=None, help="pretty-print JSON (default: compact, like the official exporter)")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("inspect", help=CAPABILITIES["inspect"][1])
    p.add_argument("file")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.add_argument("--tree", action="store_true", help="print the node tree")
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("verify", help=CAPABILITIES["verify"][1])
    p.add_argument("file")
    p.add_argument("--warnings", action="store_true", help="print warnings too")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("textures", help=CAPABILITIES["textures"][1])
    p.add_argument("file")
    p.add_argument("--out", default="textures", help="output directory")
    p.set_defaults(func=cmd_textures)

    p = sub.add_parser("status", help="print the capability matrix")
    p.set_defaults(func=cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except inp.InpError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

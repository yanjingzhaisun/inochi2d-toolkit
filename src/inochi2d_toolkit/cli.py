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
import importlib.util
import json
import os
import platform
import random
import shutil
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
    "doctor": ("implemented", "report what this install can actually do"),
    "from-layers": ("planned", "build a rigged puppet from layered art (mesh + bindings)"),
    "render": ("planned", "headless render of a puppet to PNG (needs the Creator bridge)"),
    "bridge": ("planned", "install/refresh the Creator CLI bridge on a workstation"),
}

# External things a capability needs. The implemented ones need nothing at all,
# which is the point: a fresh clone runs without a D toolchain, without Inochi
# Creator and without network access.
REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "new": (),
    "inspect": (),
    "verify": (),
    "textures": (),
    "doctor": (),
    "from-layers": ("bridge",),
    "render": ("bridge",),
    "bridge": ("d-toolchain", "creator-source"),
}

BRIDGE_ENV = "INOCHI2D_BRIDGE"
CREATOR_ENV = "INOCHI2D_CREATOR"


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


def find_bridge() -> Path | None:
    """Locate the optional headless bridge executable, if this machine has one."""
    override = os.environ.get(BRIDGE_ENV)
    if override:
        candidate = Path(override)
        if candidate.is_file():
            return candidate
    for name in ("inochi2d-bridge", "inochi2d-bridge.exe"):
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


def find_creator() -> Path | None:
    """Locate an installed Inochi Creator, which is only needed by the bridge."""
    override = os.environ.get(CREATOR_ENV)
    if override:
        candidate = Path(override)
        if candidate.is_file():
            return candidate
    for name in ("Inochi Creator", "Inochi Creator.exe", "inochi-creator"):
        found = shutil.which(name)
        if found:
            return Path(found)
    guesses: list[Path] = []
    if sys.platform == "win32":
        for root in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), "E:\\Programs"):
            if root:
                guesses += [
                    Path(root) / "Inochi2D" / "creator" / "Inochi Creator.exe",
                    Path(root) / "Inochi2D" / "Inochi Creator.exe",
                ]
    for candidate in guesses:
        if candidate.is_file():
            return candidate
    return None


def doctor_report() -> dict[str, object]:
    """What this install can actually do, checked rather than assumed.

    Returns a dict so the CLI, the MCP tool and the tests all read the same
    measurement. Nothing here imports an optional dependency, so the check
    itself never needs anything beyond the standard library.
    """
    bridge = find_bridge()
    creator = find_creator()
    source_env = os.environ.get("INOCHI2D_CREATOR_SOURCE")
    checks = [
        {
            "check": "python",
            "ok": sys.version_info >= (3, 10),
            "detail": f"{platform.python_version()} (needs >= 3.10)",
        },
        {"check": "core", "ok": True, "detail": "inp/puppet/build import from the standard library only"},
        {
            "check": "extra:mcp",
            "ok": importlib.util.find_spec("mcp") is not None,
            "detail": "optional: only the MCP server shell needs it",
        },
        {
            "check": "extra:rig",
            "ok": importlib.util.find_spec("numpy") is not None and importlib.util.find_spec("PIL") is not None,
            "detail": "optional: numpy/Pillow for the planned rigging work",
        },
        {
            "check": "d-toolchain",
            "ok": shutil.which("dub") is not None,
            "detail": "optional: only needed to build the bridge from source",
        },
        {
            "check": "creator-source",
            "ok": bool(source_env) or (Path.cwd() / "source" / "creator").is_dir(),
            "detail": "optional: a v0_8 clone, for building the bridge",
        },
        {
            "check": "bridge",
            "ok": bridge is not None,
            "detail": f"optional: {bridge}" if bridge else f"optional: set ${BRIDGE_ENV} or put inochi2d-bridge on PATH",
        },
        {
            "check": "creator-install",
            "ok": creator is not None,
            "detail": f"optional: {creator}" if creator else "optional: an installed Creator, for GUI-side checks",
        },
    ]

    found = {entry["check"]: bool(entry["ok"]) for entry in checks}
    capabilities = []
    for name, (status, description) in CAPABILITIES.items():
        needs = REQUIREMENTS.get(name, ())
        missing = [need for need in needs if not found.get(need, False)]
        capabilities.append(
            {
                "capability": name,
                "status": status,
                "needs": list(needs),
                "ready": not missing,
                "blocked_by": missing,
                "description": description,
            }
        )

    return {
        "toolkit_version": __version__,
        "checks": checks,
        "capabilities": capabilities,
        "implemented_ready": all(c["ready"] for c in capabilities if c["status"] == "implemented"),
    }


def cmd_doctor(args: argparse.Namespace) -> int:
    report = doctor_report()
    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if report["implemented_ready"] else 1

    print(f"inochi2d-toolkit {report['toolkit_version']}")
    print("environment")
    for entry in report["checks"]:
        mark = "ok     " if entry["ok"] else "missing"
        print(f"  {mark} {entry['check']:<16} {entry['detail']}")
    print("capabilities")
    for entry in report["capabilities"]:
        state = "ready  " if entry["ready"] else "blocked"
        blocked = f"  needs {', '.join(entry['blocked_by'])}" if entry["blocked_by"] else ""
        print(f"  {state} {entry['capability']:<12} {entry['status']:<11}{blocked}")
    print()
    if report["implemented_ready"]:
        print("Every implemented capability runs here with nothing but Python.")
    else:
        print("An implemented capability is missing something required — see the missing lines above.")
    return 0 if report["implemented_ready"] else 1


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

    p = sub.add_parser("doctor", help=CAPABILITIES["doctor"][1])
    p.add_argument("--json", action="store_true", help="machine-readable report")
    p.set_defaults(func=cmd_doctor)
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

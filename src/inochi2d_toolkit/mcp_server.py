"""MCP wrapper.

Design rule: the MCP server adds *no* behaviour of its own. Every tool is a
thin, typed call into the same functions the CLI uses — so an agent, a shell
script and a human all take the same code path and cannot silently diverge.

Run locally (stdio):

    python -m inochi2d_toolkit.mcp_server

Register with Hermes by adding an entry under ``mcp_servers`` in config.yaml
(see README §Registering).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import build, inp, puppet as puppet_mod

try:  # the core is dependency-free; only the server needs mcp
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - exercised only without the extra
    raise SystemExit(
        "the MCP extra is not installed; install with: pip install 'inochi2d-toolkit[mcp]'"
    ) from exc

mcp = FastMCP("inochi2d-toolkit")


@mcp.tool()
def inochi_status() -> dict[str, Any]:
    """Which capabilities are implemented versus planned."""
    from .cli import CAPABILITIES

    return {
        "toolkit_version": __import__("inochi2d_toolkit").__version__,
        "capabilities": {name: status for name, (status, _) in CAPABILITIES.items()},
    }


@mcp.tool()
def inochi_doctor() -> dict[str, Any]:
    """Report what this install can do: environment checks and per-capability readiness.

    Use it before calling anything else — capabilities that need the optional
    bridge (mesh generation, rendering) report why they are blocked instead of
    failing later.
    """
    from .cli import doctor_report

    return doctor_report()


@mcp.tool()
def inochi_inspect(path: str) -> dict[str, Any]:
    """Read a puppet (.inx/.inp) and return its structure as JSON.

    Args:
        path: absolute path to the puppet file on the machine running this server.
    """
    doc = inp.load(path)
    return puppet_mod.summarise(doc)


@mcp.tool()
def inochi_verify(path: str, include_warnings: bool = True) -> dict[str, Any]:
    """Round-trip and structurally validate a puppet.

    Returns ok=True only when the payload and every texture survive the
    read -> write -> read cycle unchanged AND validation reports no errors.
    """
    original = inp.load(path)
    rewritten = inp.parse(inp.dumps(original))
    failures: list[str] = []
    if rewritten.payload != original.payload:
        failures.append("JSON payload changed across round-trip")
    if len(rewritten.textures) != len(original.textures):
        failures.append("texture count changed across round-trip")
    for index, (a, b) in enumerate(zip(original.textures, rewritten.textures)):
        if a.encoding != b.encoding or a.data != b.data:
            failures.append(f"texture #{index} changed across round-trip")

    issues = puppet_mod.validate(original)
    errors = [str(i) for i in issues if i.severity == puppet_mod.ERROR]
    warnings = [str(i) for i in issues if i.severity == puppet_mod.WARNING]
    return {
        "path": path,
        "nodes": original.node_count(),
        "textures": len(original.textures),
        "round_trip_failures": failures,
        "errors": errors,
        "warnings": warnings if include_warnings else [],
        "ok": not failures and not errors,
    }


@mcp.tool()
def inochi_extract_textures(path: str, out_dir: str) -> dict[str, Any]:
    """Extract the textures embedded in a puppet to ``out_dir``."""
    doc = inp.load(path)
    written = inp.extract_textures(doc, out_dir)
    return {"count": len(written), "files": [str(p) for p in written]}


@mcp.tool()
def inochi_new_minimal(path: str, name: str = "New Puppet", seed: int | None = None) -> dict[str, Any]:
    """Write a minimal, structurally valid 0.8 puppet (same shape as the official empty sample)."""
    import random

    rng = random.Random(seed) if seed is not None else None
    doc = build.minimal_puppet(name, seed=rng)
    target = Path(path)
    inp.save(doc, target)
    verify = inochi_verify(str(target))
    return {"path": str(target), "bytes": target.stat().st_size, "verified": verify["ok"]}


if __name__ == "__main__":  # pragma: no cover
    mcp.run()

# inochi2d-toolkit

Read, verify and (progressively) **build Inochi2D puppets** — as a CLI for humans and scripts, and as an
MCP server for agents. Both surfaces are thin wrappers over the same core, so nothing can silently diverge.

Inochi2D has no official plugin/IPC surface and its editor (Inochi Creator) is a GUI application. This
toolkit takes the other road: **the puppet format is open** — a `TRNSRTS` container holding a JSON payload
plus textures — so rigging can be produced and checked at the file level, and the editor is only needed to
*look* at the result.

## Status

Honesty rule (inherited from our pipeline lab): every capability is labelled
**implemented / planned**. Anything not implemented exits with an error instead of pretending to work.

| Capability | Status | What it does |
| --- | --- | --- |
| `new` | implemented | write a minimal, structurally valid 0.8 puppet |
| `inspect` | implemented | read a puppet, print structure (nodes, params, textures), `--json`/`--tree` |
| `verify` | implemented | read → write → read round-trip **plus** structural validation |
| `textures` | implemented | extract embedded textures |
| `from-layers` | planned | layered art → rigged puppet (mesh generation + parameter bindings) |
| `render` | planned | headless render to PNG (via the Creator bridge) |
| `bridge` | planned | install/refresh the Creator control bridge on a workstation |

`inochi2d status` prints the same matrix from code.

## Scope (what this repo assumes — and does not)

- **Target: Inochi2D, version v0_8 payloads.** Not a Live2D pipeline. Advice that came from earlier 2D-puppet
  work is reusable; that pipeline is not.
- **No pre-existing assets.** This repo does not depend on any existing model, rig, layer set or 3D asset.
  Nothing reusable exists on the workstation this was written for, and the 3D asset we happen to hold is an
  interim artefact that is explicitly *not* a reference.
- **Upstream art is an open dependency.** Illustrations are still being produced and their layer splitting is
  not yet acceptable; `from-layers` therefore validates whatever it is handed instead of trusting it.
- **Visual review is the human's only step.** Everything up to and including a rendered PNG is meant to run
  unattended; the reviewer looks at pictures, not at files.

## Install

```bash
pip install .            # core: standard library only
pip install '.[mcp]'     # + MCP server
pip install '.[rig]'     # + numpy/Pillow for the rigging work (planned features)
```

## CLI

```bash
inochi2d new out.inx --name "Test Puppet"     # minimal puppet
inochi2d inspect out.inx --tree               # structure
inochi2d verify out.inx --warnings            # round-trip + validation, exit 1 on error
inochi2d textures out.inx --out ./textures    # pull textures out
inochi2d status                               # capability matrix
```

Regression corpus (official samples, downloaded not committed):

```bash
python tools/fetch_examples.py    # examples/empty08.inx (702 B), examples/ada-static.inx (7.1 MB)
pytest -q
```

## MCP

```bash
python -m inochi2d_toolkit.mcp_server          # stdio
```

Tools: `inochi_status`, `inochi_inspect`, `inochi_verify`, `inochi_extract_textures`, `inochi_new_minimal`.

Register with an MCP client (Hermes example):

```yaml
mcp_servers:
  inochi2d:
    command: /path/to/venv/bin/python
    args: [/path/to/inochi2d-toolkit/src/inochi2d_toolkit/mcp_server.py]
    enabled: true
```

## Design

- **CLI first.** Capabilities are implemented once, in `src/inochi2d_toolkit/`, and exposed twice
  (`cli.py`, `mcp_server.py`). The MCP layer holds no logic.
- **Dependency-free core.** `inp.py` / `puppet.py` / `build.py` use the standard library only, so the same
  code runs in a container, on a Windows workstation, or inside an MCP server.
- **The format is the interface.** Version alignment matters: this toolkit targets the **v0_8** payload
  (`meta.version` = `v0.8.6`), matching Inochi Creator 0.8.6. The 0.9 line restructured deformation
  bindings and introduced a new container (`INP2`) — see `docs/architecture.md`.
- **Verify before trusting.** Every write path is expected to be followed by `verify`, which is byte-level
  for textures and payload-deep-equal for JSON, plus structural checks (uuid uniqueness, mesh/uv parity,
  index and texture-id ranges, binding targets).

## Format facts this toolkit relies on

Verified by reading the two official samples byte-for-byte (tests pin them):

```
magic        8 bytes   "TRNSRTS\0"        (yes, really)
json length  uint32    big-endian
json         N bytes   UTF-8, the puppet payload
"TEX_SECT"   8 bytes   required
tex count    uint32
texture*     each: uint32 length, uint8 encoding (0=PNG, 1=TGA, 2=BC7), payload
"EXT_SECT"   8 bytes   optional vendor section
```

- Re-serialising the official 702-byte sample reproduces its bytes exactly (`tests/test_inp.py`).
- `Part.textures` is a **fixed-length array of 3 slots**; unused slots hold `4294967295` (uint32 −1), the same
  "nothing here" sentinel used by `meta.thumbnailId`. Do not read that value as a texture index.
- A `Part` carries `mesh` (`verts`/`uvs` flat pairs, `indices`, `origin`), `blend_mode`, `tint`, `screenTint`,
  `emissionStrength`, `mask_threshold`, `opacity`.
- The official textured sample ships a **TGA** texture — PNG is not the only encoding in practice.
- The official exporter's own output validates clean; a validator that flags it is wrong (that is a test).

## Credits / licence

MIT (see `LICENSE`) — chosen for recognition, not for a difference in permission: MIT and BSD-2-Clause grant
the same rights (use, modify, redistribute, sublicense, sell, closed-source) and neither is copyleft, so the
licence here is not constrained by the upstream projects.

This toolkit is independent and not affiliated with the Inochi2D Project. It contains **no upstream code**:
the reader/writer was written from the format's own behaviour, verified against the official samples. Inochi2D,
Inochi Creator and Inochi Session are BSD-2-Clause projects by the Inochi2D Project; the official samples are
downloaded by `tools/fetch_examples.py` and **not redistributed here**, so they stay under their own licence.

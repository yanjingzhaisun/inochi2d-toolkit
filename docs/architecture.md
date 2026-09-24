# Architecture

## Why file-level, not GUI automation

Inochi Creator has **no official plugin or IPC surface**, and the only public MCP attempt
(`ozekimasaki/inochi-creator-mcp`, 1★, single-day commit history) works by patching the creator's D source
and rebuilding it. We do not adopt it: its registered RPC methods stop at project/node/parameter/viewport
level, with **no mesh vertex editing and no parameter-binding methods** — i.e. exactly the two things
"rigging" means.

The puppet file, on the other hand, is open and readable:

```
"TRNSRTS\0" + uint32(BE) json length + JSON payload + "TEX_SECT" + count + textures [+ "EXT_SECT" ...]
```

So the toolkit's centre of gravity is the file: generate it, verify it, hand it to a runtime/editor for
visual check.

## Layers

```
┌─────────────────┐   ┌──────────────────┐
│  cli.py         │   │  mcp_server.py   │   two surfaces, no logic of their own
└────────┬────────┘   └────────┬─────────┘
         └──────────┬──────────┘
                    ▼
        ┌───────────────────────┐
        │  inp.py    container  │   read/write TRNSRTS, textures, ext sections
        │  puppet.py walk+check │   structure summary, structural validation
        │  build.py  construct  │   minimal puppet, node/uuid helpers
        │  rig.py    (planned)  │   meshes, deformers, bindings, physics
        └───────────────────────┘
                    │
                    ▼            a file the user reviews in Creator / Session
              model.inx
```

Planned additions that stay on the same side of the line:

- **`rig.py`** — mesh generation from layer alpha masks (contour extraction + constrained Delaunay with
  density driven by deformation need), deformer tree inference, parameter bindings, physics, and the
  displacement fields for head-turn / squash-and-stretch ("jelly") effects.
- **`bridge/`** — a *headless CLI* patch for Inochi Creator (`--load`, `--set-param`, `--export-inp`,
  `--render-png`) so the toolkit can render for visual review without a human driving a GUI. D source,
  built against `v0_8`; it is a control surface, not a rigging mechanism.
- **`verify --render`** — pixel-level regression: render a puppet at fixed parameter values and compare
  against a stored reference (needs the bridge).

## Version alignment (the trap)

| Line | Payload | Container | Notes |
| --- | --- | --- | --- |
| **0.8.x (v0_8 branch)** | `meta.version = v0.8.6` | `TRNSRTS` (this toolkit) | what Inochi Creator 0.8.6 / Session 0.8.7 use today |
| 0.9 (main) | restructured | `INP2` (see `tech-docs/inp2-puppet.md`) | `param/bindings/deform.d` is commented out; not targeted |

Deform bindings (mesh vertex offsets), `MeshDeformer` / `LatticeDeformer`, `SimplePhysics` and the serde
layer all live in the **v0_8** branch of `inochi2d`: `source/inochi2d/core/{param/binding.d, mesh.d,
math/deform.d, nodes/deformer/*.d, format/serde/*.d}`.

## Open questions (do not assume answers)

1. Exact JSON field names/encoding for deform bindings in v0_8 — read `core/param/binding.d`, then prove it
   with a write → read→write diff loop against a real editor export.
2. Whether Creator 0.8.6 accepts a puppet with textures in `BC7` (encoding 2) on all platforms.
3. Whether `tex count = 0` with later `EXT_SECT` is legal (the official empty sample has `TEX_SECT` only).

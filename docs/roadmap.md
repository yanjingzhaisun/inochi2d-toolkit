# Roadmap

Status as of the first commit (2026-09-24). Ordered by "what unblocks the next thing", not by glamour.

## 0. Container & verification — **done**

- `inp.py`: read/write `TRNSRTS` containers (big-endian, JSON payload, `TEX_SECT`, optional `EXT_SECT`),
  texture extraction, PNG/TGA/BC7 encodings.
- `puppet.py`: structural summary + validation (uuid uniqueness, mesh uv/vertex parity, index range,
  texture-id range, mask modes, binding targets, physics sanity).
- `build.py`: minimal puppet + node/uuid helpers.
- `cli.py` / `mcp_server.py`: `new`, `inspect`, `verify`, `textures`, `status`.
- Regression: official `empty08.inx` re-serialises byte-for-byte; `ada-static.inx` round-trips with its
  texture intact.

## 1. Control surface — **next**

Goal: render a puppet to PNG with no human in the loop, so every later step can be reviewed visually.

- [ ] `bridge/`: patch Inochi Creator `v0_8` with a headless CLI (`--load`, `--set-param`, `--export-inp`,
      `--render-png`, `--auto-mesh`) and build it (D compiler + VS2022 C++ + CMake; `bindbc-imgui` must be a recursive
      clone pinned to 0.7.0).
- [ ] `inochi2d render` in the CLI, calling the bridge on a workstation.
- [ ] Fixed-parameter render regression: same puppet + same params ⇒ comparable PNG.

## 2. Rigging from layers — **after 1**

- [ ] Mesh generation from alpha masks: boundary-fitted vertices (contour trace), interior density driven
      by how much each region must deform; constrained Delaunay triangulation.
- [ ] Node/deformer tree from layer geometry (containment + expected hierarchical motion).
- [ ] Parameter set: eye open, mouth open, head angle X/Y/Z, breath — plus the displacement data behind
      head-turn and squash-and-stretch ("jelly" eyes).
- [ ] Every artefact must pass `verify`; acceptance is visual review of renders at extreme parameter
      values, not "the file was written".

## 3. Upstream assets — **blocked, do not assume them**

Scope note (2026-09-24, owner): there are **no reusable assets on the workstation** for this work. The 3D
model we happen to hold is an interim artefact and **is not a reference**; the illustrations are still being
generated and their layer splitting is **not yet acceptable**. The instruction that came from the earlier
2D-puppet guidance is reusable; the Live2D pipeline itself is **not** — this toolkit targets Inochi2D only.

Consequences:

- [ ] No step here may depend on an existing model, rig, layer set or 3D asset. `from-layers` must accept
      whatever layer stack arrives later and validate it on entry (mask coverage, empty layers, duplicate
      bounds, layer order) instead of trusting it.
- [ ] Upstream readiness is an **open dependency**, not a milestone of this repo: the layer source is a
      separate pipeline that must reach "acceptable" before rigging can be judged.
- [ ] Until then, effort goes to the parts that do not need upstream art: control surface (§1), format
      writers, verification and the acceptance machinery.
- [ ] Displacement fields for head-turn / squash-and-stretch are to be **computed from the layer geometry
      and parameter intent**, not sampled from any 3D asset.

## Non-goals

- Reimplementing the Inochi runtime/renderer (a Rust port exists; it does not yet support `MeshGroup` or
  animations, so it cannot replace the editor as our acceptance renderer).
- Supporting the 0.9 `INP2` line before it stabilises.
- Reusing or extending earlier Live2D-oriented tooling: the guidance carries over, the pipeline does not.


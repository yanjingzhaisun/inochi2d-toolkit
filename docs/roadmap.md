# Roadmap

Status as of the first commit (2026-09-24). Ordered by "what unblocks the next thing", not by glamour.

## 0. Container & verification — **done**

- `inp.py`: read/write `TRNSRTS` containers (big-endian, JSON payload, `TEX_SECT`, optional `EXT_SECT`),
  texture extraction, PNG/TGA/BC7 encodings.
- `puppet.py`: structural summary + validation (uuid uniqueness, mesh uv/vertex parity, index range,
  texture-id range, mask modes, binding targets, physics sanity).
- `build.py`: minimal puppet + node/uuid helpers.
- `cli.py` / `mcp_server.py`: `new`, `inspect`, `verify`, `textures`, `status`, `doctor`.
- `doctor` states the dependency promise in code: every implemented capability declares no external
  requirement, and a missing optional (bridge, D toolchain, Creator) is reported as `blocked` per capability
  instead of surfacing later as a failure. `tests/test_capability_sync.py` holds `CAPABILITIES`, the three
  README tables, the roadmap and the doctor report together.
- Regression: official `empty08.inx` re-serialises byte-for-byte; `ada-static.inx` round-trips with its
  texture intact.

## 1. Control surface — **next**

Goal: render a puppet to PNG with no human in the loop, so every later step can be reviewed visually.

- [ ] `bridge/`: patch Inochi Creator `v0_8` with a headless CLI (`--load`, `--set-param`, `--export-inp`,
      `--render-png`, `--auto-mesh`) and build it (D compiler + VS2022 C++ + CMake; `bindbc-imgui` must be a recursive
      clone pinned to 0.7.0). Build prerequisites **verified on the workstation 2026-09-24**: VS2022 with the
      VC++ x86/x64 tools, Windows SDK 10.0.22621.0/10.0.26100.0, DUB 1.42.0, dub registry reachable.
- [ ] Prefer the **link** route over patching where possible (our own `dub` recipe importing the automesh
      modules) — upstream stays untouched, and the call site is ours. See `docs/skinning-survey.md`.
- [ ] Build once, ship the artefact: the D toolchain is a build-machine dependency, never a user's.
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

## Upstream contribution — **hold until our side is stable** (decided 2026-09-24)

Owner's call: no PR to `Inochi2D/inochi-creator` yet. When our own toolchain is proven, in this order:

1. Fix the adjacent bug first: `--version`, `--help` and any non-file argument **segfault** (upstream issue
   #335, open since 2024-02-28 with two comments, reported by the Arch package maintainer). Small,
   uncontroversial, and it opens the relationship.
2. Then offer headless/batch mode (`--load`, `--set-param`, `--auto-mesh`, `--export-inp`, `--render-png`),
   designed **small and format-agnostic**: argument parsing in `app.d` plus calls into existing internals,
   nothing in the format or renderer core — so it can be accepted on `v0_8` and survive a 0.9 rebase.

Why that order (checked 2026-09-24): the default branch is `v0_8`; the most recent merge was the Russian
translation PR #485 (2025-03-12); last push was 2025-06-16; 144 issues are open; there is no `CONTRIBUTING.md`
and no PR template. Review latency is measured in months, so the upstream route must never be a prerequisite
for our own capability — the link route and our own built artefact stay the primary path.

When a patch does land upstream, drop the "we ship a patched build" note from `THIRD_PARTY_NOTICES.md`.

## Non-goals

- Reimplementing the Inochi runtime/renderer (a Rust port exists; it does not yet support `MeshGroup` or
  animations, so it cannot replace the editor as our acceptance renderer).
- Supporting the 0.9 `INP2` line before it stabilises.
- Reusing or extending earlier Live2D-oriented tooling: the guidance carries over, the pipeline does not.


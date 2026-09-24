# 2D skinning for Inochi2D: what exists, and what we would have to write

Survey date: 2026-09-24. Grades: **[source]** read the code · **[measured]** we ran it ·
**[paper]** publication, not reproduced · **[upstream]** project documentation · **[unverified]** single
secondary source.

## What "2D skinning" means here

An Inochi2D puppet has **no skeleton and no skin weights**. Displacement comes from three different
mechanisms, and only the first is what people usually call meshing:

| Mechanism | In Inochi2D (v0_8) | Equivalent problem |
| --- | --- | --- |
| Mesh | each drawable owns `mesh` (`verts`/`uvs`/`indices`) | where do vertices go |
| Binding | parameter → deformer/keyform vertex offsets; deformer trees (mesh/lattice deformers) | what moves, by how much, when a parameter changes |
| Physics | `SimplePhysics` chains driven by parameters | hair, cloth, jelly-eye follow-through |

So "auto-rigging" is really **mesh generation + displacement authoring + physics tuning**. Bunraku states the
same for Live2D ("needs no skeleton or skin weights"), which is why it predicts per-vertex displacement fields
rather than weights.

## 1. Mesh generation — solved, and already shipped in the editor we target

**Inochi Creator v0_8 contains its own automatic mesher** — `source/creator/viewport/common/automesh/`
(`package.d` re-exports two modules, so the editor offers two modes):

- `contours.d` (374 lines): read the texture's alpha, `bwlabel` connected components, `findContours`,
  **centroid moment**, `resampling(samplingRate, mirrorHoriz/axisHoriz, mirrorVert/axisVert)`, then
  `scaling(..., erode_dilate)`; anchor selection by nearest-point search; with an explicit
  "do not allow existing points to cross over" constraint. **[source]**
- `grid.d` (232 lines): compute the opaque bounds from the alpha channel (`minX/minY`), `divideAxes()`, a
  per-axis scale configuration, then place a grid of vertices. **[source]**

Consequence: mesh generation is **not** something we have to invent or port. The base class is a thin
interface over a pure computation (`source/creator/viewport/common/automesh/automesh.d`):

```d
class AutoMeshProcessor {
public:
    abstract IncMesh autoMesh(Drawable targets, IncMesh meshData, bool mirrorHoriz = false, float axisHoriz = 0,
                             bool mirrorVert = false, float axisVert = 0);
    abstract void configure();   // settings panel (ImGui)
    abstract string icon();      // toolbar icon
};
```

`autoMesh()` takes a `Drawable` plus the existing mesh and returns an `IncMesh` — no window, no viewport
state, and the base class imports only `creator.viewport.common.mesh` and `inochi2d.core`. The GUI coupling is
confined to `configure()`/`icon()`. The processors are instantiated in
`source/creator/viewport/vertex/package.d` as `new ContourAutoMeshProcessor()` / `new GridAutoMeshProcessor()`.

So the real constraint is not "port it" but "**there is no call site**": the classes live inside the GUI
binary, with no CLI, no shared library and no IPC. Adding one entry point beside the one we already need for
rendering is the whole job. Compare with the published recipes, which are parameterisations of the same idea:

| Source | Recipe | Grade |
| --- | --- | --- |
| SpriteToMesh (arXiv 2602.21153) | segmentation (EfficientNet-B0+U-Net, IoU 0.87 on 100k sprite/mask pairs) → exterior contour with Douglas–Peucker at ε=0.003·P + adaptive arc subdivision → interior vertices on bilateral+Canny multi-channel edges (min length 150 px, ≥6 px from the boundary, 18 px dedup) → Delaunay with centroid-in-mask filtering. **Negative result: predicting vertex positions directly by heatmap regression does not converge** (loss plateau 0.061) — vertex placement is artist-ambiguous, so learn segmentation where ground truth is unambiguous and place vertices algorithmically. | [paper] |
| Bunraku (arXiv 2607.27348) | mesh per layer from the **alpha channel alone**: content = α>4, dilate 3 px, sample **all** exterior contours (so a hair layer with a detached lock stays meshed) with a per-contour budget proportional to arc length, add a jittered interior lattice restricted to content, Delaunay. **~55% of the vertex budget on the boundary**; two load-bearing details "established by measurement rather than design". Mesh construction is only 2.7% of Stage-2 runtime. | [paper] |
| psd2live (`tsunehimatoi/psd2live`, GPL-3.0) | separable Gaussian smoothing + 95th-percentile adaptive binarisation → periodic cubic Bézier fit with physical-window corner detection + curvature-weighted densification (up to 12×) → **constrained Delaunay with dynamic Lawson flips and midpoint bisection of over-long interior edges**; user-facing mesh spacing (default 64 px). | [upstream] |
| Live2D Cubism "Automatic Mesh generator" | exposes dot interval (inside/outside), boundary margin (inside/outside), minimum margin of boundary, minimum boundary points, alpha threshold. Useful as a parameterisation reference for our defaults. | [upstream] |

## 2. Displacement authoring — the actual open problem

Nothing released predicts Inochi bindings. The learned options, checked today:

| Project | Claim | Code today | Grade |
| --- | --- | --- | --- |
| **Bunraku** (arXiv 2607.27348, Jul 2026) | first end-to-end single-illustration → Live2D: ordered RGBA layers, per-layer mesh, and the parameter-driven keypose displacement field of **all layers jointly** (every vertex of every layer is one token, self-attention across layers; direction bounded + log-magnitude factorisation). 5.1M-param Transformer, 13 forward passes for a whole rig, fits a consumer card; per-vertex direction cosine 0.768 (median 0.828) on 50 held-out characters. Also Live2D-Bench (120 PSDs) and an 8,884-model corpus (~50k decomposition, ~35k animation records). | **`SparcAI-Inc/Bunraku` is a placeholder**: 34★, every file is one `readme.md` (722 B), no code, no weights, created and last pushed 2026-07-31. Neither benchmark nor corpus is downloadable. | [paper] + repo checked |
| **CartoonAlive** (arXiv 2507.17327) | single portrait → Live2D: shape-basis blendshapes for facial components (x/y/scale, −30..30), a 4-layer MLP mapping detected landmarks → Live2D parameters (100k synthetic renders), underlying-face repainting to kill animation artifacts, hair texture extraction. <30 s per character. Face only. | **`Human3DAIGC/CartoonAlive` has 3 files** (`.gitignore`, `README.md`, a video still) — no code, despite the README's "Apache License" line. GitHub reports no licence file. | [paper] + repo checked |
| **Spiritus** / "A Semantic-Driven Framework for Layered 2D Character" (ACM 2025, 10.1145/3746059.3747707) | text+sketch → character, open mask library + semantic matching, **shape-compatible mesh system**, automatic skeleton rigging (15 bones, VRM-inspired naming), per-attachment skinning weights, exports **Spine**-compatible skeletal animation. | paper only; no repository found | [paper] |
| **Stretchy Studio** (`MangoLion/stretchystudio`, MIT) | browser rig editor: auto-triangulation, **auto-rig from tagged PSD via DWPose ONNX or a heuristic fallback**, vertex skinning for limb bending, eye clipping, shape keys/variants, physics-driven hair sway; exports Spine / Cubism / Live2D-runtime bundles. Ships a documented Live2D-export research stream (`docs/live2d-export/{AUTO_RIG_PLAN,CMO3_FORMAT,WARP_DEFORMERS,head-angle-x-technique}`). | **real code**, MIT, 487★, but last pushed 2026-04-28 | [source] |
| **psd2live** (GPL-3.0) | layered PSD → Cubism `.cmo3`/`.moc3`: adaptive meshing, **deformer hierarchy** incl. a nine-axis (AngleX ±45° × AngleY ±30°) 8×8 facial mesh, eye/mouth warps with pupil counter-compensation, eyelash U-curve for closing, teeth/tongue masked by the mouth, hair multi-pendulum physics, jelly-eye as a damped spring oscillator, 6 s looping idle, MCP workspace with token auth. | **real code**, 449★, pushed 2026-09-24. GPL-3.0 — read it for algorithms, do not copy code into this BSD/MIT-style repo. | [source] |
| Live2D Cubism "Auto Generation of Deformer" | builds a standard human deformer configuration and uses AI to estimate which part each ArtMesh belongs to. The commercial equivalent of what we need — closed, but evidence that automatic *binding structure* is tractable with part semantics. | [upstream] |

## 3. Decomposition (upstream of all of this)

See-through (arXiv 2602.03749, Apache-2.0, 4.1k★, pushed 2026-08-05): single image → up to 23 inpainted
semantic layers with inferred drawing order; ships `inference/scripts/inference_psd.py` and a heuristic
part-segmentation script; 8 GB VRAM path via NF4 quantisation. Its README states plainly that **rigging
(deformation mesh, physics, motion curves) is not covered**. Stretchy Studio is built as its downstream
animation engine. [source]/[upstream]

## What this means for us

1. **Mesh: call the editor's own automesh, do not port it.** `AutoMeshProcessor.autoMesh()` is a pure function
   over a Drawable; it only lacks an entry point. The bridge we need for `render` (a rendered PNG for human
   review) is the same bridge that can expose `--auto-mesh`, so the marginal cost is one more command, not a
   second subsystem. A Python port is a **fallback**, justified only if we later need meshes inside the
   container/CI with no Windows in the loop, or if the build turns out to be blocked.
2. **Binding: heuristics first, models later.** No released model produces Inochi bindings, and the two
   learned options are paper-only today. The tractable first version is geometric and deterministic:
   parameter-role templates (head angle grid, eye open, mouth open, breath, hair follow) with per-parameter
   keyform offsets computed from layer geometry — the same shape of solution psd2live and Cubism ship. It also
   survives our rule that a write path must be verifiable by round-trip plus a render.
3. **Learned displacement only if the geometric version fails review.** Bunraku's 0.768 direction cosine is
   the number to beat, and its ablation says joint (cross-layer) prediction is the gain, not scale.
4. **Physics: deterministic.** Damped springs / pendulums. No model required.
5. **Verification stays ours.** Render at extreme parameter values, look at pictures — no upstream project
   gives us an acceptance gate for `.inx`.

## There is no reflection path into the shipped binary

Checked against `v0_8` before planning around it: the repository has **no plugin or `SharedLibrary` support**,
**no use of `Object.factory` or `ClassInfo`**, and **no built-in HTTP/websocket surface** (the well-known
`127.0.0.1:17320` endpoint belongs to a third-party MCP patch, not upstream). `dub.sdl` declares an
executable — there is no library target to link against. D's `Object.factory` resolves names only inside one
process with one druntime, and injecting a second druntime means two GCs and no exported class metadata, so
"reflection into the running editor" is a dead end rather than a shortcut. **[source]**

What works instead, in order of intrusion:

1. **Link, do not patch** — write our own `dub` recipe whose `sourcePaths` point at the cloned creator sources,
   add a `main.d` that instantiates `ContourAutoMeshProcessor`/`GridAutoMeshProcessor` and calls `autoMesh()`.
   Upstream stays untouched (no fork, no patch, no merge conflicts) and the call site is our MIT code.
2. **Patch + build Creator** — one entry point beside the one we already need for `--render-png`; gives a
   headless editor, which is what visual review needs.
3. **GUI automation** of the stock binary — no compile, but locale/layout dependent and needs a desktop session.

## Build prerequisites (verified on the workstation, 2026-09-24)

| Check | Result |
| --- | --- |
| VS2022 C++ workload (`vswhere -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64`) | present — `C:\Program Files\Microsoft Visual Studio\2022\Community` |
| Windows SDK | 10.0.22621.0 and 10.0.26100.0 |
| DUB | 1.42.0 (2026-08-17), `C:\D\dmd2\windows\bin` |
| Dub registry reachability | `code.dlang.org` returns HTTP 200 |
| Clone | first attempt failed with `RPC failed; curl 92 HTTP/2 stream reset`; retried with `http.version=HTTP/1.1` and `--depth 1 --shallow-submodules` |

## Open questions recorded, not assumed

- Does `autoMesh()`'s texture access work without a GL context? The processors build a CPU-side `Image` from
  the drawable's texture; whether pixel access needs an uploaded texture is unverified.
- Are the automesh settings (sampling rate, scale, erode/dilate, grid axis scales) settable as plain instance
  fields from a headless caller, given `configure()` is the ImGui-only path? Verified shape says yes; not yet
  exercised.
- Is the 8,884-model Live2D corpus ever released? It would be the only route to *learning* Inochi-style
  bindings (the formats differ, but the displacement semantics are close).
- SpriteToMesh's abstract says the trained model is released; the location is unverified here.

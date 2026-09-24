# References

Evidence grades used throughout this repo: **[measured]** we ran it · **[source]** read the upstream code or
spec · **[upstream]** upstream documentation/README · **[paper]** publication, not reproduced ·
**[unverified]** single secondary source.

## Format and runtime

| Item | Grade | Notes |
| --- | --- | --- |
| `Inochi2D/inochi2d` — INP spec (`docs.inochi2d.com/.../spec/inp`) | [source] | container layout, big-endian, PNG/TGA/BC7 ids |
| `Inochi2D/inochi2d` — `examples/empty08.inx` (702 B) | [measured] | minimal 0.8 puppet; re-serialising it byte-for-byte is a test here |
| `Inochi2D/inochi2d` — `examples/ada-static.inx` (7.1 MB) | [measured] | single-part puppet with a real texture |
| `Inochi2D/inochi2d` wiki "JSON Data Specification" | [source] | node/drawable/part/mask/pathdeform/mesh/transform fields — the page itself is marked out of date; treat the code as truth |
| `Inochi2D/inochi-creator` `v0_8` (BSD-2, 0.8.6, 2024-09-18) | [source] | `source/creator/io/{save,inpexport,imageexport,psd,kra}.d`, `source/creator/actions/{mesh,mesheditor,binding}.d`, `source/app.d` (accepts only a project path as `args[1]`) |
| `Inochi2D/inochi-session` 0.8.7 | [source] | matched the local install byte-for-byte (19,522,550 B) |
| `ozekimasaki/inochi-creator-mcp` | [source] | bridge patched into Creator, `127.0.0.1:17320`; RPC set has **no** mesh/binding methods |
| `Inochi2D/inox2d` (Rust port) | [upstream] | prototype; no MeshGroup, no animations, licence NOASSERTION — not usable as our renderer |
| `k4wai1/Manager-Inochi2D-Puppet` | [unverified] | CLI claiming to inspect/modify `.inp` files |

## Rigging / mesh generation (candidates, none adopted)

| Item | Grade | Why we care |
| --- | --- | --- |
| SpriteToMesh — *Automatic Mesh Generation for 2D Skeletal Animation Using Learned Segmentation and Contour-Aware Vertex Placement* (arXiv 2602.21153) | [paper] | closest published match to "put vertices where deformation needs them" |
| Bunraku — *Turning a Single Illustration into an Editable Live2D Character* (arXiv 2607.27348) | [paper] | single image → editable character; repository is thin (not a deployable toolchain) |
| *A Semantic-Driven Framework for Layered 2D Character* (ACM 2025, 10.1145/3746059.3747707) | [paper] | semantic layer decomposition feeding rig construction |
| *Automated Accessory Rigs for Layered 2D Character Illustrations* (UIST 2021, 10.1145/3472749.3474809) | [paper] | inferring motion relationships between layers — accessory/deformer hierarchies |
| AniDiffusion — *Automatic Diffusion-Based Rigging* (arXiv 2503.15586) | [paper] | diffusion-based automatic rigging across topologies |
| `l768350/3D_to_Live2D_Equivalent` | [unverified] | method reference only: generating Inochi2D head-turn/roll deformers *from a 3D model*. **Not our plan** — we hold no valid 3D reference asset and will not build on one. |
| Live2D Cubism "Auto Mesh" | [upstream] | industrial reference for what "good enough automatic meshing" looks like |

## Our wider pipeline (context, not part of this repo)

- Layer segmentation is a **separate, not-yet-acceptable** pipeline: illustrations are still being generated
  and their layer splitting does not meet the bar yet. Nothing in this repo may assume it is available.
- Candidates seen for that upstream work include `See-through` (SIGGRAPH 2026, Apache-2.0 — up to 23 semantic
  anime part layers with inpainting and an inferred draw order). [upstream] — recorded as a candidate, not a
  decision, and not a dependency here.
- This toolkit only owns the puppet end: container I/O, construction, validation, control surface.

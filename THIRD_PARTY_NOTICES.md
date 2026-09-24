# Third-party notices and licence policy

This repository is MIT (see `LICENSE`). This file records every external work we depend on, how we use it,
and which licence obligations that creates.

## Policy

1. **Calling and linking do not change our licence; copying does.** Linking against a BSD-2-Clause library, or
   compiling its sources into a tool of ours at build time, leaves our own code MIT. What BSD-2 requires is
   narrower and simpler: **keep the copyright notice and licence text** when source or binary is
   redistributed — and state the modifications if we patched it.
2. **Porting is more encumbered than linking.** Translating their code into Python is a derivative work: the
   ported file must carry the upstream copyright notice and licence, and stops being purely our MIT code. This
   is backwards from intuition, and it is why we prefer to *call* the Inochi Creator auto-mesh rather than
   reimplement it.
3. **GPL-3.0 stays at arm's length.** We may read a GPL project's algorithm description and implement it
   independently. We do not copy its code and we do not link it into anything we ship: either would place the
   combined work under GPL-3.0.
4. **Reading files and data is not a licence event.** Reading `.inx`/`.inp` containers, PSDs or official sample
   models creates no obligation; licence terms only attach when we copy, derive from, or redistribute someone's
   code or binaries.
5. **Anything shipped needs the notice.** If we ever distribute a binary that embeds upstream sources, that
   package includes the upstream licence text and a note saying what we changed.

## Entries

| Work | Licence | How we use it | Obligation |
| --- | --- | --- | --- |
| `Inochi2D/inochi-creator` (v0_8, `dub.sdl` declares `license "BSD 2-clause"`) | BSD-2-Clause | Source-level reference; planned target for **linking its `automesh` modules into our own CLI**, and for the headless `bridge` patch | Notice + licence text only if we redistribute a built binary; declare the patch if we ship a patched build. No code is copied into this repo. |
| `Inochi2D/inochi2d` (core, BSD-2) | BSD-2-Clause | Format and runtime authority; INP spec | Same, if ever redistributed. Not shipped here. |
| `Inochi2D/inochi-session` (BSD-2) | BSD-2-Clause | Tracking driver, not part of this repo | None while local-only. |
| `examples/empty08.inx`, `examples/ada-static.inx` | BSD-2-Clause (from `inochi2d`) | Regression corpus | Downloaded by `tools/fetch_examples.py`; **not redistributed here**, so no obligation attaches to this repo. |
| `tsunehimatoi/psd2live` | **GPL-3.0** | Read-only reference for rigging algorithms (constrained Delaunay, deformer hierarchy, jelly-eye spring, hair pendulums) | **No code copied, no linkage.** Keep it that way. |
| `MangoLion/stretchystudio` | MIT | Reference for auto-rig/skinning behaviour | None while not copied; keep the notice if code is ever reused. |
| `shitagaki-lab/see-through` | Apache-2.0 | Upstream layer decomposition (separate pipeline, not this repo) | Notice + `NOTICE` file if we redistribute it or a derivative. |
| SpriteToMesh, Bunraku, CartoonAlive, Spiritus, AniDiffusion (papers) | publications | Method reference only | Attribution in `docs/skinning-survey.md`. |

## What this means in practice

- Our GitHub repository stays MIT; nothing above forces a licence change on the code we wrote.
- The auto-mesh plan is the interesting case: **linking** keeps our code ours, whereas **porting** would put
  the upstream notice inside one of our modules. Both are legal under BSD-2; only one is tidy.
- If a GPL project ever becomes genuinely necessary, the decision is not "can we use the algorithm" (yes) but
  "are we willing to ship under GPL" (a product decision, not an engineering one).

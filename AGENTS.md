# Working agreement (for AI agents and humans)

Read `README.md` and `docs/architecture.md` before changing anything. Then:

## Truth rules

1. **Never claim more than is proven.** Each capability carries one of:
   *planned* · *upstream claims* · *local measurement* · *acceptance passed*. Anything unverified stays
   *planned*, in code comments, docs and commit messages alike.
2. **A PNG, a stub or a mock is not a result.** Writing a file that no Inochi runtime can load is not
   "rigging done". If the editor cannot open it or the runtime cannot render it, it is not done.
3. **Round-trip or it did not happen.** Every write path must be followed by `inochi2d verify` (payload
   deep-equal + texture bytes identical + zero validation errors). A passing `verify` is the minimum bar
   for calling a writer "implemented".
4. **Unknown fields are preserved.** Parsing must not drop fields the toolkit does not understand: the
   payload is passed through as data, not reconstructed from a schema model.

## Format discipline

- Target the **v0_8** payload (`meta.version == v0.8.6`) to match Inochi Creator 0.8.6. Do not mix in the
  0.9 line: `param/bindings/deform.d` is commented out there and `INP2` is a different container.
- Integer fields are **big-endian** on the wire; JSON numbers are floats — keep `1000.0`, not `1000`.
- uuids are unsigned 32-bit and must be unique within a puppet; references (bindings, masks) are uuids.
- Node `type` strings seen in the wild: `Node`, `Part`, `Mask`, `Composite`, `MeshGroup`,
  `SimplePhysics`, `Camera`, `PathDeform`.

## Engineering

- Core stays dependency-free (stdlib only). New runtime dependencies belong in the `rig`/`mcp` extras.
- The MCP server holds no logic: it wraps core functions the CLI also calls.
- Tests must run without network. Network-dependent corpora are fetched by `tools/fetch_examples.py` and
  skip when absent.
- Add a test with every behaviour; if a rule cannot be tested, it goes in `docs/` as an open question
  instead of into code as an assumption.

## Documentation

- The README is maintained in three languages: `README.md` (**English, the standard entry point**),
  `README.zh-CN.md`, `README.ja.md`. Change all three in the same commit — a section added to one and missing
  from another is a defect, not a nicety.
- Translations follow the English text. If they disagree, English is correct; fix the translation.
- Every localised README keeps its language switcher on line 3 and states that English is canonical.
- Section order and the capability table must match across all three; only wording is translated.
- Behaviour docs (`README.md`, `AGENTS.md`, `docs/`) describe what exists — planned work stays labelled
  *planned* in all languages.

## Repository hygiene

- Source only: no editor binaries, no Inochi SDKs, no model files, no large experiment output in git.
- Keep `CAPABILITIES` in `cli.py`, the README table and `docs/roadmap.md` in sync in the same commit.

# Fix `mod` traversal regex for visibility-qualified declarations (parity baseline generators)

## Goal
Make the Rust `mod` traversal regex in both parity baseline generators follow
visibility-qualified file-module declarations (`pub(crate) mod`, `pub(super) mod`,
`pub(in path) mod`) so previously-skipped child modules are scanned for public
symbols.

## Finding verification (verified against current code)
- VALID for both files. The traversal regex is identical and only matches
  `mod x;` and `pub mod x;`:
  - `tools/node_api_parity/generate_baseline.py:404`
  - `tools/python_api_parity/generate_baseline.py:432`
  - Current pattern: `r"(?m)^\s*(?:pub\s+)?mod\s+([A-Za-z0-9_]+)\s*;"`
- Real `pub(crate) mod` declarations exist inside crates that are in
  `RUST_TARGET_CRATES` for both tools, so their child modules are silently
  skipped today:
  - `business-logic/classic-config-core/src/lib.rs:15` -> `pub(crate) mod crashgen_registry_yaml;`
  - `business-logic/classic-update-core/src/lib.rs:59` -> `pub(crate) mod manifest_fetch;`
  - `business-logic/classic-settings-core/src/merge.rs:3` -> `pub(crate) mod documents;`
  - (`cpp-bindings/classic-cpp-bridge/src/lib.rs:70` also has one, but that crate
    is not a node/python parity target.)

## Change (minimal, both files)
Replace ONLY the traversal regex literal:
- From: `r"(?m)^\s*(?:pub\s+)?mod\s+([A-Za-z0-9_]+)\s*;"`
- To:   `r"(?m)^\s*(?:pub(?:\s*\([^)]*\))?\s+)?mod\s+([A-Za-z0-9_]+)\s*;"`

Apply at:
1. `tools/node_api_parity/generate_baseline.py:404` (inside `_collect_crate_sources` `visit`)
2. `tools/python_api_parity/generate_baseline.py:432` (inside `_collect_crate_sources` `visit`)

Matches `mod x;`, `pub mod x;`, `pub(crate) mod x;`, `pub(super) mod x;`,
`pub(self) mod x;`, `pub(in crate::a) mod x;`. Still ignores inline
`mod foo { ... }` (no trailing `;`), preserving current behavior.

## Intentionally skipped (with reason)
- The symbol-emission regex `r"(?m)^\s*pub\s+mod\s+([A-Za-z0-9_]+)\s*;"`
  (`node:421`, `python:473`) is left unchanged. A `pub(crate) mod` is crate-private
  and must NOT be emitted as a public "module" symbol. This is correct as-is and
  outside the finding's scope.

## Risks
- The git-tracked baselines `docs/implementation/node_api_parity/baseline/rust_api_surface.json`
  and `docs/implementation/python_api_parity/baseline/rust_api_surface.json` will
  gain `pub fn`/`pub struct`/`pub use` symbols from the now-reachable child modules
  (`crashgen_registry_yaml`, `manifest_fetch`, `documents`, plus any further nested
  modules they declare). This is the intended effect; regenerated artifacts must be
  reviewed and committed.
- Confirm no contract gap status flips unexpectedly (extra manifest symbols are
  normally harmless because the gate iterates `tier1Mappings`, but a newly-captured
  symbol name could change a `missing_rust` row to `matched`).

## Validation steps (run from repo root)
1. Tool unit tests (pure Python; conftest sets `sys.path`, no maturin venv needed):
   - `python -m pytest tools/node_api_parity/tests tools/python_api_parity/tests -q`
2. Regenerate baselines:
   - `python tools/node_api_parity/generate_baseline.py`
   - `python tools/python_api_parity/generate_baseline.py`
3. Review regenerated artifacts and confirm additions are expected/additive:
   - `git diff -- docs/implementation/node_api_parity/baseline docs/implementation/python_api_parity/baseline`
4. Run the parity gate checks and confirm clean exit / no regression:
   - `python tools/node_api_parity/check_parity_gate.py`
   - `python tools/python_api_parity/check_parity_gate.py`
5. Commit both source edits and the regenerated baseline artifacts together.

## Execution note
Requires source edits plus running the generator scripts, so apply in an
implementation-capable agent (this plan was produced in Plan Mode).

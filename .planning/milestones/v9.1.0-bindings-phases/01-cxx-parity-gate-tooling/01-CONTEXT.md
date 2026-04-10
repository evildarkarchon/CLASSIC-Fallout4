# Phase 1: CXX Parity Gate Tooling - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the first-class C++ bridge parity gate as a Python tool under `tools/cxx_api_parity/`. The gate parses every `#[cxx::bridge]` source file enumerated by `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs` (currently 14 files), extracts a structured surface inventory, compares it against a committed baseline contract, and exits non-zero on drift. The gate is **source-only** — no Rust build, no MSVC, no `cxx-build` invocation. It mirrors the established `tools/python_api_parity/` and `tools/node_api_parity/` script structure so contributors can reuse muscle memory.

Phase 1 establishes the gate against the **current narrowed bridge state** so the baseline is born green. Phase 2 (CXX Bridge Surface Expansion) widens the bridge and uses `--update-baseline` to refresh the committed contract as new entries land. Phase 5 (CI Enforcement) wires the gate into CI with branch protection.

**In scope:** gate script + generate-baseline script + initial committed baseline + contributor docs.
**Out of scope:** any change to `build.rs` or to the bridge crate source files; CI wiring (Phase 5); governance file deletion (Phase 6); error-contract documentation (Phase 6).

</domain>

<decisions>
## Implementation Decisions

### Symbol Enumeration Scope

- **D-01:** The gate parses each `#[cxx::bridge] mod ffi { ... }` block and extracts **functions + shared types**: `extern "Rust"` function signatures, `extern "C++"` function signatures, shared `struct` definitions (with field names + field types), shared `enum` definitions (with variants), and opaque type declarations (`type Foo;`). Comments, `use` statements, and type aliases are NOT part of the contract.
- **D-02:** Drift comparison is **symbol + types**: a function row matches the baseline iff the symbol name, ordered argument types, and return type all match. Lifetime annotations, `&`/`&mut`, `Pin<&mut T>` wrapping, and `UniquePtr<T>` are part of the signature and ARE compared (they're ABI-relevant). Struct rows match iff the ordered list of `(field_name, field_type)` pairs is unchanged. Enum rows match iff the ordered variant list is unchanged. **Doc comments are not compared** — that would trip on every doc edit.

### Contract Shape

- **D-03:** The CXX `parity_contract.json` uses a **CXX-specific shape**, not a mirror of Python's `tier1Mappings`. Top-level wrapper key is `entries` (a flat list). Each row: `{ id, rustSymbol, kind: "function" | "struct" | "enum" | "opaque", bridgeModule (e.g. "scangame"), sourceFile (e.g. "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs"), signature (only for kind=function: serialized arg-types + return-type), fields (only for kind=struct: ordered list), variants (only for kind=enum: ordered list) }`. There is NO second-binding column — the bridge IS the contract.
- **D-04:** No `tier1Mappings`/`tier2*` wrapper keys exist anywhere in the CXX gate. There is no Tier-2 concept in the CXX gate from birth — this avoids the Python-gate trap that Phase 6 (DOC-01) has to retroactively fix.

### Baseline Location & Refresh Workflow

- **D-05:** The committed baseline lives at `docs/implementation/cxx_api_parity/baseline/parity_contract.json`, mirroring the Python (`docs/implementation/python_api_parity/baseline/`) and Node (`docs/implementation/node_api_parity/baseline/`) layout. Generated artifacts (`rust_api_surface.json`, `cxx_diff_report.json`, `cxx_diff_report.md`, `cxx_gate_report.md`) live in the same `baseline/` directory and are also committed (the same way Python/Node commit their generated reports).
- **D-06:** Two scripts under `tools/cxx_api_parity/`:
  1. `check_parity_gate.py` — read-only diff against the committed baseline; supports `--repo-root`, `--contract`, `--output-dir`, `--baseline-output-dir`, and `--update-baseline` (the in-place refresh path that maintainers use after intentional bridge changes). Mirrors `tools/python_api_parity/check_parity_gate.py`.
  2. `generate_baseline.py` — standalone baseline bootstrap; called by Phase 1 itself to create the first committed baseline AND used internally by `check_parity_gate.py` (both scripts share `parse_cxx_bridge_surface()` helper).
- **D-07:** Both scripts read the bridge file list **dynamically** by parsing `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs` for the `cxx_build::bridges([...])` array. Hardcoding the list of 14 files in the gate script would create a second source-of-truth that would silently drift when Phase 2 adds files to `build.rs`.
- **D-08:** Generated runtime artifacts go to `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/parity-artifacts/` (ephemeral, gitignored), and `--update-baseline` copies a tracked subset over to `docs/implementation/cxx_api_parity/baseline/` via a `sync_baseline_artifacts()` helper analogous to the Python gate's. This separates "fresh run output" from "committed contract."

### Bridge Module Discovery (`path.rs` and friends)

- **D-09:** The Phase 1 gate is **strictly file-list-based**: it parses only the files listed in `build.rs::cxx_build::bridges([...])`. `src/path.rs` exists in the bridge crate's source tree but is NOT listed in `build.rs`, so it is invisible to the Phase 1 gate. The Phase 1 baseline reflects the current narrowed bridge surface and is born GREEN.
- **D-10:** Phase 2 (CXX Bridge Surface Expansion) is responsible for adding `src/path.rs`, the new `src/constants.rs`, and the new `src/web.rs` to `build.rs::cxx_build::bridges`. As soon as those entries land, the gate will detect the new bridge functions/types as drift; the maintainer accepts them by running `python tools/cxx_api_parity/check_parity_gate.py --update-baseline` as part of the Phase 2 commit. There is NO `expected_missing` allowlist, NO Tier-2 deferral, NO sibling-coverage report — those would re-introduce the Tier-2 pattern this milestone is killing.
- **D-11:** Cross-crate sibling coverage (which `-core` crates have Python/Node bindings but no CXX bridge module) is intentionally **not** part of the gate's drift detection. That information lives in `docs/api/binding-parity-overview.md`; Phase 6 rewrites that doc as the harmony-achieved reference. Mixing it into the CXX gate would conflate Phase 1 (gate exists) with Phase 2 (surface complete) and recreate the "born red, allowlist to bootstrap" trap.

### Deferred-Registry Trap Avoidance (CXXG-04)

- **D-12:** The CXX gate has NO `--deferred-registry` argument and NO concept of deferred backlog. The script's CLI surface is intentionally narrower than Python's so the hardcoded-path failure mode cannot exist. Phase 6 (DOC-01) will retrofit the Python and Node gates to make their `--deferred-registry` argument optional/missing-tolerant — the CXX gate is born without the trap.

### Output Artifacts

- **D-13:** `check_parity_gate.py` writes the following artifacts to `--output-dir` on every run:
  - `rust_api_surface.json` — full enumerated surface from the 14 bridge source files
  - `cxx_diff_report.json` — structured diff between baseline and current surface
  - `cxx_diff_report.md` — human-readable diff (similar shape to Python's `parity_diff_report.md`)
  - `cxx_gate_report.md` — concise pass/fail report with failing rows in markdown table form (similar to Python's `tier1_gate_report.md`, but no `tier1_*` language)
- **D-14:** Stale committed-artifact detection mirrors the Python gate: `check_parity_gate.py` exits non-zero if the committed baseline artifacts no longer match what a fresh source scan produces. This is the freshness gate that CI-06 will rely on in Phase 5.

### Contributor Docs (CXXG-05)

- **D-15:** The contributor doc lives at `docs/api/cxx-parity-gate.md` (per the CXXG-05 requirement wording). It documents: how to run the gate locally (`python tools/cxx_api_parity/check_parity_gate.py --repo-root .`), how to refresh the baseline after an intentional bridge change (`--update-baseline`), how to bootstrap from scratch (`generate_baseline.py`), what the contract row schema means, and the relationship to `build.rs` (single source of truth for the file list). A minimal `tools/cxx_api_parity/README.md` may exist as a one-line pointer to the canonical doc, but the full reference is in `docs/api/`.

### Local Invocation Convention

- **D-16:** Local invocation is `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` — pure Python script, no PowerShell wrapper. This matches the Python and Node gate invocations and avoids adding a Windows-only entrypoint to a tool that is itself cross-platform Python. (The bridge crate it inspects is Windows-only, but the gate parses Rust source and never runs the build.)

### Claude's Discretion

- The exact regex/parser strategy used inside `parse_cxx_bridge_surface()` (hand-rolled regex like the Python gate, vs `syn`-via-shell-out, vs a small Rust helper binary). The Python and Node gates use hand-rolled regex against `lib.rs`; the Phase 1 planner is free to pick whichever yields a robust 14-file scan. **Constraint:** the parser must be deterministic and produce stable JSON output (sorted keys, normalized whitespace) so the diff is meaningful.
- The exact field-name choices inside the row schema (e.g., `bridgeModule` vs `bridge_module`, `sourceFile` vs `source_file`). Recommend `camelCase` to match Python/Node `parity_contract.json` JSON style.
- Whether `parse_cxx_bridge_surface()` is exported as a reusable helper from `generate_baseline.py` or lives in a small `cxx_surface_parser.py` module — Claude's discretion based on what reads cleanest.
- Test fixtures for the gate itself: a small `tests/fixtures/` with synthetic bridge source files exercising each `kind` (function/struct/enum/opaque) is recommended but the test layout is the planner's call.

### Folded Todos

None — `gsd-tools todo match-phase 1` returned 0 matches.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Requirements
- `.planning/REQUIREMENTS.md` §CXX Parity Gate (CXXG) — CXXG-01..05 are this phase's complete requirement set
- `.planning/ROADMAP.md` §Phase 1: CXX Parity Gate Tooling — phase goal + 5 success criteria

### Research (this milestone)
- `.planning/research/SUMMARY.md` — synthesized cross-cutting findings (no new Cargo deps; deferred-registry trap; sub-module re-export gap; phase ordering)
- `.planning/research/STACK.md` §"C++ parity gate" — confirms Python tooling under `tools/cxx_api_parity/` parsing `#[cxx::bridge]` source files via `build.rs` enumeration; rejects generated-header parsing
- `.planning/research/ARCHITECTURE.md` §"C++ parity gate is a new Python tool" — confirms `tools/cxx_api_parity/` location, source-regex approach, CI placement deferred to Phase 5
- `.planning/research/FEATURES.md` §"C++ parity gate" — anti-feature: binary ABI checks; minimum viable: source enumeration + freshness checks
- `.planning/research/PITFALLS.md` §"Documentation Reset", §"CI gate cascade failures" — the deferred-registry hardcoded-path trap and the branch-protection-in-same-PR rule

### Source-of-truth files the gate inspects
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs` — the 14-file list this gate parses dynamically (single source of truth for which `#[cxx::bridge]` modules exist)
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/types.rs` — DTO module; first file in `build.rs` list
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` — currently the most-narrowed module (Phase 2 will widen it; Phase 1 baseline locks the current state)

### Established parity gate patterns to mirror
- `tools/python_api_parity/check_parity_gate.py` — argument shape, `sync_baseline_artifacts()` helper, `--update-baseline` flag, exit-code semantics, stale-artifact detection
- `tools/python_api_parity/generate_baseline.py` — `parse_rust_surface()` helper structure, `write_json()` helper, contract loading
- `tools/node_api_parity/check_parity_gate.py` — Node equivalent for cross-checking convention drift
- `docs/implementation/python_api_parity/baseline/parity_contract.json` — committed baseline layout to mirror at `docs/implementation/cxx_api_parity/baseline/parity_contract.json`

### Existing API docs that describe the bridge surface (background reading, not contract)
- `docs/api/classic-cpp-bridge-game-entrypoints.md` — current path/game/scangame bridge entry points
- `docs/api/classic-cpp-bridge-data-entrypoints.md` — current config/file/database/scanner bridge entry points
- `docs/api/binding-parity-overview.md` — current cross-binding comparison; will be rewritten in Phase 6, but Phase 1 reads it to understand the existing CXX surface inventory

### Architectural rules
- `AGENTS.md` §"Always-On Repository Rules" — single Tokio runtime, never write to `nul`, never run raw `ctest`
- `CLAUDE.md` §"Build Commands" — does NOT need to be invoked by Phase 1 (gate is source-only); listed for cross-reference

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`tools/python_api_parity/check_parity_gate.py`** — full reference implementation of the script architecture (argparse layout, artifact paths, `sync_baseline_artifacts`, exit-code semantics). Phase 1 can copy the structural skeleton verbatim and replace the body with CXX-specific parsing.
- **`tools/python_api_parity/generate_baseline.py`** — `parse_rust_surface()` shows how the existing gates do regex-based Rust parsing; pattern is reusable for `parse_cxx_bridge_surface()` even though the regex itself is different.
- **`binding_parity_runtime_coverage.py`** — has a `load_json_file()` helper. Phase 1 may or may not reuse it; CXX gate has no runtime coverage concept (no equivalent to "did this Python method get called in tests?"), so most of this module is irrelevant.
- **`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs`** — the 14-file list. Parse it via regex for `cxx_build::bridges([...])`; do NOT hardcode the list in the gate.

### Established Patterns

- **All existing parity gates parse Rust source via hand-rolled regex against `lib.rs`** (NOT `syn`, NOT a Rust helper binary). Phase 1 should follow this same convention but parse the 14 individual `src/*.rs` files instead of `lib.rs`. The regex approach has known limitations (no macro expansion, sensitive to formatting) but is the established repo norm.
- **Committed baselines under `docs/implementation/{python,node}_api_parity/baseline/`** — Phase 1 mirrors this exact location convention at `docs/implementation/cxx_api_parity/baseline/`.
- **`parity-artifacts/` runtime output directories live next to the binding crate** (e.g., `ClassicLib-rs/python-bindings/parity-artifacts/`, `ClassicLib-rs/node-bindings/classic-node/parity-artifacts/`). For CXX, the equivalent location is `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/parity-artifacts/` — Phase 1 creates this and adds it to `.gitignore` if not already covered.
- **Generated reports use `# Tier-1 ... Parity Gate Report` markdown headers** — CXX gate uses `# CXX Parity Gate Report` (no Tier-1 wording, no Tier-2 wording — single tier from birth).

### Integration Points

- **Phase 5 (CI Enforcement)** will add a `cxx-parity-gate` job to `.github/workflows/ci-cpp.yml` that runs `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` and blocks merges on non-zero exit. Phase 1 must produce a script whose CLI is stable enough that Phase 5 can wire it without further changes.
- **Phase 2 (CXX Bridge Surface Expansion)** will be the first consumer of `--update-baseline`. Every Phase 2 plan that lands a new bridge module or widens an existing one will run `--update-baseline` and commit the refreshed baseline as part of its commit.
- **`.gitignore`** — `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/parity-artifacts/` should be gitignored if it isn't already; this is the same pattern used for the Python and Node `parity-artifacts/` directories.

</code_context>

<specifics>
## Specific Ideas

- The gate parser must be **deterministic and produce stable JSON output** (sorted keys, normalized whitespace) so diffs are minimal and meaningful — this is non-negotiable for the freshness check (D-14) to work.
- The CXX gate's exit codes must match the Python/Node gate exit codes: `0` = pass, `1` = drift detected. Phase 5 CI wiring assumes this.
- The contract row `id` field should be a stable, deterministic hash of `rustSymbol + kind + bridgeModule` so that re-running `generate_baseline.py` against an unchanged source tree produces byte-identical output.
- The bridge file list in `build.rs` is parsed at gate-runtime; **do not hardcode** even as a fallback. If parsing `build.rs` fails, the gate exits non-zero with a diagnostic — silent fallback to a hardcoded list would defeat the dynamic-discovery design (D-07).

</specifics>

<deferred>
## Deferred Ideas

- **Cross-crate sibling coverage report** (suggested as Option C in path.rs discussion) — explicitly out of scope for the parity gate. The information already lives in `docs/api/binding-parity-overview.md` and is rewritten in Phase 6 as the harmony-achieved reference. If we ever want a machine-generated checklist of "which `-core` crates have Python/Node bindings but no CXX module," that's a separate one-off script — not part of the gate.
- **Doc-comment comparison** as part of drift detection — rejected because it would trip on every doc edit.
- **Binary ABI checks** — explicit anti-feature per Features research; redundant given CXX's compile-time type system, fragile against MSVC version drift.
- **Cargo test / Rust-native gate implementation** — rejected in favor of Python tooling for consistency with Python and Node gates. Reconsider only if the Python regex approach proves unmanageable across all 14 bridge files.
- **`schemars`-based contract generation** from a single Rust source-of-truth annotated type — out of scope; static markdown / hand-curated JSON is sufficient for v9.1.0-bindings (matches the v2/SCHEMA-01 deferral in REQUIREMENTS.md).

</deferred>

---

*Phase: 01-cxx-parity-gate-tooling*
*Context gathered: 2026-04-06*

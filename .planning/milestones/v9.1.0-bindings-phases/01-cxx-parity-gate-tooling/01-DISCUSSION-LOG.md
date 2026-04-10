# Phase 1: CXX Parity Gate Tooling - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> The authoritative decisions live in `01-CONTEXT.md`. This file is for human reference
> (compliance reviews, post-mortems, or "why did we decide that?" lookups).

**Discussed:** 2026-04-06
**Workflow:** `/gsd:discuss-phase 1`
**Mode:** discuss (interactive AskUserQuestion, no advisor mode, no `--auto`)

---

## Context Loaded

- `.planning/PROJECT.md` (v9.1.0-bindings milestone goal + active requirements + key decisions)
- `.planning/REQUIREMENTS.md` (CXXG-01..05 — Phase 1 scope)
- `.planning/STATE.md` (defining requirements; no current plan)
- `.planning/research/SUMMARY.md` (synthesized cross-cutting findings)
- `.planning/research/STACK.md` (no new Cargo deps; `tools/cxx_api_parity/` Python tool; parse `build.rs`-listed `#[cxx::bridge]` source files)
- `.planning/research/ARCHITECTURE.md` (CXX gate is a NEW Python tool, not extension of Python gate; CI placement = `cxx-parity-gate` job in `ci-cpp.yml`)
- `.planning/research/FEATURES.md` (binary ABI checks = anti-feature; minimum viable = source enumeration + freshness checks)
- `.planning/research/PITFALLS.md` (deferred-registry hardcoded-path trap; sub-module re-export gap; branch-protection-in-same-PR rule)
- No prior `*-CONTEXT.md` files (this is the first phase of a new milestone)

## Codebase Scout

- `tools/python_api_parity/check_parity_gate.py` — full reference Python parity gate (read in detail)
- `tools/python_api_parity/generate_baseline.py` (file existence confirmed; structure inferred from check_parity_gate imports)
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs` (read in full — confirmed 14-file `cxx_build::bridges([...])` list, confirmed `src/path.rs` is NOT listed)
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/` directory listing (17 `.rs` files: 14 in bridges + lib.rs + path.rs + types.rs which IS in bridges)
- `tools/python_api_parity/`, `tools/node_api_parity/` directory listings (confirmed parallel structure: `check_parity_gate.py`, `generate_baseline.py`, `generate_wave_manifest.py`)

## Cross-Reference Todos

`gsd-tools todo match-phase 1` returned 0 matches. No backlog items folded.

---

## Gray Area Selection

**Question:** Which gray areas do you want to discuss for Phase 1?
**Type:** AskUserQuestion (multiSelect)
**Options presented:**
1. Symbol enum scope — what gets extracted from each `#[cxx::bridge]` block
2. Contract shape — mirror Python `tier1Mappings` vs CXX-specific
3. Baseline + refresh — committed baseline location and refresh workflow
4. path.rs detection — strict file-list-based vs cross-check `-core` inventory

**User selected:** ALL FOUR

---

## Area 1: Symbol Enumeration Scope

### Q1 — What should the CXX parity gate extract from each bridge block?

**Options presented:**
1. **Functions + shared types (Recommended)** — `extern "Rust"` functions, `extern "C++"` function signatures, shared structs (with field names + types), shared enums (with variants), opaque type declarations
2. Functions only — just function signatures
3. Everything in the mod — including type aliases, use statements, comments

**User selected:** Functions + shared types (Recommended)

**Rationale captured:** Matches Python/Node gate granularity; struct field renames and enum variant additions silently break C++ frontends until compile time, so they belong in the gate. Comments and `use` statements would trip on noise.

### Q2 — How strict is the signature comparison?

**Options presented:**
1. **Symbol + types (Recommended)** — name + ordered arg types + return type; lifetimes, refs, `Pin<&mut T>`, `UniquePtr<T>` ARE compared
2. Symbol only — name match only
3. Symbol + types + docs — also compares attached doc comments

**User selected:** Symbol + types (Recommended)

**Rationale captured:** Lifetimes and ref/value distinctions are ABI-relevant for CXX FFI. Doc comments would make the gate trip on every doc edit — explicitly rejected.

---

## Area 2: Contract Shape

### Q3 — What shape should the CXX parity_contract.json take?

**Options presented:**
1. **CXX-specific shape (Recommended)** — `entries: []` flat list; rows have `{id, rustSymbol, kind, bridgeModule, sourceFile, signature}`; NO second-binding column
2. Mirror Python field-for-field — keep `tier1Mappings` wrapper, add `cxxNamespace` as second-side column
3. Hybrid — CXX-specific row shape but keep `tier1Mappings` wrapper for cross-gate tooling

**User selected:** CXX-specific shape (Recommended)

**Rationale captured:** The bridge IS the contract — there's no second binding-language API to map TO, so a `cxxNamespace` second column is largely derivable from `rustSymbol + bridgeModule` and would be misleading dead weight. Phase 5 CI wiring consumes the gate's exit code and report format, not the contract layout, so cross-gate schema parity is not load-bearing.

---

## Area 3: Baseline Location & Refresh Workflow

### Q4 — Where should the committed CXX baseline live?

**Options presented:**
1. **`docs/implementation/cxx_api_parity/baseline/` (Recommended)** — mirror Python/Node convention exactly
2. `tools/cxx_api_parity/baseline/` — co-locate with the gate script
3. `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/parity-baseline.json` — co-locate with the bridge crate

**User selected:** `docs/implementation/cxx_api_parity/baseline/` (Recommended)

**Rationale captured:** Phase 6's governance sweep only deletes `governance/` subdirs, not `baseline/`. Discoverability follows existing Python/Node muscle memory.

### Q5 — How does baseline refresh work after intentional bridge changes?

**Options presented:**
1. **Both: `--update-baseline` flag + `generate_baseline.py` (Recommended)** — match Python/Node convention
2. Only `--update-baseline` flag — single script
3. Only `generate_baseline.py` — separate read-only gate from writable refresh

**User selected:** Both: `--update-baseline` flag + `generate_baseline.py` (Recommended)

**Rationale captured:** Matches Python/Node convention, no first-run special case needed (`generate_baseline.py` is the bootstrap), and shared `parse_cxx_bridge_surface()` helper avoids duplication.

---

## Area 4: `path.rs` Detection (Bridge Module Discovery)

### Q6 — How should the Phase 1 gate handle `src/path.rs` (and other `-core` crates with no bridge module yet)?

**Options presented:**
1. **Strictly file-list-based (Recommended)** — read `build.rs`, parse only the 14 listed files; Phase 1 baseline born green; Phase 2 adds new modules to `build.rs` and refreshes baseline
2. Cross-check against `-core` inventory — also enumerate `business-logic/-core` crates with Python/Node bindings; flag missing-bridge-module entries as drift; needs `expected_missing` allowlist (which is structurally Tier-2)
3. Strict + sibling report (no allowlist) — strict file-list-based for pass/fail, plus a non-blocking `cxx_sibling_coverage_report.md`

**User selected:** Strictly file-list-based (Recommended)

**Rationale captured:** Phase 1 must be born green to keep phase boundary clean. An `expected_missing` allowlist is structurally identical to Tier-2 deferral and would contradict the milestone goal. The sibling-coverage information already lives in `docs/api/binding-parity-overview.md`, which Phase 6 rewrites.

---

## Wrap-Up

### Q7 — Ready for context?

**Options presented:**
1. I'm ready for context — write 01-CONTEXT.md and 01-DISCUSSION-LOG.md, commit, finish
2. Explore more gray areas

**User selected:** I'm ready for context

---

## Decisions Captured

16 decisions (D-01 through D-16) recorded in `01-CONTEXT.md` covering:

- Symbol enumeration (D-01, D-02)
- Contract shape (D-03, D-04)
- Baseline location & refresh (D-05, D-06, D-07, D-08)
- Bridge module discovery (D-09, D-10, D-11)
- Deferred-registry trap avoidance (D-12)
- Output artifacts (D-13, D-14)
- Contributor docs (D-15)
- Local invocation convention (D-16)

Plus a "Claude's Discretion" block leaving regex-vs-helper module choice and field-name casing to the planner.

---

*Discussion log generated: 2026-04-06*

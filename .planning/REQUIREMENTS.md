# Requirements: CLASSIC v9.1.0-bindings

**Defined:** 2026-04-06
**Milestone:** v9.1.0-bindings — Full Bindings Parity
**Core Value:** Every shared Rust crate is exposed at full fidelity through C++, Node, and Python — no Tier-2 deferrals, no narrowing, with parity gates that prevent future drift on all three surfaces.

## v1 Requirements

Requirements for milestone v9.1.0-bindings. Each maps to a single roadmap phase.

### CXX Parity Gate (CXXG)

- [x] **CXXG-01**: A new `tools/cxx_api_parity/` Python tool parses every `#[cxx::bridge]` source file enumerated by `classic-cpp-bridge/build.rs` and emits a structured surface inventory JSON
- [x] **CXXG-02**: A committed `tools/cxx_api_parity/parity_contract.json` baseline captures every CXX bridge export and is regenerated/diffed by the gate script
- [x] **CXXG-03**: A `tools/cxx_api_parity/check_parity_gate.py` script fails non-zero on baseline drift, missing-from-bridge entries, and orphaned bridge entries (no Rust source-of-truth)
- [x] **CXXG-04**: The gate script's deferred-registry path is optional from day one (hardcoded-path pattern from the Python gate is not repeated)
- [x] **CXXG-05**: Contributor docs at `docs/api/cxx-parity-gate.md` describe how to run the gate locally and how to refresh the baseline after intentional bridge changes

### CXX Bridge Surface (CXXS)

- [x] **CXXS-01**: `classic-cpp-bridge` exposes a new `constants` module covering `classic-constants-core` (game labels, YAML file identifiers, Fallout 4 mode enum)
- [x] **CXXS-02**: `classic-cpp-bridge` exposes a new `web` module covering `classic-web-core` URL/user-agent/mod-site helpers
- [x] **CXXS-03**: `classic-cpp-bridge` exposes the FCX issue getter alongside the existing `fcx_reset_global_state()` so C++ frontends can read FCX issues without going through the scan pipeline
- [x] **CXXS-04**: `classic-cpp-bridge::scangame` is widened from its current 2-entry-point narrowing to expose every `classic-scangame-core` orchestration entry point used by Python/Node bindings (DTO design reviewed against CXX shared-struct rules)
- [x] **CXXS-05**: `classic-cpp-bridge::database` exposes the typed result API of `classic-database-core` currently narrowed away from C++ frontends (FormID lookup typed results, batch query results)
- [x] **CXXS-06**: `classic-cpp-bridge::registry` exposes the full `classic-version-registry-core` selection metadata (OG/NG/AE/VR variants and crashgen-rule resolution)
- [x] **CXXS-07**: `classic-cpp-bridge::config` exposes the suspect-rule subset of `classic-config-core` currently absent from C++ (suspect error rules, suspect stack rules)
- [x] **CXXS-08**: `classic-cpp-bridge::path` exposes every `classic-path-core` validation/backup helper currently narrowed away from C++ frontends
- [x] **CXXS-09**: `classic-cpp-bridge::xse` exposes every `classic-xse-core` detection helper currently narrowed away from C++ frontends
- [x] **CXXS-10**: All existing C++ frontend code (`classic-cli/`, `classic-gui/`) builds clean against the widened bridge with no API breakage in `classic-cli/build_cli.ps1 -Test` or `classic-gui/build_gui.ps1 -Test`

### Python Tier Collapse (PYT)

- [x] **PYT-01**: `tools/python_api_parity/generate_baseline.py` `RUST_TARGET_CRATES` and `PYTHON_TARGET_MODULES` are expanded from 3 to all 19 business-logic crate / Python binding pairs
- [x] **PYT-02**: All 289 currently-deferred Python parity entries (228 scanlog, 34 version_registry, 26 config, 1 aux) are promoted to enforced contract rows with concurrent `pub use` re-exports added to each binding crate's `lib.rs` so the baseline generator finds them
- [x] **PYT-03**: `tools/python_api_parity/check_parity_gate.py` Tier-2 skip logic is removed; the script enforces every contract row as Tier-1
- [x] **PYT-04**: `.pyi` stubs for every promoted entry exist and match the runtime surface (`mypy --strict` clean against the bindings test suite)
- [x] **PYT-05**: `uv run pytest ClassicLib-rs/python-bindings/tests -q` passes with the expanded surface, including smoke tests for at least one method per promoted module
- [x] **PYT-06**: `tools/python_api_parity/check_parity_gate.py` exits zero with the expanded contract; deferred-entry count drops to 0 in `runtime_coverage_summary.md`

### Node Tier Collapse (NODE)

- [x] **NODE-01**: `tools/node_api_parity/generate_baseline.py` `RUST_TARGET_CRATES` and `RUST_FULL_INVENTORY_CRATES` are expanded to cover every business-logic crate that has a Node binding module
- [x] **NODE-02**: All 109 currently-deferred Node parity entries (67 scanlog, 26 config, 12 aux, 4 version_registry) are promoted to enforced contract rows; every `nodeExport` field uses the camelCase identifier produced by NAPI auto-conversion
- [ ] **NODE-03**: `tools/node_api_parity/check_parity_gate.py` Tier-2 skip logic is removed; the script enforces every contract row as Tier-1
- [x] **NODE-04**: `ClassicLib-rs/node-bindings/classic-node/index.d.ts` is regenerated, committed, and the freshness gate passes against the expanded contract
- [x] **NODE-05**: `bun run test:bun && bun run test:node` pass with the expanded surface, including smoke tests for at least one method per promoted module
- [ ] **NODE-06**: `bun run parity:gate:local` exits zero with the expanded contract; deferred-entry count drops to 0 in the Node `runtime_coverage_summary.md`

### Cross-Binding Harmonization (HARM)

- [x] **HARM-01**: `ClassicLib-rs/node-bindings/classic-node/src/version.rs` exposes `extractPeVersion(path)` and `isValidPePath(path)` NAPI functions that delegate to `classic-version-core::extract_pe_version` (no direct `pelite` dep added to the Node crate)
- [x] **HARM-02**: `extractPeVersion` returns a typed object `{ major, minor, patch, build }` (or null/throw per documented Node error contract); the return shape is added to `index.d.ts` and runtime-tested for parity against the existing Python/Rust API
- [x] **HARM-03**: `foundation/classic-shared-py` is wired as a maturin build target in `rebuild_rust.ps1 -Target python` and produces an importable `classic_shared` Python module exposing `RuntimeStats`, `get_runtime_stats()`, and `is_runtime_healthy()` (already implemented in `src/lib.rs`; this requirement is build-wiring and gate enrollment)
- [x] **HARM-04**: A `classic-shared.pyi` stub exists alongside the build output and the Python parity gate's module map includes `classic_shared` so the new module is gate-enforced from day one
- [ ] **HARM-05**: `docs/api/error-contract.md` documents the per-binding error-shape conventions (Python exception classes, Node `error.code` strings or null, C++ `rust::Error` exceptions and fail-soft sentinels) for every `ClassicError` variant — explicitly documents the conventions, does not standardize them

### CI Enforcement (CI)

- [ ] **CI-01**: The Python parity gate runs in CI on every PR and blocks merges on failure (existing — verify it stays green after PYT promotion)
- [ ] **CI-02**: The Node parity gate runs in CI on every PR and blocks merges on failure (existing — verify it stays green after NODE promotion)
- [ ] **CI-03**: A new CI job runs `tools/cxx_api_parity/check_parity_gate.py` against the C++ bridge on every PR
- [ ] **CI-04**: The new C++ parity gate is added to branch-protection required checks in the **same PR** that adds the CI job (no "gate exists but doesn't block" window)
- [ ] **CI-05**: All three parity gates are wired into CI such that adding a new public Rust API in a `*-core` crate fails CI until all three bindings expose it (verified by an explicit assertion test that adds a temporary public API and observes triple-gate failure)
- [ ] **CI-06**: A `.gitignore`-respecting freshness gate exists for committed CXX artifacts (the `cxx::bridge` `build.rs` outputs a shared header that lives at a known path) so generated header drift fails CI the same way `index.d.ts` does for Node

### Documentation Reset (DOC)

- [ ] **DOC-01**: Python and Node parity gate scripts make the deferred-registry path argument optional/missing-tolerant **before** any governance file is deleted (prevents the hardcoded-path crash)
- [ ] **DOC-02**: All Tier-2 backlog/governance/manifest files under `docs/implementation/python_api_parity/governance/` are deleted (not emptied) and broken-link grep across `docs/` is clean
- [ ] **DOC-03**: All Tier-2 backlog/governance/manifest files under `docs/implementation/node_api_parity/governance/` are deleted (not emptied) and broken-link grep across `docs/` is clean
- [ ] **DOC-04**: A promotion audit trail (snapshot of which entries were promoted from each governance file) is captured in `.planning/milestones/v9.1.0-bindings-promotion-audit.md` BEFORE governance files are deleted
- [ ] **DOC-05**: `docs/api/binding-parity-overview.md` is rewritten as the "harmony achieved" reference with no Tier-2 language, no `classic-constants-core` / `classic-web-core` divergence rows, and updated CXX columns reflecting full surface exposure
- [ ] **DOC-06**: `docs/api/binding-parity-policy.md` is added as the single source-of-truth parity policy doc — when refreshes happen, who owns the gate, how to add a new public Rust API
- [ ] **DOC-07**: `docs/api/binding-contract-refresh-note.md` is updated to cover the C++ refresh workflow alongside the existing Node/Python guidance

## v2 Requirements

Deferred to future milestones. Acknowledged but not committed for v9.1.0-bindings.

### Binding ABI Hardening

- **ABI-01**: Binary ABI compatibility checking for the CXX bridge across MSVC versions
- **ABI-02**: Cross-version Python wheel ABI compatibility verification
- **ABI-03**: Cross-version NAPI ABI compatibility verification

### Schema-Driven Error Contracts

- **SCHEMA-01**: Generate per-binding error documentation from a `schemars`-decorated Rust source of truth (anti-feature for v9.1.0-bindings; static markdown is sufficient)

## Out of Scope

Explicitly excluded from v9.1.0-bindings. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| New Cargo workspace dependencies for parity tooling | Stack research confirmed no new deps required — all work is Python tooling, NAPI wrappers, and enrolling already-implemented `classic-shared-py` code |
| Standardizing the three error-shape conventions to one shape | Intentional design — Qt fail-soft callers depend on empty-string sentinel return from `db_pool_get_entry()`; Python exception classes and Node `error.code` are ergonomic norms for each consumer. Requirement is **document**, not standardize |
| Binary ABI checks for the CXX bridge | Windows-MSVC-only, fragile, redundant given CXX's compile-time type system. Source-level enumeration + generated-header freshness is the correct minimum viable C++ gate |
| `schemars`-based generated error docs | Overkill — static `docs/api/error-contract.md` markdown is enough for v9.1.0-bindings; revisit if a fourth binding lands |
| TUI-specific dependency parity (ratatui, arboard, crossterm, open) | These are local to `classic-tui`, not shared business-logic; out of scope for binding parity |
| CXX bridge `unsafe extern "C++"` rework | CXX framework manages this; no action needed beyond version upgrades |
| Major binding API redesigns | This milestone fixes parity gaps and surface coverage, not wholesale API changes |
| New end-user feature development | This is purely a parity/harmonization milestone |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CXXG-01 | Phase 1 | Complete |
| CXXG-02 | Phase 1 | Complete |
| CXXG-03 | Phase 1 | Complete |
| CXXG-04 | Phase 1 | Complete |
| CXXG-05 | Phase 1 | Complete |
| CXXS-01 | Phase 2 | Complete |
| CXXS-02 | Phase 2 | Complete |
| CXXS-03 | Phase 2 | Complete |
| CXXS-04 | Phase 2 | Complete |
| CXXS-05 | Phase 2 | Complete |
| CXXS-06 | Phase 2 | Complete |
| CXXS-07 | Phase 2 | Complete |
| CXXS-08 | Phase 2 | Complete |
| CXXS-09 | Phase 2 | Complete |
| CXXS-10 | Phase 2 | Complete |
| PYT-01 | Phase 3 | Complete |
| PYT-02 | Phase 3 | Complete |
| PYT-03 | Phase 3 | Complete |
| PYT-04 | Phase 3 | Complete |
| PYT-05 | Phase 3 | Complete |
| PYT-06 | Phase 3 | Complete |
| NODE-01 | Phase 4 | Complete |
| NODE-02 | Phase 4 | Complete |
| NODE-03 | Phase 4 | Pending |
| NODE-04 | Phase 4 | Complete |
| NODE-05 | Phase 4 | Complete |
| NODE-06 | Phase 4 | Pending |
| HARM-01 | Phase 4 | Complete |
| HARM-02 | Phase 4 | Complete |
| HARM-03 | Phase 3 | Complete |
| HARM-04 | Phase 3 | Complete |
| HARM-05 | Phase 6 | Pending |
| CI-01 | Phase 5 | Pending |
| CI-02 | Phase 5 | Pending |
| CI-03 | Phase 5 | Pending |
| CI-04 | Phase 5 | Pending |
| CI-05 | Phase 5 | Pending |
| CI-06 | Phase 5 | Pending |
| DOC-01 | Phase 6 | Pending |
| DOC-02 | Phase 6 | Pending |
| DOC-03 | Phase 6 | Pending |
| DOC-04 | Phase 6 | Pending |
| DOC-05 | Phase 6 | Pending |
| DOC-06 | Phase 6 | Pending |
| DOC-07 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 45 total
- Mapped to phases: 45
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-06*
*Last updated: 2026-04-06 after roadmap created for v9.1.0-bindings*

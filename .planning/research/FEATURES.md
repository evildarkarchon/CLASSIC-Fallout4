# Feature Research

**Domain:** Multi-language binding parity system for Rust-core workspace (C++ CXX, Python PyO3, Node NAPI-RS)
**Researched:** 2026-04-06
**Confidence:** HIGH — all findings drawn directly from source artifacts, parity tooling, and governance docs already in the repo

---

## Feature Landscape

### Table Stakes (Users / Contributors Expect These)

Features without which "Full Bindings Parity" is not credible. Missing any of these = the milestone goal is not met.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Python Tier-1/Tier-2 collapse** | 285 deferred entries means 80% of the Python surface is ungated. "Harmony achieved" requires one enforced tier. | LARGE | Runtime coverage registry has 360 tracked surfaces; 289 currently deferred. Must rebuild `parity_contract.json`, regenerate runtime coverage, regenerate `.pyi` stubs, and pass `check_parity_gate.py`. The contract file at `docs/implementation/python_api_parity/baseline/parity_contract.json` is the gate truth source. |
| **Node Tier-1/Tier-2 collapse** | 109 deferred entries (101 new per PROJECT.md; 128 total gaps per diff report). Same rationale: ungated surface is not parity. | LARGE | Tier-1 currently covers 261 rows / 287 runtime-verified surfaces. Must promote all deferred rows, rebuild `parity_contract.json`, regenerate `index.d.ts`, pass `parity:gate:local` + `dts:freshness:check`. `scanlog` owns 67 deferred Node entries — the biggest single chunk. |
| **Delete Tier-2 governance files** | Active governance/backlog files (`tier2_backlog_and_governance.md`, `tier2_wave_manifest.json`, `deferred_runtime_backlog.json`) would re-introduce the concept of "deferred is okay" after collapse. They must be deleted, not emptied. | SMALL | Files live in `docs/implementation/node_api_parity/governance/` and `docs/implementation/python_api_parity/governance/`. Deletion is a mechanical step, but it must happen after collapse gates pass or CI will fail on stale references. |
| **First-class C++ bridge parity gate** | Python and Node have automated gates (`check_parity_gate.py`, `parity:gate:local`). No equivalent exists for the CXX bridge today. Without one, C++ surface drift is invisible. | LARGE | Must enumerate CXX-exposed symbols from source (bridge `src/*.rs` module list + CXX exported functions/DTOs), define a baseline manifest, and produce a fail-on-drift check that CI can run. No binary ABI checks needed — source-level enumeration is sufficient and avoids Windows-only CI complications. |
| **C++ bridge surface completion** | The bridge currently narrows `classic-scangame-core` to 2 entry points while Node exposes ~20. Same pattern for `classic-version-registry-core` (drops 8+ fields), `classic-database-core` (no stats/typed results), `classic-path-core` (no documents validation), `classic-xse-core` (no typed `XseInfo`), and `classic-config-core` (no full suspect stack rules). | LARGE | Each crate is a separate sub-feature. The biggest gaps are `classic-scangame-core` (entirely missing orchestrator, crashgen, XSE checker, mod scan APIs) and `classic-version-registry-core` (missing `display_name`, `description`, `address_library`, `compatible_range`, `exe_hash`, `script_hashes`). |
| **First-time C++ surface for `classic-constants-core` and `classic-web-core`** | Both are already exposed in Node and Python. The C++ bridge has no module for either today. Frontend C++ code that needs game-id enums or mod-site URL helpers currently lacks a bridge path. | MEDIUM | `constants` is mostly enum projection — straightforward CXX work. `web` adds URL helpers and user-agent construction. Neither crate has async APIs, so no `block_on()` plumbing needed. |
| **C++ FCX issue getter** | Node exposes `getFcxConfigIssues()` returning a typed DTO vector. Python exposes `FcxModeHandler.get_fcx_messages()`. The C++ bridge exposes only `fcx_reset_global_state()` — reset-only, no inspection. | MEDIUM | Documented gap in `classic-cpp-bridge-data-entrypoints.md`: "keeps FCX bridge exposure reset-only in this phase; no C++ FCX issue DTO or getter exists yet." Requires a new CXX DTO type for `ConfigIssue` and a new bridge entry point in `src/scanner.rs`. |
| **Node PE-version extraction** | C++ exposes `extract_pe_version_string()` in `classic::game`. Python exposes `extract_pe_version()` returning a `(u16, u16, u16, u16)` tuple. Node exposes no PE version API — its `version.rs` has only semver parse/compare/extract/format helpers. | SMALL | The Rust implementation is `classic_version_core::pe_version::extract_pe_version()`. A Node wrapper follows the same pattern as the Python binding. Return type should be a typed object `{major, minor, patch, build}` rather than a flat string (prefer object shape over the C++ "format as string" approach). |
| **Python `classic_shared` runtime helpers as a public module** | `classic-shared-py` exists in the workspace and exposes `PyStringProcessor`, `PyPathHandler`, `PyRustPerformanceMonitor`, `RuntimeStats`, `get_runtime_stats`, `is_runtime_healthy`. The `aux` owner-module in the Python parity backlog (3 deferred entries: `BridgeMetrics`, `BridgeOperationType`, `RuntimeInfo`) maps to this surface. Node exposes equivalent helpers in `shared.rs` as `getRuntimeInfo()`, `isRuntimeAvailable()`, etc. | MEDIUM | Currently the `classic_shared` wheel is installed in `.venv` but is not part of the parity gate (`parity_contract.md` scopes only `classic_scanlog`, `classic_config`, `classic_version_registry`). Adding it to the gate means adding contract rows and runtime coverage metadata. |
| **CI enforcement: all three gates must pass** | Python and Node parity gates exist locally. A C++ gate is being created. Without CI enforcement, local gates drift between contributors. The goal is that any new Rust public API fails CI until all three bindings cover it. | MEDIUM | Requires CI workflow additions for the new C++ gate. Node already has `dts:freshness:check` in CI. Python CI runs `check_parity_gate.py`. The new C++ gate needs a similar `--fail-on-drift` invocation in the same CI pipeline. |
| **`binding-parity-overview.md` rewrite** | Current doc explicitly disclaims being a parity target or policy. After this milestone, it should be the "harmony achieved" reference showing full parity with no intentional gaps. | SMALL | Doc rewrite only. Content changes: remove disclaimer language, add harmony-achieved policy statement, update the exposure table to reflect complete coverage, link to the new C++ parity gate. |
| **Single source-of-truth parity policy doc** | No current doc states "all three binding surfaces must cover every shared Rust public API before merge." Without a codified policy, Tier-2 re-emerges organically in the next milestone. | SMALL | New doc, probably `docs/api/binding-parity-policy.md`. States the policy, links to the three gate scripts, defines what "covered" means (exposed through binding contract + gate row + test). |

### Differentiators (Genuine Best-in-Class Behaviors)

Features that go beyond "parity achieved" and make the gate system genuinely excellent. Not required for the milestone goal, but would distinguish the approach.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Unified cross-binding parity manifest** | Instead of three separate `parity_contract.json` files (Python, Node, C++ each their own), a single source-of-truth manifest tracks which Rust symbols are exposed in which bindings. Drift in any one binding is visible in one report. | LARGE | Currently each binding has its own `parity_contract.json`. Unifying them requires agreeing on a schema that supports language-specific metadata (Python `pythonExportPath`, Node `napi_name`, C++ namespace). Complex to implement correctly; adds maintenance burden if schema evolves. Depends on existing Python and Node tooling being refactored. |
| **Per-binding error-contract documentation** | A living doc that maps `Rust X error → Python Y exception → Node Z error.code → C++ rust::Error`. Currently, error-contract differences are a known source of "parity bugs" (see `binding-parity-overview.md` "Expect different error styles"). Formalizing the mapping prevents future divergence. | MEDIUM | A new doc (`docs/api/binding-error-contracts.md`) structured as a table: Rust error type / Python exception class / Node `error.code` string / C++ behavior (sentinel / `rust::Error` / exception). Does not require code changes — documentation only, but must be kept synchronized when errors change. Dependencies: requires the bridge surface completion work to be done first (can't document C++ FCX error contract if the C++ FCX getter doesn't exist yet). |
| **Generated C++ header freshness check (parallel to `dts:freshness:check`)** | Node has `bun run dts:freshness:check` that catches stale committed `index.d.ts`. The C++ bridge generates headers into `include/classic_cxx_bridge/*.h`. A freshness check that fails CI when committed headers drift from the current build would close the same category of drift. | MEDIUM | Feasible: commit a hash or diff of the generated headers, check against a fresh build in CI. Simpler than a full binary ABI check. Avoids the anti-feature of binary ABI checking while still catching header drift. Requires the C++ parity gate baseline to track header state. |
| **Structured error codes for C++ bridge** | Currently the C++ bridge loses error detail at the FFI edge (most failures become `""`, `false`, or an untyped `rust::Error` string). Exposing typed error codes through CXX DTOs (e.g., `ErrorCodeDto { code: String, message: String }`) would make C++ callers as informative as Node (`error.code`) and Python (`ClassicError` typed exceptions). | LARGE | Requires CXX DTO additions and changes to every bridge function that currently returns a sentinel. High coordination cost. Probably out of scope for v9.1.0-bindings, but worth flagging. |
| **Automated contract divergence alerting** | When a Rust public API changes and the parity gates are not run, the repo has no mechanism to alert maintainers. A pre-push hook or PR check that specifically detects "new public Rust API, no matching gate row" would catch gaps before they enter main. | MEDIUM | Could be implemented as a simple script that diffs `lib.rs` public exports against `parity_contract.json` rows. Depends on CI enforcement being in place first. |

### Anti-Features (Things to Explicitly Not Build)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Binary ABI checks for the C++ CXX bridge** | Seems like the obvious way to verify bridge correctness — compile and check symbol tables | CXX generates platform-specific binary, so ABI checks are Windows-MSVC-only, require a full C++ build in CI, and are fragile across MSVC versions. The CXX bridge correctness is already enforced at compile time by the CXX type system. Symbol-table checking adds CI complexity with no incremental safety benefit. | Source-level enumeration of bridge module exports plus generated-header freshness checks. The CXX type system plus the new source-level parity gate is sufficient. |
| **Exact surface parity across all three bindings** | "Parity" sounds like everything must match identically | C++ is Windows-only and intentionally uses sync/sentinel patterns. Python is per-crate-shaped. Node is flat-package. Forcing identical shapes would require either degrading Node/Python or adding CXX patterns that don't fit C++ consumer conventions. The value of parity is coverage (every Rust API is reachable from every binding), not identical signatures. | Coverage parity: every shared Rust public API has at least one binding entry point in each surface. Shape can legitimately differ (C++ sentinel `""` vs Node `null` vs Python `None`). |
| **Emptying (rather than deleting) Tier-2 governance files** | Feels safer — keep the file structure in case Tier-2 concept returns | Empty governance files are read as "no deferred APIs" by contributors, but the file's presence signals that Tier-2 is an accepted pattern. New contributors will populate them again in the next milestone. | Hard delete. If Tier-2 concept needs to return in a future milestone, it will be an explicit, documented decision, not an accidental population of a leftover file. |
| **Python-only or Node-only features in binding layers** | Python or Node binding code sometimes adds logic not present in Rust core (convenience wrappers, aggregation, etc.) | The `BINDING_AUDIT_CRITERIA.md` explicitly prohibits business logic in binding layers. Cross-binding features that live in one binding but not others create asymmetry the parity gate cannot detect. | Push any shared behavior to a `-core` crate. Binding layers stay thin. If a convenience API is valuable, add it to Rust core and expose it through all three bindings. |
| **Parity gate that checks internal/private Rust symbols** | Comprehensive coverage sounds better | Internal Rust symbols (`pub(crate)`, `pub(super)`) are implementation details. Gating on them creates noise when refactoring and forces binding authors to expose implementation choices. | Gate on `pub` items in `lib.rs` only. Match the existing Python and Node tooling behavior: both `check_parity_gate.py` and the Node gate parse from the public `lib.rs` surface. |
| **Automated `.pyi` generation (replacing maintained stubs)** | Python stub generation tools (stubgen, pyo3-stub-gen) can auto-generate stubs | PyO3 auto-generated stubs lose hand-authored docstrings, accurate return types for complex variants, and `#[pyo3(name = "...")]` name overrides. The existing `.pyi` files are maintained contributor artifacts that serve as the source of truth. Auto-generation would make the stub a build artifact rather than a contract, breaking the `validate_stubs.py` workflow. | Keep maintained `.pyi` stubs. Validate them with `validate_stubs.py`. The gate fails on stub/wrapper disagreement — that's the right check. |

---

## Feature Dependencies

```
[C++ parity gate (baseline)] ──required by──> [C++ CI enforcement]
[C++ parity gate (baseline)] ──required by──> [Generated header freshness check]
[C++ parity gate (baseline)] ──required by──> [Binding parity overview rewrite]

[C++ bridge surface completion] ──required by──> [C++ parity gate (baseline)]
    (can't write a complete baseline until the surface is complete)
[C++ FCX issue getter] ──part of──> [C++ bridge surface completion]
[C++ constants/web first exposure] ──part of──> [C++ bridge surface completion]

[Node Tier-1/Tier-2 collapse] ──required by──> [Node CI enforcement]
[Node Tier-1/Tier-2 collapse] ──required by──> [Binding parity overview rewrite]
[Node PE-version extraction] ──part of──> [Node Tier-1/Tier-2 collapse]
    (PE version is one of the Tier-2 deferred surfaces under version_registry/version owner)

[Python Tier-1/Tier-2 collapse] ──required by──> [Python CI enforcement]
[Python Tier-1/Tier-2 collapse] ──required by──> [Binding parity overview rewrite]
[Python classic_shared module] ──part of──> [Python Tier-1/Tier-2 collapse]
    (aux owner-module deferred entries include BridgeMetrics/RuntimeInfo from classic_shared)

[Delete Tier-2 governance files] ──requires──> [Python Tier-1/Tier-2 collapse PASS]
[Delete Tier-2 governance files] ──requires──> [Node Tier-1/Tier-2 collapse PASS]

[Single parity policy doc] ──requires──> [Binding parity overview rewrite]
[Per-binding error-contract doc] ──requires──> [C++ bridge surface completion]
    (can't document C++ error contracts for APIs that don't exist yet)
```

### Dependency Notes

- **C++ bridge surface completion must precede C++ parity gate baseline:** You cannot write an accurate "expected coverage" baseline for C++ before the surface is complete. The baseline written against an incomplete surface would need to be updated again after completion, creating double-work.
- **Node PE-version extraction is a leaf feature with no prerequisites:** The Rust implementation exists in `classic_version_core::pe_version`. The Node wrapper is a small addition to `src/version.rs`. It should return a typed object `{major: number, minor: number, patch: number, build: number}` to stay consistent with Node's preference for object shape over C++'s "format as string" approach.
- **Tier-2 governance file deletion must be the last step:** Deleting the files before all deferred entries are promoted would cause gate scripts that reference governance file paths to fail. Delete after all gates are green.
- **`classic_shared` Python module promotion:** The `classic-shared-py` crate already exists and is in the workspace. It exposes `PathHandler`, `PyRustPerformanceMonitor`, `RuntimeStats`, `get_runtime_stats`, `is_runtime_healthy`. The gap is that these helpers are not in the parity contract (`parity_contract.md` only covers `classic_scanlog`, `classic_config`, `classic_version_registry`). Adding `classic_shared` to the contract scope means adding contract rows for the `aux` owner-module entries and rebuilding the runtime coverage registry.

---

## MVP Definition

This milestone has a fixed goal ("harmony achieved"), not a product-fit validation. The MVP is the minimal set of features that makes the milestone statement true.

### Launch With (v9.1.0-bindings)

- [ ] Python Tier-1/Tier-2 collapse — all 285 deferred entries promoted, governance files deleted, gate green
- [ ] Node Tier-1/Tier-2 collapse — all 109 deferred entries promoted, governance files deleted, gate green
- [ ] C++ bridge parity gate — baseline manifest exists, fail-on-drift check passes in CI
- [ ] C++ bridge surface completion — scangame, database, version-registry, config suspect rules, path, xse all filled; constants and web exposed for first time; FCX issue getter added
- [ ] Node PE-version extraction — `extract_pe_version()` / `is_valid_executable_path()` exposed in Node
- [ ] Python `classic_shared` module added to parity gate scope
- [ ] Per-binding error-contract documentation
- [ ] CI runs all three gates on every PR
- [ ] `binding-parity-overview.md` rewritten as harmony-achieved reference
- [ ] Single source-of-truth parity policy doc created

### Add After Validation (v9.1.x or next milestone)

- [ ] Unified cross-binding parity manifest — too much tooling coordination for this milestone; single manifest may not be worth the schema complexity
- [ ] Generated C++ header freshness check — valuable but not required to claim parity; add once C++ gate is stable
- [ ] Automated contract divergence alerting (pre-push hook) — operational improvement, not parity

### Future Consideration (v10+)

- [ ] Structured error codes for C++ bridge — requires reshaping every current sentinel-return function; architectural change beyond this milestone's scope
- [ ] Binary ABI checks — explicitly anti-feature for this project (see above)

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Python Tier collapse (285 entries) | HIGH | HIGH | P1 |
| Node Tier collapse (109 entries) | HIGH | HIGH | P1 |
| C++ bridge surface completion | HIGH | HIGH | P1 |
| C++ parity gate (new) | HIGH | LARGE | P1 |
| CI enforcement (all three gates) | HIGH | MEDIUM | P1 |
| Delete Tier-2 governance files | HIGH | LOW | P1 (but last step) |
| Node PE-version extraction | MEDIUM | LOW | P1 |
| Python `classic_shared` promotion | MEDIUM | MEDIUM | P1 |
| FCX issue getter (C++) | MEDIUM | MEDIUM | P1 |
| C++ constants/web first exposure | MEDIUM | MEDIUM | P1 |
| Binding parity overview rewrite | HIGH | LOW | P1 |
| Single parity policy doc | MEDIUM | LOW | P1 |
| Per-binding error-contract doc | MEDIUM | MEDIUM | P2 |
| Generated C++ header freshness check | LOW | MEDIUM | P2 |
| Unified cross-binding manifest | LOW | LARGE | P3 |

**Priority key:**
- P1: Required for "Full Bindings Parity" to be true — ship in v9.1.0-bindings
- P2: Operational improvement — add in v9.1.x or next milestone
- P3: Nice to have — future consideration

---

## Specifics: What "Table Stakes Parity Gate" Actually Validates

This section answers the research question directly: what does a first-class binding parity gate validate?

### For Python and Node (already exist; collapse extends them)

**Table stakes (existing gates already do these):**
- Surface coverage: every Rust public symbol in `parity_contract.json` must appear in the binding (`missing_python` / `missing_node` fails the gate)
- Signature shape: callable signatures in the contract must match what the binding actually exports (signature_mismatch fails the gate)
- Freshness: Node `index.d.ts` must match a fresh build (`dts:freshness:check`); Python `.pyi` must match wrapper via `validate_stubs.py`
- Missing-from-Rust detection: if a contract row points to a Rust symbol that no longer exists, the gate catches it (`missing_rust` status)
- Runtime coverage tracking: separate from the gate itself, the `runtime_coverage_registry.json` / `runtime_coverage_summary.md` tracks which surfaces are actually exercised by tests

**Nice-to-have (neither gate currently does these):**
- Error-code parity: the gate does not check that Node `error.code` strings match Python exception class names in a cross-binding-consistent way
- Naming convention enforcement: `snake_case` vs `camelCase` is expected per language but not validated cross-binding
- DTO field completeness: if a Rust struct gains a new field and the binding DTO doesn't expose it, the gate only catches this if the contract row explicitly checks field presence
- Cross-binding consistency: no current gate checks "if Python exposes X, Node must also expose X" — each gate is per-surface

### For C++ (new gate, no prior art in this repo)

**Minimum viable C++ parity gate (table stakes for this milestone):**
- Source-level enumeration: parse each `src/*.rs` bridge module for `pub fn` signatures that are registered as CXX exports (via `#[cxx::bridge]` or the bridge module pattern)
- Baseline manifest: a committed JSON/TOML file listing expected CXX namespaces, function names, and DTO types
- Drift detection: compare current source-enumerated symbols against the baseline; fail if any symbol is missing from baseline or present in source but missing from baseline
- CI hook: the check runs on PRs and blocks merge when drift is detected

**Anti-feature for C++ gate (do not do):**
- Binary ABI checking: compiling C++ and inspecting symbol tables is Windows-MSVC-only, fragile, and adds 10+ minutes to CI. The CXX type system already provides compile-time correctness; source-level enumeration is sufficient for coverage checking.
- Cross-language exact-match enforcement: C++ DTOs legitimately differ from Node/Python shapes (sentinel patterns, flattened maps, etc.). The gate should check C++ surface completeness against a C++-appropriate baseline, not cross-validate against the Node contract schema.

### Tier Collapse Mechanics: What "Promote" Means in Tooling Terms

**For Python (per governance doc):**
1. Implement the missing binding wrapper in the relevant `*-py/src/*.rs` file
2. Update the `.pyi` stub to reflect the new export
3. Add a contract row to `parity_contract.json` with `pythonExportPath`, Rust symbol, owner, and expected signature metadata
4. Update `runtime_coverage_registry.json` to include the new surface with coverage metadata
5. Run `generate_baseline.py` and `generate_wave_manifest.py` to regenerate baseline artifacts
6. Run `check_parity_gate.py` — gate must pass
7. Run `validate_stubs.py` — stub validation must pass
8. Run pytest smoke tests — tests must pass
9. After all deferred entries are promoted: delete `tier2_backlog_and_governance.md`, `tier2_wave_manifest.json`, and `deferred_runtime_backlog.json` from the governance directory

**For Node (per governance doc):**
1. Implement the missing binding in `src/*.rs` with `#[napi]` annotations
2. Rebuild and commit `index.d.ts`
3. Add a contract row to `parity_contract.json`
4. Run `parity:gate:local`, `test:bun`, `test:node`, `dts:freshness:check` — all must pass
5. After all deferred entries are promoted: delete `tier2_backlog_and_governance.md`, `tier2_wave_manifest.json`, `deferred_runtime_backlog.json`, and `per_wave_acceptance_template.md` from the governance directory

**"Promote" in both cases is NOT just moving a JSON row from tier2 to tier1.** It requires a working implementation, an updated contract artifact, passing gate, and passing tests. The governance file deletion is the final step that signals no further deferral is possible.

---

## PE-Version Extraction Parity: What "Node Parity" Means

**C++ shape:** `extract_pe_version_string(exe_path: String) -> String` — formats `(u16,u16,u16,u16)` as `"major.minor.patch.build"`, returns `""` on any error.

**Python shape:** `extract_pe_version(path: str) -> tuple[int, int, int, int]` — raises `PyOSError` on path/IO errors, raises `PyValueError` on parse errors.

**Node target shape (recommended):** A typed object return:
```typescript
export interface PeVersionInfo {
  major: number
  minor: number
  patch: number
  build: number
}
export declare function extractPeVersion(path: string): PeVersionInfo
export declare function isValidExecutablePath(path: string): boolean
```

Rationale: Node's existing pattern (per `src/version.rs`) returns structured objects or primitives, not flat strings. Returning an object keeps parity with Python's structured return while avoiding C++'s "format as string and lose typed error info" design. Error behavior: throw on invalid path/IO (matching Python's raise pattern), which is already what Node does for validation-heavy calls (per `binding-parity-overview.md` "Node often returns null for fail-soft helpers but throws for validation-heavy calls").

---

## Sources

- `docs/api/binding-parity-overview.md` — current surface comparison table (HIGH confidence, source-backed)
- `docs/api/node-python-contract-map.md` — contract file locations (HIGH confidence, source-backed)
- `docs/api/binding-contract-refresh-note.md` — gate workflow documentation (HIGH confidence, source-backed)
- `docs/api/classic-cpp-bridge-game-entrypoints.md` — C++ bridge narrowing documentation (HIGH confidence, source-backed)
- `docs/api/classic-cpp-bridge-data-entrypoints.md` — C++ bridge data surface documentation (HIGH confidence, source-backed)
- `docs/implementation/node_api_parity/governance/tier2_backlog_and_governance.md` — Node deferred backlog (HIGH confidence, source-backed)
- `docs/implementation/node_api_parity/governance/gate_contract_baseline.md` — Node gate contract (HIGH confidence, source-backed)
- `docs/implementation/python_api_parity/governance/tier2_backlog_and_governance.md` — Python deferred backlog (HIGH confidence, source-backed)
- `ClassicLib-rs/node-bindings/classic-node/parity-artifacts/tier1_gate_report.md` — current Node gate status: 261 rows, 0 drift
- `ClassicLib-rs/node-bindings/classic-node/parity-artifacts/runtime_coverage_summary.md` — 396 tracked, 287 verified, 109 deferred
- `ClassicLib-rs/python-bindings/parity-artifacts/tier1_gate_report.md` — current Python gate status: 59 rows, 0 drift
- `ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.md` — 360 tracked, 71 verified, 289 deferred
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs` — current C++ bridge module structure (14 modules, all `#[cfg(windows)]`)
- `ClassicLib-rs/python-bindings/BINDING_AUDIT_CRITERIA.md` — thin-binding definition and audit status
- `.planning/PROJECT.md` — milestone requirements and active/pending decisions

---

*Feature research for: v9.1.0-bindings Full Bindings Parity*
*Researched: 2026-04-06*

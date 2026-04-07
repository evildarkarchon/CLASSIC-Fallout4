# Architecture Research

**Domain:** Multi-binding Rust library (C++/Python/Node parity gating)
**Researched:** 2026-04-06
**Confidence:** HIGH (sourced entirely from committed repo files)

---

## System Overview

The four-layer architecture is fixed and must not change. This document maps only
what the v9.1.0-bindings milestone adds or modifies inside it.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  FRONTENDS (consumers, Windows-only native targets)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │  classic-cli │  │  classic-gui │  │  classic-tui │                   │
│  │  (C++20/CXX) │  │  (Qt6/CXX)   │  │  (Ratatui)   │                   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                   │
├─────────┼─────────────────┼─────────────────┼──────────────────────────-┤
│  BINDING LAYER (thin adapters)                                            │
│  ┌──────────────────┐  ┌────────────────┐  ┌────────────────┐            │
│  │ classic-cpp-bridge│  │ classic-node   │  │ classic-*-py   │            │
│  │ (CXX staticlib)  │  │ (NAPI-RS cdylib│  │ (19 PyO3 crats)│            │
│  │ 14→16 modules    │  │ single crate)  │  │                │            │
│  │ + new C++ gate   │  │ + PE-version   │  │ + classic_shared│           │
│  └──────┬───────────┘  └───────┬────────┘  └───────┬────────┘            │
├─────────┼───────────────────────┼──────────────────┼────────────────────-┤
│  BUSINESS LOGIC (pure Rust, no PyO3 deps)                                 │
│  19 -core crates: classic-scanlog-core, classic-config-core, etc.         │
│  All async, all delegated from binding layer, all on shared Tokio runtime │
├──────────────────────────────────────────────────────────────────────────┤
│  FOUNDATION                                                               │
│  ┌───────────────────────┐  ┌──────────────────────────────┐              │
│  │ classic-shared-core   │  │ classic-shared-py            │              │
│  │ (runtime, errors,     │  │ (PyO3 utilities, exception   │              │
│  │  paths, strings)      │  │  hierarchy, GIL helpers)     │              │
│  └───────────────────────┘  └──────────────────────────────┘              │
└──────────────────────────────────────────────────────────────────────────┘
```

```
PARITY TOOLING (new + modified, CI-enforced after this milestone)

tools/
  python_api_parity/          -- EXISTING, extended
    check_parity_gate.py      -- MODIFIED: remove Tier-2 concept; single tier
    generate_baseline.py      -- MODIFIED: add all 19 crates, not just 3
    generate_wave_manifest.py -- MODIFIED: collapse to single manifest
  node_api_parity/            -- EXISTING, extended
    check_parity_gate.py      -- MODIFIED: remove Tier-2 concept; single tier
    generate_baseline.py      -- MODIFIED: expand surface to all promoted APIs
  cxx_api_parity/             -- NEW
    check_parity_gate.py      -- NEW: diff Rust pub items vs CXX ffi{} blocks
    generate_baseline.py      -- NEW: enumerate bridge surface from source
    generate_cxx_manifest.py  -- NEW: write baseline JSON from enumerated surface

.github/workflows/
  ci-python-bindings.yml      -- MODIFIED: Tier-2 governance steps removed
  ci-typescript.yml           -- MODIFIED: Tier-2 governance steps removed;
                                  C++ gate step NOT added here (see ci-cpp.yml)
  ci-cpp.yml                  -- MODIFIED: add cxx-parity-gate job that runs
                                  before cli-tests and gui-tests
```

---

## Component Boundaries — New vs. Modified

### 1. C++ Parity Gate (NEW component)

**Location:** `tools/cxx_api_parity/` — a new Python tool directory mirroring
the existing `tools/python_api_parity/` and `tools/node_api_parity/` directories.

**What it does:**
- Enumerates all `pub fn` / `pub struct` items in `-core` crate `lib.rs` files
  using regex parsing of Rust source (same technique as the existing Python gate's
  `parse_rust_surface()` in `tools/python_api_parity/generate_baseline.py`)
- Enumerates the CXX FFI surface by parsing `extern "Rust" { ... }` blocks inside
  `#[cxx::bridge]` / `mod ffi { }` blocks in each
  `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/*.rs` source file
- Produces a baseline JSON (`cxx_bridge_surface.json`) and a diff report
  (`cxx_parity_diff_report.md`) with the same structure as the Python/Node artifacts
- Runs without a Rust build: reads `.rs` source files only. No `syn` dependency,
  no Cargo invocation. Pure Python text analysis.
- CI invocation: `python tools/cxx_api_parity/check_parity_gate.py --repo-root .`

**Why text parsing, not `syn`:**  The existing Python/Node gates parse `.rs`
source with regex rather than a full Rust parser. Consistency is preferred.
The CXX bridge surface is also smaller and more structured than general Rust
(every public function lives inside a `mod ffi { extern "Rust" { ... } }` block),
making regex sufficient and avoiding a new Rust-in-Python dependency.

**Dependency direction:** reads Rust source → no build required → runs before
the CLI/GUI build jobs in CI. This is intentional: the gate checks intent (source),
not the compiled output.

**Output artifacts (new, committed):**
- `tools/cxx_api_parity/cxx_baseline_surface.json` — baseline bridge surface
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/parity-artifacts/` — per-run
  diff report and gate report (same layout as Node and Python parity-artifacts/)

**CI job placement in `ci-cpp.yml`:**
```
cxx-parity-gate:        # NEW job, runs first, no build needed
  runs-on: windows-latest
  steps:
    - checkout
    - setup-python 3.12
    - run: python tools/cxx_api_parity/check_parity_gate.py --repo-root .
    - upload-artifact (on failure): parity-artifacts/

cli-tests:              # EXISTING, now needs: [cxx-parity-gate]
gui-tests:              # EXISTING, now needs: [cxx-parity-gate]
```

**Build order dependency:** The CXX parity gate has NO dependency on the CXX
bridge build. It reads source. It must complete before the C++ surface expansion
phases land new modules, so that the baseline is established first.

---

### 2. New CXX Bridge Modules

**Location:** `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/`

**Existing modules (14):** config, database, files, game, markdown, message, path,
perf, registry, runtime, scangame, scanner, types, update, yaml

**New modules (2):** Follow the existing 14-module pattern — one file per domain,
one `#[cxx::bridge(namespace = "classic::domain")]` block. Do NOT create a grouping
`meta` module; the existing pattern is flat and it remains flat.

| New module file | Namespace | Source crate(s) | Bridges |
|-----------------|-----------|-----------------|---------|
| `src/constants.rs` | `classic::constants` | `classic-constants-core` | Game name enums, YAML key identifiers, constant strings |
| `src/web.rs` | `classic::web` | `classic-web-core` | URL helpers, user-agent string, mod-site helpers |

**Modified modules (several):** Existing modules gain more bridge functions to
close narrowing gaps. Key changes:

| Module | What narrows today | What gets added |
|--------|-------------------|-----------------|
| `scangame.rs` | Only `run_setup_checks` + `needs_path_detection` | BA2, INI, ENB, crashgen, Wrye checks; full setup orchestration |
| `database.rs` | Single-string and tab-delimited batch lookup | Structured row-shaped batch results |
| `game.rs` (version-registry) | Narrowed DTO missing display_name, description, etc. | Full `VersionInfoDto` + `compatible_range`, `exe_hash`, `address_library` fields; `XseInfo` typed struct |
| `game.rs` (xse) | String-based only, no typed `XseType` | Add `XseType` enum and `XseInfo` combined struct |
| `config.rs` | Narrows suspect rules | Expose structured `CrashgenRule` list; expose `YamlData.game_mods_freq` |
| `path.rs` | FO4-specific helpers only | Add `DocsPathFinder`, INI validation, `DocumentsChecker` surface |
| `scanner.rs` | FCX reset only, no FCX issue getter | Add `get_fcx_config_issues()` DTO function |

**Registration:** Each new module file is added to `lib.rs` behind `#[cfg(windows)]`:
```rust
#[cfg(windows)]
pub mod constants;
#[cfg(windows)]
pub mod web;
```

**Generated header impact:** CXX generates headers under
`include/classic_cxx_bridge/`. New modules produce new headers
(`classic_cxx_bridge/constants.h`, `classic_cxx_bridge/web.h`). The freshness
gate for generated headers (already established in the previous milestone's
`check_dts_freshness.py` analog) needs to be extended to cover generated CXX
headers. Specifically: add a `check_cxx_headers_freshness.py` script in
`tools/cxx_api_parity/` that diffs the committed header snapshots against a
fresh build output, similar to `tools/node_api_parity/check_dts_freshness.py`.

---

### 3. Python Tier Collapse

**What changes (file-touching footprint):**

| File or directory | Change type | Description |
|-------------------|-------------|-------------|
| `tools/python_api_parity/generate_baseline.py` | MODIFIED | Expand `RUST_TARGET_CRATES` from 3 entries to all 19 business-logic crates; expand `PYTHON_TARGET_MODULES` to all 19 Python binding crates |
| `tools/python_api_parity/check_parity_gate.py` | MODIFIED | Remove Tier-2 skip/defer logic; all entries are Tier-1; remove `--allow-tier2` flag if present |
| `tools/python_api_parity/generate_wave_manifest.py` | MODIFIED or DELETED | Wave concept goes away; file either deleted or repurposed as a single-manifest writer |
| `docs/implementation/python_api_parity/governance/tier2_backlog_and_governance.md` | DELETED | Tier-2 governance gone |
| `docs/implementation/python_api_parity/governance/tier2_wave_manifest.json` | DELETED | Wave manifest gone |
| `docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json` | DELETED | Deferred backlog gone |
| `docs/implementation/python_api_parity/baseline/parity_contract.json` | MODIFIED | Expanded to include all 285 previously-deferred entries now promoted to Tier-1 |
| `docs/implementation/python_api_parity/baseline/runtime_coverage_summary.{json,md}` | MODIFIED | Regenerated to reflect full surface |
| `ClassicLib-rs/python-bindings/parity-artifacts/*.{json,md}` | REGENERATED | All committed parity artifact files refreshed |
| `ClassicLib-rs/python-bindings/classic-*/classic_*.pyi` | MODIFIED | Stub files for crates that needed promoted APIs added |
| `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json` | MODIFIED | Coverage registry expanded for all promoted entries |

**Python binding crate footprint for newly promoted APIs:**
The 285 deferred entries span `scanlog` (227), `config` (18), `version_registry` (34),
and `aux` (3). The Rust wrapper files that need additions or corrections:

| Crate | Wrapper files most likely to change |
|-------|-------------------------------------|
| `classic-scanlog-py` | `src/lib.rs` + potentially new `src/streaming.rs`, `src/report.rs` |
| `classic-config-py` | `src/lib.rs` (CrashgenEntryRaw, game_mods_freq, format helpers) |
| `classic-version-registry-py` | `src/lib.rs` (MatchConfidence, MatchResult, VersionInfo, UnknownVersionHandling) |
| `classic-registry-py` (aux) | `src/lib.rs` (registrySet, registryRemove, registryClear) |

**CI change in `ci-python-bindings.yml`:**
- Remove any Tier-2 skip logic from the parity gate step
- The gate now fails on ANY missing entry (no deferred set)
- The stub validation step (`validate_stubs.py`) continues unchanged

---

### 4. Node Tier Collapse

**What changes (file-touching footprint):**

| File or directory | Change type | Description |
|-------------------|-------------|-------------|
| `tools/node_api_parity/generate_baseline.py` | MODIFIED | Expand Rust surface enumeration to include all 19 crates, not just the three currently tracked; expand Node surface to include all promoted APIs |
| `tools/node_api_parity/check_parity_gate.py` | MODIFIED | Remove Tier-2 skip/defer logic; single enforced tier |
| `tools/node_api_parity/generate_wave_manifest.py` | MODIFIED or DELETED | Wave concept gone |
| `docs/implementation/node_api_parity/governance/tier2_backlog_and_governance.md` | DELETED | |
| `docs/implementation/node_api_parity/governance/tier2_wave_manifest.json` | DELETED | |
| `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json` | DELETED | |
| `docs/implementation/node_api_parity/governance/gate_contract_baseline.md` | DELETED or SUPERSEDED | |
| `docs/implementation/node_api_parity/baseline/parity_contract.json` | MODIFIED | All 101 deferred entries promoted |
| `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.{json,md}` | MODIFIED | Regenerated |
| `ClassicLib-rs/node-bindings/classic-node/parity-artifacts/*.{json,md}` | REGENERATED | |
| `ClassicLib-rs/node-bindings/classic-node/index.d.ts` | MODIFIED | Rebuilt to include all promoted exports |
| `ClassicLib-rs/node-bindings/classic-node/src/*.rs` | MODIFIED | New `#[napi]` exports for promoted APIs |

**Node source module footprint for newly promoted APIs:**
The 101 deferred entries span `scanlog` (64 — StreamingLogParser, ReportGenerator,
detect_mods_batch, PatternMatcher), `config` (18), `version_registry` (4), and
`aux` (6 — registryClear, registryRemove, registrySet, registrySetGameVersion +2).

Most additions land in existing source files:
- `src/scanlog.rs` — new `#[napi]` functions for streaming parser and report helpers
- `src/config.rs` — CrashgenEntryRaw exposure, format_registry helpers
- `src/version_registry.rs` — MatchConfidence, MatchResult, VersionInfo, UnknownVersionHandling types
- `src/shared.rs` — registryClear, registryRemove, registrySet, registrySetGameVersion

**CI change in `ci-typescript.yml`:**
- Remove Tier-2 skip logic from parity gate step
- The `dts:freshness:check` step continues unchanged

---

### 5. Node PE-Version Extraction (NEW capability in existing module)

**Location:** `ClassicLib-rs/node-bindings/classic-node/src/version.rs` (MODIFIED)

**What gap:** `classic-version-core` exports `extract_pe_version()` via its
`pe_version` submodule. C++ exposes this through `classic::game`. Python exposes
it via `classic_version`. Node's `src/version.rs` currently stops at text-based
version helpers — `extract_pe_version` is absent.

**Integration point:** `classic-version-core` is already in `classic-node`'s
`Cargo.toml` as a dependency. `extract_pe_version` re-exports through
`classic_version_core::pe_version::extract_pe_version`. The `pelite` workspace
dependency is used by `classic-version-core`, not imported directly by
`classic-node`. No new Cargo.toml entry is needed.

**What to add to `src/version.rs`:**
```rust
/// Extract version from a Windows PE binary file.
///
/// Reads the version resource from a .exe or .dll using pelite.
/// Returns null if the file has no version resource or cannot be read.
#[napi]
pub fn extract_pe_version(path: String) -> Option<String> {
    classic_version_core::extract_pe_version(Path::new(&path))
        .ok()
        .map(|v| v.to_string())
}
```

**Downstream:** `index.d.ts` regenerates to include `extractPeVersion(path: string): string | null`.
The `dts:freshness:check` gate catches staleness.

---

### 6. Python `classic_shared` Module (NEW Python binding surface)

**Location:** `ClassicLib-rs/foundation/classic-shared-py/src/lib.rs` (ALREADY EXISTS)

**Key finding:** `classic-shared-py` already defines a `#[pymodule]` named
`classic_shared` that exposes `RuntimeStats`, `get_runtime_stats()`,
`is_runtime_healthy()`, `PyStringProcessor`, `PyPathHandler`, and
`PyRustPerformanceMonitor`. The module implementation is complete.

**What is missing:** `classic-shared-py` is NOT registered in the Cargo workspace
as a Python binding crate — check the workspace members in `ClassicLib-rs/Cargo.toml`.
It lives under `foundation/classic-shared-py` and is a Rust library dependency
used by other `-py` crates internally, but it does not produce a built Python
extension module (`.pyd`) that Python consumers can `import classic_shared` from.

**What changes:**
1. `rebuild_rust.ps1` — add `classic_shared` as a buildable target so
   `pwsh -File rebuild_rust.ps1 -Target python classic_shared` produces a
   `classic_shared*.pyd` wheel
2. `ClassicLib-rs/python-bindings/requirements-ci.txt` — no change needed
   (maturin handles the build)
3. Create `ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi` —
   the stub file for `classic_shared` (currently absent)
4. The parity contract and runtime coverage registry must include `classic_shared`
   entries (RuntimeStats, get_runtime_stats, is_runtime_healthy, etc.)
5. `ci-python-bindings.yml` — add `classic_shared` to the maturin build step
   that already builds `classic_config`, `classic_scanlog`, `classic_version_registry`

**PyO3 module name:** `classic_shared` (matches the `#[pymodule]` name already in
`classic-shared-py/src/lib.rs` at line 324).

**No new crate needed.** The module is already written. The gap is build wiring
and stub/parity registration.

---

### 7. CI Integration — Three Gate Ordering

**Current state:**
- Python parity gate: `ci-python-bindings.yml`, job `parity-gates`, runs first,
  no build required
- Node parity gate: `ci-typescript.yml`, job `parity-gates`, runs first, REQUIRES
  a full `bun run build` (NAPI binary must exist before `parity:gate` can load the
  module for runtime coverage)
- C++ parity gate: DOES NOT EXIST TODAY

**After this milestone:**

```
ci-python-bindings.yml
  parity-gates (unchanged except Tier-2 removal):
    - checkout
    - setup-python 3.12
    - python tools/python_api_parity/check_parity_gate.py --repo-root .
    - python ClassicLib-rs/validate_stubs.py ...
  build-and-test (needs: parity-gates):
    - full maturin build + pytest

ci-typescript.yml
  parity-gates (unchanged except Tier-2 removal):
    - checkout + rust + bun + python
    - bun install && bun run build      ← build required for runtime coverage
    - bun run parity:gate               ← checks runtime coverage too
    - bun run dts:freshness:check
  build-and-test (needs: parity-gates):
    - same build + bun/node tests

ci-cpp.yml
  cxx-parity-gate (NEW, source-only, no build):
    - checkout
    - setup-python 3.12
    - python tools/cxx_api_parity/check_parity_gate.py --repo-root .
    - python tools/cxx_api_parity/check_cxx_headers_freshness.py --repo-root . --check-only
    - upload-artifact on failure
  cli-tests (needs: [cxx-parity-gate]):
    - existing steps unchanged
  gui-tests (needs: [cxx-parity-gate]):
    - existing steps unchanged
```

**Fail-fast vs aggregate behavior:**
- Python gate: fail-fast on first gate failure; `build-and-test` is skipped
- Node gate: fail-fast; `build-and-test` matrix is skipped
- C++ gate: fail-fast; CLI and GUI test jobs are skipped
- Gates on separate workflows do NOT wait for each other; they run independently
  on push/PR, which means a PR can fail all three independently and surface all
  problems in one round

**No cross-workflow ordering needed.** Each gate is self-contained in its
workflow file and guards only its own downstream build/test jobs.

---

### 8. Documentation Cleanup (file-touching footprint)

| File | Change |
|------|--------|
| `docs/api/binding-parity-overview.md` | REWRITTEN — "harmony achieved" reference replacing the current "here is the current state with gaps" framing |
| `docs/api/node-python-contract-map.md` | MODIFIED — remove references to Tier-2 governance directories that are deleted |
| `docs/api/binding-contract-refresh-note.md` | MODIFIED — update to reference CXX header freshness gate alongside the dts freshness gate |
| `docs/implementation/python_api_parity/governance/` | THREE files DELETED (see Tier Collapse section) |
| `docs/implementation/node_api_parity/governance/` | FOUR files DELETED |
| New file: `docs/api/binding-parity-policy.md` | NEW — single source-of-truth parity policy: one tier, three gates, gate must pass before merge |

---

## Recommended File-Change Scope Per Phase

The seven integration areas above map to phases. Phases must respect build
order — specifically:

1. **CXX gate tooling first** — no build dependency; establishes the baseline
   surface the bridge expansion will need to satisfy
2. **CXX bridge surface expansion** — add new modules and fill narrowing gaps;
   requires bridge to build with MSVC (`ci-cpp.yml`)
3. **Python tier collapse** — tooling + wrapper expansion; requires maturin build
4. **Node tier collapse** — tooling + wrapper expansion; requires NAPI build
5. **Node PE-version** — small addition inside `src/version.rs`; included in Node build
6. **Python `classic_shared`** — stub + build wiring; included in Python build
7. **Documentation reset and governance file deletion** — no build required;
   can be done last or alongside its respective binding phase

**Dependency chain:**
```
CXX gate tooling
    |
CXX bridge expansion (gate now enforces it)
    |            |
Python tier    Node tier
collapse       collapse
    |              |
Python         Node
classic_shared  PE-version
    |              |
Documentation reset (all gates green)
```

---

## Patterns in This Milestone

### Pattern: Source-Parsing Parity Gate (applied to CXX)

**What:** A Python script reads `.rs` source to enumerate Rust public items and
bridge surface items, then diffs them. No build, no `syn`.

**When to use:** When the binding surface is small, structured, and can be
identified by syntactic patterns (`pub fn`, `extern "Rust" {`, `#[cxx::bridge]`).

**Precedent:** Both `tools/python_api_parity/generate_baseline.py` and
`tools/node_api_parity/generate_baseline.py` use the same approach: regex over
`lib.rs` for Rust symbols, regex/AST over binding source for the exposed surface.

### Pattern: Flat Module per Domain (applied to new CXX modules)

**What:** Each new bridge capability gets its own `src/domain.rs` file with a
single `#[cxx::bridge(namespace = "classic::domain")]` block. No grouping modules.

**When to use:** Always in `classic-cpp-bridge`. The existing 14 modules set this
convention; the two new ones follow it.

**Why not a `meta` module:** The bridge module list is small enough that flat
organization wins over grouping. Grouping would require restructuring the `lib.rs`
module re-exports without benefit.

### Pattern: Extend Existing Source Files (applied to Node and Python promotion)

**What:** When promoting Tier-2 entries, add `#[napi]` functions or `#[pyfunction]`
entries to the existing `src/*.rs` wrapper file that owns the domain. Create new
`src/*.rs` files only when the promoted surface is large enough to be unmanageable
in the existing file (threshold: >200 lines of new content in one file).

**When to use:** Always prefer extending existing files for 1-30 new functions.
Create a new file for a structurally distinct capability (e.g., `src/streaming.rs`
for `StreamingLogParser` if it needs its own state machine adapter).

---

## Anti-Patterns in This Scope

### Anti-Pattern: Adding `pelite` to `classic-node/Cargo.toml`

**What people might do:** Add `pelite = { workspace = true }` to `classic-node`
so `src/version.rs` can call `pelite` directly.

**Why it's wrong:** `classic-version-core` already wraps pelite behind
`extract_pe_version()`. The Node binding should call the core function, not the
underlying crate. Adding pelite directly to the node binding adds a duplicate
dependency path and violates the thin-adapter pattern.

**Do this instead:** Call `classic_version_core::extract_pe_version(path)` from
`src/version.rs`. The `pelite` crate is already a transitive dependency of
`classic-version-core`, which is already in `classic-node`'s Cargo.toml.

### Anti-Pattern: Creating a New Crate for `classic_shared` Python Module

**What people might do:** Create a new `python-bindings/classic-shared-py` crate
to host the `classic_shared` Python module, separate from the existing
`foundation/classic-shared-py`.

**Why it's wrong:** `foundation/classic-shared-py/src/lib.rs` already defines
the `#[pymodule]` named `classic_shared` with its full implementation. Creating
a second crate would either duplicate code or create a circular-looking dependency.

**Do this instead:** Wire the existing `foundation/classic-shared-py` as a
maturin build target. The module name, implementation, and exported symbols are
already correct. Add the stub file and parity registration alongside it.

### Anti-Pattern: Running the CXX Gate After the CXX Build

**What people might do:** Add the CXX parity gate as a step inside `cli-tests`
or `gui-tests` (after the CMake/Cargo build).

**Why it's wrong:** The gate is source-driven and does not need a build. Putting
it after the build adds 60-90 minutes of build latency before surfacing a parity
violation. It also means a gate failure arrives after a full build spend.

**Do this instead:** Run the CXX parity gate in a dedicated `cxx-parity-gate` job
that only needs Python and a checkout. Make `cli-tests` and `gui-tests` depend on
`cxx-parity-gate`. This pattern mirrors how `ci-python-bindings.yml` separates
`parity-gates` from `build-and-test`.

### Anti-Pattern: Merging All Three Gates Into One Workflow

**What people might do:** Add the CXX gate as a step in `ci-typescript.yml` or
`ci-python-bindings.yml` to avoid touching `ci-cpp.yml`.

**Why it's wrong:** The three binding surfaces have different build requirements
and different failure semantics. The CXX gate belongs in `ci-cpp.yml` because a
failure there should block C++ builds, not Node or Python builds. Each workflow
independently guards its own surface.

**Do this instead:** Add a `cxx-parity-gate` job to `ci-cpp.yml` only.

---

## Integration Points Summary

| Capability | Integration Point | New vs Modified | Build Dependency |
|------------|-------------------|-----------------|------------------|
| CXX parity gate | `tools/cxx_api_parity/` (new dir) + `ci-cpp.yml` new job | NEW | None (source-only) |
| CXX header freshness gate | `tools/cxx_api_parity/check_cxx_headers_freshness.py` | NEW | Needs committed header snapshot |
| New bridge modules (constants, web) | `cpp-bindings/classic-cpp-bridge/src/{constants,web}.rs` + `lib.rs` | NEW files, MODIFIED lib.rs | MSVC/CXX bridge build |
| Bridge gap closure (scangame, db, game, config, path, scanner) | `cpp-bindings/classic-cpp-bridge/src/{scangame,database,game,config,path,scanner}.rs` | MODIFIED | MSVC/CXX bridge build |
| Python tier collapse | `tools/python_api_parity/*.py` + baseline JSON + 19 `.pyi` stubs + `parity_contract.json` + `coverage_registry.json` | MODIFIED (many) | maturin develop |
| Python scanlog wrapper expansion | `python-bindings/classic-scanlog-py/src/` | MODIFIED | maturin develop |
| Python config wrapper expansion | `python-bindings/classic-config-py/src/lib.rs` | MODIFIED | maturin develop |
| Python version-registry expansion | `python-bindings/classic-version-registry-py/src/lib.rs` | MODIFIED | maturin develop |
| Python registry/aux expansion | `python-bindings/classic-registry-py/src/lib.rs` | MODIFIED | maturin develop |
| Python `classic_shared` module | `foundation/classic-shared-py/classic_shared.pyi` (NEW stub) + `rebuild_rust.ps1` + `ci-python-bindings.yml` | MODIFIED (build wiring), NEW stub | maturin develop |
| Node tier collapse | `tools/node_api_parity/*.py` + baseline JSON + `index.d.ts` + `parity_contract.json` | MODIFIED (many) | `bun run build` |
| Node scanlog expansion | `node-bindings/classic-node/src/scanlog.rs` | MODIFIED | `bun run build` |
| Node config/version_registry/aux expansion | `src/{config,version_registry,shared}.rs` | MODIFIED | `bun run build` |
| Node PE-version | `node-bindings/classic-node/src/version.rs` | MODIFIED | `bun run build` |
| Governance file deletion | `docs/implementation/{python,node}_api_parity/governance/` | DELETED (7 files) | None |
| Doc rewrite | `docs/api/binding-parity-overview.md` + new `docs/api/binding-parity-policy.md` | REWRITTEN + NEW | None |

---

## Sources

- `ClassicLib-rs/Cargo.toml` — workspace membership and shared deps (pelite confirmed workspace dep)
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs` — 14 current modules, all `#[cfg(windows)]`
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` — confirms narrowing: only 2 functions exposed
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs` — confirms PE-version in C++ bridge
- `ClassicLib-rs/node-bindings/classic-node/src/version.rs` — confirms PE-version absent from Node
- `ClassicLib-rs/node-bindings/classic-node/Cargo.toml` — confirms `pelite` absent from direct deps
- `ClassicLib-rs/foundation/classic-shared-py/src/lib.rs` — confirms `classic_shared` module fully implemented
- `ClassicLib-rs/node-bindings/classic-node/package.json` — confirms parity gate commands and CI entry points
- `.github/workflows/ci-cpp.yml` — confirms no existing parity gate job in C++ workflow
- `.github/workflows/ci-python-bindings.yml` — confirms existing Python gate structure
- `.github/workflows/ci-typescript.yml` — confirms existing Node gate structure (build-first)
- `tools/python_api_parity/generate_baseline.py` — confirms 3-crate scope today; regex-based source parsing
- `tools/node_api_parity/check_parity_gate.py` — confirms Tier-2 skip logic in gate
- `docs/implementation/node_api_parity/governance/tier2_backlog_and_governance.md` — 101 deferred Node entries confirmed
- `docs/implementation/python_api_parity/governance/tier2_backlog_and_governance.md` — 282 deferred Python entries confirmed
- `docs/api/binding-parity-overview.md` — full current-state gap inventory per crate

---
*Architecture research for: v9.1.0-bindings Full Bindings Parity*
*Researched: 2026-04-06*

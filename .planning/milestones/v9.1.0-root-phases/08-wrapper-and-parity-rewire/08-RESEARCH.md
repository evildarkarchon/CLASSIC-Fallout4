# Phase 8: Wrapper and Parity Rewire - Research

**Researched:** 2026-04-12
**Domain:** Brownfield wrapper, frontend, and parity-tool path rewiring after Rust workspace relocation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

### Wrapper Surface
- **D-01:** Phase 8 preserves all current operational entrypoints: `rebuild_rust.ps1`, `rebuild_node.ps1`, `classic-cli/build_cli.ps1`, `classic-gui/build_gui.ps1`, package-local Node scripts, and the repo-root `classic-tui` cargo flow.
- **D-02:** When commands overlap, repo-root wrappers are canonical. Package-local commands stay working, but they are secondary to the repo-root workflow.
- **D-03:** `rebuild_node.ps1` remains a supported entrypoint, but it should become a thin alias over the canonical Node rebuild flow rather than a separate maintained implementation.
- **D-04:** The TUI stays a direct repo-root Cargo entrypoint in Phase 8; do not add a dedicated TUI wrapper just to mirror the CLI/GUI script model.

### Legacy Path Policy
- **D-05:** Phase 8 ends active `ClassicLib-rs/...` support in wrapper and parity workflows.
- **D-06:** If a user or script still passes an old `ClassicLib-rs/...` path, tooling should fail fast and show the correct repo-root replacement instead of warning-and-continuing or silently normalizing.
- **D-07:** Help text and wrapper output should explicitly teach the new repo-root command/path when rejecting an old one.
- **D-08:** Regression coverage for Phase 8 should prove both root-path success and legacy-path rejection.

### Parity Tooling And Artifacts
- **D-09:** Python, Node, CXX, and Node d.ts freshness tooling should fully cut over to root-level binding paths in Phase 8; do not rely on old in-code defaults plus overrides.
- **D-10:** Keep non-baseline parity outputs in per-binding local directories at the new root-level locations.
- **D-11:** If checked-in path-bearing parity or freshness artifacts become stale because of the relocation, refresh those artifacts in Phase 8 while keeping parity contracts and API expectations unchanged.
- **D-12:** Any parity or freshness workflow that still reads from or writes to `ClassicLib-rs/...` should hard-fail as a regression.

### Native Proof Depth
- **D-13:** Phase 8 closes on build-plus-smoke proof, not build-only proof and not install/package closure by default.
- **D-14:** CLI and GUI proof should include their existing `-Test` flows through `classic-cli/build_cli.ps1 -Test` and `classic-gui/build_gui.ps1 -Test`.
- **D-15:** TUI proof should include a lightweight repo-root run check, such as `cargo run -p classic-tui -- --help` or `--version`, rather than build-only proof.
- **D-16:** Native install/package flows stay out of the default Phase 8 closure unless they are required to make the mandatory proof surfaces work.

### the agent's Discretion
- Exact alias mechanics for `rebuild_node.ps1`, as long as it delegates to one canonical Node rebuild implementation.
- Exact wording of migration hints, as long as old-path failures point to the correct repo-root replacement.
- Exact lightweight TUI smoke command (`--help` vs `--version`), as long as it proves the repo-root entrypoint runs.
- Exact placement and naming of Phase 8 regression tests, as long as they cover both canonical success and legacy-path rejection.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within Phase 8 scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INTG-01 | Contributor can run the existing Rust-consuming wrapper entrypoints after relocation, including repo rebuild scripts and native CLI/GUI/TUI integration flows | Preserve existing entrypoints, retarget all internal paths to repo root, add explicit legacy-path rejection, and prove with `rebuild_rust.ps1`, `rebuild_node.ps1`, `classic-cli/build_cli.ps1 -Test`, `classic-gui/build_gui.ps1 -Test`, and a repo-root `cargo run -p classic-tui ...` smoke path. |
| INTG-02 | Contributor can run the Python, Node, and CXX parity gates against the relocated workspace without path drift or parity-contract changes | Rewire default paths inside `tools/*_api_parity/*`, keep artifacts binding-local, refresh only path-bearing stale artifacts, and add regression coverage that fails on any `ClassicLib-rs/...` read/write in parity or freshness flows. |
</phase_requirements>

## Project Constraints (from AGENTS.md)

- Prioritize active work in `classic-cli/`, `classic-gui/`, and `ClassicLib-rs/`.
- Keep all business logic in Rust; keep wrappers/frontends thin.
- Maintain a single shared Tokio runtime from Rust core runtime facilities.
- Keep docs synchronized with architecture or workflow changes, especially `README.md` and `AGENTS.md`.
- Never write to `NUL` or `nul` on Windows.
- Consult `docs/api/README.md` before changing public Rust, bridge, GUI-consumer, or binding-facing APIs; update affected `docs/api/` pages if contracts change.
- Never run C++ tests directly via raw `ctest` or test binaries; use `classic-cli/build_cli.ps1 -Test` or `classic-gui/build_gui.ps1 -Test`.
- Native C++ targets are Windows/MSVC based.
- When using Git Bash for MSVC-targeted Rust/C++, source `tools/use_msvc_from_git_bash.sh` first.
- Python and Node bindings must stay in sync with Rust core logic.

## Summary

Phase 8 should be a path-contract rewrite, not a workflow redesign. The standard pattern is: keep every public entrypoint, derive all internal paths from repo root, hard-fail on `ClassicLib-rs/...` legacy inputs, and prove the migrated contract through the real wrapper/parity/native entrypoints instead of cargo-only checks.

The live repo already shows the main breakpoints. `rebuild_rust.ps1` still targets `ClassicLib-rs/python-bindings` and `ClassicLib-rs/node-bindings/classic-node`; `rebuild_node.ps1` points at a non-existent `rust/node-bindings/classic-node`; CMake include paths still use `../ClassicLib-rs/cpp-bindings/...`; Python/Node/CXX parity tools still default to `ClassicLib-rs/...`; and CI still caches and runs from legacy paths. The work is therefore mostly deterministic rewiring plus regression tests.

One important nuance: “no parity-contract changes” means no API-surface drift, not “leave stale path-bearing JSON untouched.” The checked-in CXX parity contract still embeds `sourceFile: ClassicLib-rs/...`, so Phase 8 should refresh path-bearing artifacts where necessary while keeping surface rows and semantics unchanged.

**Primary recommendation:** Rewire all wrappers and parity defaults to repo-root-relative paths, reject legacy `ClassicLib-rs/...` inputs explicitly, and close the phase only after the preserved entrypoints pass from the relocated layout.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Cargo virtual workspace | local `cargo 1.94.0`; repo keeps virtual manifest | Canonical workspace root and shared `Cargo.lock`/`target` | Official Cargo workspaces make the directory containing the workspace manifest the workspace root; this is the standard source of truth. |
| PowerShell wrapper entrypoints | repo-maintained (`rebuild_rust.ps1`, `rebuild_node.ps1`, `build_cli.ps1`, `build_gui.ps1`) | Preserve operator-facing workflows | Locked by context; the safe migration is to retarget them, not replace them. |
| Corrosion | repo-pinned `v0.6.1` | CMake ↔ Cargo bridge for CLI/GUI | Existing native frontends already import `classic-cpp-bridge` through Corrosion; path rewiring is lower-risk than toolchain replacement. |
| Repo parity gate scripts | repo-owned Python tools under `tools/` | Python, Node, and CXX parity/freshness enforcement | Existing gates already encode the repo contract; Phase 8 should fix defaults and tests instead of inventing a new parity system. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `@napi-rs/cli` | repo pin `^3.0.0` (`npm` latest `3.6.1`, modified 2026-04-08) | Build `classic-node` and regenerate `index.d.ts` | Keep the existing package-local Node build flow; do not upgrade during this migration unless a blocker is proven. |
| Bun | local `1.3.10` | Run Node package scripts, tests, and parity helpers | Use from `node-bindings/classic-node`. |
| uv + pytest | local `uv 0.11.6`, `pytest 9.0.3` | Python bindings venv, parity, and planning tests | Use the bindings-local `.venv`; do not switch to a repo-root venv. |
| CMake + VS wrapper bootstrap | local `cmake 4.3.1`, VS discovered via `vswhere` | Native CLI/GUI configure/build/test | Use existing `build_cli.ps1` and `build_gui.ps1` wrappers; they bootstrap VS dev shell. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Preserving wrapper entrypoints | Replace with new scripts/commands | Faster to prototype, but violates locked decisions and creates migration churn for contributors. |
| Hard-failing legacy paths | Silent normalization of `ClassicLib-rs/...` | Lower immediate friction, but keeps dual-layout behavior alive and hides regressions. |
| Existing parity tools | New ad hoc diff scripts | Reinvents audited behavior and weakens parity-contract continuity. |
| Repo-root cargo TUI entrypoint | New TUI wrapper for symmetry | Explicitly out of scope; adds maintenance with no migration value. |

**Installation:**
```bash
# No new packages should be introduced in Phase 8.
# Preserve the existing pinned stack and rewire paths only.
```

**Version verification:** `@napi-rs/cli` registry latest is `3.6.1` (modified 2026-04-08) while the repo pins `^3.0.0`; TypeScript registry latest is `6.0.2` (modified 2026-04-01) while the repo pins `^5.8.2`. Do not upgrade either in this phase. Corrosion is pinned in-repo at `v0.6.1`; upstream has newer release notes, but dependency/toolchain upgrades are explicitly out of scope.

## Architecture Patterns

### Recommended Project Structure
```text
repo root
├── rebuild_rust.ps1              # canonical Rust/Python/Node rebuild entrypoint
├── rebuild_node.ps1              # thin alias over canonical Node rebuild flow
├── classic-cli/build_cli.ps1     # native CLI build/test proof
├── classic-gui/build_gui.ps1     # native GUI build/test proof
├── node-bindings/classic-node/   # package-local Node scripts + artifacts
├── python-bindings/              # bindings-local .venv + parity artifacts
├── cpp-bindings/classic-cpp-bridge/
├── tools/*_api_parity/           # root-relative parity/freshness defaults
└── tests/planning/test_phase08_validation.py
```

### Pattern 1: Preserve public entrypoints, collapse duplicate implementations
**What:** Keep every current command surface, but route overlapping behavior through one canonical repo-root implementation.
**When to use:** `rebuild_node.ps1` vs package-local Node scripts; wrapper entrypoints that currently duplicate path logic.
**Example:**
```powershell
# Source: Phase 8 CONTEXT D-01..D-04
$nodeDir = Join-Path $ProjectRoot "node-bindings/classic-node"
Push-Location $nodeDir
try {
    & bun run build
} finally {
    Pop-Location
}
```

### Pattern 2: Explicit legacy-path rejection with migration hint
**What:** Reject `ClassicLib-rs/...` inputs at argument/default boundaries and print the repo-root replacement.
**When to use:** Wrapper parameters, parity tool options, stub validation, freshness scripts.
**Example:**
```powershell
# Source: Phase 8 CONTEXT D-05..D-07
if ($SomePath -like 'ClassicLib-rs/*') {
    Write-Error "Legacy path '$SomePath' is no longer supported. Use '$($SomePath -replace '^ClassicLib-rs/', '')' from repo root."
    exit 1
}
```

### Pattern 3: Root-relative defaults, binding-local artifacts
**What:** Default all parity/freshness tools to repo-root source paths while keeping ephemeral outputs near each binding.
**When to use:** `tools/python_api_parity/*`, `tools/node_api_parity/*`, `tools/cxx_api_parity/*`, `validate_stubs.py`.
**Example:**
```python
# Source: existing tool pattern, updated per Phase 8 D-09..D-12
parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[2]))
parser.add_argument("--output-dir", default="node-bindings/classic-node/parity-artifacts")
```

### Pattern 4: Prove with real entrypoints, not cargo-only checks
**What:** Validate the moved layout through wrapper/native/parity commands that contributors actually use.
**When to use:** Phase closure and regression tests.
**Example:**
```bash
# Source: repo wrapper conventions + AGENTS.md
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
python tools/cxx_api_parity/check_parity_gate.py --repo-root .
python tools/python_api_parity/check_parity_gate.py --repo-root .
```

### Anti-Patterns to Avoid
- **Silent normalization of legacy paths:** `validate_stubs.py` still accepts `--rust-dir ClassicLib-rs`; Phase 8 policy requires hard failure, not compatibility normalization.
- **Two maintained Node rebuild implementations:** `rebuild_node.ps1` must become an alias, not a second source of truth.
- **Refreshing parity baselines before defaults are fixed:** stale `ClassicLib-rs/...` defaults can regenerate artifacts into the wrong tree.
- **Using raw `ctest` as phase proof:** repo policy requires the PowerShell wrappers for CLI/GUI tests.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Workspace compatibility layer | A permanent dual-root shim that silently supports both repo root and `ClassicLib-rs/` | One canonical repo-root path contract + explicit failure on legacy inputs | Dual-root support hides regressions and contradicts milestone requirements. |
| Node declaration freshness | Custom string comparison for `index.d.ts` | `tools/node_api_parity/check_dts_freshness.py` | Existing tool already uses `git diff` and writes auditable artifacts. |
| Parity drift detection | New binding diff logic | Existing `check_parity_gate.py` scripts | Contracts, reports, and CI already depend on them. |
| Native wrapper commands | New CLI/GUI/TUI wrappers | Existing `build_cli.ps1`, `build_gui.ps1`, repo-root cargo for TUI | Public entrypoints are already established and locked. |
| Path mapping rules | Scattered manual string edits with no central policy | Repo-root derivation helpers + regression tests for rejection and success | Brownfield path rewires fail when every script invents its own rule. |

**Key insight:** The risky part of this phase is not compilation; it is inconsistent path policy. Reuse the repo’s existing wrappers and gates, but make them all derive from the same repo-root contract.

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `docs/implementation/cxx_api_parity/baseline/parity_contract.json` stores `sourceFile` values under `ClassicLib-rs/...`; Python/Node contracts inspected at the top level do not embed old source paths the same way. | **Data migration:** refresh the checked-in CXX parity contract/artifacts so stored source paths match repo-root locations without changing API rows or expectations. |
| Live service config | None — verified by repo audit of this phase’s owned surfaces (`rebuild_*.ps1`, CMake, parity tools, workflows, planning tests). No UI-managed external service config surfaced in the evidence read for Phase 8. | None. |
| OS-registered state | None — no Task Scheduler/systemd/launchd/pm2 registrations are represented in repo-owned Phase 8 surfaces, and the native wrappers bootstrap VS state at runtime instead of relying on a checked-in registration artifact. | None. |
| Secrets/env vars | `VCPKG_ROOT` is required for native builds; `Qt6_DIR` is optional for GUI fallback. No checked-in secret key or env-var name containing `ClassicLib-rs` was found in the inspected Phase 8 surfaces. | No rename migration. Keep env-var names unchanged; only update code/help text that mentions old paths. |
| Build artifacts | Root-local artifacts already exist at `python-bindings/.venv`, `python-bindings/dist-rust`, `python-bindings/parity-artifacts`, `node-bindings/classic-node/dist`, `node-bindings/classic-node/node_modules`, `node-bindings/classic-node/*.node`, `node-bindings/classic-node/parity-artifacts`, `cpp-bindings/classic-cpp-bridge/parity-artifacts`; stale legacy outputs still exist under `ClassicLib-rs/target/`. | **Code edit + clean rebuild:** rewire tools to write only to root-level binding locations, then regenerate. **Cleanup:** remove/ignore stale `ClassicLib-rs/target` during proof so old outputs cannot mask failures. |

## Common Pitfalls

### Pitfall 1: Wrapper drift survives the Rust move
**What goes wrong:** Cargo works from repo root, but `rebuild_rust.ps1`, `rebuild_node.ps1`, CLI/GUI CMake includes, or CI still point at legacy paths.
**Why it happens:** These consumers are path-encoded, not discovery-based.
**How to avoid:** Audit every preserved entrypoint and rewrite internal joins/defaults in the same phase.
**Warning signs:** Missing `Cargo.toml`, missing bridge include paths, or wrappers still printing `ClassicLib-rs/...` guidance.

### Pitfall 2: Legacy compatibility code violates the new policy
**What goes wrong:** A tool “helps” by accepting `ClassicLib-rs/...` and normalizing it.
**Why it happens:** Transitional logic from Phase 6/7 remains in place (`validate_stubs.py` still does this).
**How to avoid:** Replace normalization with a hard failure plus replacement hint.
**Warning signs:** Commands succeed when passed `ClassicLib-rs/...` instead of rejecting it.

### Pitfall 3: Node script depth is off by exactly one directory
**What goes wrong:** `bun run parity:gate` or `bun run dts:freshness:check` fails because `../../../tools/...` is now one level too deep.
**Why it happens:** `classic-node` moved from `ClassicLib-rs/node-bindings/classic-node` to `node-bindings/classic-node`.
**How to avoid:** Recompute every package-local relative path from the new package root; do not search-and-replace blindly.
**Warning signs:** Python reports missing script files from within package-local Node commands.

### Pitfall 4: CXX parity “no contract change” is misread as “leave stale path fields alone”
**What goes wrong:** The checked-in CXX contract keeps `sourceFile: ClassicLib-rs/...` even though the bridge moved.
**Why it happens:** The contract mixes API rows with path-bearing metadata.
**How to avoid:** Treat path-bearing contract fields as refreshable migration data while keeping surface semantics unchanged.
**Warning signs:** CXX gate passes locally only with overrides, or committed diagnostics still cite old bridge source paths.

### Pitfall 5: TUI smoke proof is assumed to exist already
**What goes wrong:** Planning picks `cargo run -p classic-tui -- --help` or `--version`, but the current binary does not parse CLI args and may still launch the full TUI.
**Why it happens:** `ui-applications/classic-tui/src/main.rs` initializes the terminal UI directly and shows no argument parsing.
**How to avoid:** Verify the actual binary behavior before locking the smoke command; add minimal arg handling only if needed.
**Warning signs:** Smoke proof enters alternate-screen TUI instead of returning lightweight output.

## Code Examples

Verified patterns from official and repo sources:

### Cargo virtual workspace at repo root
```toml
# Source: https://doc.rust-lang.org/cargo/reference/workspaces.html
[workspace]
members = ["foundation/classic-shared-core", "node-bindings/classic-node"]
resolver = "2"
```

### Local path dependencies must point to the exact crate directory
```toml
# Source: https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html#specifying-path-dependencies
[dependencies]
classic-shared-core = { path = "../../foundation/classic-shared-core" }
```

### NAPI build keeps using package-local Cargo.toml
```bash
# Source: https://github.com/napi-rs/website/blob/main/pages/docs/cli/build.en.mdx
napi build --manifest-path ./Cargo.toml
```

### Correct post-move Node script depth
```json
// Source: current repo package.json pattern, depth corrected for root move
{
  "scripts": {
    "parity:gate": "python ../../tools/node_api_parity/check_parity_gate.py --repo-root ../..",
    "dts:freshness:check": "python ../../tools/node_api_parity/check_dts_freshness.py --repo-root ../.. --check-only"
  }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Older Cargo virtual workspace examples commonly used `resolver = "2"` | Current Cargo docs show `resolver = "3"` in a 2024-edition virtual-workspace example | Current docs as of 2026 | Do **not** upgrade in Phase 8; Phase 6 explicitly locked repo resolver to `"2"`, so preserve it. |
| `napi build --cargo-cwd ...` | `napi build --manifest-path ...` | NAPI-RS CLI v2→v3 migration docs | Repo already uses the current pattern; keep it and only fix relative script depth. |
| Legacy `ClassicLib-rs/...` path normalization | Repo-root-only path policy with explicit rejection | Phase 8 locked decision | Existing transitional normalization is now technical debt, not a feature. |

**Deprecated/outdated:**
- `napi build --cargo-cwd`: replaced by `--manifest-path` in current NAPI-RS CLI docs.
- Silent `ClassicLib-rs/...` normalization in active tools: outdated for this milestone because it preserves dual-layout behavior.

## Open Questions

1. **What exact TUI smoke command is genuinely lightweight?**
   - What we know: `classic-tui` currently initializes the TUI directly in `src/main.rs`; no argument parsing was found.
   - What's unclear: whether `--help`/`--version` already behave acceptably through some other layer, or whether minimal flag handling is required.
   - Recommendation: planner should treat this as a first-wave proof decision and verify behavior before locking the task order.

2. **Should the checked-in CXX parity contract be refreshed in Phase 8 or Phase 9?**
   - What we know: it contains `sourceFile` values under `ClassicLib-rs/...`; D-11 says stale path-bearing parity/freshness artifacts should refresh in Phase 8.
   - What's unclear: whether maintainers consider those fields part of the immutable contract or refreshable metadata.
   - Recommendation: plan a targeted refresh in Phase 8, but call out explicitly that semantic API rows must remain unchanged.

3. **What is the canonical Node rebuild implementation that `rebuild_node.ps1` should delegate to?**
   - What we know: the standalone script currently points at `rust/node-bindings/classic-node`, which is already wrong; package-local `bun run build` works as the natural canonical flow.
   - What's unclear: whether delegation should call `rebuild_rust.ps1 -Target node` or invoke the package-local command directly.
   - Recommendation: choose one implementation in planning and make the other a thin wrapper only.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Cargo | workspace/TUI/native bridge builds | ✓ | `cargo 1.94.0` | — |
| Rust compiler | workspace/native bridge builds | ✓ | `rustc 1.94.0` | — |
| Python | parity tools, stub validation | ✓ | `Python 3.14.3` | — |
| uv | Python bindings venv flow | ✓ | `0.11.6` | Manual pip/venv only if absolutely necessary |
| pytest | planning + Python test execution | ✓ | `9.0.3` | `python -m pytest` already available |
| Node | Node runtime smoke/tests | ✓ | `v25.9.0` | — |
| Bun | Node build/parity/test scripts | ✓ | `1.3.10` | None for package-local scripts |
| Git | d.ts freshness gate (`git diff`) | ✓ | `2.53.0.windows.2` | None |
| CMake | CLI/GUI configure/build | ✓ | `4.3.1` | — |
| Visual Studio discovery | CLI/GUI wrapper bootstrap | ✓ | `vswhere` found VS at `C:\Program Files\Microsoft Visual Studio\18\Community` | — |
| `cl.exe` in current shell | direct native build from current shell | ✗ | — | Use `build_cli.ps1`/`build_gui.ps1`, which bootstrap VS dev shell |
| `ninja` in current shell | direct native build from current shell | ✗ | — | Use wrapper bootstrap; ensure VS install includes Ninja |
| `VCPKG_ROOT` | CLI/GUI default presets | ✓ | `C:\vcpkg` | — |
| Qt 6 config | GUI configure/build | ✗ | — | Use `system-fallback` preset with a valid system Qt via `Qt6_DIR`/`CMAKE_PREFIX_PATH`; otherwise GUI proof is locally blocked |

**Missing dependencies with no fallback:**
- None for Phase 8 overall, but local GUI proof is blocked unless Qt 6 is available.

**Missing dependencies with fallback:**
- `cl.exe` and `ninja` are missing in the current shell but are expected to be provided by the PowerShell native-build wrappers.
- `Qt6_DIR` is missing; `classic-gui` supports a `system-fallback` preset if a non-vcpkg Qt install is available.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Python `unittest` suites executed via `pytest 9.0.3` |
| Config file | none — repo uses direct `python -m pytest` invocation |
| Quick run command | `python -m pytest tests/planning/test_phase08_validation.py -q` |
| Full suite command | `python -m pytest tests/planning/test_phase08_validation.py -q && python tools/cxx_api_parity/check_parity_gate.py --repo-root . && python tools/python_api_parity/check_parity_gate.py --repo-root . && pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test && pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTG-01 | Preserved wrappers/native flows succeed from repo root and reject legacy paths | planning + smoke | `python -m pytest tests/planning/test_phase08_validation.py -q` plus wrapper/native commands under targeted test helpers | ❌ Wave 0 |
| INTG-02 | Python/Node/CXX parity gates use root-level defaults, binding-local artifacts, and reject `ClassicLib-rs/...` | planning + integration | `python -m pytest tests/planning/test_phase08_validation.py -q` plus `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` and `python tools/python_api_parity/check_parity_gate.py --repo-root .` and package-local Node parity commands | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/planning/test_phase08_validation.py -q`
- **Per wave merge:** targeted parity command(s) plus the relevant wrapper/native smoke command(s)
- **Phase gate:** preserved wrapper/native/parity entrypoints all green from repo-root paths, with legacy-path rejection covered

### Wave 0 Gaps
- [ ] `tests/planning/test_phase08_validation.py` — covers INTG-01 and INTG-02
- [ ] Assertions for `rebuild_rust.ps1`, `rebuild_node.ps1`, `classic-cli/CMakeLists.txt`, `classic-gui/CMakeLists.txt`, Node `package.json`, and parity-tool defaults
- [ ] Regression checks that legacy `ClassicLib-rs/...` inputs fail with migration guidance
- [ ] Decision-backed TUI smoke assertion once the exact lightweight command is verified

## Sources

### Primary (HIGH confidence)
- Context7 `/websites/doc_rust-lang_cargo` — workspace-root semantics, virtual workspaces, workspace dependency inheritance, and exact-path rules for local `path` dependencies
- Context7 `/napi-rs/website` — current `napi build --manifest-path` CLI semantics
- Official Cargo docs: https://doc.rust-lang.org/cargo/reference/workspaces.html
- Official Cargo docs: https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html#specifying-path-dependencies
- NAPI-RS CLI docs: https://github.com/napi-rs/website/blob/main/pages/docs/cli/build.en.mdx
- Corrosion releases: https://github.com/corrosion-rs/corrosion/blob/master/RELEASES.md

### Secondary (MEDIUM confidence)
- Live repo evidence from `rebuild_rust.ps1`, `rebuild_node.ps1`, `classic-cli/CMakeLists.txt`, `classic-gui/CMakeLists.txt`, `node-bindings/classic-node/package.json`, `validate_stubs.py`, `.github/workflows/ci-*.yml`, and `tools/*_api_parity/*`
- `AGENTS.md`, `docs/api/README.md`, and `classic-project-guide` reference docs for repo-specific command policy and parity workflow expectations

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - mostly preservation of the live repo stack, cross-checked against official Cargo and NAPI-RS docs.
- Architecture: HIGH - locked decisions are specific, and current repo files expose the exact consumers that must be rewired.
- Pitfalls: HIGH - breakpoints are directly visible in the inspected scripts, CMake files, parity tools, workflows, and stale artifact paths.

**Research date:** 2026-04-12
**Valid until:** 2026-05-12

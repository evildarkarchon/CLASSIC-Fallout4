# Phase 9: Clean Validation and CI Refresh - Research

**Researched:** 2026-04-12
**Domain:** Brownfield clean-state validation, GitHub Actions path refresh, and package-proof hardening after repo-root workspace migration
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

### Clean-State Proof
- **D-01:** Phase 9 uses a targeted clean-state reset, not a minimal rerun and not a full repository or machine scrub.
- **D-02:** The targeted reset must quarantine or remove the highest-risk generated outputs before proof: legacy `ClassicLib-rs/target`, repo-root `target`, binding `.venv`, Node build outputs, and binding/parity working artifacts touched by the validated flows.
- **D-03:** Phase 9 proof must include at least one deliberate fresh-state execution path, not only incremental reruns on top of existing outputs.

### CI Closure Surface
- **D-04:** Phase 9 closure must refresh and validate all active PR CI workflows: `.github/workflows/ci-rust.yml`, `.github/workflows/ci-python-bindings.yml`, `.github/workflows/ci-typescript.yml`, and `.github/workflows/ci-cpp.yml`.
- **D-05:** `.github/workflows/benchmarks.yml` is also part of the required Phase 9 closure surface.
- **D-06:** Phase 9 must include one required native package-sensitive proof surface in addition to the CI workflows.
- **D-07:** The required native package-sensitive proof is the GUI package flow via `classic-gui/build_gui.ps1`.

### Artifact Refresh
- **D-08:** Phase 9 regenerates only CI-owned, path-bearing artifacts that are directly used by the required CI and package proof surfaces.
- **D-09:** Phase 9 should avoid unrelated artifact churn; path-bearing outputs outside the required proof surface stay out unless the proof shows they are stale.

### Legacy Residue Policy
- **D-10:** Any new generated output under `ClassicLib-rs/` is a Phase 9 failure.
- **D-11:** This failure rule covers recreated `target`, `.venv`, parity-artifact directories, build outputs, packaging outputs, and similar generated residue under the legacy tree.
- **D-12:** Historical docs or planning references to `ClassicLib-rs` are explicitly deferred to Phase 10 unless they break an active Phase 9 proof surface.

### the agent's Discretion
- Exact targeted-clean implementation mechanics, as long as the required high-risk outputs are quarantined or removed before proof.
- Exact mapping from required proof surfaces to the CI-owned artifacts that must be regenerated.
- Exact orchestration between planning audits, workflow updates, and live package-proof execution.

### Deferred Ideas (OUT OF SCOPE)

None - discussion stayed within Phase 9 scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INTG-03 | Contributor can run CI and path-sensitive build or packaging jobs against the relocated workspace using the new repository-root layout | Refresh all five live workflows together, align `working-directory`/cache paths/hash inputs/upload paths, and prove one native package-sensitive path through `classic-gui/build_gui.ps1 -Package`. |
| INTG-04 | Contributor can verify the relocation from a clean state with regenerated path-bearing artifacts instead of relying on stale caches or outputs | Add a targeted clean harness that quarantines legacy and live generated outputs, reruns required proof surfaces from fresh state, regenerates only CI-owned path-bearing artifacts, and fails if anything new appears under `ClassicLib-rs/`. |
</phase_requirements>

## Project Constraints (from AGENTS.md)

- Prioritize active work in `classic-cli/`, `classic-gui/`, and `ClassicLib-rs/`.
- Keep all business logic in Rust; keep non-interface layers thin.
- Maintain a single shared Tokio runtime from Rust core runtime facilities.
- Keep docs synchronized with architecture or workflow changes, especially `README.md` and `AGENTS.md`.
- Never write to `NUL` or `nul` on Windows.
- Consult `docs/api/README.md` before changing public Rust, bridge, GUI-consumer, or binding-facing APIs; update affected `docs/api/` pages if contracts change.
- Never run C++ tests directly via raw `ctest` or test binaries; use `classic-cli/build_cli.ps1 -Test` or `classic-gui/build_gui.ps1 -Test`.
- Native C++ targets are Windows/MSVC based.
- When using Git Bash for MSVC-targeted Rust/C++, source `tools/use_msvc_from_git_bash.sh` first.
- Python and Node bindings must stay in sync with Rust core logic.

## Summary

Phase 9 should be treated as a proof-hardening phase, not a tooling redesign phase. The established pattern is to keep the current CI/workflow stack, but refresh every path-sensitive surface together: command paths, `working-directory`, cache `path`, cache key inputs, artifact upload locations, and the small set of path-bearing generated artifacts those jobs consume. Official Cargo docs confirm that the workspace lockfile and default `target/` live at the workspace root, and GitHub Actions docs confirm caches and artifacts are keyed entirely by the paths and keys you declare. That means stale `ClassicLib-rs/...` cache keys or upload paths can create false greens even after commands themselves were rewired.

The live repo shows exactly that risk today. `ci-rust.yml` already uses repo-root Cargo commands, but still hashes `ClassicLib-rs/**/*.rs`; `ci-python-bindings.yml`, `ci-typescript.yml`, and `ci-cpp.yml` still cache or upload from legacy `ClassicLib-rs/...` paths; and the benchmark workflow still keys its Rust cache from `ClassicLib-rs/**/*.rs`. The clean-state side has the same issue: `tests/planning/phase06_clean_run.ps1` quarantines only `ClassicLib-rs/target`, while Phase 9 explicitly requires a stronger targeted reset that also handles repo-root `target`, binding `.venv`, Node outputs, and touched parity/package artifacts.

The right closeout is therefore: add one deterministic targeted-clean harness, refresh all five workflows as a single path-contract set, prove at least one deliberate fresh-state execution path, and run one native package-sensitive flow through `classic-gui/build_gui.ps1 -Package`. Any newly generated output under `ClassicLib-rs/` should be treated as a hard regression.

**Primary recommendation:** Build Phase 9 around one targeted-clean proof harness plus one workflow/package audit suite, and require every CI cache path, hash input, upload path, and regenerated artifact to be repo-root-correct before claiming closure.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Cargo workspace at repo root | local `cargo 1.94.0`; repo-root virtual workspace | Canonical build/test/cache root | Official Cargo workspaces share one root `Cargo.lock` and default `target/` at the workspace root; clean proof should use that contract directly. |
| GitHub Actions workflow stack | repo pins `actions/checkout@v6`, `actions/cache@v5`, `actions/upload-artifact@v6`, `actions/setup-python@v6`, `dtolnay/rust-toolchain@stable` | CI execution, cache restore/save, diagnostics upload | This is the live CI surface already used by the repo; Phase 9 should correct path contracts, not replace Actions primitives. |
| Existing parity/stub gates | repo-owned `tools/python_api_parity/check_parity_gate.py`, `tools/node_api_parity/check_parity_gate.py`, `tools/cxx_api_parity/check_parity_gate.py`, `validate_stubs.py` | Regenerate and verify CI-owned path-bearing artifacts | These scripts already own the parity contract and artifact shape; use them to regenerate only the required artifacts. |
| Native package flow wrapper | repo-owned `classic-gui/build_gui.ps1` | Required package-sensitive proof surface | AGENTS.md requires wrapper-based C++/GUI execution; this script already owns configure/build/install/package orchestration. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PowerShell | local `7.6.0` | Clean harness, wrapper orchestration, Windows-native proof | Use for targeted clean/reset and native wrapper execution. |
| uv | local `0.11.6` | Create `python-bindings/.venv` when clean proof removes it | Use only for the Python workflow surface touched by proof. |
| Bun | local `1.3.10` | Rebuild Node package-local outputs after targeted clean | Use from `node-bindings/classic-node` only when that workflow is part of the required proof set. |
| CMake/CTest | local `4.3.1` | GUI install/package orchestration | Use only through `classic-gui/build_gui.ps1`; not directly as the public proof command. |
| VS/vcpkg bootstrap | `vswhere` found; `VCPKG_ROOT=C:\vcpkg` | Native Windows dependency resolution | Required by CLI/GUI flows; keep wrapper bootstrap intact. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| One targeted clean harness | Ad hoc per-workflow manual cleanup | Easier short-term, but guarantees drift between proof surfaces. |
| Existing Actions cache/upload primitives | Custom scripting for cache/artifact transport | Reinvents official semantics and makes CI harder to audit. |
| Existing parity/stub generators | Manual artifact edits | High risk of semantic drift and self-validating output churn. |
| `classic-gui/build_gui.ps1 -Package` | Raw `cmake --install` / `cpack` commands | Violates repo policy and bypasses the real contributor-facing package flow. |

**Installation:**
```bash
# No new libraries should be introduced in Phase 9.
# Use the repo's existing workflow/tool stack and refresh only path-sensitive contracts.
```

**Version verification:** This phase should preserve the repo-pinned workflow/action/tool stack. The current local environment provides `cargo 1.94.0`, `rustc 1.94.0`, `uv 0.11.6`, `bun 1.3.10`, `pytest 9.0.3`, `cmake 4.3.1`, and `git 2.53.0.windows.2`; CI pins Python 3.12 and Node 22 even though the current local shell has Python 3.14.3 and Node 25.9.0.

## Architecture Patterns

### Recommended Project Structure
```text
repo root
├── .github/workflows/                 # all five Phase 9-owned CI surfaces
├── tests/planning/                    # targeted clean harness + phase audit
├── python-bindings/parity-artifacts/  # regenerated only if touched by required CI proof
├── node-bindings/classic-node/        # package-local build outputs + parity artifacts
├── cpp-bindings/classic-cpp-bridge/parity-artifacts/
├── target/                            # canonical live Cargo output; must be clean-proofed
└── classic-gui/build_gui.ps1          # required package-sensitive proof surface
```

### Pattern 1: Targeted clean-state reset before proof
**What:** Quarantine only the high-risk generated outputs named in context, then rerun the required proof surfaces from fresh state.
**When to use:** At least once in Phase 9 closure; not on every incremental rerun.
**Example:**
```powershell
# Source: tests/planning/phase06_clean_run.ps1 + Phase 9 CONTEXT D-01..D-03
$legacyTarget = Join-Path $RepoRoot "ClassicLib-rs/target"
$rootTarget = Join-Path $RepoRoot "target"
if (Test-Path $legacyTarget) { Rename-Item $legacyTarget "$legacyTarget.phase9-backup" }
if (Test-Path $rootTarget) { Remove-Item -Recurse -Force $rootTarget }
```

### Pattern 2: Refresh command path, cache path, cache key, and upload path together
**What:** Treat workflow path contracts as a single unit. If one path-bearing field changes, all related fields change in the same edit.
**When to use:** Every workflow in `.github/workflows/*.yml` touched by Phase 9.
**Example:**
```yaml
# Source: GitHub Actions dependency caching docs + live repo workflows
- uses: actions/cache@v5
  with:
    path: target
    key: ${{ runner.os }}-cargo-build-${{ hashFiles('**/Cargo.lock') }}-${{ hashFiles('business-logic/**/*.rs', 'foundation/**/*.rs', 'cpp-bindings/**/*.rs', 'node-bindings/**/*.rs', 'python-bindings/**/*.rs', 'ui-applications/**/*.rs') }}
```

### Pattern 3: Regenerate only CI-owned, path-bearing artifacts
**What:** Refresh only the generated artifacts directly consumed by the required CI/package proof surfaces.
**When to use:** After workflow/tool defaults are fixed and only for touched proof surfaces.
**Example:**
```python
# Source: tools/python_api_parity/check_parity_gate.py
parser.add_argument("--output-dir", default="python-bindings/parity-artifacts")
parser.add_argument("--baseline-output-dir", default="docs/implementation/python_api_parity/baseline")
```

### Pattern 4: Package-sensitive proof must use the public wrapper
**What:** Run GUI package proof through `classic-gui/build_gui.ps1 -Package`, which already implies install and deployment steps.
**When to use:** Required native package-sensitive closure proof.
**Example:**
```powershell
# Source: classic-gui/build_gui.ps1
if ($Package) { $Install = $true }
& cpack --config $cpackConfig -B $packageDir
```

### Anti-Patterns to Avoid
- **Workflow-only success without clean proof:** a green PR run after cache reuse does not satisfy INTG-04.
- **Updating command paths but leaving `hashFiles('ClassicLib-rs/**/*.rs')`:** stale cache keys can keep old artifacts alive.
- **Refreshing all baselines “just in case”:** Phase 9 explicitly forbids unrelated artifact churn.
- **Using raw `ctest`, `cmake --install`, or `cpack` as the public proof command:** repo policy requires wrapper-based native proof.
- **Leaving clean-state logic to human memory:** Phase 9 needs committed, executable proof.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cache invalidation semantics | Custom partial cache-busting scripts | `actions/cache@v5` with correct `path`, exact `key`, and ordered `restore-keys` | Official cache behavior is deterministic; custom logic hides why a cache hit happened. |
| CI diagnostics transport | Ad hoc zip/copy scripts | `actions/upload-artifact@v6` | Official artifact uploads already support named paths and retention policy. |
| Cargo output cleanup | Manual target-folder heuristics only | `cargo clean` for workspace artifacts plus explicit PowerShell quarantine for non-Cargo outputs | Cargo knows its own workspace output structure; custom deletion should only cover non-Cargo directories. |
| Parity/stub artifact refresh | Manual JSON/MD edits | Existing parity/stub generators and gates | The checked-in artifacts encode semantic invariants that manual editing can easily corrupt. |
| GUI packaging proof | Direct `cmake`/`cpack` command sequences in tests | `classic-gui/build_gui.ps1 -Package` | The wrapper already owns VS bootstrap, install, signing hook, and package output conventions. |

**Key insight:** The danger in this phase is not missing a command; it is missing one path-bearing side effect of that command. Reuse the repo’s existing workflow, wrapper, and parity infrastructure so each proof surface stays authoritative.

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `ClassicLib-rs/target/**` exists as legacy generated build output; root-level checked-in parity baselines under `docs/implementation/**/baseline` and generated working reports under `python-bindings/parity-artifacts/` are path-bearing data relevant to CI proof. | **Data migration + cleanup:** quarantine/remove `ClassicLib-rs/target` before proof; regenerate only CI-owned path-bearing artifacts that the required workflows/package proof actually consume. |
| Live service config | None found for this phase’s owned surfaces. CI config is file-backed under `.github/workflows/`; no UI-only external service config was evidenced in the required proof surfaces. | None — verified by inspected workflow/package surfaces. |
| OS-registered state | None found. The native wrappers discover VS tooling at runtime via `vswhere` and do not rely on Task Scheduler/systemd/launchd/pm2 registrations. | None. |
| Secrets/env vars | `VCPKG_ROOT` is required for native builds; `QT_QPA_PLATFORM` is set in GUI CI; `GITHUB_TOKEN`, `CLASSIC_SCAN_DIAGNOSTICS`, and `CLASSIC_DB_COUNTER_INTERVAL` exist but are unrelated to the path migration itself. No env-var name containing `ClassicLib-rs` was found. | No migration of secret names. Keep env vars unchanged; only refresh path-bearing workflow/script usage. |
| Build artifacts | Legacy `ClassicLib-rs/target/**` exists; root `target/` is the canonical live Cargo output; root `python-bindings/.venv/` and `node-bindings/classic-node/node_modules/` are currently absent; `node-bindings/classic-node/classic-node.win32-x64-msvc.node` exists; `python-bindings/parity-artifacts/**` exists. | **Code edit + clean proof:** delete/quarantine stale outputs before proof, recreate only the touched ones from required workflows, and fail if any new generated output appears under `ClassicLib-rs/`. |

## Common Pitfalls

### Pitfall 1: Cache keys still hash `ClassicLib-rs/**/*.rs`
**What goes wrong:** CI restores an apparently valid cache even though the live Rust tree moved to repo root.
**Why it happens:** `actions/cache` keys are only as correct as the declared `hashFiles(...)` inputs.
**How to avoid:** Refresh hash inputs and cache `path` in the same edit as command/path rewires.
**Warning signs:** Workflow commands are repo-root-correct, but cache keys still reference `ClassicLib-rs/**/*.rs`.

### Pitfall 2: Artifact upload paths lag behind command rewires
**What goes wrong:** jobs run correctly, but failure diagnostics upload from dead legacy directories or miss files entirely.
**Why it happens:** upload paths are easy to overlook because they run only on failure.
**How to avoid:** audit every `actions/upload-artifact` step as part of the same path-contract pass.
**Warning signs:** `if-no-files-found: warn` on a path that still starts with `ClassicLib-rs/`.

### Pitfall 3: “Clean proof” only removes Cargo output
**What goes wrong:** the proof still benefits from a stale Python `.venv`, stale Node addon, or old parity working artifacts.
**Why it happens:** Phase 6 only quarantined legacy `ClassicLib-rs/target`; Phase 9 scope is intentionally stronger.
**How to avoid:** explicitly classify the proof surface and remove the non-Cargo outputs that surface uses.
**Warning signs:** clean proof does not touch `.venv`, `.node`, `dist`, or parity-artifact directories for the validated flow.

### Pitfall 4: GUI proof stops at `-Test`
**What goes wrong:** build/test looks green, but install/package path handling and `windeployqt`/CPack behavior are never exercised.
**Why it happens:** `-Test` was the Phase 8 closure depth; Phase 9 adds package-sensitive proof.
**How to avoid:** require `classic-gui/build_gui.ps1 -Package` in the Phase 9 proof story.
**Warning signs:** plan mentions GUI build or GUI test proof but never `-Package`.

### Pitfall 5: Legacy residue is checked only before proof, not after proof
**What goes wrong:** the run recreates output under `ClassicLib-rs/`, but no one notices because the directory already existed before cleanup.
**Why it happens:** teams often validate absence only once.
**How to avoid:** compare pre-proof and post-proof legacy-tree state and fail on newly created generated residue.
**Warning signs:** new files appear under `ClassicLib-rs/target`, `ClassicLib-rs/.venv`, or `ClassicLib-rs/.../parity-artifacts` after the proof run.

### Pitfall 6: Local environment differs materially from CI
**What goes wrong:** local proof passes on Python 3.14 / Node 25, but CI runs on Python 3.12 / Node 22.
**Why it happens:** local shell versions are newer than workflow pins.
**How to avoid:** treat local proof as smoke only and keep CI-pinned version expectations explicit in the validation plan.
**Warning signs:** local-only fixes rely on behavior not exercised in the workflow versions.

## Code Examples

Verified patterns from official and repo sources:

### Clean Cargo workspace outputs from the workspace root
```bash
# Source: https://doc.rust-lang.org/cargo/commands/cargo-clean.html
cargo clean
```

### Cache exact repo-root outputs and key off repo-root source trees
```yaml
# Source: https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching
- uses: actions/cache@v5
  with:
    path: target
    key: ${{ runner.os }}-cargo-build-${{ hashFiles('**/Cargo.lock') }}-${{ hashFiles('foundation/**/*.rs', 'business-logic/**/*.rs', 'cpp-bindings/**/*.rs', 'node-bindings/**/*.rs', 'python-bindings/**/*.rs', 'ui-applications/**/*.rs') }}
    restore-keys: |
      ${{ runner.os }}-cargo-build-${{ hashFiles('**/Cargo.lock') }}-
      ${{ runner.os }}-cargo-build-
```

### Upload diagnostics from the exact generated directory
```yaml
# Source: https://docs.github.com/en/actions/how-tos/writing-workflows/choosing-what-your-workflow-does/storing-and-sharing-data-from-a-workflow
- uses: actions/upload-artifact@v6
  if: failure()
  with:
    name: python-parity-diagnostics
    path: python-bindings/parity-artifacts/
    retention-days: 7
```

### GUI package flow is wrapper-owned and implies install
```powershell
# Source: classic-gui/build_gui.ps1
if ($Package) { $Install = $true }
& cmake --install $buildDirName --prefix $installDir
& cpack --config $cpackConfig -B $packageDir
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Incremental reruns over existing outputs | Deliberate fresh-state proof with targeted quarantine/removal of high-risk generated outputs | Current Phase 9 decision | Catches path bugs and stale artifact shadowing that incremental reruns miss. |
| Rewire commands only | Rewire command path, cache path, key inputs, `working-directory`, and upload path as one contract | Current GitHub Actions best practice | Prevents false cache hits and missing diagnostics. |
| Treat uploaded artifacts as mutable scratch space | Treat artifacts as immutable run outputs and upload the exact directory for each failing surface | GitHub artifact behavior in current docs | Encourages precise artifact ownership and avoids stale mixed-content debugging bundles. |
| Legacy-tree tolerance after migration | Fail Phase 9 on any newly generated output under `ClassicLib-rs/` | Current milestone policy | Makes hidden dual-layout regressions visible immediately. |

**Deprecated/outdated:**
- Cache keys based on `ClassicLib-rs/**/*.rs` after the repo-root move.
- Upload paths under `ClassicLib-rs/.../parity-artifacts/` for active CI jobs.
- Using GUI `-Test` alone as closure proof once package-sensitive validation is required.

## Open Questions

1. **Should Phase 9 introduce a new `phase09_clean_run.ps1` or extend `phase06_clean_run.ps1`?**
   - What we know: the Phase 6 harness already quarantines legacy `ClassicLib-rs/target`, but Phase 9 scope is broader.
   - What's unclear: whether maintainers want one evolving clean-run harness or a phase-local proof artifact.
   - Recommendation: prefer a new Phase 9 harness so the stronger clean-state contract stays explicit and auditable.

2. **Which exact path-bearing checked-in artifacts are CI-owned for this phase?**
   - What we know: Python/Node/CXX parity tools and workflow diagnostics own path-bearing outputs; Phase 9 must avoid unrelated churn.
   - What's unclear: whether benchmark outputs or any additional package metadata should be checked in or remain ephemeral.
   - Recommendation: map each required workflow/package surface to its artifact list before implementation and exclude everything else.

3. **How much local GUI package proof is realistic on this machine?**
   - What we know: `VCPKG_ROOT` is set and VS discovery exists, but `cl.exe`, `ninja`, `qtpaths6`, and `windeployqt` are not visible in the current shell.
   - What's unclear: whether wrapper bootstrap plus vcpkg is sufficient for full local `-Package` proof, or whether CI should be treated as the authoritative package run.
   - Recommendation: planner should keep wrapper-based local smoke available but treat CI package proof as the non-negotiable gate if local Qt packaging is blocked.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Cargo | Rust CI + clean proof | ✓ | `1.94.0` | — |
| Rust compiler | Rust CI + bridge/native builds | ✓ | `1.94.0` | — |
| Python | parity/stub tooling | ✓ | `3.14.3` local | CI pins 3.12 |
| pytest | planning + parity tool tests | ✓ | `9.0.3` | — |
| uv | recreate `python-bindings/.venv` after targeted clean | ✓ | `0.11.6` | Manual venv/pip only if absolutely necessary |
| Bun | Node workflow/package-local proof | ✓ | `1.3.10` | None |
| Node | Node runtime smoke | ✓ | `25.9.0` local | CI pins 22 |
| Git | freshness checks / diff-based tooling | ✓ | `2.53.0.windows.2` | — |
| PowerShell | clean harness + wrappers | ✓ | `7.6.0` | — |
| CMake | GUI package flow | ✓ | `4.3.1` | — |
| CTest | GUI/CLI wrapper test execution | ✓ | `4.3.1` | Use wrapper-owned invocation only |
| `cl.exe` in current shell | direct native execution without wrapper bootstrap | ✗ | — | Use `build_cli.ps1` / `build_gui.ps1` which bootstrap VS dev shell |
| `ninja` in current shell | direct native execution without wrapper bootstrap | ✗ | — | Use wrapper bootstrap |
| `VCPKG_ROOT` | native dependency resolution | ✓ | `C:\vcpkg` | — |
| `python-bindings/.venv` | Python clean-state rerun after quarantine | ✗ | — | Recreate with `uv venv python-bindings/.venv` |
| `node-bindings/classic-node/node_modules` | Node package-local proof after quarantine | ✗ | — | Recreate with `bun install` |
| Qt helper binaries on PATH (`qtpaths6`, `windeployqt`) | direct local Qt/package diagnostics | ✗ | — | Rely on wrapper + vcpkg Qt resolution or CI proof |

**Missing dependencies with no fallback:**
- None for repo-wide planning, but direct shell-native GUI package diagnostics are locally uncertain without visible Qt helper binaries.

**Missing dependencies with fallback:**
- `cl.exe` and `ninja` are absent in the current shell but wrapper bootstrap is the intended execution path.
- `python-bindings/.venv` and `node_modules` are absent, but Phase 9 clean proof is expected to recreate them when those surfaces are exercised.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Python `unittest` executed via `pytest 9.0.3`, plus existing PowerShell contract suites and parity-tool pytest suites |
| Config file | none — repo uses direct `python -m pytest` and PowerShell wrapper invocations |
| Quick run command | `python -m pytest tests/planning/test_phase09_validation.py -q` |
| Full suite command | `python -m pytest tests/planning/test_phase09_validation.py -q && pwsh -ExecutionPolicy Bypass -File tests/powershell/rebuild_rust.general_target.test.ps1 && pwsh -ExecutionPolicy Bypass -File tests/powershell/rebuild_node.wrapper_contract.test.ps1 && pwsh -ExecutionPolicy Bypass -File tests/powershell/cpp_build_scripts.test.ps1 && python -m pytest tools/python_api_parity/tests/test_check_parity_gate.py tools/python_api_parity/tests/test_generate_baseline_targets.py tools/node_api_parity/tests/test_check_parity_gate.py tools/node_api_parity/tests/test_generate_baseline_targets.py tools/cxx_api_parity/tests/test_parser.py tools/cxx_api_parity/tests/test_gate.py -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTG-03 | All five workflows use repo-root command/cache/upload/package paths, and GUI package flow is represented as a required proof surface | planning audit | `python -m pytest tests/planning/test_phase09_validation.py -q -k workflow_and_package_surface` | ❌ Wave 0 |
| INTG-04 | Targeted clean proof removes/quarantines required outputs, regenerates touched artifacts, and detects new legacy residue | planning audit + smoke harness | `python -m pytest tests/planning/test_phase09_validation.py -q -k clean_state_and_residue` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/planning/test_phase09_validation.py -q`
- **Per wave merge:** quick phase audit plus the relevant live proof command(s) for the touched workflow/package surface
- **Phase gate:** targeted clean proof, refreshed workflow audit, and required package-sensitive proof all green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/planning/test_phase09_validation.py` — phase-local audit for workflow paths, cache keys, artifact uploads, clean-state contract, and GUI package proof surface
- [ ] `tests/planning/phase09_clean_run.ps1` (or equivalent) — executable targeted-clean harness stronger than Phase 6
- [ ] Assertions that no active workflow still references `ClassicLib-rs/target`, `ClassicLib-rs/**/*.rs`, or `ClassicLib-rs/.../parity-artifacts`
- [ ] Assertions that required regenerated artifacts stay scoped to touched proof surfaces only
- [ ] Post-proof residue check that fails on newly generated output under `ClassicLib-rs/`

## Sources

### Primary (HIGH confidence)
- Official Cargo docs: https://doc.rust-lang.org/cargo/reference/workspaces.html — workspace root, shared `Cargo.lock`, shared default `target/`
- Official Cargo docs: https://doc.rust-lang.org/cargo/commands/cargo-clean.html — clean semantics and workspace-root `target`
- Official GitHub Actions docs: https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching — cache `path`, `key`, `restore-keys`, and cache-hit behavior
- Official GitHub Actions docs: https://docs.github.com/en/actions/how-tos/writing-workflows/choosing-what-your-workflow-does/storing-and-sharing-data-from-a-workflow — upload-artifact behavior and retention

### Secondary (MEDIUM confidence)
- Live repo workflows: `.github/workflows/ci-rust.yml`, `ci-python-bindings.yml`, `ci-typescript.yml`, `ci-cpp.yml`, `benchmarks.yml`
- Live repo proof surfaces: `classic-gui/build_gui.ps1`, `tests/planning/phase06_clean_run.ps1`, `tests/planning/test_phase08_validation.py`, `tools/*_api_parity/check_parity_gate.py`, `validate_stubs.py`
- Planning references: `.planning/research/SUMMARY.md`, `.planning/research/PITFALLS.md`, `.planning/research/ARCHITECTURE.md`, `.planning/research/STACK.md`, `.planning/phases/08-wrapper-and-parity-rewire/08-VALIDATION.md`

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - mostly preservation of the live repo/toolchain stack, cross-checked with official Cargo and GitHub Actions docs.
- Architecture: HIGH - locked decisions are specific and the repo’s current workflows/scripts expose the exact proof surfaces that need refresh.
- Pitfalls: HIGH - current workflow files directly show stale cache keys, upload paths, and working directories that would create false greens.

**Research date:** 2026-04-12
**Valid until:** 2026-05-12

# Pitfalls Research

**Domain:** Brownfield Rust workspace-root relocation in a multi-language repo
**Researched:** 2026-04-11
**Confidence:** HIGH — grounded in current repo paths/scripts plus Cargo workspace documentation.

---

## Critical Pitfalls

### Pitfall 1: Dual-Workspace / Partial-Move State

**What goes wrong:**
The repo ends up with a new root `Cargo.toml` and a still-live `ClassicLib-rs/Cargo.toml`, or only some crates move while others still point at the legacy subtree. Cargo then resolves different workspace roots depending on where commands are run, and different tools silently operate against different graphs.

**Why it happens:**
Cargo searches parent directories for a `[workspace]` root, and member crates can also be forced to a workspace via manifest configuration. In a brownfield move, teams often add the new root before fully deleting or tombstoning the old one.

**How to avoid:**
- Make the move atomic at the workspace level: one canonical `[workspace]`, never two live ones.
- Treat `ClassicLib-rs/Cargo.toml` as a temporary migration shim only if it is deliberately non-authoritative and documented as such; otherwise delete it in the same phase that activates the root workspace.
- Run `cargo metadata --format-version 1` from repo root and from representative subcrate directories; verify the same `workspace_root` every time.
- Add a roadmap gate: no later phase starts until the legacy workspace root is removed or explicitly neutered.

**Warning signs:**
- `cargo metadata` reports different `workspace_root` values depending on current directory.
- `cargo test` works from one folder but not another.
- Both `Cargo.toml` files still contain `[workspace]` sections.

**Phase to address:**
Phase 1 — workspace migration contract + Phase 2 — Cargo root cutover.

---

### Pitfall 2: Path-Dependency Fan-Out Rewrite Is Incomplete

**What goes wrong:**
Some crates still depend on `../../foundation/...` or `../../business-logic/...` paths that were correct under `ClassicLib-rs/` but are wrong after the move. A few crates build; others fail later, usually in bindings or C++ bridge crates with the highest path fan-out.

**Why it happens:**
This repo has a large number of explicit local `path = "..."` dependencies across core crates, Python crates, the Node crate, the TUI crate, and the C++ bridge. The move is not just a workspace-member edit; it is a workspace-wide relative-path rewrite.

**How to avoid:**
- Inventory all `path =` entries before moving anything.
- Rewrite manifests mechanically, not by hand crate-by-crate.
- After the rewrite, run `cargo metadata`, `cargo check --workspace`, and targeted `cargo check -p classic-cpp-bridge -p classic-node` from the new root.
- Add a validation script/grep in the roadmap that fails if any `Cargo.toml` still contains a path segment anchored to the old depth.

**Warning signs:**
- A subset of crates build, but `classic-cpp-bridge`, `classic-node`, or `classic-*-py` fails with missing local dependency errors.
- Grep still finds old relative paths in moved manifests.

**Phase to address:**
Phase 2 — manifest/path rewrite.

---

### Pitfall 3: Frontend and Wrapper Scripts Still Target `ClassicLib-rs`

**What goes wrong:**
Rust itself may build from repo root, but the real product entrypoints break: CLI/GUI CMake still points to `../ClassicLib-rs/Cargo.toml`, PowerShell rebuild scripts still look for `ClassicLib-rs/python-bindings/.venv`, and VS-dev-shell helpers still launch in old directories.

**Why it happens:**
The operational surface is bigger than Cargo. Current repo files hardcode the old root in:
- `classic-cli/CMakeLists.txt`
- `classic-gui/CMakeLists.txt`
- `rebuild_rust.ps1`
- `tools/enter_vs_dev_shell.ps1`

**How to avoid:**
- Make wrapper/script rewiring its own roadmap phase, not a cleanup footnote.
- Replace hardcoded `ClassicLib-rs/...` joins with variables derived from repo root + new workspace root.
- Validate through real entrypoints, not just Cargo:
  - `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test`
  - `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test`
  - `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target workspace`
  - `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python ...`

**Warning signs:**
- Cargo passes, but CLI/GUI configure fails with a missing manifest/include path.
- `rebuild_rust.ps1` errors that `.venv` or `Cargo.toml` cannot be found under `ClassicLib-rs`.

**Phase to address:**
Phase 3 — wrapper/front-end integration rewiring.

---

### Pitfall 4: Parity Tools and Generated-Artifact Commands Keep Writing to Old Paths

**What goes wrong:**
Parity gates, baseline generators, d.ts freshness checks, and stub validation keep reading or writing `ClassicLib-rs/...` artifact locations. The move looks successful until parity or freshness jobs run, then they either fail outright or regenerate files into abandoned directories.

**Why it happens:**
The parity tooling is path-encoded, not discovery-based. Current defaults in `tools/python_api_parity/*`, `tools/node_api_parity/*`, and `tools/cxx_api_parity/*` point directly at `ClassicLib-rs/...` source and artifact paths. Node `package.json` scripts also assume the old depth (`../../../tools/... --repo-root ../../..`).

**How to avoid:**
- Treat parity-tool rewiring as first-class migration work.
- Update default paths and script relative paths in the same change as the directory move.
- Re-run all three gates after rewiring:
  - `python tools/cxx_api_parity/check_parity_gate.py --repo-root .`
  - `python tools/python_api_parity/check_parity_gate.py --repo-root .`
  - Node parity from the new `node-bindings/classic-node` location
- Add a sweep that fails if any tool default still contains `ClassicLib-rs/`.

**Warning signs:**
- Gate reports missing source files even though the crate exists at its new location.
- Freshness/parity artifacts appear under a recreated `ClassicLib-rs/` subtree.
- Node scripts fail because `../../../tools/...` is now the wrong relative depth.

**Phase to address:**
Phase 3 — tooling/parity rewiring, before any baseline refresh.

---

### Pitfall 5: Stale Build Caches and Generated Outputs Make the Move Look Green

**What goes wrong:**
CI or local runs appear green because they reuse old `ClassicLib-rs/target`, old parity-artifact directories, old `dist/`, or an old Python `.venv`. Then a clean machine fails because the real new-root paths were never exercised.

**Why it happens:**
This repo caches and documents many path-sensitive artifacts:
- CI caches `ClassicLib-rs/target`
- benchmarks use `ClassicLib-rs/target/criterion`
- Python uses `ClassicLib-rs/python-bindings/.venv`
- parity artifacts live under binding-specific directories

In a root move, stale artifacts can hide missing rewires.

**How to avoid:**
- Add a dedicated clean-state validation phase after path rewrites.
- Delete or invalidate old-path caches before claiming success.
- On CI, update cache keys and cache paths in the same PR as the move.
- On local validation, run at least one clean build/test with old target/artifact directories absent.
- Explicitly check that no new files are created under `ClassicLib-rs/` after the move.

**Warning signs:**
- Incremental builds pass but clean builds fail.
- CI uploads artifacts from `ClassicLib-rs/...` after the supposed cutover.
- A new empty `ClassicLib-rs/` directory reappears during validation.

**Phase to address:**
Phase 4 — artifact/cache invalidation + clean validation.

---

### Pitfall 6: Docs, Planning, and Agent Context Drift Far Behind the Code Move

**What goes wrong:**
The code is moved, but contributor instructions, planning docs, API docs, agent skills, and milestone validation docs still encode `ClassicLib-rs/...`. Humans and automation then keep reintroducing old paths in follow-up work.

**Why it happens:**
This repo has a very large documentation/agent surface. A broad sweep already finds pervasive `ClassicLib-rs` references across `.planning/`, `docs/`, repo guidance, and tests. In this codebase, stale documentation is not cosmetic; it actively drives future edits and validations.

**How to avoid:**
- Give doc/agent cleanup its own roadmap phase with explicit scope.
- Prioritize high-authority sources first: `AGENTS.md`, `CLAUDE.md`, project skill docs, `docs/api/README.md`, quick starts, CI guides, testing guides, and active milestone/project docs.
- Run grep-based audits before closure, not after.
- Update validation/proof docs so future phases do not keep using `--manifest-path ClassicLib-rs/Cargo.toml`.

**Warning signs:**
- New plans or PRs copy `ClassicLib-rs/...` commands after the move.
- Agent instructions and API docs disagree with the live tree.
- Planning validation tests still assert old paths.

**Phase to address:**
Phase 5 — docs/agent/planning reconciliation.

---

### Pitfall 7: Validation Tests Encode the Old Topology and Block Closure Late

**What goes wrong:**
The migration seems complete until planning tests, parity-tool tests, or synthetic repo tests fail because fixtures and assertions still require `ClassicLib-rs/...` paths. This usually happens late, after most mechanical work is already merged locally.

**Why it happens:**
Repo tests in `tests/planning/` and under `tools/*_api_parity/tests/` contain hardcoded path assertions. They are easy to miss because they are not the main product tests, but they are exactly the tests that enforce repo contract drift.

**How to avoid:**
- Inventory test files with `ClassicLib-rs` references before the move.
- Rewrite them in the same phase as tooling/docs updates.
- Run planning/tooling suites explicitly, not just product builds.
- Add one migration-specific test that asserts the old root is absent from active commands and canonical paths.

**Warning signs:**
- Product builds pass, but `tests/planning` or `tools/*_api_parity/tests` fails on string/path assertions.
- Synthetic test repos still generate a `ClassicLib-rs` subtree.

**Phase to address:**
Phase 5 — validation-contract updates.

---

### Pitfall 8: Hidden Relative Fixture / Include / Benchmark Paths Break After Move

**What goes wrong:**
Less obvious relative paths inside source, benches, bridge tests, or packaging scripts break after the move. These are not Cargo dependency paths; they are runtime fixture paths, include roots, benchmark working directories, and generated-header locations.

**Why it happens:**
The repo contains path-sensitive internals such as:
- fixture paths in bridge/tests/bench code
- benchmark workflow `working-directory: ClassicLib-rs`
- CMake bridge include paths under `ClassicLib-rs/cpp-bindings/...`
- Criterion and profiling docs/scripts anchored to `ClassicLib-rs/target/...`

These are usually discovered only when niche workflows run.

**How to avoid:**
- Add a targeted path audit for non-manifest path consumers.
- Validate at least one benchmark/profiling path and one bridge/test fixture path after the move.
- Search for `ClassicLib-rs/`, `../..`, and known old include roots in `.rs`, `.ps1`, `.yml`, `.md`, `CMakeLists.txt`, and package manifests.

**Warning signs:**
- Benchmarks fail only in CI or only on clean machines.
- C++ bridge compiles but fixture-based tests fail.
- Docs and scripts still point to `ClassicLib-rs/target/criterion` after cutover.

**Phase to address:**
Phase 4 — nonstandard path consumer audit, then rechecked in Phase 5.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Leave a live `ClassicLib-rs/Cargo.toml` “for compatibility” | Fewer immediate edits | Dual-workspace ambiguity and future path drift | Never, unless it is an explicit tombstone shim with no live `[workspace]` authority |
| Update Cargo only, defer docs/tools/scripts | Faster initial green build | Follow-up PRs keep reintroducing stale paths | Never for this repo |
| Keep old CI cache/artifact paths until later | Fewer workflow edits | False greens from stale outputs | Never |
| Hand-edit manifests one by one | Feels safe | Missed path rewrites in high-fan-out crates | Only if backed by a complete inventory + grep-based closure audit |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| CMake frontends | Only updating Rust workspace, not `MANIFEST_PATH` or bridge include dirs | Rewire `classic-cli/CMakeLists.txt` and `classic-gui/CMakeLists.txt` in the same phase as workspace cutover |
| Node binding package | Forgetting `package.json` script depth changes | Recompute relative `tools/...` paths and rerun Bun + Node parity/runtime commands from the new directory |
| Python bindings | Moving crates but leaving `.venv`, `requirements-ci.txt`, or `validate_stubs.py` paths anchored to `ClassicLib-rs` | Rewire all Python commands and stub-validation defaults together |
| CI caches/artifacts | Updating commands but not cache/upload paths | Change command paths, cache paths, and artifact upload paths in the same PR |
| Benchmark workflow | Keeping `working-directory: ClassicLib-rs` and `ClassicLib-rs/target/...` baseline paths | Move working directory and criterion cache roots together, then run one benchmark smoke validation |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Huge grep-only cleanup deferred to the end | Late-stage surprise failures in docs/tests/scripts | Front-load a path inventory and classify authoritative vs archival references | Immediately in a repo with dense planning/docs surfaces like this one |
| Relying on incremental builds after path surgery | Clean CI fails, local incremental build passes | Require one clean-state validation after move | As soon as stale `target`/artifact directories exist |
| Refreshing baselines before path rewiring is complete | Parity artifacts regenerated into wrong directories | Rewire paths first, refresh artifacts second | Immediately when parity jobs run |

## Security / Integrity Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Accidentally committing generated artifacts from a recreated legacy subtree | Confusing source of truth and noisy diffs | Assert `ClassicLib-rs/` stays absent or empty after cutover and audit `git status` before closure |
| Letting CI upload diagnostics from old directories | Misleading failure analysis and false confidence | Update upload-artifact paths in the same change as the move |

## UX / Contributor Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Commands still require `--manifest-path ClassicLib-rs/Cargo.toml` in docs | Contributors think the move is incomplete or broken | Standardize on repo-root Cargo commands immediately after cutover |
| Agent docs still route work into `ClassicLib-rs/` | Future AI/human edits keep targeting dead paths | Update high-authority instructions before milestone closure |

## "Looks Done But Isn't" Checklist

- [ ] **Workspace cutover:** `cargo metadata` from repo root and subcrates reports the same `workspace_root`.
- [ ] **Manifest rewrite:** no active `Cargo.toml` still uses old-depth local dependency paths.
- [ ] **Frontend integration:** CLI and GUI wrappers pass after CMake manifest/include rewiring.
- [ ] **Parity tooling:** Python, Node, and CXX gate scripts no longer default to `ClassicLib-rs/...` paths.
- [ ] **Generated artifacts:** CI/cache/upload paths no longer point at `ClassicLib-rs/target` or old parity-artifact dirs.
- [ ] **Docs/agents:** authoritative instructions no longer tell contributors to use `ClassicLib-rs/Cargo.toml`.
- [ ] **Legacy tombstone:** running the full validation suite does not recreate or depend on a live `ClassicLib-rs/` subtree.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Dual workspace / partial move | HIGH | Stop feature work, choose one canonical root, rerun `cargo metadata` audits, then revalidate all wrappers and CI commands |
| Incomplete path-dependency rewrite | MEDIUM | Inventory all `path =` entries, mechanize the rewrite, rerun `cargo check --workspace` and high-fan-out target checks |
| Wrapper/CI breakage | MEDIUM | Rewire scripts/CMake/workflows together, invalidate stale caches, rerun end-to-end entrypoints |
| Artifact shadowing | MEDIUM | Delete stale old-path outputs, fix cache/upload paths, rerun from clean state |
| Docs/agent drift | LOW/MEDIUM | Update authoritative docs first, then planning/API docs, then add grep-based regression checks |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Dual-workspace / partial move | Phase 1-2 | `cargo metadata` shows one canonical `workspace_root`; no live legacy workspace remains |
| Incomplete path-dependency rewrite | Phase 2 | `cargo check --workspace` plus grep over `Cargo.toml` path dependencies |
| Frontend/wrapper breakage | Phase 3 | CLI, GUI, rebuild, and shell-entrypoint commands succeed |
| Parity tool stale-path drift | Phase 3 | All three parity gates run from new paths without recreating old directories |
| Artifact/cache shadowing | Phase 4 | Clean local/CI runs succeed with old caches removed |
| Hidden fixture/include/benchmark path breaks | Phase 4 | Benchmark/fixture/path-sensitive smoke checks pass |
| Docs/agent/planning drift | Phase 5 | Grep/audit of authoritative docs, planning docs, and agent instructions is clean |
| Validation tests still encode old topology | Phase 5 | `tests/planning` and `tools/*_api_parity/tests` pass under the new topology |

## Sources

- Cargo workspaces reference: https://doc.rust-lang.org/cargo/reference/workspaces.html — workspace root semantics, parent discovery, and `workspace.package` path behavior. **HIGH**
- Cargo manifest reference: https://doc.rust-lang.org/cargo/reference/manifest.html — manifest/root behavior. **HIGH**
- `ClassicLib-rs/Cargo.toml` — current workspace members/dependencies. **HIGH**
- `classic-cli/CMakeLists.txt`, `classic-gui/CMakeLists.txt` — frontend manifest/include path coupling. **HIGH**
- `rebuild_rust.ps1`, `tools/enter_vs_dev_shell.ps1` — wrapper-script coupling to old paths. **HIGH**
- `.github/workflows/ci-rust.yml`, `ci-python-bindings.yml`, `ci-typescript.yml`, `ci-cpp.yml`, `benchmarks.yml` — cache/artifact/working-directory coupling. **HIGH**
- `tools/python_api_parity/*`, `tools/node_api_parity/*`, `tools/cxx_api_parity/*` — parity/default-path coupling. **HIGH**
- `.planning/PROJECT.md` and current `.planning/` / `docs/` path references — stale-path drift risk across planning and documentation surfaces. **HIGH**

---
*Pitfalls research for: moving the Rust workspace to the repository root*
*Researched: 2026-04-11*

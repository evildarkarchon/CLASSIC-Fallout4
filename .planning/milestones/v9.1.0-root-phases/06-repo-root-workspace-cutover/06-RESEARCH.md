# Phase 6: Repo-Root Workspace Cutover - Research

**Researched:** 2026-04-11
**Domain:** Cargo workspace-root cutover in a brownfield multi-language repo
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Phase 6 moves the full workspace-owned file set to the repository root, not just `Cargo.toml`.
- **D-02:** The Phase 6 move includes `Cargo.toml`, `Cargo.lock`, `.cargo/config.toml`, `validate_stubs.py`, `criterion.toml`, `benchmark-config.yaml`, and `benches/`.
- **D-03:** `validate_stubs.py` becomes a repo-root tool in this phase and should treat the repo root as the Rust workspace root.
- **D-04:** The cutover preserves current Cargo alias and profile behavior exactly; only the authoritative root path changes.
- **D-05:** `ClassicLib-rs/Cargo.toml` is retired in Phase 6 as a live workspace manifest.
- **D-06:** The old manifest should be removed entirely, not kept live and not retained as a compatibility workspace.
- **D-07:** Phase 6 is cargo-first, not wrapper-first: direct Cargo workflows and Rust CI must stop depending on `ClassicLib-rs/Cargo.toml` now, while broader wrapper/CMake rewires can remain in later phases.
- **D-08:** The important cutover rule is one canonical workspace root with no direct old-manifest usage; Phase 6 does not need extra blocker machinery just to stop Cargo parent-directory discovery inside `ClassicLib-rs/...`.
- **D-09:** Repo-root `cargo fmt`, `cargo clippy`, `cargo build`, and `cargo test` are all first-class Phase 6 workflows.
- **D-10:** Package-filtered repo-root commands such as `cargo build -p classic-scanlog-core` are also part of the Phase 6 contract.
- **D-11:** Active workflows should prefer plain repo-root `cargo ...` invocation style after the cutover, not `--manifest-path` calls to either the old or new root manifest.
- **D-12:** Existing alias/profile-based developer flows from `.cargo/config.toml` should keep working from repo root after the cutover.
- **D-13:** Phase 6 closes only after both repo-root Cargo workflows and cargo-based Rust CI are updated to the new root behavior.
- **D-14:** Proof must include an explicit Cargo root-detection check such as `cargo metadata` so the planner verifies one canonical workspace root.
- **D-15:** Proof must include at least one clean validation pass that does not rely on stale `ClassicLib-rs/target` outputs.
- **D-16:** Proof must include an explicit audit that active cargo-based workflows no longer mention `ClassicLib-rs/Cargo.toml`.

### the agent's Discretion
- Exact file-move mechanics for promoting the workspace root, as long as the moved file set and behavior above are preserved.
- Exact command ordering for the clean validation pass and old-manifest audit.
- Whether Phase 6 proves root detection with `cargo metadata`, `cargo locate-project --workspace`, or both, as long as Cargo itself confirms the canonical root.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within Phase 6 scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ROOT-01 | Contributor can run the Rust workspace from the repository root without using `ClassicLib-rs/Cargo.toml` as the canonical workspace manifest | Use a repo-root **virtual workspace** as the only live manifest; retire `ClassicLib-rs/Cargo.toml`; prove root detection with `cargo locate-project --workspace` and `cargo metadata --format-version 1 --no-deps`. |
| ROOT-02 | Contributor can use repo-root Cargo workflows for the relocated workspace, including `cargo fmt --all`, `cargo clippy --workspace`, and `cargo test --workspace` | Move `Cargo.lock`, `.cargo/config.toml`, profiles, and workspace tables intact to root; update Rust CI to plain repo-root Cargo commands; validate from a clean state without `ClassicLib-rs/target`. |
</phase_requirements>

## Summary

Use a **single repo-root virtual Cargo workspace** and treat the current `ClassicLib-rs/Cargo.toml` as source material, not a compatibility shim. Official Cargo docs are clear: the workspace root is the directory containing the authoritative `Cargo.toml`, virtual workspaces run against all members by default from the root, and shared `Cargo.lock`, `target`, `[profile.*]`, `[workspace.dependencies]`, and `[workspace.lints]` semantics belong at that root. For this phase, the correct implementation is to promote the existing workspace manifest contents to `./Cargo.toml`, keep `resolver = "2"` to preserve current behavior, move the full workspace-owned support set to root, and delete the old live manifest.

The biggest hidden risks are not the manifest move itself. They are (1) leaving a second effective workspace root alive, (2) forgetting that `.cargo/config.toml` and `Cargo.lock` are root-scoped behavior, (3) letting stale `ClassicLib-rs/target` outputs mask breakage, (4) keeping proof commands on `--manifest-path`, and (5) over-scoping CI rewires that the roadmap intentionally sequences later. Cargo already provides the authoritative mechanisms needed here: `cargo locate-project --workspace` and `cargo metadata --format-version 1 --no-deps` should be the phase-proof primitives instead of custom path detection.

**Primary recommendation:** Create a repo-root **virtual workspace** by moving the existing workspace tables and root-owned support files intact to the repository root, **omit `workspace.default-members`**, delete `ClassicLib-rs/Cargo.toml`, update `ci-rust.yml` to plain repo-root Cargo commands, and treat `benchmarks.yml` as a later-phase CI refresh unless the moved benchmark assets would otherwise leave it immediately broken.

## Project Constraints (from AGENTS.md)

- Prioritize active work in `classic-cli/`, `classic-gui/`, and `ClassicLib-rs/`.
- Keep all business logic in Rust; non-interface layers stay thin.
- Maintain one shared Tokio runtime; do not introduce separate runtimes.
- Keep docs synchronized with architecture/workflow changes, especially `README.md` and `AGENTS.md`.
- Never write to `NUL` or `nul` as a file path on Windows.
- Consult `docs/api/README.md` before changing public Rust/bridge/binding-facing APIs; update affected `docs/api/` pages if the contract changes.
- Never run C++ tests via raw binaries or raw `ctest`; use `classic-cli/build_cli.ps1 -Test` or `classic-gui/build_gui.ps1 -Test`.
- On Git Bash for Rust/MSVC C++ commands, use `tools/use_msvc_from_git_bash.sh` so Git's linker does not shadow MSVC.

## Standard Stack

### Core
| Library / Tool | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Cargo virtual workspace | Cargo docs current; local tool `cargo 1.94.0` | Single canonical repo-root workspace manifest | Official Cargo pattern when the root is not itself a crate; preserves default all-members behavior at workspace root. |
| `Cargo.lock` at workspace root | shared lockfile | Single dependency-resolution source of truth | Cargo workspaces share one lockfile at the workspace root. |
| `.cargo/config.toml` at workspace root | current Cargo config hierarchy | Preserve aliases/config behavior | Cargo searches `.cargo/config.toml` from current dir upward; root placement is the canonical project-scoped config. |
| `cargo locate-project --workspace` + `cargo metadata --format-version 1 --no-deps` | built into Cargo | Canonical root-detection proof | These are official Cargo mechanisms; do not hand-roll path/root discovery. |

### Supporting
| Library / Tool | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `rustfmt` component | installed locally | Validate `cargo fmt --all` from repo root | For repo-root formatting proof and CI format checks. |
| `clippy` component | installed locally | Validate `cargo clippy --workspace` from repo root | For repo-root lint proof and Rust CI. |
| `validate_stubs.py` | existing repo tool | Python stub validation against repo-root workspace | After it is moved to root, invoke it with `--rust-dir .` or rely on its root default. |
| GitHub Actions `dtolnay/rust-toolchain@stable` + `actions/cache@v5` | current repo standard | Preserve Rust CI behavior after path cutover | Use for CI path/cache rewiring; do not change CI stack during this phase. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Repo-root virtual workspace | Root package workspace | Root-package workspaces default differently and imply a root crate that this phase does not need. |
| Deleting old manifest | Keeping `ClassicLib-rs/Cargo.toml` as compatibility workspace | Violates the one-root requirement and preserves dual-source ambiguity. |
| Cargo-native root detection | Custom PowerShell/Python path probing | More brittle and less authoritative than `cargo locate-project` / `cargo metadata`. |
| Preserving resolver/profile behavior | Opportunistic resolver/profile upgrade | Cargo 2024-era SOTA is `resolver = "3"` for edition-2024 roots, but user decisions lock this phase to behavior preservation, so keep `resolver = "2"` now. |

**Installation:**
```bash
rustup component add rustfmt clippy
```

**Version verification:** No new third-party package install is required for this phase. Local environment audit on 2026-04-11 found `cargo 1.94.0`, `rustc 1.94.0`, `python 3.14.3`, `node 25.9.0`, and `bun 1.3.10`; `rustfmt` and `clippy` are already installed.

## Architecture Patterns

### Recommended Project Structure
```text
repo-root/
├── Cargo.toml                # authoritative virtual workspace manifest
├── Cargo.lock                # shared workspace lockfile
├── .cargo/
│   └── config.toml           # aliases/config now discovered from repo root
├── benches/                  # workspace-owned benchmark entrypoints
├── criterion.toml            # workspace-level criterion config
├── benchmark-config.yaml     # benchmark threshold config
├── validate_stubs.py         # repo-root stub validator
├── ClassicLib-rs/
│   ├── foundation/
│   ├── business-logic/
│   ├── cpp-bindings/
│   ├── node-bindings/
│   ├── python-bindings/
│   └── ui-applications/
└── target/                   # new active Cargo target dir
```

### Pattern 1: Promote the existing manifest as a root virtual workspace
**What:** Move the existing `[workspace]`, `[workspace.dependencies]`, `[workspace.lints]`, and `[profile.*]` sections to `./Cargo.toml`, keeping member paths rooted at `ClassicLib-rs/...` for this phase.

**When to use:** Immediately at cutover; this is the canonical phase-6 architecture.

**Planner rule:** Do **not** add `workspace.default-members` in Phase 6. Official Cargo behavior for a virtual workspace with no `default-members` is already “all members”, which exactly matches the required plain repo-root command contract and avoids unnecessary churn.

**Example:**
```toml
# Source: https://doc.rust-lang.org/cargo/reference/workspaces.html
[workspace]
members = [
  "ClassicLib-rs/foundation/classic-shared-core",
  "ClassicLib-rs/business-logic/classic-scanlog-core",
  "ClassicLib-rs/python-bindings/classic-config-py",
  "ClassicLib-rs/node-bindings/classic-node",
  "ClassicLib-rs/cpp-bindings/classic-cpp-bridge",
  "ClassicLib-rs/ui-applications/classic-tui",
]
resolver = "2"

[workspace.dependencies]
# copied intact from the current live workspace manifest

[workspace.lints.rust]
deprecated = "deny"
unused = "deny"

[profile.release]
opt-level = 3
lto = "thin"
codegen-units = 1
strip = true
```

### Pattern 2: Preserve root-scoped Cargo behavior by moving support files with the manifest
**What:** Move `Cargo.lock`, `.cargo/config.toml`, `criterion.toml`, `benchmark-config.yaml`, `benches/`, and `validate_stubs.py` with the root cutover.

**When to use:** Same change as the root manifest promotion.

**Example:**
```toml
# Source: https://doc.rust-lang.org/cargo/reference/config.html
[alias]
flame = "flamegraph"
flame-bench = "flamegraph --bench"
profile-build = "build --profile release-with-debug"
```

### Pattern 3: Use Cargo itself as the cutover oracle
**What:** Prove the root changed with Cargo-native commands, not filesystem assumptions.

**When to use:** Phase proof, validation scripts, and planning audits.

**Example:**
```bash
# Source: https://doc.rust-lang.org/cargo/commands/cargo-locate-project.html
cargo locate-project --workspace

# Source: https://doc.rust-lang.org/cargo/commands/cargo-metadata.html
cargo metadata --format-version 1 --no-deps
```

### Anti-Patterns to Avoid
- **Dual live manifests:** Never keep both `./Cargo.toml` and `ClassicLib-rs/Cargo.toml` authoritative.
- **Root wrapper manifest:** Do not create a thin forwarding manifest that still makes contributors think `ClassicLib-rs/Cargo.toml` is live.
- **Behavior drift during relocation:** Do not upgrade resolver/profile behavior in the same phase; preserve current alias/profile semantics exactly.
- **Redundant `workspace.default-members`:** Do not add it “for clarity” when the desired set is already “all members”; that creates a second member-selection surface to maintain.
- **Proof by grep alone:** A grep audit is necessary, but the canonical proof is Cargo returning the new workspace root.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Workspace-root detection | Custom script that infers the root from path strings | `cargo locate-project --workspace` and `cargo metadata --format-version 1 --no-deps` | Cargo already knows the authoritative root and target dir. |
| Workspace dependency inheritance | Manual per-crate dependency duplication | Existing `[workspace.dependencies]` + `workspace = true` | The repo already uses this extensively; duplicating versions will create drift fast. |
| Alias/profile preservation | Shell wrappers that emulate aliases/profiles | Move `.cargo/config.toml` and `[profile.*]` intact | Cargo-native behavior is already defined and tested. |
| Clean-state proof | Ad hoc “looks clean enough” checks | Delete/ignore stale `ClassicLib-rs/target`, then run canonical repo-root Cargo commands | Old target outputs can mask a broken cutover. |

**Key insight:** Cargo already provides the root-selection, shared-lockfile, shared-target, and config-discovery behavior this phase needs. Custom compatibility layers mostly create ambiguity.

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None found for the exact workspace-root string in repo-managed databases or local datastore contracts. This phase changes workspace anchor paths, not persisted business data keys. | None — code edit only. |
| Live service config | None verified outside git. Active CI/workflow path assumptions are committed in repo; no evidence found of UI-only service config storing `ClassicLib-rs/Cargo.toml` as live state. | None outside repo edits. |
| OS-registered state | None found. No evidence in project guidance of Task Scheduler, launchd, systemd, or pm2 registrations tied to `ClassicLib-rs/Cargo.toml` for this phase. | None. |
| Secrets/env vars | No secret key or env-var names were found that encode `ClassicLib-rs` as an exact key name. Existing vars like `VCPKG_ROOT` and `GITHUB_TOKEN` are unaffected by the cutover. | None — code/path edits only. |
| Build artifacts | `ClassicLib-rs/target` is the current active Cargo output directory (`cargo metadata` reports `target_directory = J:\CLASSIC-Fallout4\ClassicLib-rs\target`). Benchmarks also cache `ClassicLib-rs/target/criterion/*`. These will become stale immediately after root cutover. | **Data migration:** none. **Code edit:** update active workflows to use repo-root `target`. **Cleanup:** run at least one clean validation pass that does not reuse `ClassicLib-rs/target`. |

## Common Pitfalls

### Pitfall 1: Dual-root steady state
**What goes wrong:** Root commands work, but `ClassicLib-rs/Cargo.toml` still exists and some callers keep using it.
**Why it happens:** Teams treat the old manifest as a harmless compatibility shim.
**How to avoid:** Delete the old live manifest in the same phase that activates root `Cargo.toml`.
**Warning signs:** `cargo locate-project --workspace` differs by cwd, or active workflows still use `--manifest-path ClassicLib-rs/Cargo.toml`.

### Pitfall 2: Forgetting root-scoped support files
**What goes wrong:** Repo-root `cargo` works differently than before because aliases, profiles, lockfile, or benchmark config were stranded under `ClassicLib-rs/`.
**Why it happens:** The move is treated as “just Cargo.toml”.
**How to avoid:** Move the full workspace-owned set together: `Cargo.toml`, `Cargo.lock`, `.cargo/config.toml`, `validate_stubs.py`, `criterion.toml`, `benchmark-config.yaml`, `benches/`.
**Warning signs:** `cargo flame` or custom profile flows stop resolving from repo root; new root generates an unexpected lockfile or target layout.

### Pitfall 3: Accidental behavior change via resolver/default-members
**What goes wrong:** Root commands stop selecting the full workspace, or dependency resolution behavior changes unexpectedly.
**Why it happens:** The new root manifest is changed from the current virtual-workspace pattern, resolver is opportunistically upgraded, or `workspace.default-members` is added and later drifts from `members`.
**How to avoid:** Keep a **virtual** workspace, preserve `resolver = "2"`, and rely on Cargo's default all-members behavior instead of adding `workspace.default-members`.
**Warning signs:** Plain `cargo test` from root no longer covers the expected members, `default-members` differs from `members`, or lockfile churn appears unrelated to path changes.

### Pitfall 6: Pulling benchmark CI into the wrong phase boundary
**What goes wrong:** Phase 6 expands into broad CI/path refresh work that the roadmap reserved for later phases, or benchmark CI is silently broken because benchmark assets moved without minimum path fixes.
**Why it happens:** `benchmarks.yml` is cargo-based CI, but Phase 6 requirements only lock repo-root Cargo workflows plus cargo-based **Rust CI** proof.
**How to avoid:** Update `ci-rust.yml` in Phase 6. For `benchmarks.yml`, do only the minimum required to keep the moved benchmark assets from breaking an active workflow; defer broader cache/path validation and benchmark-proof obligations to Phase 9.
**Warning signs:** Planner tries to make benchmark CI a closure gate for ROOT-01/02, or moved `criterion.toml` / `benchmark-config.yaml` would make `benchmarks.yml` fail immediately after the cutover.

### Pitfall 4: Stale target cache hides breakage
**What goes wrong:** CI/local runs pass because `ClassicLib-rs/target` already contains usable artifacts.
**Why it happens:** Cargo target dir moves from `ClassicLib-rs/target` to root `target` after cutover, but proof still trusts old outputs.
**How to avoid:** Clean or isolate target outputs and require one validation pass that does not reuse `ClassicLib-rs/target`.
**Warning signs:** A supposedly clean cutover only passes on machines that built the old layout before.

### Pitfall 5: `validate_stubs.py` still thinks the Rust root is `ClassicLib-rs`
**What goes wrong:** Stub validation cannot find `python-bindings/` after the file is moved.
**Why it happens:** The script currently defaults `--rust-dir` to `Path(__file__).parent` and expects `python-bindings/` under that root.
**How to avoid:** After moving the script to repo root, run it with `--rust-dir .` or rely on the new repo-root default.
**Warning signs:** Error message: `python-bindings directory not found`.

## Code Examples

Verified patterns from official sources:

### Canonical workspace-root proof
```bash
# Source: https://doc.rust-lang.org/cargo/commands/cargo-locate-project.html
cargo locate-project --workspace

# Source: https://doc.rust-lang.org/cargo/commands/cargo-metadata.html
cargo metadata --format-version 1 --no-deps | python -c "import sys,json; d=json.load(sys.stdin); print(d['workspace_root']); print(d['target_directory'])"
```

### Canonical repo-root command contract
```bash
# Source: https://doc.rust-lang.org/cargo/reference/workspaces.html
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace --release -- --nocapture
cargo build -p classic-scanlog-core
```

### Repo-root stub validation after cutover
```bash
# Source: repo tool behavior in ClassicLib-rs/validate_stubs.py
python validate_stubs.py --rust-dir . --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `cargo ... --manifest-path ClassicLib-rs/Cargo.toml` | Plain repo-root `cargo ...` with Cargo parent-directory discovery | Current Cargo docs; required by this phase | Simpler contributor workflow and one authoritative root. |
| Root package workspace assumptions | Virtual workspace at repo root when the root is not a crate | Long-standing Cargo pattern; current docs still recommend it | Keeps plain root commands operating across all members by default. |
| `resolver = "2"` as newest behavior | `resolver = "3"` is the edition-2024 default for new roots (Rust 1.84+) | Current Cargo docs | SOTA changed, but Phase 6 should **not** adopt it because behavior preservation is locked. |
| Legacy `.cargo/config` | `.cargo/config.toml` preferred | Cargo 1.39+ | Keep `.cargo/config.toml`; do not regress to legacy file naming. |

**Deprecated/outdated:**
- Live dual-manifest compatibility (`./Cargo.toml` plus active `ClassicLib-rs/Cargo.toml`) — outdated for this phase because it preserves two roots.
- Proof by `grep` only — outdated because Cargo already exposes authoritative root/target metadata.

## Open Questions Resolved

### 1. `workspace.default-members`
**Recommendation:** **Do not add `workspace.default-members` in Phase 6.**

**Rationale:**
- Official Cargo docs for `cargo test`, `cargo bench`, and workspaces all agree: when `default-members` is absent, a **virtual workspace** defaults to **all members**.
- That behavior is exactly what Phase 6 wants for plain repo-root `cargo fmt`, `cargo clippy`, `cargo test`, and package-filtered commands.
- Adding `workspace.default-members` would not improve correctness here; it would create a second list that can drift from `members` during Phase 7 crate relocation.
- Omitting it best preserves today's effective behavior with the least maintenance surface.

**Confidence:** HIGH

**Planner-facing implication:**
- Build the new root manifest as a virtual workspace with `members = [...]` and `resolver = "2"`.
- Do **not** include `default-members` unless the plan intentionally wants a subset different from “all members” (which Phase 6 does not).
- Validation should prove the plain root commands work because the virtual-workspace default covers all members, not because an explicit `default-members` list was added.

### 2. Benchmark workflow rewiring
**Recommendation:** **Benchmark workflow rewiring is not a Phase-6 closure requirement by default, but minimum path fixes become required if moving the benchmark assets would otherwise leave the active workflow broken.**

**What must change in Phase 6:**
- Move `criterion.toml`, `benchmark-config.yaml`, and `benches/` to repo root per D-02.
- Audit `.github/workflows/benchmarks.yml` immediately after that move.
- If the move leaves `benchmarks.yml` pointing at now-missing paths or a dead workspace root, update only the **minimum path contracts** needed to keep it viable:
  - `working-directory: ClassicLib-rs` → repo root or no override
  - `ClassicLib-rs/target/...` cache and baseline paths → `target/...`
  - any implicit dependence on `ClassicLib-rs/Cargo.toml` via cwd discovery → repo-root Cargo discovery

**What can wait until later phases:**
- Treating `benchmarks.yml` as a formal closure gate for ROOT-01/02
- Broader CI/path-sensitive validation beyond `ci-rust.yml`
- Regenerated benchmark artifacts/baselines as milestone proof
- Comprehensive CI refresh and clean-state artifact validation, which the roadmap explicitly places in **Phase 9** (`INTG-03`, `INTG-04`)

**Rationale:**
- Phase 6 success criteria mention repo-root Cargo workflows and one canonical workspace root; they do **not** require benchmark CI proof.
- D-13 locks Phase 6 to repo-root workflows plus cargo-based **Rust CI** update; the context names `.github/workflows/ci-rust.yml` specifically as the active Rust CI surface.
- The roadmap reserves CI and path-sensitive job refresh for Phase 9, so making benchmark workflow completion a Phase-6 gate would overrun the documented phase boundary.
- However, D-02 explicitly moves benchmark-owned files in Phase 6. If those moves would otherwise strand an active workflow on dead paths, the minimum rewiring needed to keep it non-broken belongs in Phase 6.

**Confidence:** MEDIUM-HIGH

**Planner-facing implication:**
- Make `ci-rust.yml` rewiring mandatory in Phase 6.
- Add a small audit task for `benchmarks.yml`.
- Only promote benchmark-workflow edits into Phase 6 if they are required to keep the moved root-owned benchmark assets from breaking an active workflow immediately.
- Do **not** require benchmark job green status as the closure proof for ROOT-01/02 unless the planner discovers no extra scope beyond those minimum path fixes.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Cargo | Repo-root workspace cutover and proof | ✓ | 1.94.0 | — |
| Rust compiler | Workspace validation | ✓ | 1.94.0 | — |
| `rustfmt` | `cargo fmt --all` proof | ✓ | installed via rustup | `rustup component add rustfmt` |
| `clippy` | `cargo clippy --workspace` proof | ✓ | installed via rustup | `rustup component add clippy` |
| Python | `validate_stubs.py` and small metadata parsing helpers | ✓ | 3.14.3 | Use repo CI's Python 3.12 if local incompatibility appears |

**Missing dependencies with no fallback:**
- None.

**Missing dependencies with fallback:**
- None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Python `unittest` planning audit + direct Cargo command checks |
| Config file | none — per-phase audit file under `tests/planning/` |
| Quick run command | `python -m pytest tests/planning/test_phase06_validation.py -q` |
| Full suite command | `cargo fmt --all -- --check && cargo clippy --workspace --all-targets --all-features -- -D warnings && cargo test --workspace --release -- --nocapture && python -m pytest tests/planning/test_phase06_validation.py -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ROOT-01 | Repo root is the only canonical workspace root | planning audit + smoke | `cargo locate-project --workspace` and `cargo metadata --format-version 1 --no-deps` from repo root | ❌ Wave 0 |
| ROOT-02 | Repo-root fmt/clippy/test and package-filtered build work without `--manifest-path` | smoke | `cargo fmt --all -- --check && cargo clippy --workspace --all-targets --all-features -- -D warnings && cargo test --workspace --release -- --nocapture && cargo build -p classic-scanlog-core` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/planning/test_phase06_validation.py -q`
- **Per wave merge:** `cargo fmt --all -- --check && cargo clippy --workspace --all-targets --all-features -- -D warnings && cargo test --workspace --release -- --nocapture`
- **Phase gate:** Full suite green plus explicit old-manifest absence/root-detection audit

### Wave 0 Gaps
- [ ] `tests/planning/test_phase06_validation.py` — assert repo-root `cargo locate-project --workspace` / `cargo metadata` root and absence of active `ClassicLib-rs/Cargo.toml` usage in Rust CI
- [ ] Clean-state validation step — explicitly avoid stale `ClassicLib-rs/target`

## Sources

### Primary (HIGH confidence)
- Context7 `/websites/doc_rust-lang_cargo` — workspace semantics, virtual workspaces, resolver rules, `cargo metadata`, `cargo locate-project`
- https://doc.rust-lang.org/cargo/reference/workspaces.html — workspace root, virtual workspace behavior, default member behavior
- https://doc.rust-lang.org/cargo/reference/config.html — `.cargo/config.toml` hierarchy and root-scoped config discovery
- https://doc.rust-lang.org/cargo/reference/resolver.html — resolver versions, including `resolver = "3"` as the edition-2024 default
- https://doc.rust-lang.org/cargo/commands/cargo-locate-project.html — canonical workspace-root detection
- https://doc.rust-lang.org/cargo/commands/cargo-metadata.html — canonical `workspace_root` / `target_directory` proof surface
- https://doc.rust-lang.org/cargo/commands/cargo-test.html — workspace package selection and `--workspace` semantics
- `J:\CLASSIC-Fallout4\ClassicLib-rs\Cargo.toml` — current live workspace tables and resolver/profile state
- `J:\CLASSIC-Fallout4\ClassicLib-rs\.cargo\config.toml` — current alias behavior that must be preserved
- `J:\CLASSIC-Fallout4\.github\workflows\ci-rust.yml` — active Rust CI manifest-path and cache assumptions
- `J:\CLASSIC-Fallout4\ClassicLib-rs\validate_stubs.py` — current `--rust-dir` default and `python-bindings/` assumption

### Secondary (MEDIUM confidence)
- `.planning/research/SUMMARY.md` — milestone sequencing and no-dual-root framing
- `.planning/codebase/STACK.md` / `.planning/codebase/TESTING.md` / `.planning/codebase/STRUCTURE.md` — current repo contracts and validation surfaces
- `rebuild_rust.ps1` and `.github/workflows/benchmarks.yml` — downstream path consumers to classify for later phases or explicit deferral

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Cargo behavior is documented officially and matches the live repo structure.
- Architecture: HIGH - The phase is a path-anchor cutover, not a redesign, and the repo already demonstrates the current source material.
- Pitfalls: HIGH - They are concrete repo-path risks verified by current manifests, CI files, target directories, and script assumptions.

**Research date:** 2026-04-11
**Valid until:** 2026-05-11

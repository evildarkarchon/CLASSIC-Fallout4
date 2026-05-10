---
phase: 06-repo-root-workspace-cutover
verified: 2026-04-12T13:12:01Z
status: passed
score: 3/3 must-haves verified
---

# Phase 6: Repo-Root Workspace Cutover Verification Report

**Phase Goal:** Contributors can treat the repository root as the single authoritative Cargo workspace root.
**Verified:** 2026-04-12T13:12:01Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Contributor can run Cargo from the repository root without relying on `ClassicLib-rs/Cargo.toml` as the live workspace manifest. | ✓ VERIFIED | `cargo locate-project --workspace` returned `J:\CLASSIC-Fallout4\Cargo.toml`; `cargo metadata --format-version 1 --no-deps` reported `workspace_root=J:\CLASSIC-Fallout4`; `ClassicLib-rs/Cargo.toml` is absent. |
| 2 | Contributor can run canonical repo-root workspace commands including `cargo fmt --all`, `cargo clippy --workspace`, and `cargo test --workspace`. | ✓ VERIFIED | From repo root: `cargo fmt --all -- --check`, `cargo clippy --workspace --all-targets --all-features -- -D warnings`, `cargo test --workspace --release -- --nocapture`, and `cargo build -p classic-scanlog-core` all completed successfully. |
| 3 | Contributor can observe one active workspace root instead of a dual-workspace steady state. | ✓ VERIFIED | Root `Cargo.toml`, `Cargo.lock`, and `.cargo/config.toml` exist; legacy root-scoped copies under `ClassicLib-rs/` are absent; active workflows/docs point to repo-root commands; `classic-cli/CMakeLists.txt` and `classic-gui/CMakeLists.txt` now import `../Cargo.toml`. |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `Cargo.toml` | Authoritative repo-root workspace manifest | ✓ VERIFIED | `[workspace]`, `resolver = "2"`, root profiles/dependencies/lints, and `ClassicLib-rs/...` members present. |
| `Cargo.lock` | Shared lockfile at repo root | ✓ VERIFIED | Exists at repo root; no `ClassicLib-rs/Cargo.lock` copy remains. |
| `.cargo/config.toml` | Repo-root Cargo alias/config discovery | ✓ VERIFIED | Exists at repo root with `flame`, `flame-bench`, and `profile-build`. |
| `validate_stubs.py` | Repo-root stub validator with transitional normalization | ✓ VERIFIED | Defaults `--rust-dir` to repo root and normalizes both repo root and `ClassicLib-rs`; gsd-tools reported a literal-pattern miss, but manual read verified dynamic path construction and live `python-bindings` resolution. |
| `rebuild_rust.ps1` | Repo-root rebuild entrypoint | ✓ VERIFIED | Uses `Cargo.toml` at repo root, plain `cargo` commands, and no `--manifest-path ClassicLib-rs/Cargo.toml`. |
| `criterion.toml` | Repo-root benchmark config | ✓ VERIFIED | Exists at root with `criterion_home = "./target/criterion"`; legacy copy removed. |
| `benchmark-config.yaml` | Repo-root benchmark thresholds | ✓ VERIFIED | Exists at root with current warning/failure thresholds; legacy copy removed. |
| `benches/common/mod.rs` | Repo-root shared benchmark helpers | ✓ VERIFIED | Exists and benchmark include paths were rewired to `../../../../benches/common/...`. |
| `.github/workflows/ci-rust.yml` | Rust CI on repo-root workspace | ✓ VERIFIED | Uses plain root `cargo` commands and `target` cache paths. |
| `.github/workflows/benchmarks.yml` | Benchmark workflow viable against repo-root paths | ✓ VERIFIED | Uses root `target/criterion/baseline` and `CONFIG_FILE="benchmark-config.yaml"`. |
| `tests/planning/test_phase06_validation.py` | Phase audit proving root contract | ✓ VERIFIED | 14 tests passed, including root detection, old-manifest audit, workflow/doc sync, and clean-run helper checks. |
| `tests/planning/phase06_clean_run.ps1` | Clean proof script for repo-root contract | ✓ VERIFIED | Renames `ClassicLib-rs/target`, runs root cargo commands, then restores legacy target directory. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `Cargo.toml` | `ClassicLib-rs/business-logic/classic-scanlog-core/Cargo.toml` | `[workspace].members` | ✓ WIRED | Member path present in root workspace manifest. |
| `.cargo/config.toml` | `Cargo.toml` | Cargo root discovery | ✓ WIRED | Root Cargo config sits beside the active workspace manifest and is consumed by successful root commands. |
| `validate_stubs.py` | `ClassicLib-rs/python-bindings/` | `normalize_rust_dir()` | ✓ WIRED | Manual verification: repo root default plus explicit `ClassicLib-rs` input both normalize to the live bindings tree. |
| `rebuild_rust.ps1` | `Cargo.toml` | plain repo-root cargo commands | ✓ WIRED | Script binds `$WorkspaceRootManifest` to root `Cargo.toml` and executes plain cargo build/clean flows. |
| `ClassicLib-rs/.../scanlog_benchmarks.rs` | `benches/common/mod.rs` | updated `#[path]` include | ✓ WIRED | Include rewritten to `../../../../benches/common/mod.rs`. |
| `.github/workflows/ci-rust.yml` | `Cargo.toml` | plain repo-root cargo commands | ✓ WIRED | Workflow jobs invoke root `cargo fmt/clippy/build/test` commands without manifest-path shims. |
| `.github/workflows/benchmarks.yml` | `benchmark-config.yaml` | explicit root config lookup | ✓ WIRED | Workflow sets `CONFIG_FILE="benchmark-config.yaml"` and uses root `target/criterion/...` paths. |
| `tests/planning/test_phase06_validation.py` | `CLAUDE.md` and active docs | stale-path audit | ✓ WIRED | Audit scans active doc/workflow surfaces for any remaining live-manifest references. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `tests/planning/test_phase06_validation.py` | `locate_result.stdout`, `metadata["workspace_root"]`, `metadata["target_directory"]` | Live `cargo locate-project` and `cargo metadata` subprocess output | Yes | ✓ FLOWING |
| `validate_stubs.py` | `normalized_rust_dir`, `bindings_dir` | Filesystem-backed `normalize_rust_dir()` resolution from repo root / legacy input | Yes | ✓ FLOWING |
| `.github/workflows/benchmarks.yml` | `CONFIG_FILE`, `target/criterion/baseline` | Root benchmark config file and root target directory | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Root workspace discovery | `cargo locate-project --workspace --message-format plain` | `J:\CLASSIC-Fallout4\Cargo.toml` | ✓ PASS |
| Root metadata reports one workspace root | `python -c "... cargo metadata ..."` | `workspace_root=J:\CLASSIC-Fallout4`, `target_directory=J:\CLASSIC-Fallout4\target`, `workspace_members=37` | ✓ PASS |
| Root rustfmt check | `cargo fmt --all -- --check` | exited 0 | ✓ PASS |
| Root clippy check | `cargo clippy --workspace --all-targets --all-features -- -D warnings` | exited 0 | ✓ PASS |
| Root workspace tests | `cargo test --workspace --release -- --nocapture` | exited 0; tool output truncated after many passing test binaries | ✓ PASS |
| Package-filtered root build | `cargo build -p classic-scanlog-core` | exited 0 | ✓ PASS |
| Phase audit suite | `python -m pytest tests/planning/test_phase06_validation.py -q` | `14 passed, 90 subtests passed` | ✓ PASS |
| Clean root-workflow proof | `pwsh -File tests/planning/phase06_clean_run.ps1` | exited 0; validated root detection, fmt, clippy, test, build, and audit with `ClassicLib-rs/target` quarantined | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| ROOT-01 | 06-00, 06-01, 06-02, 06-03 | Contributor can run the Rust workspace from the repository root without using `ClassicLib-rs/Cargo.toml` as the canonical workspace manifest | ✓ SATISFIED | Root manifest exists, legacy manifest is absent, cargo root detection resolves to repo root, workflows/docs/scripts target root manifest. |
| ROOT-02 | 06-00, 06-01, 06-02, 06-03 | Contributor can use repo-root Cargo workflows including `cargo fmt --all`, `cargo clippy --workspace`, and `cargo test --workspace` | ✓ SATISFIED | All canonical commands were executed successfully from repo root; CI and helper scripts teach and use those commands. |

**Orphaned requirements:** None. `REQUIREMENTS.md` maps only `ROOT-01` and `ROOT-02` to Phase 6, and both appear in phase plan frontmatter.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| None in scanned phase-owned active artifacts | — | No blocking TODO/FIXME/placeholder or stub implementation found in the verified Phase 6 contract surfaces | ℹ️ Info | No anti-patterns blocking the goal were detected. |

### Human Verification Required

None.

### Gaps Summary

No goal-blocking gaps found. The repository root is the active Cargo workspace root in code, automation, and active guidance. Cargo-native root detection, canonical root commands, benchmark support relocation, clean-state proof, and active workflow/doc rewires all verify the Phase 6 contract. Unrelated modified Python parity-artifact files were present in `git status`, but they do not contradict the Phase 6 workspace-root contract and were not treated as failures.

---

_Verified: 2026-04-12T13:12:01Z_
_Verifier: the agent (gsd-verifier)_

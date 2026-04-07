---
phase: 08-workspace-and-infrastructure
verified: 2026-04-07T04:36:59Z
status: passed
score: 5/6 requirements verified, 1/6 pending Phase 11 traceability step
---

# Phase 08: Workspace and Infrastructure Verification Report

**Phase Goal:** Workspace dependency management is clean, Linux Proton path discovery works end-to-end, and Node type definitions are committed with CI freshness checks.
**Verified:** 2026-04-07T04:36:59Z
**Status:** passed for the Phase 8 Rust/workspace and Proton proof surfaces, with the remaining Node declaration-governance evidence added in the Phase 11 follow-up task.
**Initial verification:** Yes — this is the first authoritative Phase 8 verification artifact.

## Goal Achievement

Phase 8 already shipped the implementation in Plans 08-01 through 08-03. This report is the missing authoritative proof artifact the milestone audit expected. `08-VALIDATION.md` provides the command contract; the Phase 8 summaries are used only as provenance.

### Observable Truths

| # | Truth | Status | Current evidence |
|---|---|---|---|
| SC1 | `winreg` is workspace-owned and inherited by the Windows-gated `classic-path-core` manifest | VERIFIED | `ClassicLib-rs/Cargo.toml` declares `winreg = "0.52"` in `[workspace.dependencies]`; `ClassicLib-rs/business-logic/classic-path-core/Cargo.toml` uses `winreg = { workspace = true }` under `[target.'cfg(windows)'.dependencies]`; `cargo check -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml` is the validation proof from `08-VALIDATION.md` |
| SC2 | `phf` is workspace-owned and inherited by `classic-constants-core` | VERIFIED | `ClassicLib-rs/Cargo.toml` declares `phf = { version = "0.13.1", features = ["macros"] }`; `ClassicLib-rs/business-logic/classic-constants-core/Cargo.toml` uses `phf = { workspace = true }`; `cargo check -p classic-constants-core --manifest-path ClassicLib-rs/Cargo.toml` is the validation proof |
| SC3 | Linux documents-path discovery prefers a valid Fallout 4 Proton docs path before local-share fallback | VERIFIED | `ClassicLib-rs/business-logic/classic-path-core/src/docs_path.rs` routes non-Windows detection through `find_docs_path_linux()` → `find_docs_path_linux_with(...)`, validates `construct_proton_docs_path(...)`, then falls back to `home/.local/share/<relative_path>` |
| SC4 | The Proton integration proof is executable and distinct from the wiring claim | VERIFIED | `ClassicLib-rs/business-logic/classic-path-core/tests/linux_proton_docs_path.rs` covers the Proton-happy-path winner plus both fallback branches and the legacy local-share regression; `cargo test -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml proton -- --nocapture` and `cargo test -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml` are the proof commands |
| SC5 | The `classic-shared-core` `zerovec` workaround is no longer needed and `gui-bridge` remains validated | VERIFIED | `ClassicLib-rs/foundation/classic-shared-core/Cargo.toml` no longer carries the old workaround dependency; the crate keeps `gui-bridge = ["slint", "tokio-util"]`; `docs/api/classic-shared-core.md` documents the post-workaround gui-bridge contract; `cargo test -p classic-shared-core --features gui-bridge --manifest-path ClassicLib-rs/Cargo.toml` is the focused proof command |
| SC6 | Node declaration freshness/runtime governance is recorded as one evidence bundle | PENDING IN TASK 2 | Phase 8 Plan 03 summary, `package.json`, `.gitignore`, `index.d.ts`, freshness script, and `ci-typescript.yml` will be promoted into this report in the Phase 11 follow-up task so `INFRA-05` is covered with direct evidence instead of summary-only provenance |

## Required Artifacts

| Artifact | Role | Status | Evidence |
|---|---|---|---|
| `.planning/phases/08-workspace-and-infrastructure/08-VALIDATION.md` | Phase 8 command source of truth | USED | Contains the exact command map for `08-01-01` through `08-03-02` |
| `.planning/phases/08-workspace-and-infrastructure/08-01-SUMMARY.md` | Provenance for workspace dependency and gui-bridge cleanup delivery | CROSS-CHECKED | Confirms the plan shipped `INFRA-01`, `INFRA-02`, and `INFRA-04`, but is not treated as proof by itself |
| `.planning/phases/08-workspace-and-infrastructure/08-02-SUMMARY.md` | Provenance for Proton wiring and integration-test delivery | CROSS-CHECKED | Confirms the plan shipped `INFRA-03` and `TEST-03`, but is not treated as proof by itself |
| `ClassicLib-rs/Cargo.toml` | Workspace dependency ownership for `winreg` and `phf` | VERIFIED | `[workspace.dependencies]` now owns both declarations |
| `ClassicLib-rs/business-logic/classic-path-core/Cargo.toml` | Windows-gated `winreg` inheritance proof | VERIFIED | `winreg = { workspace = true }` under the Windows-only dependency block |
| `ClassicLib-rs/business-logic/classic-constants-core/Cargo.toml` | `phf` inheritance proof | VERIFIED | `phf = { workspace = true }` |
| `ClassicLib-rs/foundation/classic-shared-core/Cargo.toml` | `gui-bridge` feature and workaround-removal proof | VERIFIED | Only `slint` and `tokio-util` remain as optional GUI-bridge dependencies; no crate-local `zerovec` workaround remains |
| `ClassicLib-rs/business-logic/classic-path-core/src/docs_path.rs` | Shared Linux docs-path wiring proof | VERIFIED | Non-Windows path discovery validates Proton first, then local-share fallback |
| `ClassicLib-rs/business-logic/classic-path-core/tests/linux_proton_docs_path.rs` | Proton integration proof file | VERIFIED | Covers Proton win path, Steam-lookup failure fallback, invalid Proton fallback, and legacy local-share behavior |
| `docs/api/classic-shared-core.md` | Post-workaround gui-bridge contributor contract | VERIFIED | Documents `async_bridge` as the `gui-bridge`-gated public surface |
| `docs/api/classic-path-core.md` | Contributor-facing docs-path API behavior | VERIFIED | Documents Proton-first Linux docs-path behavior |
| `docs/api/game-setup-workflow.md` | Cross-crate workflow documentation for documents discovery | VERIFIED | Documents the current Linux strategy order with Proton first and local-share second |

## Key Link Verification

| Link | Status | Evidence |
|---|---|---|
| `08-VALIDATION.md` → this report via task rows `08-01-01` / `08-01-02` | VERIFIED | The `cargo check` and `cargo test -p classic-shared-core --features gui-bridge` commands are promoted below into explicit requirement-backed evidence |
| `08-VALIDATION.md` → this report via task rows `08-02-01` / `08-02-02` | VERIFIED | The focused Proton command and the full crate test command are promoted below into separate `INFRA-03` and `TEST-03` rows |
| `classic-path-core/src/docs_path.rs` → this report | VERIFIED | This artifact records the actual `find_docs_path_linux_with`, `construct_proton_docs_path`, and local-share fallback behavior instead of citing only summaries |
| `docs/api/classic-path-core.md` and `docs/api/game-setup-workflow.md` → this report | VERIFIED | Both pages align with the source-backed Proton-first workflow now verified here |

## Behavioral Spot-Checks

| Surface | Command | Expected behavior | Why it matters |
|---|---|---|---|
| Workspace ownership (`INFRA-01`) | `cargo check -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml` | PASS with `classic-path-core` resolving the workspace-owned, Windows-gated `winreg` dependency | Proves the workspace manifest owns `winreg` while the member crate inherits it correctly |
| Workspace ownership (`INFRA-02`) | `cargo check -p classic-constants-core --manifest-path ClassicLib-rs/Cargo.toml` | PASS with `classic-constants-core` resolving the workspace-owned `phf` declaration | Proves the constants crate inherits the shared `phf` contract from the workspace root |
| `gui-bridge` proof (`INFRA-04`) | `cargo test -p classic-shared-core --features gui-bridge --manifest-path ClassicLib-rs/Cargo.toml` | PASS with the current Slint-backed bridge feature and no legacy workaround dependency reintroduced | Confirms the workaround cleanup did not regress the feature the docs promise |
| Proton-focused proof (`INFRA-03`) | `cargo test -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml proton -- --nocapture` | PASS for the injected Proton-first path-selection scenarios | Proves the Linux discovery logic is wired to prefer valid Proton documents paths |
| Full crate proof (`TEST-03`) | `cargo test -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml` | PASS with the Proton integration test file present in the full crate suite | Proves the integration file is not a dead targeted-only test |

## Requirements Coverage

| Requirement | Source plan | Status | Direct proof |
|---|---|---|---|
| INFRA-01 | `08-01-PLAN.md` | SATISFIED | `ClassicLib-rs/Cargo.toml` owns `winreg`; `ClassicLib-rs/business-logic/classic-path-core/Cargo.toml` inherits it under `cfg(windows)`; validated by `cargo check -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml` |
| INFRA-02 | `08-01-PLAN.md` | SATISFIED | `ClassicLib-rs/Cargo.toml` owns `phf`; `ClassicLib-rs/business-logic/classic-constants-core/Cargo.toml` inherits it; validated by `cargo check -p classic-constants-core --manifest-path ClassicLib-rs/Cargo.toml` |
| INFRA-03 | `08-02-PLAN.md` | SATISFIED | `ClassicLib-rs/business-logic/classic-path-core/src/docs_path.rs` calls `find_docs_path_linux_with(...)` and validates `construct_proton_docs_path(...)` before the local-share fallback; focused Proton test command passes |
| INFRA-04 | `08-01-PLAN.md` | SATISFIED | `ClassicLib-rs/foundation/classic-shared-core/Cargo.toml` shows the cleaned `gui-bridge` dependency surface; `docs/api/classic-shared-core.md` documents the current contract; validated by `cargo test -p classic-shared-core --features gui-bridge --manifest-path ClassicLib-rs/Cargo.toml` |
| TEST-03 | `08-02-PLAN.md` | SATISFIED | `ClassicLib-rs/business-logic/classic-path-core/tests/linux_proton_docs_path.rs` provides the mock Proton-prefix integration proof and remains covered by the focused and full crate test commands |

## Anti-Patterns Found

- No new implementation drift was found in the Rust workspace or docs sources reviewed for `INFRA-01` through `INFRA-04` and `TEST-03`.
- The pre-existing anti-pattern was verification-only: Phase 8 had summaries and validation commands, but no authoritative `08-VERIFICATION.md`, which left all six requirements orphaned in the milestone audit.
- This report avoids the known bad pattern of treating summary files as proof. They are used only as provenance.

## Human Verification Required

None. All Phase 8 proof surfaces covered in this task have automated verification commands recorded in `08-VALIDATION.md` and promoted above.

## Gaps Summary

- **Closed:** Missing authoritative Phase 8 verification artifact for workspace dependency ownership, Proton wiring, Proton integration proof, and gui-bridge/workaround cleanup.
- **Remaining for Task 2:** Promote the Phase 8 Node declaration-governance evidence bundle (`INFRA-05`) into this report and then synchronize `.planning/REQUIREMENTS.md` so all six Phase 8 requirements map cleanly to Phase 11 closure.

---

_Verified: 2026-04-07T04:36:59Z_
_Verifier: GPT-5.4 (gsd plan executor)_

---
phase: 2
slug: cxx-bridge-surface-expansion
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-07
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `cargo test` (Rust) + Catch2 3 via `build_cli.ps1 -Test` / `build_gui.ps1 -Test` (C++) + `pytest` for `check_parity_gate.py` |
| **Config file** | `ClassicLib-rs/Cargo.toml` (workspace), `classic-cli/CMakeLists.txt`, `classic-gui/CMakeLists.txt`, `tools/cxx_api_parity/` |
| **Quick run command** | `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml` |
| **Full suite command** | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml && pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test && pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test && python tools/cxx_api_parity/check_parity_gate.py --repo-root .` |
| **Estimated runtime** | Quick: ~30s · Full: ~8–15 min (clean C++ builds dominate) |

---

## Sampling Rate

- **After every task commit:** Run `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml` plus `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` (parity gate must remain at 0 drift)
- **After every plan wave:** Run incremental `build_cli.ps1 -Test` + `build_gui.ps1 -Test` (no `-Clean` unless the wave added a new `build.rs::bridges` file)
- **After every plan that adds a new `src/*.rs` to `build.rs::cxx_build::bridges`:** MANDATORY clean-build pair — `build_cli.ps1 -Clean -Test` AND `build_gui.ps1 -Clean -Test` (per D-10, catches Pitfall 5 header generation order)
- **Before `/gsd:verify-work`:** Full suite must be green, including clean `-Test` on both frontends and `check_parity_gate.py` at 0 drift
- **Max feedback latency:** ~30s for Rust-only loop; clean-build sample is ≤15 min and is taken once per qualifying plan commit

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 (path.rs promotion) | 1 | CXXS-08 | unit + clean-build | `cargo test -p classic-cpp-bridge path::tests` + `build_cli.ps1 -Clean -Test` + `build_gui.ps1 -Clean -Test` + `check_parity_gate.py` | ❌ W0 | ⬜ pending |
| 2-02-01 | 02 (constants.rs) | 1 | CXXS-01 | unit + clean-build | `cargo test -p classic-cpp-bridge constants::tests` + clean-build pair + parity gate | ❌ W0 | ⬜ pending |
| 2-03-01 | 03 (web.rs) | 1 | CXXS-02 | unit + clean-build | `cargo test -p classic-cpp-bridge web::tests` + clean-build pair + parity gate | ❌ W0 | ⬜ pending |
| 2-04-01 | 04 (xse.rs + version_registry.rs split) | 2 | CXXS-06, CXXS-09 | unit + clean-build | `cargo test -p classic-cpp-bridge xse::tests version_registry::tests` + clean-build pair + parity gate | ❌ W0 | ⬜ pending |
| 2-05-01 | 05 (scangame widening — BA2/INI/ENB/TOML/Wrye) | 3 | CXXS-04 | unit + incremental build | `cargo test -p classic-cpp-bridge scangame::tests` + `build_cli.ps1 -Test` + parity gate | ❌ W0 | ⬜ pending |
| 2-06-01 | 06 (scangame widening — integrity/setup/crashgen orchestrator) | 3 | CXXS-04 | unit + incremental build | `cargo test -p classic-cpp-bridge scangame::tests` + `build_cli.ps1 -Test` + `build_gui.ps1 -Test` + parity gate | ❌ W0 | ⬜ pending |
| 2-07-01 | 07 (config suspect-rule + database typed results) | 3 | CXXS-05, CXXS-07 | unit + incremental build | `cargo test -p classic-cpp-bridge config::tests database::tests` + `build_cli.ps1 -Test` + parity gate | ❌ W0 | ⬜ pending |
| 2-08-01 | 08 (scanner FCX issues + frontend call-site migration + final baseline) | 4 | CXXS-03, CXXS-10 | unit + clean-build + parity gate | `cargo test -p classic-cpp-bridge scanner::tests` + `build_cli.ps1 -Clean -Test` + `build_gui.ps1 -Clean -Test` + `check_parity_gate.py` at 0 drift | ❌ W0 | ⬜ pending |

*Per-plan task rows will be expanded by the planner during plan file emission. Rows above capture the minimum one test-anchor per plan.*

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs` — add `#[cfg(test)] mod tests` block (file exists; tests absent until Plan 01)
- [ ] `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs` — NEW file, must be created with a `#[cfg(test)] mod tests` block
- [ ] `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs` — NEW file, must be created with a `#[cfg(test)] mod tests` block
- [ ] `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs` — NEW file, must be created with a `#[cfg(test)] mod tests` block using `serial_test::serial` where XSE detection touches global state
- [ ] `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/version_registry.rs` — NEW file, must be created with a `#[cfg(test)] mod tests` block
- [ ] `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` — expand existing tests module with per-domain coverage (BA2, INI, ENB, TOML, Wrye, integrity, setup orchestrator, crashgen orchestrator)
- [ ] `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs` — add typed-result test coverage
- [ ] `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs` — add suspect-rule subset test coverage
- [ ] `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` — add FCX issues getter test coverage
- [ ] `docs/implementation/cxx_api_parity/baseline/parity_contract.json` — refreshed per plan via `check_parity_gate.py --update-baseline` (Phase 1 produced the initial baseline)

*Framework install: none — `cargo test`, MSVC Catch2 toolchain, and `pytest` for `check_parity_gate.py` all already exist in the repo.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| C++ shared-enum exhaustiveness across `classic-cli` / `classic-gui` call sites | CXXS-04, CXXS-06, CXXS-09 | `-Wswitch`-style exhaustiveness is a compiler warning, not a unit test; requires a clean MSVC build to surface | `build_cli.ps1 -Clean -Test` and `build_gui.ps1 -Clean -Test` must succeed with no `C4062` or unhandled-enum warnings after each shared-enum addition (constants, scangame severities, ModSite variants) |
| CXX header generation order (Pitfall 5) | CXXS-01..CXXS-10 | Incremental MSVC builds can hide "incomplete type" errors that only appear on clean builds | Run the mandatory `-Clean -Test` pair after every plan that adds a new file to `build.rs::cxx_build::bridges` |
| `classic::constants::*` / `classic::web::*` / `classic::xse::*` / `classic::version_registry::*` namespaces link cleanly in frontends | CXXS-01, CXXS-02, CXXS-06, CXXS-09 | New namespaces require the CMake Corrosion integration to pick up the refreshed static library before C++ code can include the generated headers | Delete `classic-cli/build*` and `classic-gui/build*` directories (or `-Clean`), re-run the PowerShell wrappers, and confirm the generated `.h` files appear in `include/classic_cxx_bridge/` |
| D-11 consumer migration (at least one production caller per new bridge fn) | CXXS-10 | Static analysis can prove bridge fns *exist*; only compile+link of the migrated C++ call sites proves they are *used* | After each migration commit, inspect `classic-cli/` / `classic-gui/` diff for the removed hand-rolled path and confirm the matching `build_*_Test` run is green |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify (enforced because every plan commits with `cargo test` + `check_parity_gate.py`)
- [ ] Wave 0 covers all MISSING references (new bridge files + widened test modules enumerated above)
- [ ] No watch-mode flags (`-Test` wrappers run to completion, never watch mode)
- [ ] Feedback latency < 30s for Rust loop; ≤15 min for the mandatory clean-build sample on qualifying plans
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

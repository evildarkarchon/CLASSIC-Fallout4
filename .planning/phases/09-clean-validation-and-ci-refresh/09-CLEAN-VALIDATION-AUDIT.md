# Phase 9 Clean Validation Audit

## Targeted Clean Inventory

| Surface | Path | Phase 9 action | Why it is in scope |
|---------|------|----------------|--------------------|
| Legacy Cargo output | `ClassicLib-rs/target` | Quarantine to `ClassicLib-rs/target.phase9-backup` before proof, then restore after the run | Detect fresh writes into the legacy tree without destroying a contributor's pre-existing local output |
| Live Cargo output | repo-root `target` | Remove before proof | Force Cargo to prove the repo-root workspace from a fresh output directory |
| Python virtualenv | `python-bindings/.venv` | Remove before proof | Prevent stale interpreter state from masking repo-root Python workflow issues |
| Node dependency tree | `node-bindings/classic-node/node_modules` | Remove before proof | Force package-local dependency recreation for the TypeScript proof surface |
| Node build output | `node-bindings/classic-node/dist` | Remove before proof | Ensure TypeScript build output is recreated from current sources |
| Built Node addon outputs | built `.node` outputs under `node-bindings/classic-node` | Delete before proof | Catch stale native addon binaries that could shadow a broken rebuild |
| Python parity working artifacts | `python-bindings/parity-artifacts` | Clear before proof | Regenerate only the CI-owned Python proof artifacts |
| Node parity working artifacts | `node-bindings/classic-node/parity-artifacts` | Clear before proof | Regenerate only the CI-owned Node proof artifacts |
| CXX parity working artifacts | `cpp-bindings/classic-cpp-bridge/parity-artifacts` | Clear before proof | Regenerate only the CI-owned CXX proof artifacts |

## Workflow Contract Matrix

| Surface | Repo-root contract | Cache, hash, and diagnostics contract |
|---------|--------------------|---------------------------------------|
| `.github/workflows/ci-rust.yml` | Repo-root Cargo commands stay authoritative | Cache path is `target`; Rust source hash inputs use repo-root globs under `foundation/**/*.rs`, `business-logic/**/*.rs`, `cpp-bindings/**/*.rs`, `node-bindings/**/*.rs`, `python-bindings/**/*.rs`, and `ui-applications/**/*.rs`; legacy `ClassicLib-rs/**/*.rs` is forbidden |
| `.github/workflows/ci-python-bindings.yml` | Runs `python validate_stubs.py --rust-dir .` and uses repo-root binding paths | Uses `python-bindings/.venv`, cache path `target`, diagnostics path `python-bindings/parity-artifacts/`, and JSON output `python-bindings/parity-artifacts/stub_validation_report.json` |
| `.github/workflows/ci-typescript.yml` | Runs from `working-directory: node-bindings/classic-node` | Uses cache path `target` and diagnostics path `node-bindings/classic-node/parity-artifacts/`; legacy `ClassicLib-rs/node-bindings/classic-node` is forbidden |
| `.github/workflows/ci-cpp.yml` | Keeps wrapper-owned native commands rooted at repo root | Uses cache path `target`, diagnostics path `cpp-bindings/classic-cpp-bridge/parity-artifacts/`, and native failure outputs under `classic-cli/` and `classic-gui/` |
| `.github/workflows/benchmarks.yml` | Uses repo-root Cargo workspace commands | Uses repo-root Rust source hash inputs and keeps benchmark cache/proof data under `target/criterion/baseline` only |

## CI-Owned Artifact Scope

Phase 9 may refresh only the path-bearing artifacts directly owned by the required proof surfaces:

- `python-bindings/parity-artifacts/`
- `node-bindings/classic-node/parity-artifacts/`
- checked-in baseline contracts under `docs/implementation/**/baseline/`, but only if the proof commands actually regenerate path-bearing metadata there

Anything outside those directories is out of scope for this phase unless a required proof surface demonstrates it is stale.

## Refreshed Artifact Results

Live proof run completed on 2026-04-13.

- Tracked diffs were produced under `python-bindings/parity-artifacts/`:
  - `parity_diff_report.json`
  - `parity_diff_report.md`
  - `python_api_surface.json`
  - `runtime_coverage_summary.json`
  - `runtime_coverage_summary.md`
  - `rust_api_surface.json`
- The proof log also reported fresh Python proof outputs at `python-bindings/parity-artifacts/tier1_gate_report.md` and `python-bindings/parity-artifacts/stub_validation_report.json`.
- The proof reran `node-bindings/classic-node/parity-artifacts/` and `cpp-bindings/classic-cpp-bridge/parity-artifacts/` without producing tracked diffs in the worktree.
- The proof reran with no tracked baseline diffs under `docs/implementation/python_api_parity/baseline/`, `docs/implementation/node_api_parity/baseline/`, or `docs/implementation/cxx_api_parity/baseline/`.
- The required GUI package proof produced `classic-gui/build/packages/CLASSIC-1.0.0-win64.zip` and signed `classic-gui/install/CLASSIC.exe`.

Record only the files that actually changed. If a Phase 9-owned artifact directory stays byte-identical after rerun, note that explicitly instead of rewriting unrelated files.

## GUI Package Proof Surface

The required package-sensitive proof surface is `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Package`.

The final clean proof runs these commands in order:

1. `cargo locate-project --workspace --message-format plain`
2. `cargo metadata --format-version 1 --no-deps`
3. `python tools/python_api_parity/check_parity_gate.py --repo-root .`
4. `python validate_stubs.py --rust-dir . --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings`
5. `bun install` from `node-bindings/classic-node`
6. `bun run build` from `node-bindings/classic-node`
7. `bun run parity:gate` from `node-bindings/classic-node`
8. `bun run dts:freshness:check` from `node-bindings/classic-node`
9. `python tools/cxx_api_parity/check_parity_gate.py --repo-root .`
10. `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Package`
11. `python -m pytest tests/planning/test_phase09_validation.py -q`

Phase 9 must not downgrade the package proof to `-Test` or build-only validation.

## Legacy Residue Failure Rules

Any new generated output under `ClassicLib-rs/` is a Phase 9 failure.

### Post-proof legacy residue check

The targeted clean harness must capture `ClassicLib-rs/` generated-state before proof and compare it to the post-proof state before any quarantined backup is restored.

The failure rule covers recreated legacy outputs such as:

- `ClassicLib-rs/target`
- `ClassicLib-rs/**/.venv`
- `ClassicLib-rs/**/node_modules`
- `ClassicLib-rs/**/dist`
- `ClassicLib-rs/**/*.node`
- `ClassicLib-rs/**/parity-artifacts`
- package or install outputs recreated anywhere under `ClassicLib-rs/`

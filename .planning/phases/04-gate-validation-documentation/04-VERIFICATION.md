# Phase 4 Verification Draft

## Task 1 Command Evidence

- [x] `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` — exit 0
- [x] `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test` — exit 0
- [x] `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test` — exit 0
- [x] `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` — exit 0
- [x] `python tools/python_api_parity/check_parity_gate.py --repo-root .` — exit 0
- [x] `bun run parity:gate` (from `ClassicLib-rs/node-bindings/classic-node`) — exit 0

## Notes

- Native wrapper validation ran only through the repo PowerShell wrappers required by `AGENTS.md`.
- Final plain parity reruns stayed green after native validation.

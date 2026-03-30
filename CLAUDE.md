# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md
@docs/api/README.md

## Build Commands

### Rust (from repo root)

```
cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml
cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml
cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml -- --check
cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings
```

### C++ (always use PowerShell wrappers, never raw ctest)

```
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 [-Clean] [-Test] [-Install] [-Package] [-Debug]
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 [-Clean] [-Test] [-Install] [-Package] [-Debug]
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -CTestName "test name"
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -IntegrationTestName help,version
```

### Node bindings (from ClassicLib-rs/node-bindings/classic-node)

```
bun install && bun run build
bun run parity:gate:local
bun run test:bun && bun run test:node
```

### Python bindings

```
./rebuild_rust.ps1 -Target python [-Crates <names>]
python tools/python_api_parity/check_parity_gate.py --repo-root .
uv run pytest ClassicLib-rs/python-bindings/tests -q
```

### Formatting (pre-commit minimum)

```
cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml
uv run ruff format .
```

## Commit Conventions

Prefix commits: `Feat:`, `Fix:`, `Docs:`, `Refactor:`, `Chore:`, `Update:`. Capitalize the first word after the prefix.

## Key Gotchas

- `VCPKG_ROOT` env var must be set for C++ builds.
- From Git Bash, source `tools/use_msvc_from_git_bash.sh` before Rust or MSVC C++ commands so Git's `link.exe` doesn't shadow the VS linker.
- Python venv for bindings lives at `ClassicLib-rs/python-bindings/.venv`, not repo root.
- `sample_logs/FO4/` is a git submodule with test fixtures.
- Trailing whitespace is intentionally NOT trimmed in markdown files.
- Never output to `nul` on Windows — it creates an undeletable file on system drives.

## Subdirectory CLAUDE.md

For module-specific instructions (e.g., `ClassicLib-rs/CLAUDE.md`, `classic-cli/CLAUDE.md`), add a CLAUDE.md in that directory. It loads automatically when Claude works there.

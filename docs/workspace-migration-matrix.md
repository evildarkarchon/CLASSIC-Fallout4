# Workspace Migration Matrix

Use this page as the single source of truth for translating legacy `ClassicLib-rs/...` workspace-root guidance into the live repo-root contract.

## Quick Rules

- Run Cargo, parity, and wrapper workflows from the repository root unless a row below says to change directories first.
- Use repo-root layer paths: `foundation/`, `business-logic/`, `cpp-bindings/classic-cpp-bridge/`, and `ui-applications/classic-tui/`.
- The Python and Node binding trees, their commands, and their artifacts have no live translation: they were deleted when the bindings retired (ADR-0010, in [`docs/adr/`](adr/)), and an annotated `archive/` tag on the commit before that change preserves the last tree.
- **D-07:** `ClassicLib-rs` may appear only inside clearly labeled migration or historical notes. Never use it as live workspace-root guidance.

## Command Translation

| Legacy workflow | Repo-root workflow | Notes |
| --- | --- | --- |
| `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` | `cargo build --workspace` | Run from repo root. |
| `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` | `cargo test --workspace` | Run from repo root. |
| `cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml -- --check` | `cargo fmt --all -- --check` | Repo root is the only live workspace shell. |
| `cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` | `cargo clippy --workspace --all-targets --all-features -- -D warnings` | No legacy manifest-path shim remains. |
| `python tools/cxx_api_parity/check_parity_gate.py --repo-root ClassicLib-rs` | `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` | The repo root is now the bridge parity gate root. |

## Path-Root Translation

| Legacy path root | Live path root | Notes |
| --- | --- | --- |
| `ClassicLib-rs/foundation/` | `foundation/` | Shared runtime and utility crates. |
| `ClassicLib-rs/business-logic/` | `business-logic/` | Rust business logic crates. |
| `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/` | `cpp-bindings/classic-cpp-bridge/` | Active C++ bridge surface. |
| `ClassicLib-rs/ui-applications/classic-tui/` | `ui-applications/classic-tui/` | Active Rust TUI application. |
| `ClassicLib-rs/target/` | `target/` | Cargo outputs now live at repo root. |

## Artifact And Report Translation

| Legacy artifact/report location | Live artifact/report location | Owned by |
| --- | --- | --- |
| `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/parity-artifacts/` | `cpp-bindings/classic-cpp-bridge/parity-artifacts/` | CXX parity outputs |
| `ClassicLib-rs/target/criterion/baseline/` | `target/criterion/baseline/` | Criterion benchmark baselines |
| `ClassicLib-rs/docs/implementation/cxx_api_parity/baseline/` | `docs/implementation/cxx_api_parity/baseline/` | Checked-in CXX parity contract and summaries |

## Historical-Note Rules

Use these labels whenever older material still needs to mention the retired path root:

- **Migration note:** explain the old path or command and link back to this matrix.
- **Historical note:** preserve context for shipped milestones or archived guidance.

Anything not explicitly labeled as a migration or historical note must teach the live repo-root paths and commands.

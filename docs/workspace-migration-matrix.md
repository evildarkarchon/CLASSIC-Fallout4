# Workspace Migration Matrix

Use this page as the single source of truth for translating legacy `ClassicLib-rs/...` workspace-root guidance into the live repo-root contract.

## Quick Rules

- Run Cargo, parity, and wrapper workflows from the repository root unless a row below says to change directories first.
- Use repo-root layer paths: `foundation/`, `business-logic/`, `cpp-bindings/classic-cpp-bridge/`, `node-bindings/classic-node/`, `python-bindings/`, and `ui-applications/classic-tui/`.
- **D-07:** `ClassicLib-rs` may appear only inside clearly labeled migration or historical notes. Never use it as live workspace-root guidance.

## Command Translation

| Legacy workflow | Repo-root workflow | Notes |
| --- | --- | --- |
| `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` | `cargo build --workspace` | Run from repo root. |
| `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` | `cargo test --workspace` | Run from repo root. |
| `cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml -- --check` | `cargo fmt --all -- --check` | Repo root is the only live workspace shell. |
| `cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` | `cargo clippy --workspace --all-targets --all-features -- -D warnings` | No legacy manifest-path shim remains. |
| `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate` | `cd node-bindings/classic-node && bun run parity:gate` | Node parity gate still runs from the package directory; only the path root changed. |
| `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:update-baseline` | `cd node-bindings/classic-node && bun run parity:gate:update-baseline` | Use only when intentional source-backed drift requires a baseline refresh. |
| `python tools/python_api_parity/check_parity_gate.py --repo-root ClassicLib-rs` | `python tools/python_api_parity/check_parity_gate.py --repo-root .` | The repo root is now the parity gate root. |
| `python tools/cxx_api_parity/check_parity_gate.py --repo-root ClassicLib-rs` | `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` | The repo root is now the bridge parity gate root. |
| `python validate_stubs.py --rust-dir ClassicLib-rs` | `python validate_stubs.py --rust-dir .` | Stub validation now targets the repo-root workspace. |
| `uv venv ClassicLib-rs/python-bindings/.venv` | `uv sync --project python-bindings --inexact` | `python-bindings/` is now a uv-managed project (`pyproject.toml` + `uv.lock`). `uv sync` creates the venv and installs the locked tooling set in one step. `--inexact` is load-bearing: it keeps uv from pruning the maturin-built `classic-*-py` wheels. |
| `uv pip install --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe -r ClassicLib-rs/python-bindings/requirements-ci.txt` | `uv sync --project python-bindings --inexact` (add `--group drift-guards` for `ruamel.yaml`) | `requirements-ci.txt` is retired. The tooling set (`maturin`, `pytest`, optional `ruamel.yaml`) lives in `python-bindings/pyproject.toml`. Use `--locked` in CI to fail on lockfile drift. |
| `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests -q` | `uv run --project python-bindings python -m pytest python-bindings/tests -q` | `--project <dir>` discovers the uv project and its `.venv` without changing CWD, so `python-bindings/tests` stays repo-root-relative. Keep the `python -m pytest` form: `classic_config` anchors settings to `sys.argv[0]`'s parent, and the `pytest.exe` console-script entrypoint breaks that shape. |

## Path-Root Translation

| Legacy path root | Live path root | Notes |
| --- | --- | --- |
| `ClassicLib-rs/foundation/` | `foundation/` | Shared runtime and utility crates. |
| `ClassicLib-rs/business-logic/` | `business-logic/` | Rust business logic crates. |
| `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/` | `cpp-bindings/classic-cpp-bridge/` | Active C++ bridge surface. |
| `ClassicLib-rs/node-bindings/classic-node/` | `node-bindings/classic-node/` | Active Node/Bun package. |
| `ClassicLib-rs/python-bindings/` | `python-bindings/` | Active Python binding tree. |
| `ClassicLib-rs/ui-applications/classic-tui/` | `ui-applications/classic-tui/` | Active Rust TUI application. |
| `ClassicLib-rs/target/` | `target/` | Cargo outputs now live at repo root. |
| `ClassicLib-rs/python-bindings/.venv/` | `python-bindings/.venv/` | Binding-local Python virtualenv stays local to the binding tree. |

## Artifact And Report Translation

| Legacy artifact/report location | Live artifact/report location | Owned by |
| --- | --- | --- |
| `ClassicLib-rs/node-bindings/classic-node/parity-artifacts/` | `node-bindings/classic-node/parity-artifacts/` | Node parity/runtime outputs |
| `ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json` | `python-bindings/parity-artifacts/stub_validation_report.json` | Python stub validation report |
| `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/parity-artifacts/` | `cpp-bindings/classic-cpp-bridge/parity-artifacts/` | CXX parity outputs |
| `ClassicLib-rs/target/criterion/baseline/` | `target/criterion/baseline/` | Criterion benchmark baselines |
| `ClassicLib-rs/docs/implementation/node_api_parity/baseline/` | `docs/implementation/node_api_parity/baseline/` | Checked-in Node parity contract and summaries |
| `ClassicLib-rs/docs/implementation/python_api_parity/baseline/` | `docs/implementation/python_api_parity/baseline/` | Checked-in Python parity contract and summaries |
| `ClassicLib-rs/docs/implementation/cxx_api_parity/baseline/` | `docs/implementation/cxx_api_parity/baseline/` | Checked-in CXX parity contract and summaries |

## Historical-Note Rules

Use these labels whenever older material still needs to mention the retired path root:

- **Migration note:** explain the old path or command and link back to this matrix.
- **Historical note:** preserve context for shipped milestones or archived guidance.

Anything not explicitly labeled as a migration or historical note must teach the live repo-root paths and commands.

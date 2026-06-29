## 1. classic-message-core: dedicated logger initialization

- [x] 1.1 Add `env_logger = { workspace = true }` to `business-logic/classic-message-core/Cargo.toml` `[dependencies]`
- [x] 1.2 Implement `logging::init()` in `src/logging.rs`: install `env_logger` for the `"CLASSIC"` target with `Env::default().default_filter_or("info")`, idempotent via `try_init()`
- [x] 1.3 Implement `logging::init_with_filter(filter: &str)`: install `env_logger` with the provided filter directive, idempotent
- [x] 1.4 Re-export `init` and `init_with_filter` from `src/lib.rs` root alongside the existing `logging` re-exports
- [x] 1.5 Add regression tests in `src/logging_tests.rs` asserting idempotent re-init (no panic, no replace) and that `Logger::new()` / crate import install no global backend

## 2. classic-message-core: remove emoji stripping, preserve UTF-8 formatter

- [x] 2.1 Remove `strip_emoji` from `src/formatter.rs`
- [x] 2.2 Rewrite `format_log_message(content, details)` to return content verbatim, appending `"\nDetails: {details}"` when details are present (no emoji stripping)
- [x] 2.3 Drop `strip_emoji` from the `pub use formatter::{...}` re-export in `src/lib.rs`; keep `format_log_message` exported
- [x] 2.4 Update `src/formatter_tests.rs`: remove `strip_emoji` cases; add UTF-8-preservation cases (emoji preserved in content, details appended verbatim, no-details returns content only)
- [x] 2.5 Update crate-level doc examples in `src/lib.rs` that reference `strip_emoji` or emoji-stripped output

## 3. C++ bridge: delegate initialization to core

- [x] 3.1 Rewrite `init_logging()` in `cpp-bindings/classic-cpp-bridge/src/message.rs` to call `classic_message_core::logging::init()`; remove the bridge-local `env_logger::Builder`
- [x] 3.2 Remove `env_logger = { workspace = true }` from `cpp-bindings/classic-cpp-bridge/Cargo.toml`
- [x] 3.3 Update `cpp-bindings/classic-cpp-bridge/src/message_tests.rs` to assert delegation (core init is called, no local builder)

## 4. Python binding: remove strip_emoji, emoji-preserving format

- [x] 4.1 Remove the `strip_emoji` `#[pyfunction]` and its `wrap_pyfunction!(strip_emoji, m)?` registration in `python-bindings/classic-message-py/src/lib.rs`
- [x] 4.2 Keep `format_log_message` delegating to the (now emoji-preserving) `core::format_log_message`; update its docstring example
- [x] 4.3 Update `python-bindings/classic-message-py/classic_message.pyi` to drop `strip_emoji` and reflect emoji-preserving `format_log_message`
- [x] 4.4 Update `python-bindings/tests/test_promoted_residuals_smoke.py`: remove/replace `test_message_strip_emoji_free_function`; add a UTF-8-preservation assertion for `format_log_message`

## 5. Node binding: remove stripEmojiText, emoji-preserving formatMessage

- [x] 5.1 Remove `strip_emoji_text` / `stripEmojiText` from `node-bindings/classic-node/src/message.rs`
- [x] 5.2 Keep `formatMessage` delegating to emoji-preserving `format_log_message`; update its doc comment
- [x] 5.3 Update `node-bindings/classic-node/index.d.ts` to drop `stripEmojiText` and reflect emoji-preserving `formatMessage`
- [x] 5.4 Update `node-bindings/classic-node/__test__/message.spec.ts`: remove emoji-stripping cases and add UTF-8-preservation assertions for `formatMessage`

## 6. Parity baselines and artifacts refresh

- [x] 6.1 Regenerate CXX baseline: `python tools/cxx_api_parity/generate_baseline.py --repo-root .`
- [x] 6.2 Regenerate Python baseline: `python tools/python_api_parity/generate_baseline.py --repo-root .`
- [x] 6.3 Regenerate Node baseline: `cd node-bindings/classic-node && bun run parity:gate:update-baseline`
- [x] 6.4 Refresh tracked `docs/implementation/*/baseline/*` parity artifacts if regenerated separately from the baselines
- [x] 6.5 Run CXX gate and confirm zero drift: `python tools/cxx_api_parity/check_parity_gate.py --repo-root .`
- [x] 6.6 Run Python gate and confirm zero drift: `python tools/python_api_parity/check_parity_gate.py --repo-root .`
- [x] 6.7 Run Node gate and confirm zero drift: `cd node-bindings/classic-node && bun run parity:gate`

## 7. Docs update

- [x] 7.1 Update `docs/api/classic-message-core.md`: reverse the "Do not use this crate for owning a log backend" guidance; document `logging::init()` / `init_with_filter()`; document emoji-preserving `format_log_message`; remove `strip_emoji` from the API map and usage example; update the contributor note about backend installation
- [x] 7.2 Review `docs/api/binding-parity-overview.md` and `docs/api/node-python-contract-map.md` for `strip_emoji` / `stripEmojiText` references and update if present

## 8. Verification gates

- [x] 8.1 Build the core crate and workspace (`cargo build`; set `$env:PYO3_PYTHON` to `python-bindings\.venv\Scripts\python.exe` before any pyo3-touching cargo command)
- [x] 8.2 Run core unit tests: `cargo test -p classic-message-core` (sibling `_tests.rs` modules)
- [x] 8.3 C++ tests via `classic-cli/build_cli.ps1 -Test` (never invoke `ctest` or test binaries directly)
- [x] 8.4 Python binding tests: `uv sync --project python-bindings --inexact` → `./python-bindings/rebuild_rust.ps1 -Target python` → set `$env:PYO3_PYTHON` → `uv run --project python-bindings python -m pytest python-bindings/tests -q`
- [x] 8.5 Node follow-up checks: `bun run test:bun`, `bun run test:node`, `bun run dts:freshness:check`
- [x] 8.6 Umbrella compliance: `python tools/binding_compliance/check_compliance.py --repo-root . --profile ci`

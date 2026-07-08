## Why

`classic-message-core` is already CLASSIC's shared message DTO, routing-enum, and log-formatting layer, yet it deliberately does not own a log backend (its own API guide says "Do not use this crate for owning a log backend"). Logger initialization is instead scattered across consumers: `env_logger` in the C++ bridge, `tracing_subscriber` in the TUI, and no Rust backend at all in the Python/Node embeddings. At the same time the crate's formatter carries a hand-rolled `strip_emoji` Unicode-range filter meant to dodge Windows console encoding issues — a fragile, incomplete workaround that mangles legitimate symbols and duplicates work a real logging backend already handles. A robust logging crate writes UTF-8 and renders emoji/symbols natively, so the stripping is obsolete. This change makes `classic-message-core` the dedicated logging router/formatter: it owns logger initialization via an established backend (`env_logger`, already a workspace dependency and already used by the C++ bridge), removes the obsolete emoji stripping, and positions the crate as the unified logger the rest of the codebase can adopt over time.

## What Changes

- **BREAKING**: Remove `strip_emoji` from `classic-message-core`'s public API (root re-export and the `formatter` module).
- **BREAKING**: `format_log_message(content, details)` no longer strips emojis. It returns the content verbatim, appending `"\nDetails: {details}"` when details are present, and preserves all valid UTF-8 including emoji/symbol characters.
- **BREAKING**: Remove `strip_emoji` from the Python bindings (`classic-message-py`); the bound `format_log_message` preserves UTF-8.
- **BREAKING**: Remove `stripEmojiText` from the Node bindings (`classic-node`); `formatMessage` preserves UTF-8.
- Add `env_logger` as a dependency of `classic-message-core` and expose a dedicated, opt-in, idempotent logger initialization entry point (e.g. `logging::init()` and `logging::init_with_filter(...)`) that installs the `"CLASSIC"`-targeted `env_logger` backend, defaulting to `info` when `RUST_LOG` is unset.
- Migrate the C++ bridge's `init_logging()` to delegate to `classic-message-core`'s init, removing the bridge-local `env_logger::Builder` setup and the bridge's direct `env_logger` dependency.
- Update `docs/api/classic-message-core.md` to reverse the prior "do not own a backend" guidance and document the new dedicated-logger-init capability plus the emoji-preserving formatter behavior.
- Regenerate the CXX, Python, and Node parity baselines/artifacts to reflect the removed and behavior-changed surface symbols.
- Out of scope (long-term follow-up, noted here for direction): migrating the TUI's `tracing_subscriber` and the Python/Node host-logging bridges onto the unified core logger.

## Capabilities

### New Capabilities
- `message-logger-router`: `classic-message-core` acting as the dedicated logging router/formatter — it owns opt-in, idempotent `env_logger` initialization for the `"CLASSIC"` target, preserves UTF-8 (no emoji stripping) in its log-text formatter, removes the emoji-stripping public surface, and is the logger-init entry point that consumers (starting with the C++ bridge) delegate to.

### Modified Capabilities
<!-- No existing spec requirement changes. `cross-language-logging-parity` governs severity, event taxonomy, and redaction requirements, none of which are altered here; only the parity baselines/artifacts that track binding surface symbols are refreshed. -->

## Impact

- **Code**: `business-logic/classic-message-core/src/{lib.rs,formatter.rs,logging.rs}` plus sibling `_tests.rs` modules; `cpp-bindings/classic-cpp-bridge/src/message.rs`; `python-bindings/classic-message-py/src/lib.rs` and its `.pyi` stub; `node-bindings/classic-node/src/message.rs` and `index.d.ts`.
- **Tests**: core `formatter_tests.rs` and `logging_tests.rs`; `python-bindings/tests/test_promoted_residuals_smoke.py` (remove/update the `strip_emoji` smoke test); `node-bindings/classic-node/__test__/message.spec.ts` (remove/update the emoji-stripping cases). New core unit tests follow the sibling `_tests.rs` layout required by AGENTS.md rule 10.
- **Dependencies**: add `env_logger = { workspace = true }` to `classic-message-core`; remove `env_logger` from the C++ bridge's direct dependencies once it delegates to core.
- **Public API surface (breaking)**: removal of `strip_emoji` (Rust + Python) and `stripEmojiText` (Node); behavior change to `format_log_message` / `formatMessage` (now emoji-preserving).
- **Docs**: `docs/api/classic-message-core.md` (scope reversal and formatter-behavior update); review `binding-parity-overview.md` and `node-python-contract-map.md` references to the removed symbols.
- **Parity**: regenerate CXX/Python/Node baselines and `docs/implementation/*/baseline/*` artifacts; run the binding compliance suite (`tools/binding_compliance/check_compliance.py --repo-root . --profile ci`) plus the three per-surface parity gates.

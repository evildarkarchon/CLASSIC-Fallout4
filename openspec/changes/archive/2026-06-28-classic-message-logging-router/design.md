## Context

`classic-message-core` (`business-logic/classic-message-core/`) is CLASSIC's shared message DTO, routing-enum, and log-formatting layer. Today it:

- Owns `Message`, `MessageType`, `MessageTarget`, the `Logger` facade over the `log` crate (target `"CLASSIC"`), `ContractEvent` structured logging, and the `redaction` helpers.
- Emits through the `log` facade only (`log::info!`, `log::warn!`, …) and **does not install a backend**. Its API guide explicitly states "Do not use this crate for owning a log backend."
- Carries a hand-rolled `strip_emoji` Unicode-range filter plus `format_log_message`, both built on emoji stripping to dodge Windows console encoding issues.

Logger backend initialization is therefore scattered across consumers:

- `cpp-bindings/classic-cpp-bridge/src/message.rs:84` — `env_logger::Builder::from_env(Env::default().default_filter_or("info")).try_init()`.
- `ui-applications/classic-tui/src/main.rs:106` — `tracing_subscriber::fmt()` (a separate `tracing` stack, not connected to the `log` facade).
- Python (`python-bindings/classic-message-py`) and Node (`node-bindings/classic-node`) — no Rust global logger; they bridge to host logging (Python `logging`, JS console).

`env_logger` is already a workspace dependency (`env_logger = "0.11.11"` in the root `Cargo.toml`) and the only backend actually in use. `strip_emoji` and `format_log_message` have **no internal Rust call sites** — they exist solely as exported binding helpers (Python `strip_emoji` / `format_log_message`, Node `stripEmojiText` / `formatMessage`) and parity contract symbols.

Constraints: AGENTS.md rule 2 (business logic stays in Rust), rule 3 (bindings stay thin wrappers), rule 7 (update `docs/api/` for API/contract changes in the same change), rule 8 (C++ tests via `build_cli.ps1`/`build_gui.ps1 -Test`, never raw `ctest`), rule 9 (Python binding tests via the uv venv + `rebuild_rust.ps1 -Target python` + `python -m pytest`), rule 10 (Rust unit tests in sibling `_tests.rs`), and the one-tier binding parity policy (`docs/api/binding-parity-policy.md`) which requires all three bindings refreshed in the same change.

## Goals / Non-Goals

**Goals:**
- Make `classic-message-core` own a dedicated, opt-in, idempotent logger initialization backed by `env_logger` for the `"CLASSIC"` target.
- Remove the obsolete `strip_emoji` surface (Rust/Python/Node) and make `format_log_message` / `formatMessage` emoji-preserving.
- Migrate the C++ bridge to delegate logger init to the core crate, making core the single Rust logger-init owner (first unified consumer).
- Keep bindings thin (rule 3): binding changes are wrapper removals/delegations, not logic re-implementations.
- Refresh parity baselines/artifacts and `docs/api/classic-message-core.md` in the same change.

**Non-Goals:**
- Migrating the TUI's `tracing_subscriber` onto the core logger (deferred follow-up; may need a `tracing-log` bridge).
- Changing the Python/Node host-logging routing model (they keep host logging authoritative; core init stays opt-in).
- Exposing core's `init()` to host scripts from Python/Node in this change.
- Adding JSON/structured-sink output, async log transport, or a sink registry.
- Altering `MessageType`/`MessageTarget` enums, `ContractEvent` taxonomy, or redaction behavior.

## Decisions

### Decision 1: Backend is `env_logger`, not `tracing`/`fern`/`simplelog`
`Logger` already emits through the `log` facade. `env_logger` is the canonical backend for `log`, is already a workspace dependency, is already used by the C++ bridge, and writes UTF-8 (rendering emoji/symbols natively — the whole reason the stripping can go). It is the minimal, consistent choice.
- *Alternatives considered:* `tracing`/`tracing_subscriber` (used by the TUI) — rejected for this change; it would force migrating the facade across every consumer and a `tracing-log` bridge, expanding scope far beyond removing stripping + centralizing init. `fern` / `simplelog` — rejected; less canonical and have no existing usage in the repo.

### Decision 2: Init lives in `classic-message-core`, not a foundation crate
The crate already owns the `Logger` facade, the `"CLASSIC"` target, and structured contract logging; collocating init keeps one logging module. The user explicitly asked for `classic-message` to be the dedicated logger. Init is opt-in with no construction-time side effects, so pure-logic callers and host-bridged runtimes are unaffected.
- *Alternatives considered:* Put init in a foundation crate (e.g. `classic-shared-core`). Rejected — it would split the logging module across two crates and require core to depend on foundation purely for init, against the user's scoping.

### Decision 3: Init is opt-in and idempotent, never auto-installed
Python/Node embeddings bridge `log::*` to host logging and must keep control of the global Rust logger; auto-install would hijack their routing. `env_logger::Builder::try_init()` swallows the "already initialized" error, making repeated calls safe.
- *Alternatives considered:* Auto-install on first `Logger::new()`. Rejected — a silent global side effect that breaks host-bridged runtimes and surprises pure-logic callers.

### Decision 4: Keep `format_log_message` as an emoji-preserving formatter (do not remove it)
It still has formatting value (appending `"\nDetails: {details}"`) and the bindings expose it; only the obsolete stripping is removed. Keeping it preserves the "formatter" role the user wants and avoids a second unnecessary breaking removal.
- *Alternatives considered:* Remove `format_log_message` entirely. Rejected — it still produces a useful single log line and is part of the binding surface with no internal callers to absorb its behavior.

### Decision 5: C++ bridge drops its direct `env_logger` dependency and delegates
Centralizes init in core (single owner); the bridge's `init_logging()` becomes a one-line call to `classic_message_core::logging::init()` and the bridge no longer constructs its own `env_logger::Builder`. The bridge's `Cargo.toml` removes the direct `env_logger` dependency used for initialization.
- *Alternatives considered:* Keep the bridge's `env_logger` as a fallback. Rejected — it defeats the single-owner goal and risks two `try_init` races producing ambiguous behavior.

### Decision 6: Emoji-stripping removal is a clean breaking change with same-change parity refresh, not a deprecation window
`strip_emoji`/`stripEmojiText` are auxiliary helpers with no internal callers; the one-tier parity policy expects binding surface refresh in the same change. A deprecation shim would keep the obsolete logic alive, contradicting the change's goal.
- *Alternatives considered:* Deprecate first (`#[deprecated]`), remove in a later change. Rejected — prolongs the fragile, incomplete Unicode-range workaround this change eliminates.

## Risks / Trade-offs

- **[Risk] Removing `strip_emoji` breaks downstream Python/Node scripts that import it** → Mitigation: parity gates and the compliance suite fail closed on the removed symbol; baselines are refreshed in the same change; the symbol had no internal callers, so the blast radius is external user scripts only, documented in the API guide update.
- **[Risk] A core-installed `env_logger` in the C++ app captures `log::*` calls from other crates and changes their output destination** → Mitigation: behavior matches the current bridge (it already installs `env_logger`); the `"CLASSIC"` target and `RUST_LOG` filter preserve existing filtering; the default `info` matches the current `default_filter_or("info")`.
- **[Risk] Python/Node embeddings keep no-op Rust `log::*` if they never call `init()`** → Mitigation: unchanged from today (init is opt-in); host bridges keep their routing; the API guide documents that consumers wanting Rust-side stderr logging call `init()`.
- **[Trade-off] Core gains a global-state init function, slightly blurring the "pure business logic" boundary** → accepted because the crate is already the designated logging module and init is opt-in/idempotent with no construction side effects.
- **[Trade-off] The TUI's `tracing_subscriber` stays a separate stack for now** → accepted; unifying it (via a `tracing-log` bridge or facade migration) is an explicit follow-up, out of scope here.

## Migration Plan

Implementation order (each step verifiable before the next):

1. **Core crate** — add `env_logger = { workspace = true }`; implement `logging::init()` / `logging::init_with_filter(&str)`; remove `strip_emoji`; rewrite `format_log_message` to be emoji-preserving; update `lib.rs` re-exports; update sibling `_tests.rs` (`formatter_tests.rs`, `logging_tests.rs`) and add init tests there.
2. **C++ bridge** — `init_logging()` delegates to `classic_message_core::logging::init()`; remove bridge `env_logger` dep; update `message_tests.rs`.
3. **Python binding** — remove `strip_emoji` wrapper + registration; `format_log_message` delegates to the (now emoji-preserving) core fn; update `classic_message.pyi`; update `tests/test_promoted_residuals_smoke.py`.
4. **Node binding** — remove `stripEmojiText`; `formatMessage` delegates to emoji-preserving core fn; update `index.d.ts`; update `__test__/message.spec.ts`.
5. **Parity & docs** — regenerate CXX/Python/Node baselines and `docs/implementation/*/baseline/*` artifacts; run the three per-surface gates; update `docs/api/classic-message-core.md` (reverse the "do not own a backend" guidance, document `init`, document emoji-preserving formatter).

Rollback: all changes are localized and artifact-refresh is reproducible; reverting the commits and re-running the parity generators against the pre-change surface restores baselines. No data or schema migration is involved.

Verification (repo-approved commands): build core + bindings via the Rust workspace; run core unit tests; C++ tests via `classic-cli/build_cli.ps1 -Test`; Python via `uv sync --project python-bindings --inexact` → `./python-bindings/rebuild_rust.ps1 -Target python` → `uv run --project python-bindings python -m pytest python-bindings/tests -q` (set `$env:PYO3_PYTHON` first); Node via `bun run parity:gate`, `bun run test:bun`, `bun run test:node`, `bun run dts:freshness:check`; CXX/Python parity gates via `tools/cxx_api_parity/` and `tools/python_api_parity/`; umbrella via `python tools/binding_compliance/check_compliance.py --repo-root . --profile ci`.

## Open Questions

- **Init surface shape**: `init()` + `init_with_filter(&str)`, or also expose a `Builder` for custom format/write-target? *Lean:* start with `init()` and `init_with_filter(&str)`; expose a builder only if a consumer needs finer control.
- **tracing-log bridge now or later**: install a `tracing-log` adapter in core's `init()` so TUI `tracing` events flow through the same backend immediately, or defer entirely to the follow-up? *Lean:* defer — out of scope and risks changing TUI output today.
- **Expose `init()` to host scripts**: should the Python/Node bindings surface `init()` so a host script can opt into Rust-side stderr logging? *Lean:* not in this change (host routing stays authoritative); revisit if requested.

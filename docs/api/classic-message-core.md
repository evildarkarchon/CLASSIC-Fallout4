# `classic-message-core` API Guide

Contributor-facing API documentation for [`business-logic/classic-message-core/`](../../business-logic/classic-message-core).

Crate metadata:

- Crate: `classic-message-core`
- Description: `Core message routing and formatting for CLASSIC`

This crate is CLASSIC's small shared message model and logging helper layer. It defines the message payload used across bindings, the routing enums that tell callers whether a message is for GUI, CLI, or logs, the formatting helpers used to produce log text, and the opt-in logger initialization entry point for Rust `log` output.

It also owns the structured startup-contract logging helpers now used from bridge and binding layers. That makes this crate part message DTO, part log-level adapter, and part structured-event formatter.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- construct a shared `Message` value with content, severity, routing target, and optional metadata
- decide whether a message should be shown in GUI, CLI, or logs only
- map `MessageType` into Rust `log::Level`
- initialize the shared Rust `env_logger` backend for CLASSIC log output when a process wants Rust-side stderr logging
- preserve valid UTF-8 while formatting content and optional details for log output
- emit structured startup or contract events through a single CLASSIC log target
- reuse message and logging behavior across Rust, C++, Python, and Node layers

Do not use this crate for:

- asynchronous message transport, queues, channels, or subscriber fan-out
- user-facing rich formatting beyond the simple log-text helpers in `formatter.rs`
- domain-specific error propagation; this crate does not expose a crate-specific error type

This crate is intentionally lightweight. It provides common message and logging primitives, while concrete frontends and bindings decide when to display, forward, or persist the resulting text.

---

## Module And API Map

This crate has several internal modules, but most of the contributor-facing API is re-exported from the crate root.

## Internal modules

- `enums` - defines `MessageType` and `MessageTarget`
- `message` - defines the `Message` struct and its builder/setter API
- `formatter` - defines UTF-8-preserving log-text formatting helpers
- `logging` - defines `Logger`, logger initialization, `ContractEvent`, structured-event formatting, and startup contract helpers
- `redaction` - defines redaction helpers used by structured contract logging

## Root-level API

- `Message`
- `MessageType`
- `MessageTarget`
- `format_log_message(content, details)`
- `Logger`
- `init()`
- `init_with_filter(filter)`
- `ContractEvent`
- `format_contract_event(event)`
- `redact_field_value(field_name, value)`
- `redact_contract_fields(fields)`
- `EVENT_STARTUP_BINDING_CONTRACT_VALIDATED`
- `EVENT_STARTUP_BINDING_CONTRACT_FAILED`
- `EVENT_STARTUP_ACCELERATION_STATUS`

Contributor note:

- `logging` is also a public module, so callers may use either `classic_message_core::Logger` or `classic_message_core::logging::Logger`, and either `classic_message_core::init()` or `classic_message_core::logging::init()`
- `enums`, `message`, `formatter`, and `redaction` are private modules with selected root re-exports only

---

## Public API Surface

## `MessageType`

`MessageType` is the shared severity/category enum.

Current variants:

- `Info`
- `Warning`
- `Error`
- `Success`
- `Progress`
- `Debug`
- `Critical`

Important methods:

- `to_log_level() -> log::Level`
- `name() -> &'static str`

Behavior visible in source:

- `Info` and `Success` map to `log::Level::Info`
- `Warning` maps to `log::Level::Warn`
- `Error` and `Critical` map to `log::Level::Error`
- `Debug` and `Progress` map to `log::Level::Debug`
- `name()` returns title-cased names such as `"Info"` and `"Critical"`

Contributor note:

- `MessageType` derives `Serialize` and `Deserialize`, so it is part of the crate's serialization-facing API as well as its Rust API

## `MessageTarget`

`MessageTarget` controls where a message should be shown.

Current variants:

- `All`
- `GuiOnly`
- `CliOnly`
- `LogOnly`
- `Gui`
- `Console`

Important methods:

- `should_display_in_gui() -> bool`
- `should_display_in_cli() -> bool`
- `should_display() -> bool`
- `Default` -> `All`

Behavior visible in source:

- `All` displays in both GUI and CLI
- `GuiOnly` and `Gui` both count as GUI-display targets
- `CliOnly` and `Console` both count as CLI-display targets
- `LogOnly` is the only target for which `should_display()` returns `false`

Contributor note:

- `GuiOnly` and `CliOnly` are documented in source as legacy names, while `Gui` and `Console` are the preferred spellings for new code

## `Message`

`Message` is the main shared payload type.

Stored fields:

- `content: String`
- `msg_type: MessageType`
- `target: MessageTarget`
- `title: Option<String>`
- `details: Option<String>`

Construction and builder methods:

- `Message::new(content, msg_type)` - defaults `target` to `MessageTarget::All`
- `Message::with_target(content, msg_type, target)`
- `with_title(title)`
- `with_details(details)`

Read accessors:

- `content() -> &str`
- `msg_type() -> MessageType`
- `target() -> MessageTarget`
- `title() -> Option<&str>`
- `details() -> Option<&str>`

Mutation methods:

- `set_content(...)`
- `set_msg_type(...)`
- `set_target(...)`
- `set_title(Option<...>)`
- `set_details(Option<...>)`

Behavior visible in source:

- `Message::new(...)` and `Message::with_target(...)` start with no title and no details
- the builder-style methods consume and return `Self`, making them convenient for one-shot construction
- the setter methods allow in-place mutation when a caller needs to reuse a `Message`
- `Message` derives `Serialize` and `Deserialize`, which is important for wrapper crates and boundary types

## `format_log_message(content, details)`

This is the crate's plain log-text formatting helper.

- returns `content` verbatim when no details are present
- appends details verbatim as `"\nDetails: {details}"` when present
- preserves all valid UTF-8, including emoji and symbols, relying on the configured logging backend to render it

Contributor note:

- `Logger::log_message(...)` does not call `format_log_message(...)`; it logs raw `Message` text plus optional title/details formatting. Callers that need the simple details-appending format should opt into `format_log_message(...)` explicitly.

## `ContractEvent`

`ContractEvent` is the public structured-event type used for parity/startup-style logging.

Stored fields:

- `event: String`
- `severity: MessageType`
- `component: String`
- `outcome: String`
- `context: BTreeMap<String, String>`

Important methods:

- `ContractEvent::new(component, event, severity, outcome)`
- `with_context(key, value)`
- `event() -> &str`
- `severity() -> MessageType`
- `component() -> &str`
- `outcome() -> &str`
- `context() -> &BTreeMap<String, String>`

Behavior visible in source:

- context fields are stored in a `BTreeMap`, so formatting order is stable by key
- `with_context(...)` follows the same consuming-builder pattern as `Message`
- event severity is stored as `MessageType`, then converted to lowercase contract severity names during formatting

## `format_contract_event(event)`

`format_contract_event(...)` converts a `ContractEvent` into one stable key=value log line.

Source-visible formatting flow:

1. Start with required fields: `event`, `severity`, `component`, `outcome`.
2. Convert severity into one of `info`, `warning`, `error`, or `debug`.
3. Redact context values through `redact_contract_fields(...)`.
4. Append each redacted context field as `key=value`.
5. Quote values when empty or when they contain spaces, `=`, `"`, or a newline.

Important visible behavior:

- quotes inside quoted values are escaped as `\"`
- context key ordering is stable because both the original and redacted maps are `BTreeMap`
- sensitive values are redacted before formatting, not after string assembly

## `Logger`

`Logger` is the crate's thin adapter over Rust's `log` macros.

Important API:

- `init()`
- `init_with_filter(filter)`
- `Logger::new()`
- `Logger::LOGGER_NAME`
- `name() -> &str`
- `info(msg)`
- `warning(msg)`
- `error(msg)`
- `debug(msg)`
- `trace(msg)`
- `log(level, msg)`
- `log_message(&Message)`
- `log_contract_event(&ContractEvent)`
- `log_startup_binding_contract_validated(...)`
- `log_startup_binding_contract_failed(...)`
- `log_startup_acceleration_status(...)`
- `is_enabled_for(level)`
- `is_info_enabled()`
- `is_debug_enabled()`
- `is_trace_enabled()`
- `Default` -> `Logger::new()`

Behavior visible in source:

- `init()` installs `env_logger` with `RUST_LOG` support and a default `info` filter when the environment is unset
- `init_with_filter(filter)` installs `env_logger` with the supplied filter directive
- both init functions are idempotent via `try_init()` and leave an existing process-wide logger in place
- `Logger::new()` is side-effect free and does not install a global backend
- the logger target is always `"CLASSIC"`
- `Logger` contains no mutable state; it is effectively just a typed wrapper around that target name
- `log_message(...)` builds log text as `"{title}: {content} - {details}"` when title and details are both present
- `log_message(...)` chooses log level from `message.msg_type().to_log_level()`
- startup helper methods build canonical `ContractEvent` values, optionally attach `correlation_id`, then forward through `log_contract_event(...)`

Contributor note:

- this crate owns the shared Rust logger initialization entry point, but initialization remains opt-in. If no backend is initialized by the application or binding layer, log macros may be no-ops.

## Redaction helpers

The root re-exports `redact_field_value(...)` and `redact_contract_fields(...)` even though `redaction` itself is a private module.

Current public behavior:

- secret-like field names such as `api_key`, `token`, `authorization`, or `private_key` become `[REDACTED]`
- path-like field names such as `path`, `file`, `directory`, or `location` become `<path-redacted>`
- some secret markers in values such as `token=` or `password=` also trigger `[REDACTED]`
- non-sensitive values pass through unchanged

These helpers are currently used by `format_contract_event(...)`, but they are also part of the root public API.

---

## Message Routing And Formatting Flow

The source-visible message flow is straightforward:

1. A caller constructs a `Message` with `Message::new(...)` or `Message::with_target(...)`.
2. The caller chooses a severity with `MessageType` and a route with `MessageTarget`.
3. Display code checks `message.target().should_display_in_gui()`, `should_display_in_cli()`, or `should_display()`.
4. Logging code either:
   - logs the `Message` directly through `Logger::log_message(...)`, or
   - converts text through `format_log_message(...)` when the simple details-appending format is required, or
   - builds a `ContractEvent` and emits a structured log line through `Logger::log_contract_event(...)`.
5. Structured-event logging redacts sensitive context fields before output.

There is no built-in dispatcher, sink registry, or event bus in this crate. Routing here means policy helpers on the message model, not a delivery system.

---

## Error Handling Model

This crate does not currently expose a crate-specific error enum or `Result` alias.

Public APIs are intentionally infallible:

- `Message`, `MessageType`, and `MessageTarget` construction is infallible
- formatting helpers return `String`, not `Result<String, _>`
- `Logger` methods return `()`
- redaction helpers return transformed values directly

Contributor implications:

- log delivery failures are delegated to the configured `log` backend rather than surfaced through this crate's API
- invalid or incomplete contract-event semantics are mostly a caller concern; the crate does not validate required context keys beyond the startup convenience helpers it constructs itself
- if future contributors need fallible formatting or sink-specific guarantees, that would be a material public API expansion and should be documented explicitly

---

## Important Dependencies And Related Crates

Important direct dependencies:

- `env_logger` - opt-in global logger backend for Rust `log` output
- `log` - log level type plus log macro integration
- `serde` - serialization derives for `Message`, `MessageType`, and `MessageTarget`

Related CLASSIC crates and consumers:

- [`classic-cpp-bridge`](../../cpp-bindings/classic-cpp-bridge/src/message.rs) - forwards C++ log calls and startup contract diagnostics through `Logger`
- [`classic-node`](../../node-bindings/classic-node/src/message.rs) - exposes `Message`, formatting helpers, and a wrapped logger to JavaScript/TypeScript
- [`classic-node`](../../node-bindings/classic-node/src/logging_contract.rs) - emits Node startup diagnostics through the structured contract helpers
- [`classic-message-py`](../../python-bindings/classic-message-py/src/lib.rs) - wraps `Message`, `MessageType`, and `MessageTarget` for Python
- [`classic-message-py`](../../python-bindings/classic-message-py/src/logging.rs) - wraps `Logger` for Python callers

Source-observed note:

- the crate is shared heavily at ABI boundaries, so changes to enum variants, root re-exports, or message field semantics can cascade into Python, Node, and C++ wrappers even when the Rust surface looks small

---

## Usage Example

This example stays close to the actual root API and current formatting/logging behavior.

```rust
use classic_message_core::{
    ContractEvent, Logger, Message, MessageTarget, MessageType, format_contract_event,
    format_log_message,
};

let message = Message::with_target(
    "Startup complete ✅",
    MessageType::Success,
    MessageTarget::Console,
)
.with_title("CLASSIC")
.with_details("Loaded 12 plugins 🎉");

assert!(message.target().should_display_in_cli());
assert!(!message.target().should_display_in_gui());

let log_text = format_log_message(message.content(), message.details());
assert_eq!(log_text, "Startup complete ✅\nDetails: Loaded 12 plugins 🎉");

let event = ContractEvent::new(
    "integration.startup",
    "classic.startup.binding_contract.validated",
    MessageType::Info,
    "success",
)
.with_context("contract", "startup_all")
.with_context("install_path", r"C:\Users\alice\Documents\My Games\Fallout4");

let structured = format_contract_event(&event);
assert!(structured.contains("event=classic.startup.binding_contract.validated"));
assert!(structured.contains("install_path=<path-redacted>"));

let logger = Logger::new();
classic_message_core::init();
logger.log_message(&message);
logger.log_contract_event(&event);
```

---

## Contributor Notes And Known Limits

- `format_log_message(...)` preserves UTF-8; removed emoji/symbol stripping was a breaking API change across Rust, Python, and Node
- `Logger::new()` and `Message` construction do not install a log backend; call `init()` or `init_with_filter(...)` when a Rust process wants CLASSIC-owned `env_logger` output
- `MessageTarget` still exposes legacy `GuiOnly` and `CliOnly` variants because bindings and older call paths may still depend on them
- the crate has no public error type, validation API, or delivery abstraction beyond the `log` facade
- structured contract-event formatting is string-based; there is no separate JSON/event object output API today
- the public redaction logic is heuristic and token-based, not schema-driven
- the startup helper methods encode current canonical event ids and field names; changing them has cross-binding compatibility impact
- `logging` is a public module, but most other modules stay private behind root re-exports

If you extend this crate, update this document when you change:

- root exports in `src/lib.rs`
- `MessageType` or `MessageTarget` variants and their mapping behavior
- `Message` fields or builder/setter semantics
- contract-event formatting, quoting, or redaction rules
- canonical startup event ids or helper method signatures
- binding-facing serialization assumptions for message payloads

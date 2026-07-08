# Capability: message-logger-router

## Purpose

Define how CLASSIC's message/logging subsystem routes and initializes logging across Rust core and language bindings.

## Requirements

### Requirement: Dedicated logger initialization
`classic-message-core` SHALL provide a public, opt-in logger initialization entry point that installs an established logging backend (`env_logger`) for the `"CLASSIC"` log target, so the crate owns the process-wide Rust logger rather than each consumer installing its own.

#### Scenario: Default initialization installs the backend
- **WHEN** a consumer calls `classic_message_core::logging::init()` with `RUST_LOG` unset
- **THEN** the crate installs `env_logger` for the `"CLASSIC"` target with a default filter of `info`, and subsequent `log::info!`, `log::warn!`, and `log::error!` calls are emitted while `log::debug!` and `log::trace!` calls are suppressed

#### Scenario: Custom filter initialization
- **WHEN** a consumer calls `classic_message_core::logging::init_with_filter(filter)` with a non-empty filter directive
- **THEN** the crate installs `env_logger` using the provided filter directive, overriding the `info` default

#### Scenario: Idempotent re-initialization is safe
- **WHEN** `logging::init()` is called after a global logger is already installed
- **THEN** the call does not panic and does not replace the already-installed logger

### Requirement: Logger initialization is opt-in and side-effect free at construction
`classic-message-core` SHALL NOT auto-install its logger on crate load or as a side effect of `Logger::new()`, so host-bridged runtimes that route through their own logging retain control of the global Rust logger.

#### Scenario: Importing the Python binding does not install a backend
- **WHEN** the `classic_message` Python module is imported and `logging::init()` is never called
- **THEN** `classic_message_core` installs no global Rust logger and the Python-side logging configuration remains authoritative

#### Scenario: Logger construction installs no backend
- **WHEN** `Logger::new()` is constructed
- **THEN** no logger backend is installed as a side effect of construction

### Requirement: Log-text formatter preserves valid UTF-8
`format_log_message(content, details)` SHALL return the content verbatim, appending `"\nDetails: {details}"` when details are present, without removing emoji or symbol characters, relying on the logging backend to render UTF-8.

#### Scenario: Emoji in content is preserved
- **WHEN** `format_log_message("Success! ✅", None)` is called
- **THEN** the returned string still contains `"✅"`

#### Scenario: Details are appended verbatim
- **WHEN** `format_log_message("Done", Some("All tests passed 🎉"))` is called
- **THEN** the returned string equals `"Done\nDetails: All tests passed 🎉"`

#### Scenario: Absent details return content only
- **WHEN** `format_log_message("Hello", None)` is called
- **THEN** the returned string equals `"Hello"`

### Requirement: Emoji-stripping public API is removed
`classic-message-core` SHALL NOT expose an emoji-stripping helper in its public API across Rust, Python, and Node surfaces.

#### Scenario: strip_emoji is absent from the Rust surface
- **WHEN** a consumer references `classic_message_core::strip_emoji`
- **THEN** the symbol is absent from the crate root and from the `formatter` module

#### Scenario: strip_emoji is absent from the Python surface
- **WHEN** the `classic_message` Python module is inspected
- **THEN** it exposes no `strip_emoji` function

#### Scenario: stripEmojiText is absent from the Node surface
- **WHEN** the `classic-node` JavaScript module is inspected
- **THEN** it exposes no `stripEmojiText` function

### Requirement: classic-message-core is the single Rust logger-init owner
`classic-message-core` SHALL be the single owner of Rust global-logger initialization; native consumers that initialize a Rust logging backend SHALL delegate to `classic-message-core`'s init entry point instead of installing their own backend.

#### Scenario: C++ bridge delegates initialization to core
- **WHEN** `classic::message::init_logging()` is invoked from C++
- **THEN** it calls `classic_message_core`'s logger init entry point and does not construct its own `env_logger::Builder`

#### Scenario: C++ bridge no longer declares an env_logger init dependency
- **WHEN** the C++ bridge initializes logging
- **THEN** it relies on `classic_message_core`'s `env_logger` backend rather than a bridge-local `env_logger` dependency used for initialization

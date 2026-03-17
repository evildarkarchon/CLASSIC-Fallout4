# `classic-registry-core` API Guide

Contributor-facing API documentation for [`ClassicLib-rs/business-logic/classic-registry-core/`](../../ClassicLib-rs/business-logic/classic-registry-core).

Crate metadata:

- Crate: `classic-registry-core`
- Description: `Core registry for global singleton management in CLASSIC`

This crate is CLASSIC's small process-wide registry layer. It stores values behind string keys in a single global map so Rust code, bindings, and bridge crates can share singleton-like state without passing every value through every call boundary.

It is intentionally generic: the crate does not define a domain model for most entries. Instead, it exposes a typed key-value store plus a handful of convenience helpers around well-known CLASSIC keys such as the current game, GUI mode, and some Fallout 4 version-related flags.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- register process-wide state under a string key
- retrieve previously-registered values by key and concrete Rust type
- reuse shared well-known keys through `Keys`
- bridge simple registry state across Rust, C++, Python, and Node wrappers
- keep lightweight global state in one place without introducing a new singleton per crate

Do not use this crate for:

- durable configuration storage
- schema validation or typed domain modeling of registry contents
- fine-grained ownership/lifetime management across subsystems
- inferring value types from keys at runtime
- replacing normal function parameters when a dependency can be passed explicitly

This crate is a utility layer, not a source of truth for most business logic. Higher-level crates still own the meaning of the values they put into the registry.

---

## Module And API Map

This crate has two internal modules, but the public API is re-exported from the crate root.

## Internal modules

- `keys` - defines the `Keys` struct with well-known registry key constants
- `registry` - defines the global storage plus all register/get/remove helpers

## Root-level API

- `Keys` - shared string constants for common CLASSIC registry entries
- `register(key, value)` - insert or replace a value
- `get(key) -> Option<V>` - retrieve and clone a value if the key exists and the requested type matches
- `is_registered(key) -> bool` - check key presence only
- `unregister(key) -> bool` - remove one key
- `clear_all()` - wipe the entire registry

## Root-level convenience helpers

- `get_game()` / `set_game(...)`
- `is_gui_mode()`
- `get_yaml_cache<T>()`
- `get_manual_docs_gui<T>()`
- `get_game_path_gui<T>()`
- `get_vr()`
- `get_game_version<T>()`
- `is_version_auto_detected()`
- `get_local_dir()`
- `get_config_suffix()`
- `is_vr_version()`
- `is_xse_valid()`
- `is_enb_present()`
- `get_game_version_string()`

Contributor note:

- there are no public submodules to import from; callers use `classic_registry_core::register`, `classic_registry_core::Keys`, and the other root re-exports directly

---

## Public API Surface

## `Keys`

`Keys` is a zero-sized struct used only as a namespace for well-known `&'static str` keys.

Current public constants include:

- `YAML_CACHE`
- `MANUAL_DOCS_GUI`
- `GAME_PATH_GUI`
- `GAME_PATH`
- `DOCS_PATH`
- `IS_GUI_MODE`
- `OPEN_FILE_FUNC`
- `VR`
- `GAME`
- `GAME_VERSION`
- `VERSION_AUTO_DETECTED`
- `LOCAL_DIR`
- `IS_PRERELEASE`
- `XSE_VALID`
- `XSE_VERSION`
- `ENB_PRESENT`
- `GAME_VERSION_DETECTED`

The crate does not attach type metadata to those keys. `Keys::GAME` is just a string constant; the expected value type is a convention established by callers.

## `register<K, V>(key, value)`

`register` inserts or replaces a value in the global registry.

Bounds:

- `K: Into<String>`
- `V: Any + Send + Sync + 'static`

Behavior visible in source:

- the key is copied into an owned `String`
- the value is stored behind `Arc<dyn Any + Send + Sync>`
- registering the same key again overwrites the previous entry
- there is no separate "insert only if absent" API

## `get<K, V>(key) -> Option<V>`

`get` is the main typed lookup API.

Bounds:

- `K: AsRef<str>`
- `V: Clone + Any + Send + Sync + 'static`

Behavior visible in source:

- returns `Some(cloned_value)` only when both the key exists and the stored type is exactly `V`
- returns `None` for both missing keys and type mismatches
- clones the stored value instead of returning a reference

That last point matters for contributors: consumers cannot tell "missing key" apart from "wrong requested type" through the return value alone.

## `is_registered<K>(key) -> bool`

- checks only whether a key exists
- does not validate the stored type

## `unregister<K>(key) -> bool`

- removes one entry
- returns `true` when something was removed, `false` when the key was absent
- does not return the removed value

## `clear_all()`

- clears the entire global registry
- is heavily used in tests
- affects all users of the crate in the current process, not one subsystem

---

## Registry Lifecycle And Lookup Flow

The registry flow in current source is simple and fully global:

1. A caller picks a string key, usually from `Keys`.
2. The caller stores a `'static` value with `register(...)`.
3. The global `once_cell::sync::Lazy` initializes the underlying `DashMap` on first use.
4. Another caller checks presence with `is_registered(...)` or requests the concrete type with `get::<_, T>(...)`.
5. If the key is removed with `unregister(...)` or all state is wiped with `clear_all()`, later lookups return `None` or default through convenience helpers.

Example using the real root API:

```rust
use classic_registry_core::{Keys, clear_all, get, is_registered, register, unregister};
use std::path::PathBuf;

clear_all();

register(Keys::GAME, "Fallout4".to_string());
register(Keys::LOCAL_DIR, PathBuf::from("C:/Games/Fallout 4"));

assert!(is_registered(Keys::GAME));

let game: Option<String> = get(Keys::GAME);
let local_dir: Option<PathBuf> = get(Keys::LOCAL_DIR);

assert_eq!(game.as_deref(), Some("Fallout4"));
assert!(local_dir.is_some());

assert!(unregister(Keys::GAME));
assert_eq!(get::<_, String>(Keys::GAME), None);
```

Source-visible behavior to keep in mind:

- the registry is not scoped per game, task, thread, or runtime handle
- overwriting a key discards the previous value without a dedicated migration hook
- typed retrieval works only when every writer and reader agrees on the exact stored type

---

## Convenience Helpers And Well-Known Flows

Most of the crate is generic, but a small part of the public API encodes current CLASSIC conventions.

## Game and mode helpers

- `get_game() -> String` reads `Keys::GAME` and defaults to `"Fallout4"`
- `set_game(game_name)` stores the provided game name under `Keys::GAME`
- `is_gui_mode() -> bool` reads `Keys::IS_GUI_MODE` and defaults to `false`
- `get_local_dir() -> PathBuf` reads `Keys::LOCAL_DIR` and falls back to `std::env::current_dir()`, then `.` if that fails

## Generic typed passthrough helpers

- `get_yaml_cache<T>() -> Option<T>` reads `Keys::YAML_CACHE`
- `get_manual_docs_gui<T>() -> Option<T>` reads `Keys::MANUAL_DOCS_GUI`
- `get_game_path_gui<T>() -> Option<T>` reads `Keys::GAME_PATH_GUI`
- `get_game_version<T>() -> Option<T>` reads `Keys::GAME_VERSION`

These helpers do not enforce a specific concrete type themselves; they are convenience wrappers over `get(...)`.

## Fallout 4 version-related helpers

- `is_version_auto_detected() -> bool` reads `Keys::VERSION_AUTO_DETECTED` and defaults to `false`
- `get_game_version_string() -> String` reads `Keys::GAME_VERSION` as `String` and defaults to `"auto"`
- `get_config_suffix() -> String` returns `"VR"` only when `Keys::GAME_VERSION` or legacy `Keys::VR` is stored as the exact string `"VR"`
- `is_vr_version() -> bool` is just `get_config_suffix() == "VR"`
- `get_vr() -> String` reads only the legacy `Keys::VR` key and defaults to `""`

Important limitation from the current implementation:

- `Keys::GAME_VERSION` comments describe storing a `Fallout4Version` enum, but `get_config_suffix()`, `is_vr_version()`, and `get_game_version_string()` only look for a stored `String`
- if a caller stores an enum or some wrapper type under `Keys::GAME_VERSION`, those string-oriented helpers will behave as if no matching string value exists
- `get_vr()`'s doc comment says it can derive VR state from `GAME_VERSION`, but the implementation currently only reads the legacy `Keys::VR` entry

## Small status helpers

- `is_xse_valid() -> bool` reads `Keys::XSE_VALID` and defaults to `false`
- `is_enb_present() -> bool` reads `Keys::ENB_PRESENT` and defaults to `false`

---

## Error Handling Model

This crate does not currently expose a crate-specific error enum or `Result` alias.

Public error behavior is intentionally lightweight:

- `register(...)` is infallible at the API level
- `get(...)` uses `Option<V>` instead of a typed error
- `is_registered(...)`, `unregister(...)`, and `clear_all()` are also infallible
- convenience helpers generally return plain values with defaults instead of surfacing lookup failures

Contributor implications:

- missing keys are usually silent
- type mismatches are also silent and collapse into `None` or a default value
- callers that need diagnostics must add them outside this crate

Source-visible note:

- `Cargo.toml` depends on `thiserror`, but the current public source in `src/` does not define or export an error type yet

---

## Concurrency And Global State Notes

This crate is explicitly process-global and concurrent.

Implementation details visible in `src/registry.rs`:

- storage is a single `static` `once_cell::sync::Lazy<DashMap<String, Arc<dyn Any + Send + Sync>>>`
- initialization is lazy and happens on first registry access
- `DashMap` provides concurrent access without one global mutex around every operation
- values must be `Send + Sync + 'static` to be stored safely
- reads clone the stored value, so retrieved types must implement `Clone`

Contributor cautions:

- this is shared mutable global state across the whole process
- `clear_all()` and key reuse can interfere with parallel tests or unrelated subsystems if used carelessly
- the crate does not provide namespaces, transactions, or scoped cleanup
- storing large or non-cheaply-clonable values can make `get(...)` more expensive than it looks from the API

The tests in this crate and in `classic-cpp-bridge` use `serial_test` specifically because the registry is global process state.

---

## Important Dependencies And Related Crates

Important direct dependencies:

- `dashmap` - concurrent map backing the registry
- `once_cell` - lazy initialization of the global map
- `serde` and `serde_json` - not used for a typed crate API here, but used by some consumers such as Node bindings storing JSON values

Related CLASSIC crates and wrappers:

- [`classic-cpp-bridge`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs) - exposes CXX-friendly string/bool/i32 registry accessors on top of this crate
- [`classic-registry-py`](../../ClassicLib-rs/python-bindings/classic-registry-py/src/lib.rs) - stores Python objects through a wrapper type so Python code can share registry entries
- [`classic-node`](../../ClassicLib-rs/node-bindings/classic-node/src/shared.rs) - uses `serde_json::Value` plus fallbacks to common Rust scalar types when reading registry values from Node
- [`classic-constants-core`](../../ClassicLib-rs/business-logic/classic-constants-core) - documents that `classic-registry-core` stores active Fallout 4 version state, but this registry crate itself remains generic

The collaboration pattern is consistent across those wrappers: each binding layer chooses a concrete storage type that fits its ABI, then uses the same string keys to share process-wide state.

---

## Usage Example

This example stays close to `examples/basic_usage.rs` and the real crate root API.

```rust
use classic_registry_core::{Keys, get, get_game, is_gui_mode, register, set_game};
use std::path::PathBuf;

set_game("Skyrim");
assert_eq!(get_game(), "Skyrim");

register(Keys::IS_GUI_MODE, true);
register(Keys::LOCAL_DIR, PathBuf::from("C:/CLASSIC"));

let gui_mode: Option<bool> = get(Keys::IS_GUI_MODE);
let local_dir: Option<PathBuf> = get(Keys::LOCAL_DIR);

assert_eq!(gui_mode, Some(true));
assert!(is_gui_mode());
assert_eq!(local_dir, Some(PathBuf::from("C:/CLASSIC")));

register("number", 123);
assert_eq!(get::<_, i32>("number"), Some(123));
assert_eq!(get::<_, String>("number"), None);
```

That final pair of assertions captures an important contract: this registry is type-safe at retrieval time, but type mismatches are reported only as `None`.

---

## Contributor Notes And Known Limits

- the public API is entirely crate-root re-exports from `src/lib.rs`; changing those exports changes the contributor-facing API
- `Keys` provides naming conventions only, not enforced schemas
- `get(...)` cannot distinguish missing keys from wrong requested types
- convenience helpers use defaults heavily, so absent state can be masked
- several Fallout 4 version helpers are string-oriented even though comments describe enum-oriented storage under `Keys::GAME_VERSION`
- `get_vr()` still behaves as a legacy helper over `Keys::VR` only
- `clear_all()` is useful for tests but risky in shared process flows
- `thiserror` is declared as a dependency even though no public error type is currently exposed

If you extend this crate, update this document when you change:

- root-level exports in `src/lib.rs`
- the set of well-known keys in `Keys`
- the storage contract for convenience helpers, especially version-related helpers
- the concurrency model or global singleton initialization behavior
- any binding-facing assumptions about stored types for Python, Node, or C++ callers

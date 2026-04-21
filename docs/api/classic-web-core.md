# `classic-web-core` API Guide

Contributor-facing API documentation for [`business-logic/classic-web-core/`](../../business-logic/classic-web-core).

Crate metadata:

- Crate: `classic-web-core`
- Description: `Web utilities for CLASSIC (no PyO3)`

This crate is the small shared web-helper layer for CLASSIC's Rust workspace. It does not perform HTTP requests and it does not own any async runtime behavior. Instead, it provides a narrow set of reusable helpers for validating URLs, building URLs, generating CLASSIC user-agent strings, and mapping supported games to a few mod-site URLs.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- validate contributor- or config-provided URL strings before passing them elsewhere
- extract a host/domain from a parsed HTTP or HTTPS URL
- construct a URL from a trusted base plus a relative path or query parameters
- generate the shared CLASSIC user-agent string used by wrapper crates
- map a [`GameId`](../../foundation/classic-shared-core) to a small set of well-known mod-site URLs

Do not use this crate for:

- making HTTP requests
- managing retries, headers, cookies, or auth
- storing remote-site metadata beyond the small hardcoded `ModSite` enum
- parsing arbitrary site-specific pages or APIs
- owning network/runtime configuration

Those concerns belong in callers or higher layers. In current source, this crate is mostly a stable helper surface for bindings and other lightweight consumers.

---

## Module And API Map

This crate currently exposes a single public file, `src/lib.rs`. There are no public submodules; the full contributor-facing API is at the crate root.

## Root-level error and result types

- `WebError` - crate-wide error enum for URL parsing/validation failures
- `WebResult<T>` - `Result<T, WebError>` alias

## Root-level constants

- `CLASSIC_VERSION` - user-agent version string currently used by helper functions
- `USER_AGENT_PREFIX` - fixed prefix used for user-agent strings

## Root-level functions

- `get_user_agent()` - returns `CLASSIC/<version>`
- `get_user_agent_with_suffix(suffix)` - returns `CLASSIC/<version> (<suffix>)`
- `validate_url(url_str)` - parses a URL and enforces `http` or `https`
- `is_valid_url(url_str)` - boolean convenience wrapper over `validate_url`
- `extract_domain(url_str)` - returns `host_str()` from a validated URL
- `join_url(base, path)` - joins a validated base URL with a path
- `build_url_with_query(base, params)` - appends query parameters to a validated base URL

## Root-level enum

- `ModSite` - small enum for `NexusMods`, `BethesdaNet`, and `ModDB`

---

## Public API Surface

## `WebError`

`WebError` is the crate's public error enum.

Variants:

- `InvalidUrl(String)`
- `UrlParseError(url::ParseError)`
- `InvalidScheme(String)`

Important behavior from the source:

- `UrlParseError` is created automatically through `#[from] url::ParseError`
- `InvalidScheme` is used after parsing succeeds but the scheme is not `http` or `https`
- `InvalidUrl("URL has no host")` is used by `extract_domain()` when `host_str()` is absent
- `join_url()` converts `url::Url::join()` failures into `InvalidUrl(...)` text rather than preserving a separate join-specific error variant

## `WebResult<T>`

`WebResult<T>` is just:

```rust
type WebResult<T> = Result<T, WebError>;
```

The crate uses this alias for all fallible helpers.

## `CLASSIC_VERSION` and `USER_AGENT_PREFIX`

These constants drive the user-agent helpers:

- `CLASSIC_VERSION: &str = "8.0.0"`
- `USER_AGENT_PREFIX: &str = "CLASSIC"`

Contributor-visible note:

- current source uses the hardcoded `CLASSIC_VERSION` constant for user-agent strings; it does not derive the value from Cargo package metadata
- as of this source snapshot, that constant is `8.0.0` while `Cargo.toml` declares crate version `9.0.0`

If user-agent versioning changes, update both the source constant and this document together.

## User-agent helpers

### `get_user_agent() -> String`

Returns `CLASSIC/<version>` using the two constants above.

Current behavior:

- returns a newly allocated `String`
- performs no environment detection
- always uses the crate constant, so output is currently `CLASSIC/8.0.0`

### `get_user_agent_with_suffix(suffix: &str) -> String`

Returns `CLASSIC/<version> (<suffix>)`.

Current behavior worth knowing:

- formatting is unconditional, so an empty suffix becomes `CLASSIC/8.0.0 ()`
- the function does not sanitize or trim the suffix

## URL validation helpers

### `validate_url(url_str: &str) -> WebResult<url::Url>`

This is the main validation entry point.

Behavior:

- parses with `url::Url::parse`
- accepts only `http` and `https`
- returns the parsed `Url` on success so callers can reuse it instead of reparsing

Source-visible limits:

- a syntactically valid non-HTTP scheme like `ftp://...` still fails with `InvalidScheme`
- the function does not impose extra CLASSIC-specific host allowlists or path rules

### `is_valid_url(url_str: &str) -> bool`

Thin convenience wrapper over `validate_url(url_str).is_ok()`.

Use this when the caller only needs a boolean gate and does not care why validation failed.

### `extract_domain(url_str: &str) -> WebResult<String>`

Validates the URL, then returns `host_str()` as an owned `String`.

Behavior worth knowing:

- ports are not included in the returned string
- the function returns host text only; it does not normalize to a registrable domain
- IP addresses are returned as strings when present
- if the URL parses but has no host, the function returns `WebError::InvalidUrl("URL has no host")`

## `ModSite`

`ModSite` is the crate's small site-mapping enum.

Variants:

- `NexusMods`
- `BethesdaNet`
- `ModDB`

Derived traits:

- `Debug`, `Clone`, `Copy`, `PartialEq`, `Eq`, `Hash`, `Serialize`, `Deserialize`

Important methods:

- `base_url(self) -> &'static str`
- `name(self) -> &'static str`
- `game_url(self, game_id: classic_shared_core::GameId) -> String`

### `base_url()`

Static mappings in current source:

- `NexusMods` -> `https://www.nexusmods.com`
- `BethesdaNet` -> `https://bethesda.net`
- `ModDB` -> `https://www.moddb.com`

### `name()`

Display-like mappings in current source:

- `NexusMods` -> `Nexus Mods`
- `BethesdaNet` -> `Bethesda.net`
- `ModDB` -> `ModDB`

### `game_url()`

`game_url()` is where this crate collaborates directly with [`classic-shared-core`](../../foundation/classic-shared-core): it accepts a `GameId` and maps it to a site-specific URL.

Current `GameId` slug mapping used for Nexus Mods:

- `GameId::Fallout4` -> `fallout4`
- `GameId::Fallout4VR` -> `fallout4vr`
- `GameId::Skyrim` -> `skyrimspecialedition`
- `GameId::Starfield` -> `starfield`

Site-specific URL behavior:

- `NexusMods` appends the per-game slug to the base URL
- `BethesdaNet` always returns `https://bethesda.net/mods`, regardless of `GameId`
- `ModDB` always returns `https://www.moddb.com/games`, regardless of `GameId`

Contributor note:

- only Nexus currently has per-game URL output in the source; the other sites use shared landing pages rather than game-specific paths

## URL building helpers

### `join_url(base: &str, path: &str) -> WebResult<String>`

Validates `base`, then calls `url::Url::join(path)`.

Behavior worth knowing:

- the function returns a `String`, not `Url`
- join semantics come from the `url` crate, including relative-path resolution rules
- leading/trailing slashes on `base` and `path` affect the final output according to `Url::join`
- join failures become `WebError::InvalidUrl(...)`

Because it uses `Url::join`, this helper is better for relative-path composition than for arbitrary string concatenation.

### `build_url_with_query(base: &str, params: &[(&str, &str)]) -> WebResult<String>`

Validates `base`, then appends query pairs with `query_pairs_mut().append_pair(...)`.

Behavior worth knowing:

- parameters are appended in input order
- encoding is delegated to the `url` crate
- the function does not clear pre-existing query parameters on the base URL; it appends to whatever is already there
- the function returns a `String`, not `Url`

---

## Web / URL Helper Flow

The crate is easiest to think about as a short pipeline with two entry patterns.

## Flow A: validate or inspect an existing URL

1. Call `validate_url()` when the caller needs a parsed `Url` and structured failure information.
2. Call `is_valid_url()` instead when only a yes/no check is needed.
3. Call `extract_domain()` when the caller needs the host text after the same HTTP/HTTPS validation gate.

## Flow B: produce a URL from trusted pieces

1. Start from a known source such as `ModSite::base_url()` or `ModSite::game_url(GameId::...)`.
2. Use `join_url()` to add a relative path when `url::Url::join` semantics are appropriate.
3. Use `build_url_with_query()` to append query parameters.
4. If the caller receives URL text from outside the crate afterward, run `validate_url()` again before treating it as trusted input.

Practical examples from current source shape:

- site lookup: `ModSite::NexusMods.game_url(GameId::Fallout4)`
- path composition: `join_url("https://example.com/api/", "mods")`
- query composition: `build_url_with_query("https://example.com/search", &[("page", "1")])`

---

## Error Handling Model

This crate uses a single small error enum rather than `anyhow::Error` in its public API.

Public error patterns:

- parse failures from `url::Url::parse` surface as `WebError::UrlParseError`
- syntactically valid but non-HTTP URLs surface as `WebError::InvalidScheme`
- higher-level helper failures that are not parse failures surface as `WebError::InvalidUrl`
- infallible convenience functions such as `get_user_agent()`, `get_user_agent_with_suffix()`, and `ModSite::{base_url,name}` do not return `Result`

Contributor note:

- `Cargo.toml` declares `anyhow`, but the current public crate API does not expose `anyhow::Result` or `anyhow::Error`

---

## Important Dependencies And Related Crates

Important direct dependencies:

- `url` - parsing, joining, host extraction, and query construction
- `thiserror` - `WebError` derive and display messages
- `serde` - `ModSite` serialization/deserialization
- [`classic-shared-core`](../../foundation/classic-shared-core) - provides `GameId` used by `ModSite::game_url()`

Related crates in this repository:

- [`python-bindings/classic-web-py`](../../python-bindings/classic-web-py) - Python wrapper over this crate's public surface
- [`node-bindings/classic-node/src/web.rs`](../../node-bindings/classic-node/src/web.rs) - Node/N-API wrapper over this crate's public surface
- [`classic-shared-core`](../../foundation/classic-shared-core) - upstream enum definitions for supported games

Current collaboration pattern in the repo:

- `classic-web-core` keeps the pure-Rust shared logic small
- binding crates translate `WebError` into language-specific exceptions/errors
- there is no separate business-logic crate in current source that appears to depend on `classic-web-core` for HTTP behavior; the most visible consumers are the wrapper layers

---

## Usage Example

This example stays within the real public API: choose a site for a supported game, extend the URL, and validate the result before reuse.

```rust
use classic_shared_core::GameId;
use classic_web_core::{
    ModSite,
    build_url_with_query,
    extract_domain,
    get_user_agent,
    join_url,
    validate_url,
};

let base = ModSite::NexusMods.game_url(GameId::Fallout4);
assert_eq!(base, "https://www.nexusmods.com/fallout4");

let mods_url = join_url(&base, "mods")?;
let paged_url = build_url_with_query(&mods_url, &[("page", "1"), ("sort", "updated")])?;

let parsed = validate_url(&paged_url)?;
assert_eq!(parsed.scheme(), "https");
assert_eq!(extract_domain(&paged_url)?, "www.nexusmods.com");

let ua = get_user_agent();
assert!(ua.starts_with("CLASSIC/"));

# Ok::<(), classic_web_core::WebError>(())
```

---

## Contributor Notes And Known Limits

- the entire public API is currently defined in `src/lib.rs`; changing root-level exports changes the crate surface immediately
- this crate validates URL syntax and scheme only; it does not verify reachability, content type, redirects, or remote API contracts
- `ModSite` is intentionally small and hardcoded; adding a site or changing a URL mapping is a public-behavior change and should be documented alongside wrapper updates
- only `http` and `https` are accepted today; if a future caller needs other schemes, that is a source-level behavior change, not just a caller-side policy choice
- user-agent helpers currently use a hardcoded `CLASSIC_VERSION` constant rather than the Cargo package version
- `build_url_with_query()` appends parameters to the provided base URL; it does not expose a policy for replacing existing parameters
- `BethesdaNet` and `ModDB` currently ignore `GameId` when building `game_url()` output beyond satisfying the function signature
- `serde` support exists only for `ModSite`; the free functions and error types are not designed as a serialized protocol layer

If you extend this crate, update this document when you change:

- any `WebError` variant or error message contract that wrappers surface to users
- accepted URL schemes or validation rules
- `ModSite` variants, site names, or URL mappings
- user-agent string format or version source
- the relationship between this crate and binding wrappers

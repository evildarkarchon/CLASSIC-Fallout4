# Path Normalization fixtures

These inputs migrate the deterministic `normalizePath`, `joinPaths` and
`validatePathsBatch` checks from the Node Tier-1 auxiliary smoke case. Each
participant creates the same disposable directory and file, joins components
through its public binding, normalizes the returned path, and validates an ordered
batch containing directories, files and an absent path.

Only native separators, Windows extended-path prefixes and the temporary root are
normalized in observations. The missing-path case preserves `..` in the join
result and exercises Rust's lexical fallback in normalization. The CXX bridge has
no corresponding `classic-shared-core::PathHandler` API and is not a participant.
Expectations live in `tests/conformance/packs/path_normalization/v1.json`.

## 1. Add ClientBuild variant to UpdateError

- [x] 1.1 In `classic-update-core/src/github.rs`, add `ClientBuild(#[from] reqwest::Error)` variant to the `UpdateError` enum with display message `"Failed to create HTTP client: {0}"`

## 2. Convert GitHubClient constructors to return Result

- [x] 2.1 Change `GitHubClient::new(...)` signature from `-> Self` to `-> Result<Self, UpdateError>`
- [x] 2.2 Replace `.expect("Failed to create HTTP client")` in `new()` with `?` operator on `ClientBuilder::build()`
- [x] 2.3 Change `GitHubClient::new_with_token(...)` signature from `-> Self` to `-> Result<Self, UpdateError>`
- [x] 2.4 Replace `.expect("Failed to create HTTP client")` in `new_with_token()` with `?`

## 3. Update call sites for GitHubClient constructors

- [x] 3.1 Search all crates for `GitHubClient::new(` and `GitHubClient::new_with_token(` and update each call site to handle `Result` (use `?` where the calling function returns `Result`, or `.unwrap_or_else(|e| ...)` with logging for optional update checks)
- [x] 3.2 Check `python-bindings/classic-update-py/` for any PyO3 wrapper of `GitHubClient` construction and update accordingly (map error to `PyErr`)

## 4. Fix expect() in orchestrator.rs

- [x] 4.1 In `classic-scanlog-core/src/orchestrator.rs` at line 645, replace `.expect("FormID analyzer creation should not fail")` with `?`
- [x] 4.2 At line 679, replace the second `.expect("FormID analyzer creation should not fail")` with `?`
- [x] 4.3 Confirm the enclosing function already returns `Result<..., ...>` (so `?` is valid)

## 5. Build and test

- [x] 5.1 Run `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` and confirm clean compilation across all crates
- [x] 5.2 Run `cargo test -p classic-update-core --manifest-path ClassicLib-rs/Cargo.toml` and confirm tests pass
- [x] 5.3 Run `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml` and confirm tests pass
- [x] 5.4 Run `cargo clippy --workspace --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` and resolve any warnings

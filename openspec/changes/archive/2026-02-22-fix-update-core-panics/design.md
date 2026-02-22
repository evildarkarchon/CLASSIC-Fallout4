## Context

Two sites in production non-test code use `.expect()` where a recoverable error path exists:

**Site 1** — `classic-update-core/src/github.rs`, two `GitHubClient` constructors:
```rust
let client = reqwest::Client::builder()
    .user_agent(...)
    .build()
    .expect("Failed to create HTTP client");  // panics if TLS init fails
```
`reqwest::ClientBuilder::build()` fails on platforms where TLS cannot be initialized. This is rare but real (e.g., missing CA bundle, FIPS mode restrictions). The panic is unrecoverable and opaque to the user.

**Site 2** — `classic-scanlog-core/src/orchestrator.rs`, lines 645 and 679:
```rust
FormIDAnalyzerCore::new(...)
    .expect("FormID analyzer creation should not fail")
```
`FormIDAnalyzerCore::new()` currently always returns `Ok(...)`, but the `.expect()` creates a future footgun — any `Err` path added later becomes a hidden panic in production.

## Goals / Non-Goals

**Goals:**
- Convert `GitHubClient::new()` and `GitHubClient::new_with_token()` to return `Result<Self, UpdateError>`
- Convert the two `.expect()` calls in `orchestrator.rs` to `?` propagation
- Update all call sites accordingly

**Non-Goals:**
- Changing the behavior of update checks when the client builds successfully
- Changing `FormIDAnalyzerCore::new()` itself
- Fixing the `.expect()` calls that are inside `#[test]` functions (those are acceptable)

## Decisions

### UpdateError gets a ClientBuild variant

```rust
#[derive(Debug, thiserror::Error)]
pub enum UpdateError {
    // existing variants...
    #[error("Failed to create HTTP client: {0}")]
    ClientBuild(#[from] reqwest::Error),
}
```

`reqwest::ClientBuilder::build()` returns `reqwest::Error`, which is already a dependency. The `#[from]` impl allows `?` in the constructors.

### GitHubClient constructors return Result

```rust
pub fn new(...) -> Result<Self, UpdateError> {
    let client = reqwest::Client::builder()
        .user_agent(...)
        .build()?;  // propagates instead of panicking
    Ok(Self { ... })
}
```

All call sites must be updated to handle `Result<GitHubClient, _>`. Check Python binding (`classic-update-py`) and any C++ bridge usages.

### Orchestrator: ? propagation

The orchestrator's `process_log` (or whichever function creates `FormIDAnalyzerCore`) already returns `Result<...>`. The two `.expect()` calls become `?`. No signature change needed at the orchestrator level.

## Risks / Trade-offs

- **Call site ripple**: Converting constructors to `Result` means all callers must propagate or handle. The number of call sites is small (check before implementing).
- **Python binding impact**: If `classic-update-py` exposes `GitHubClient` directly, its Python-facing constructor will need to map the error to `PyErr`.

## Migration Plan

1. Add `ClientBuild` variant to `UpdateError` in `github.rs`
2. Change both `GitHubClient::new` and `GitHubClient::new_with_token` signatures to `Result<Self, UpdateError>`
3. Replace `.expect(...)` with `?` in both constructors
4. Update all call sites (grep for `GitHubClient::new`)
5. In `orchestrator.rs`, replace both `.expect("FormID analyzer creation should not fail")` with `?`
6. Build workspace and fix any remaining type errors

## Open Questions

*(none)*

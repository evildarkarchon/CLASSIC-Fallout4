## Why

`classic-update-core/src/github.rs` constructs `reqwest::Client` in two constructors using `.expect("Failed to create HTTP client")`. `reqwest::ClientBuilder::build()` can fail if the TLS backend fails to initialize (missing system certificates, platform TLS issues). A panic in a constructor is unrecoverable and gives the user no actionable error message. Similarly, two `.expect()` calls in `classic-scanlog-core/src/orchestrator.rs` for `FormIDAnalyzerCore::new()` would panic if that constructor ever returns `Err` in the future.

## What Changes

- **Change** both `GitHubClient` constructors in `github.rs` to return `Result<Self, UpdateError>` instead of panicking; propagate the `reqwest` error
- **Change** the two `.expect("FormID analyzer creation should not fail")` calls in `orchestrator.rs` to use `?` operator propagation
- **Update** all call sites that construct `GitHubClient` to handle the `Result`

## Capabilities

### New Capabilities

*(none — this is an error handling correctness fix)*

### Modified Capabilities

*(no spec-level behavior change — errors that previously panicked now surface as `Result::Err`)*

## Impact

- **Modified**: `ClassicLib-rs/business-logic/classic-update-core/src/github.rs` (constructor signatures)
- **Modified**: `ClassicLib-rs/business-logic/classic-scanlog-core/src/orchestrator.rs` (two call sites)
- **Modified**: Any callers of `GitHubClient::new()` / `GitHubClient::new_with_token()` (check Python bindings and C++ bridge)
- **Safety**: Eliminates two panic sites in production non-test code

## Purpose

Define requirements for propagating recoverable update-core and orchestrator initialization errors instead of panicking.

## Requirements

### Requirement: GitHubClient constructors return Result
`GitHubClient::new()` and `GitHubClient::new_with_token()` SHALL return `Result<Self, UpdateError>` to propagate HTTP client initialization failures rather than panicking.

#### Scenario: Successful construction
- **WHEN** the reqwest HTTP client builds successfully
- **THEN** both constructors SHALL return `Ok(GitHubClient { ... })`

#### Scenario: TLS initialization failure surfaces as error
- **WHEN** `reqwest::ClientBuilder::build()` returns an error (e.g., TLS backend unavailable)
- **THEN** the constructor SHALL return `Err(UpdateError::ClientBuild(...))` instead of panicking

### Requirement: UpdateError includes a ClientBuild variant
The `UpdateError` enum SHALL include a `ClientBuild(reqwest::Error)` variant representing HTTP client initialization failures.

#### Scenario: Error variant is displayable
- **WHEN** an `UpdateError::ClientBuild` is formatted with `Display`
- **THEN** the message SHALL include a human-readable description of the underlying reqwest error

### Requirement: FormIDAnalyzerCore creation errors propagate in orchestrator
The two `FormIDAnalyzerCore::new(...).expect(...)` call sites in `orchestrator.rs` SHALL be replaced with `?`-propagation.

#### Scenario: Creation error propagates to caller
- **WHEN** `FormIDAnalyzerCore::new()` returns `Err` (hypothetical future case)
- **THEN** the orchestrator function SHALL return that error to its caller rather than panicking

#### Scenario: Current behavior unchanged when Ok
- **WHEN** `FormIDAnalyzerCore::new()` returns `Ok` (current behavior)
- **THEN** the orchestrator SHALL continue processing identically to before this change

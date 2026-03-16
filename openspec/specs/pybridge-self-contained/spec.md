## Purpose

Define requirements for retiring obsolete `classic-pybridge-py` now that the Python application it supported no longer exists.

## Requirements

### Requirement: classic-pybridge-py is removed from the active workspace
`classic-pybridge-py` SHALL NOT remain a maintained Python binding crate in the workspace, CI, or parity toolchain.

#### Scenario: Workspace member absent
- **WHEN** the workspace `Cargo.toml` is inspected
- **THEN** `"python-bindings/classic-pybridge-py"` SHALL NOT appear in the `members` array

#### Scenario: Crate directory absent
- **WHEN** the `ClassicLib-rs/python-bindings/` directory is listed
- **THEN** no `classic-pybridge-py/` subdirectory SHALL exist

### Requirement: Python parity tooling no longer expects classic_pybridge
The Python parity baselines, smoke tests, and generation scripts SHALL NOT treat `classic_pybridge` as a maintained module.

#### Scenario: Smoke tests skip removed module
- **WHEN** Python binding smoke tests are executed
- **THEN** they SHALL NOT import or assert behavior for `classic_pybridge`

#### Scenario: Parity generator omits removed module
- **WHEN** parity baselines are regenerated
- **THEN** `classic_pybridge` SHALL NOT appear in maintained-surface outputs or runtime coverage manifests

### Requirement: Documentation reflects removal
Repo docs and agent guidance SHALL stop describing `classic-pybridge-py` as an intentional exception or maintained binding surface.

#### Scenario: Architecture docs no longer mention exception
- **WHEN** the architecture section of any maintained repo guidance file is read
- **THEN** it SHALL NOT describe `classic-pybridge-py` as an active exception to the `*-core -> *-py` pairing rule

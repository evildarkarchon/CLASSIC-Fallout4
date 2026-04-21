## ADDED Requirements

### Requirement: Unit tests live in sibling submodule files
Every Rust source file in the workspace SHALL keep its unit tests in a sibling submodule file rather than inside an inline `#[cfg(test)] mod tests { ... }` block. For a source file `src/<name>.rs`, the tests SHALL live in `src/<name>_tests.rs` and SHALL be declared from the parent module by a single attribute-bearing line of the form `#[cfg(test)] #[path = "<name>_tests.rs"] mod tests;` (the `#[path]` attribute is required so the sibling file resolves alongside `<name>.rs` rather than under a `<name>/` directory). This rule applies to every Rust crate under `foundation/`, `business-logic/`, `cpp-bindings/classic-cpp-bridge/`, `node-bindings/classic-node/`, `python-bindings/`, `ui-applications/classic-tui/`, and any future Rust crate added under those layer roots.

#### Scenario: Inline test block is forbidden in production source
- **WHEN** a contributor opens any committed Rust source file under one of the listed layer roots and searches for `#[cfg(test)]\nmod tests {`
- **THEN** no occurrence is found, because each former inline block has been moved into a sibling `<name>_tests.rs` file

#### Scenario: Sibling file is colocated with the source it tests
- **WHEN** a contributor lists the directory containing `src/foo.rs` for any module that has tests
- **THEN** the directory contains both `foo.rs` and `foo_tests.rs`, where `foo_tests.rs` holds exactly the test items previously defined under that file's `mod tests` block

#### Scenario: Module declaration uses the standard one-line form
- **WHEN** a contributor inspects the parent source file `src/foo.rs`
- **THEN** the only test-related line in `foo.rs` is `#[cfg(test)] #[path = "foo_tests.rs"] mod tests;`, with no test bodies, fixtures, or helpers remaining inline

### Requirement: Test relocation preserves observable test behavior
Moving an inline `#[cfg(test)] mod tests { ... }` block into a sibling submodule file SHALL NOT change which tests run, the names cargo reports for them, the modules they belong to from a `cargo test <filter>` standpoint, or whether they pass. `cargo test --workspace` from the repo root MUST produce the same set of passing tests after the move as it did before, on a per-crate basis.

#### Scenario: Per-crate cargo test parity before and after relocation
- **WHEN** a maintainer runs `cargo test -p <crate>` against the crate's pre-conversion state, then again against the post-conversion state
- **THEN** both runs report the same total test count, the same list of test names, and the same pass/fail outcome for every test

#### Scenario: Filter-by-name continues to work for relocated tests
- **WHEN** a maintainer runs `cargo test -p <crate> tests::<some_test_name>` after the conversion
- **THEN** the same test that ran under that filter before the conversion still runs and still passes, because the `tests` module path is unchanged

#### Scenario: super::* imports continue to resolve
- **WHEN** the relocated test file uses `use super::*;` to reach items declared in the parent source file
- **THEN** the import resolves to the parent module exactly as it did when the tests were inline, because the sibling submodule is still declared as `mod tests` of the parent

### Requirement: Public surface and parity baselines are unchanged by relocation
Relocating tests SHALL NOT add, remove, rename, or alter the visibility of any item in any crate's public API, and SHALL NOT change any binding-facing surface (CXX bridge entries, Node `index.d.ts`, or Python `.pyi` stubs). The committed parity baselines under `docs/implementation/cxx_api_parity/baseline/`, `docs/implementation/node_api_parity/baseline/`, and `docs/implementation/python_api_parity/baseline/` MUST remain byte-stable across the conversion.

#### Scenario: CXX parity gate stays green
- **WHEN** a maintainer runs `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` after a per-crate conversion lands
- **THEN** the gate reports no drift against the committed CXX baseline

#### Scenario: Node parity gate stays green
- **WHEN** a maintainer runs `bun run parity:gate` from `node-bindings/classic-node/` after a per-crate conversion lands
- **THEN** the gate reports no drift against the committed Node baseline

#### Scenario: Python parity gate stays green
- **WHEN** a maintainer runs `python tools/python_api_parity/check_parity_gate.py --repo-root .` after a per-crate conversion lands
- **THEN** the gate reports no drift against the committed Python baseline

### Requirement: Integration tests and other test directories are out of scope
This layout rule SHALL apply only to in-source unit tests (those previously written inside a source file as `#[cfg(test)] mod tests`). Tests that already live in a crate's `tests/` directory (Cargo integration tests), `benches/` directory (criterion benches), or in dedicated `tests/common/` shared modules SHALL remain where they are and SHALL NOT be moved or renamed by work performed under this rule.

#### Scenario: Existing integration tests are untouched
- **WHEN** a contributor inspects any crate's `tests/` directory after the conversion
- **THEN** the file set in `tests/` is unchanged from before the conversion, and no integration test has been moved into a `<name>_tests.rs` sibling

#### Scenario: Bench files stay where they are
- **WHEN** a contributor inspects any crate's `benches/` directory after the conversion
- **THEN** the bench file set is unchanged, including any `benches/common/*.rs` helper files

### Requirement: New Rust modules and crates scaffold sibling test files
When a new Rust source module is created — whether by hand or via the existing `rust-crate` skill — it SHALL be created with the sibling test layout from the start. The author SHALL NOT introduce a fresh inline `#[cfg(test)] mod tests { ... }` block in any new source file under the listed layer roots.

#### Scenario: rust-crate skill produces sibling test files
- **WHEN** a contributor scaffolds a new crate using the `rust-crate` skill after this rule lands
- **THEN** the generated `src/lib.rs` contains `#[cfg(test)] #[path = "lib_tests.rs"] mod tests;` and a sibling `src/lib_tests.rs` file is generated next to it

#### Scenario: New module file added to an existing crate
- **WHEN** a contributor adds a new module file `src/foo.rs` to an existing crate and includes any unit tests
- **THEN** the tests live in `src/foo_tests.rs` and `foo.rs` declares them via the standard `#[cfg(test)] #[path = "foo_tests.rs"] mod tests;` line

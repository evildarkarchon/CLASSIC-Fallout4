## Why

Binding parity gates currently prove that maintained Tier-1 rows match the Rust core, but large portions of the exposed Node and Python surfaces still sit outside runtime-oriented verification. As the binding APIs expand, we need a clearer contract for how much surface must be covered by parity tests so drift is caught before it reaches consumers.

## What Changes

- Define a binding parity test coverage contract for Node and Python bindings against the Rust core.
- Require parity workflows to track covered, deferred, and newly introduced API surface so uncovered gaps remain visible instead of silently growing.
- Expand runtime-oriented verification expectations for promoted and high-value deferred APIs, especially workflow entry points, constructors, factories, and representative methods.
- Add acceptance criteria for parity maintenance artifacts, local checks, and CI signals that demonstrate coverage expansion over time.

## Capabilities

### New Capabilities
- `binding-parity-test-coverage`: Defines required parity coverage accounting, promotion verification, and runtime test expectations for Node and Python bindings relative to the Rust core.

### Modified Capabilities
- None.

## Impact

- Affected code: `tools/node_api_parity/`, `tools/python_api_parity/`, `ClassicLib-rs/node-bindings/classic-node/__test__/`, `ClassicLib-rs/python-bindings/tests/`, and parity baseline artifacts under `docs/implementation/`.
- APIs/interfaces: Node and Python binding exports mapped to Rust public symbols, parity contract manifests, and runtime smoke/parity suites.
- Tooling/tests: Local parity gates, stub validation, Bun/Node runtime tests, Python smoke/parity tests, and CI workflows that report or enforce coverage.
- Operations: Contributors get a clearer definition of what "binding parity coverage" means and what evidence is required before expanding or promoting binding APIs.

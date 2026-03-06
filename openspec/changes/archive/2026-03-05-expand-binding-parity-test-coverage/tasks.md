## 1. Coverage Registry And Tooling

- [x] 1.1 Define stable Node and Python runtime coverage registry formats keyed by parity contract IDs or binding export identifiers, and seed them with the current Tier-1 surface.
- [x] 1.2 Extend `tools/node_api_parity/` and `tools/python_api_parity/` to join manifests, parity contracts, and coverage registries into generated coverage summary artifacts with per-module totals.
- [x] 1.3 Add non-regression checks that fail when tracked exports are unclassified, Tier-1 rows lack runtime coverage metadata, or parity artifacts have not been refreshed after tracked surface changes.

## 2. Node Runtime Coverage Expansion

- [x] 2.1 Refactor `ClassicLib-rs/node-bindings/classic-node/__test__/` runtime suites into table-driven cases sourced from the Node coverage registry.
- [x] 2.2 Expand Node runtime coverage for Tier-1 exports and the highest-value deferred `scanlog`, `config`, `version_registry`, and `aux` surfaces, updating `parity_contract.json` and `index.d.ts` for any promoted APIs.
- [x] 2.3 Regenerate Node parity artifacts and verify `bun run parity:gate:local`, `bun run test:bun`, and `bun run test:node` pass with the new coverage summaries.

## 3. Python Runtime Coverage Expansion

- [x] 3.1 Refactor `ClassicLib-rs/python-bindings/tests/` smoke and parity suites into parametrized cases sourced from the Python coverage registry.
- [x] 3.2 Expand Python runtime coverage for Tier-1 exports and the highest-value deferred `scanlog`, `config`, `version_registry`, and `aux` surfaces, updating parity contract and stub files for any promoted APIs.
- [x] 3.3 Regenerate Python parity artifacts and verify `python tools/python_api_parity/check_parity_gate.py --repo-root .`, `python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings`, and `uv run python -m pytest ClassicLib-rs/python-bindings/tests -q` pass with the new coverage summaries.

## 4. Published Backlog And CI Adoption

- [x] 4.1 Publish updated Node and Python deferred backlog artifacts with owner, rationale, and wave metadata that reflect surfaces moved into runtime-verified coverage.
- [x] 4.2 Integrate coverage summary generation and non-regression enforcement into the relevant CI workflows and contributor documentation.

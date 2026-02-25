# Node Bindings Tier-2 Backlog And Governance (Phase 5)

## Status Baseline

Source baseline: `docs/implementation/node_api_parity/phase1/parity_diff_report.md` and `docs/implementation/node_api_parity/phase1/handoff_map.md`.

- Tier-1 contract rows: `35`
- Tier-1 drift: `0` (all matched)
- Deferred Tier-2 gaps: `315`

Phase 0 setup artifacts:

- Locked wave/subwave manifest: `docs/implementation/node_api_parity/phase5/tier2_wave_manifest.json`
- Per-wave acceptance template: `docs/implementation/node_api_parity/phase5/per_wave_acceptance_template.md`
- Gate contract baseline: `docs/implementation/node_api_parity/phase5/phase0_gate_contract_baseline.md`

Manifest regeneration command:

- `python tools/node_api_parity/generate_phase0_wave_manifest.py --repo-root .`

Tier-2 remains intentionally deferred so we can preserve guaranteed parity for high-value workflow APIs while avoiding churn on low-level or internal-style surfaces.

## Tier-2 Deferred Backlog (Published)

The complete, machine-readable backlog is tracked in:

- `docs/implementation/node_api_parity/phase1/parity_diff_report.json`
- `docs/implementation/node_api_parity/phase1/handoff_map.md`

Working summary by owner module:

| Owner Module | Tier-2 Gap Count | Deferred Rationale | Representative Deferred APIs |
|---|---:|---|---|
| `scanlog` | 72 | Advanced parser/scanner internals and helper types are not required for current cross-language app workflows. | `StreamingLogParser`, `ReportGenerator`, `PatternMatcher`, `detect_mods_batch` |
| `config` | 58 | Low-level YAML/settings/cache internals are intentionally not part of the guaranteed Tier-1 workflow surface. | `ConfigError`, `PathConfig`, `yamlParse`, `loadSettingsAsync` |
| `version_registry` | 43 | Extended matching/tuning internals are stable in Rust but not required for immediate Node workflow parity. | `VersionMatcher`, `AddressLibraryConfig`, `UnknownVersionStrategy`, `get_version_registry` |
| `aux` | 142 | Utility-heavy and integration-adjacent exports are broad and currently outside Tier-1 guarantees. | `GithubClient`, `JsFileIO`, `runGameChecks`, `validateUrl` |

## Tier-2 To Tier-1 Promotion Criteria

An API can be promoted only when all criteria below are met:

1. **Workflow necessity**: Required by a shipped app workflow or cross-language integration path (Python/Node/C++).
2. **Rust stability**: Rust API shape is expected to remain stable for at least one release cycle.
3. **Node design clarity**: Node naming/signature is finalized and reviewed for consistency with existing exports.
4. **Typing coverage**: `index.d.ts` declarations are generated and pass freshness checks.
5. **Parity contract update**: API is added to `docs/implementation/node_api_parity/phase1/parity_contract.json` with owner and expected signature metadata.
6. **Verification coverage**: Tier-1 parity gate and runtime tests (`bun` + `node`) include the new surface.

Promotion implementation requirements:

- Add or update `#[napi]` exports in `ClassicLib-rs/node-bindings/classic-node/src/`.
- Rebuild declarations and commit `ClassicLib-rs/node-bindings/classic-node/index.d.ts`.
- Run local gates from `ClassicLib-rs/node-bindings/classic-node`:
  - `bun run parity:gate:local`
  - `bun run test:bun`
  - `bun run test:node`

## Ongoing Parity Maintenance Loop

### Ownership Model

- **Parity gate owner**: maintainers of `ClassicLib-rs/node-bindings/classic-node`.
- **Module owners**:
  - `scanlog` + `config`: Squad A
  - `version_registry` + `aux`: Squad B
- **Release approver**: release manager verifies parity gates are green before tagging.

### Trigger Points

Run parity maintenance whenever one or more of these occur:

- Public Rust API changes in:
  - `ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs`
  - `ClassicLib-rs/business-logic/classic-config-core/src/lib.rs`
  - `ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs`
- Node export or signature changes in `ClassicLib-rs/node-bindings/classic-node/src/`.
- Regeneration of `ClassicLib-rs/node-bindings/classic-node/index.d.ts`.
- Release branch cut, RC preparation, or version tag preparation.

### Loop Cadence

1. **PR-time check (required)**: contributor runs `bun run parity:gate:local` and updates contract/tests when promoting APIs.
2. **CI enforcement (required)**: `ci-typescript.yml` parity jobs must pass:
   - `Node Parity Gates`
   - `NAPI-RS Build + Runtime Tests (bun/node)`
3. **Backlog review (scheduled)**: module owners review Tier-2 backlog at least once per release cycle and nominate promotions.
4. **Release gate (required)**: no release tag unless Tier-1 parity gate passes and `index.d.ts` freshness gate passes on the release commit.

## Release Gating Policy

A release candidate is blocked until all are true:

- Tier-1 parity drift is zero (`bun run parity:gate` passes).
- `index.d.ts` is fresh (`bun run dts:freshness:check` passes).
- Runtime coverage passes in both `bun` and `node`.
- Any promoted APIs are reflected in:
  - `parity_contract.json`
  - `index.d.ts`
  - parity/runtime tests

If a release-critical API cannot satisfy these requirements in time, it remains Tier-2 and is tracked in the deferred backlog until promotion criteria are met.

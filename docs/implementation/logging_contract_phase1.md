# Cross-Language Logging Contract (Phase 1)

This document defines the phase-1 logging parity contract for `replicate-python-logging-standards`.

Machine-readable source of truth: `docs/implementation/logging_contract_phase1.json`.

## Scope

- Included now: `python`, `rust`.
- Deferred to later phases: `cpp`, `node`.
- This contract is intentionally minimal and stable for parity tests and CI drift checks.

## Required Fields

Every canonical event in parity-scoped flows must include:

- `event`
- `severity`
- `component`
- `outcome`

## Optional Fields

Use when context exists:

- `contract`
- `checked_bindings`
- `missing_binding`
- `failure_type`
- `failure_hint`
- `error`
- `correlation_id`
- `active_components`
- `total_components`
- `acceleration_level`

## Severity Mapping

| Message type | Contract severity |
| --- | --- |
| `Info` | `info` |
| `Success` | `info` |
| `Warning` | `warning` |
| `Error` | `error` |
| `Critical` | `error` |
| `Debug` | `debug` |
| `Progress` | `debug` |

## Canonical Event IDs

| Event key | Canonical ID | Intent |
| --- | --- | --- |
| `startup_binding_contract_validated` | `classic.startup.binding_contract.validated` | Startup dependency contract passed |
| `startup_binding_contract_failed` | `classic.startup.binding_contract.failed` | Startup dependency contract failed |
| `startup_acceleration_status` | `classic.startup.acceleration.status` | Startup acceleration summary |

## Event Templates

### `classic.startup.binding_contract.validated`

- Required:
  - `event=classic.startup.binding_contract.validated`
  - `severity=info`
  - `component=integration.startup`
  - `outcome=success`
- Recommended optional:
  - `contract`
  - `checked_bindings`
  - `correlation_id`

### `classic.startup.binding_contract.failed`

- Required:
  - `event=classic.startup.binding_contract.failed`
  - `severity=error`
  - `component=integration.startup`
  - `outcome=failure`
- Recommended optional:
  - `contract`
  - `missing_binding`
  - `failure_type`
  - `failure_hint`
  - `error`
  - `correlation_id`

### `classic.startup.acceleration.status`

- Required:
  - `event=classic.startup.acceleration.status`
  - `severity=info`
  - `component=integration.startup`
  - `outcome=success`
- Recommended optional:
  - `active_components`
  - `total_components`
  - `acceleration_level`
  - `correlation_id`

## Startup/Bridge Diagnostic Rules

- Startup validation must emit one validated or failed canonical event.
- Failed startup contract events must include an actionable `failure_hint`.
- Severity must follow the contract matrix; no runtime may silently downgrade failure semantics.
- Contract event payloads must be redacted before emission.

## Migration and Rollback Notes (Phase 1)

- Phase 1 adapters are additive and backward compatible with existing logger APIs.
- Legacy plain-text logs remain; contract events are emitted in parallel for parity validation.
- If regressions appear, revert only the contract-adapter call sites while keeping contract tests available to identify drift.

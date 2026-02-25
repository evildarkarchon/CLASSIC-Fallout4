# Phase 0 Gate Contract Baseline

## Command Workflow Validation

Validated on `2026-02-25` from `ClassicLib-rs/node-bindings/classic-node`:

```bash
bun run parity:gate:local
bun run test:bun
bun run test:node
bun run dts:freshness:check
```

Observed baseline result:

- `parity:gate:local`: pass (`Tier-1 parity gate passed.`)
- `test:bun`: pass (`866 pass`, `0 fail`)
- `test:node`: pass (`pass 4`, `fail 0`)
- `dts:freshness:check`: pass (`index.d.ts freshness check passed.`)

## Per-Wave Acceptance Template

Use `docs/implementation/node_api_parity/phase5/per_wave_acceptance_template.md` for every wave/subwave promotion PR.

## Enforced Gate Contract

Each wave/subwave is accepted only when all are true:

1. Scope matches `docs/implementation/node_api_parity/phase5/tier2_wave_manifest.json` exactly.
2. Promotion rows are reflected in `docs/implementation/node_api_parity/phase1/parity_contract.json`.
3. `ClassicLib-rs/node-bindings/classic-node/index.d.ts` is regenerated and fresh.
4. Local gates pass:
   - `bun run parity:gate:local`
   - `bun run test:bun`
   - `bun run test:node`
   - `bun run dts:freshness:check`
5. Docs are refreshed:
   - `docs/implementation/node_api_parity/phase1/parity_diff_report.md`
   - `docs/implementation/node_api_parity/phase1/handoff_map.md`
   - `docs/implementation/node_api_parity/phase5/tier2_backlog_and_governance.md`

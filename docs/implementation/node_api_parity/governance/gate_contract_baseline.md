# Gate Contract Baseline

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

Use `per_wave_acceptance_template.md` for every wave/subwave promotion PR.

For companion guidance on when contract refresh work also needs Python stub follow-up, see [`docs/api/binding-contract-refresh-note.md`](../../../api/binding-contract-refresh-note.md). That note supplements this gate contract; it does not replace any Node acceptance requirement here.

## Enforced Gate Contract

Each wave/subwave is accepted only when all are true:

1. Scope matches `tier2_wave_manifest.json` exactly.
2. Promotion rows are reflected in `parity_contract.json`.
3. `ClassicLib-rs/node-bindings/classic-node/index.d.ts` is regenerated, committed as the tracked snapshot, and fresh.
4. Local gates pass:
   - `bun run parity:gate:local`
   - `bun run test:bun`
   - `bun run test:node`
   - `bun run dts:freshness:check`
5. Docs are refreshed:
  - `parity_diff_report.md`
  - `handoff_map.md`
  - `tier2_backlog_and_governance.md`

Contributors should inspect the committed `index.d.ts` snapshot directly when reviewing the public Node contract. Builds are for regeneration and verification, not for first access to the type surface.

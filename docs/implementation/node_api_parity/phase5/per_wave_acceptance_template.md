# Node API Parity Per-Wave Acceptance Template

Use this template for every promotion wave and subwave PR.

## 1) Wave Scope Lock

- Wave ID: `<wave1|wave2|wave3|wave4.1|wave4.2|wave4.3>`
- Branch/PR: `<link-or-branch>`
- Owner squad: `<Squad A|Squad B>`
- Manifest source: `docs/implementation/node_api_parity/phase5/tier2_wave_manifest.json`
- Scope query:
  - `wave=<...>` and (if aux) `subwave=<...>`
- Locked counts:
  - Total in scope: `<n>`
  - `rust_unmapped`: `<n>`
  - `node_unmapped`: `<n>`

## 2) Implementation Contract

- [ ] Add/update exact `#[napi]` exports for all scoped rows.
- [ ] Promote corresponding rows in `docs/implementation/node_api_parity/phase1/parity_contract.json` from `tier2` to `tier1`.
- [ ] Regenerate and commit `ClassicLib-rs/node-bindings/classic-node/index.d.ts`.
- [ ] Add/refresh tests in `ClassicLib-rs/node-bindings/classic-node/__test__/`.

## 3) Required Local Gate Commands

Run from `ClassicLib-rs/node-bindings/classic-node` in this order:

```bash
bun run parity:gate:local
bun run test:bun
bun run test:node
bun run dts:freshness:check
```

Record evidence:

- `parity:gate:local`: `<pass/fail + key lines>`
- `test:bun`: `<pass/fail + summary>`
- `test:node`: `<pass/fail + summary>`
- `dts:freshness:check`: `<pass/fail + key lines>`

## 4) Docs Refresh Checklist

- [ ] `docs/implementation/node_api_parity/phase1/parity_contract.json`
- [ ] `docs/implementation/node_api_parity/phase1/parity_diff_report.md`
- [ ] `docs/implementation/node_api_parity/phase1/handoff_map.md`
- [ ] `docs/implementation/node_api_parity/phase5/tier2_backlog_and_governance.md`
- [ ] `docs/implementation/node_api_parity/phase5/tier2_wave_manifest.json` (if wave scope changed)

## 5) Acceptance Decision

- [ ] Scope in manifest and implementation match exactly (no omissions or extras).
- [ ] All four local gate commands pass.
- [ ] CI parity jobs in `ci-typescript.yml` pass.
- [ ] PR ready to merge.

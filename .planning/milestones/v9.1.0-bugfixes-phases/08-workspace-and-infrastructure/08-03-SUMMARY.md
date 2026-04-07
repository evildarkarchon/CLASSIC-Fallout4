---
phase: 08-workspace-and-infrastructure
plan: 03
subsystem: classic-node
tags: [node, napi-rs, typescript, parity, docs]
requires: [08-01, 08-02]
provides:
  - Tracked `classic-node/index.d.ts` policy aligned with git ignore rules
  - Contributor docs that point to the committed Node contract snapshot first
  - Green local Node freshness, parity, Bun, and Node runtime gates
affects: [INFRA-05, docs]
tech-stack:
  added: []
  patterns: [tracked generated artifact, same-change contract refresh]
key-files:
  created:
    - .planning/phases/08-workspace-and-infrastructure/08-03-SUMMARY.md
  modified:
    - ClassicLib-rs/node-bindings/classic-node/.gitignore
    - docs/api/binding-parity-overview.md
    - docs/api/binding-contract-refresh-note.md
    - docs/implementation/node_api_parity/governance/gate_contract_baseline.md
key-decisions:
  - "Kept the existing `dts:freshness:*` and parity scripts as the only Node contract gate instead of adding a duplicate workflow."
  - "Used the existing local freshness workflow to regenerate `index.d.ts`; the snapshot was already current, so no declaration diff was required."
patterns-established:
  - "`classic-node/index.d.ts` is a tracked generated artifact that contributors review directly from git."
  - "Public Node contract changes refresh `index.d.ts` in the same change and finish with the existing Node gate sequence."
requirements-completed: [INFRA-05]
duration: 11min
completed: 2026-04-06
---

# Phase 8 Plan 03: Node contract artifact governance Summary

**The committed Node declaration snapshot is now the documented first-class contract artifact, the `.gitignore` policy no longer contradicts that, and the existing local Node gates passed without needing a declaration diff.**

## Accomplishments

- Removed the `.gitignore` entry that treated tracked `index.d.ts` as a disposable build artifact.
- Updated contributor-facing docs to say the committed `index.d.ts` snapshot is the first place to inspect the public Node contract and that export changes refresh it in the same change.
- Reused the existing Node freshness and parity workflow; regeneration confirmed `index.d.ts` was already fresh.

## Verification

- `cd ClassicLib-rs/node-bindings/classic-node && bun run dts:freshness:check`
- `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local && bun run test:bun && bun run test:node && bun run dts:freshness:check`

## Self-Check: PASSED

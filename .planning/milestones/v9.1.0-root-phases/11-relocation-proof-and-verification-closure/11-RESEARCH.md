---
phase: 11-relocation-proof-and-verification-closure
created: 2026-04-14
status: complete
discovery_level: 0
---

# Phase 11 Research

## Question

What needs to be true to plan Phase 11 well?

## Scope

Phase 11 is a verification-closure phase, not a new feature phase. The work is limited to refreshing stale relocation-proof artifacts and recording current evidence for `MOVE-01` and `MOVE-02`.

## Key Findings

1. `MOVE-01` and `MOVE-02` are orphaned only because `.planning/phases/07-crate-relocation-and-path-rewire/07-VERIFICATION.md` does not exist.
2. The checked-in relocation proof is stale because both `.planning/phases/07-crate-relocation-and-path-rewire/07-RELOCATION-AUDIT.md` and `tests/planning/test_phase07_validation.py` still expect `ClassicLib-rs/.cargo/` residue, but that directory no longer exists.
3. `07-03-SUMMARY.md` already contains the authoritative closure intent and command set for the moved-crate proof: use repo-root Cargo discovery/metadata plus the relocation audit and Phase 7 planning test.
4. `tests/planning/test_phase11_validation.py` is an obsolete file from an older milestone and should be replaced with a current Phase 11 audit that validates the refreshed Phase 7 proof and the new `07-VERIFICATION.md`.

## Existing Proof Surfaces To Reuse

- `.planning/phases/07-crate-relocation-and-path-rewire/07-RELOCATION-AUDIT.md`
- `tests/planning/test_phase07_validation.py`
- `.planning/phases/07-crate-relocation-and-path-rewire/07-03-SUMMARY.md`
- `.planning/v9.1.0-MILESTONE-AUDIT.md`
- `.planning/phases/10-docs-guidance-and-tripwires/10-VERIFICATION.md` as the current verification-report shape

## Constraints

- No crate moves, API redesign, or parity-contract changes.
- Keep proof focused on relocation closure; wrapper/parity/CI replay gaps stay in Phase 12.
- Use repo-root commands and current repo-root paths only.

## Recommended Plan Shape

1. Replace the obsolete Phase 11 planning audit with a current closure scaffold.
2. Refresh the stale Phase 7 audit/test surfaces so they match the current `ClassicLib-rs` residue inventory.
3. Write `07-VERIFICATION.md` with direct evidence for `MOVE-01` and `MOVE-02`, then update planning status files.

## Validation Architecture

- Primary audit: `python -m pytest tests/planning/test_phase11_validation.py -q`
- Supporting proof: `python -m pytest tests/planning/test_phase07_validation.py -q`
- Workspace proof: `cargo locate-project --workspace --message-format plain && cargo metadata --format-version 1 --no-deps`

These are sufficient because the phase only closes file-backed relocation evidence; no new runtime surface is introduced.

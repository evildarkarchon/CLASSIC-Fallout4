---
phase: quick-260411-m7y
plan: 01
subsystem: planning-docs
tags: [docs, planning, phase-3, scope-amendment]
requires: []
provides: ["Phase 3 three-target redistribution scope in ROADMAP/REQUIREMENTS/PROJECT"]
affects: [".planning/ROADMAP.md", ".planning/REQUIREMENTS.md", ".planning/PROJECT.md"]
tech_stack:
  added: []
  patterns: []
key_files:
  created:
    - .planning/quick/260411-m7y-amend-roadmap-md-requirements-md-and-pro/260411-m7y-SUMMARY.md
  modified:
    - .planning/ROADMAP.md
    - .planning/REQUIREMENTS.md
    - .planning/PROJECT.md
decisions:
  - Align planning docs with 03-CONTEXT.md D-01 (three-target redistribution) before /gsd:plan-phase 3
metrics:
  duration: ~5 min
  completed: 2026-04-11
---

# Quick Task 260411-m7y: Amend Phase 3 scope to three-target redistribution Summary

Rewrote the Phase 3 scope language in `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, and `.planning/PROJECT.md` to match D-01 in `03-CONTEXT.md` — Phase 3 now redistributes `classic-constants-core` across three semantic-domain targets instead of a flat merge into `classic-version-registry-core`. Single atomic commit, pure docs, no code/tests/builds.

## What Changed

### .planning/ROADMAP.md

- **Phase list bullet (line 21):** `Phase 3: Constants -> Version Registry Merge` -> `Phase 3: Constants Redistribution` with updated bullet description mentioning three target crates.
- **Phase Details heading (line 88):** `### Phase 3: Constants -> Version Registry Merge` -> `### Phase 3: Constants Redistribution`.
- **Phase 3 Goal line (line 89):** Rewritten to describe the three-target redistribution: Fallout4Version + NULL_VERSION -> version-registry-core, YamlFile + settings constants -> settings-core, GameId -> shared-core.
- **Phase 3 Success Criteria (lines 92-97):** Expanded from 4 to 6 criteria covering each target crate's accessibility plus the existing deletion/build criteria.
- **Progress table row (line 120):** `3. Constants -> Version Registry Merge` -> `3. Constants Redistribution`.
- **Phase 3 checkbox:** Remains `- [ ]` (unchanged — still not complete).

### .planning/REQUIREMENTS.md

- **Section header (line 23):** `### Constants -> Version Registry Merge` -> `### Constants Redistribution`.
- **CNST-01 (line 25):** Rewritten to describe semantic-domain redistribution across the three target crates with public API names preserved at new locations.
- **CNST-02 (line 26):** Rewritten to describe importing from the semantic-domain-appropriate target crate.
- **CNST-03 (line 27):** Unchanged verbatim.
- **Traceability table (lines 65-67):** Unchanged — CNST-01/02/03 status stays `Pending`, phase stays `Phase 3`.

### .planning/PROJECT.md

- **Target features bullet (line 10):** `Merge classic-constants-core into classic-version-registry-core (unify game/version identity metadata)` -> three-target redistribution bullet naming all three targets and their symbols.
- **Active requirements bullet (line 70):** `Merge classic-constants-core into classic-version-registry-core` -> `Redistribute classic-constants-core across version-registry-core, settings-core, and shared-core`.
- **Footer timestamp (line 134):** Cosmetic update to `2026-04-11 after Phase 3 scope amendment to three-target redistribution`.
- **Validated / Out of Scope / Context / Constraints / Key Decisions / Evolution sections:** Unchanged.

## Stale Strings Removed

Verified absent after commit:

- `Phase 3: Constants -> Version Registry Merge` (ROADMAP.md) — absent
- `Merge classic-constants-core into classic-version-registry-core` (PROJECT.md target-features bullet) — absent

## New Strings Present

Verified present after commit:

- `Phase 3: Constants Redistribution` in ROADMAP.md (lines 21, 88)
- `Fallout4Version and NULL_VERSION live in classic-version-registry-core` in ROADMAP.md (line 89)
- `### Constants Redistribution` in REQUIREMENTS.md (line 23)
- `semantic-domain-appropriate target crate` in REQUIREMENTS.md (line 26)
- `classic-shared-core` in PROJECT.md (line 10)

## Files Touched

Exactly three files, all pure docs:

1. `.planning/ROADMAP.md`
2. `.planning/REQUIREMENTS.md`
3. `.planning/PROJECT.md`

## Commit

- **Hash:** `d644da8e`
- **Stat:** 3 files changed, 16 insertions(+), 14 deletions(-)
- **Message:**

```
Docs(quick-260411-m7y): Amend Phase 3 scope to three-target redistribution

Align ROADMAP.md, REQUIREMENTS.md, and PROJECT.md with D-01 in
.planning/phases/03-constants-version-registry-merge/03-CONTEXT.md.
Phase 3 now redistributes classic-constants-core by semantic domain:
Fallout4Version + NULL_VERSION to classic-version-registry-core,
YamlFile + SETTINGS_IGNORE_NONE + must_not_be_none to classic-settings-core,
and GameId to classic-shared-core. Zero consumer-visible behavior change.
Prerequisite for /gsd:plan-phase 3.
```

## 03-CONTEXT.md Untouched Confirmation

`git log --oneline -1 -- .planning/phases/03-constants-version-registry-merge/03-CONTEXT.md` returns `b321b7e1 docs(03): capture phase context for constants redistribution` — an unrelated prior commit. Our commit `d644da8e` did not modify 03-CONTEXT.md, and `git diff HEAD~1 HEAD --stat` confirms only the three planning-doc files changed.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- [x] `.planning/ROADMAP.md` edited — FOUND (new strings present, stale strings absent)
- [x] `.planning/REQUIREMENTS.md` edited — FOUND (new strings present)
- [x] `.planning/PROJECT.md` edited — FOUND (new strings present, stale strings absent)
- [x] `.planning/quick/260411-m7y-amend-roadmap-md-requirements-md-and-pro/260411-m7y-SUMMARY.md` — this file
- [x] Commit `d644da8e` — FOUND in git log
- [x] `.planning/phases/03-constants-version-registry-merge/03-CONTEXT.md` — NOT modified by this commit
- [x] Phase directory `.planning/phases/03-constants-version-registry-merge/` — NOT renamed

# Plan 09a — Pre-Task Rule 2 Stub Audit

**Generated:** 2026-04-09 (Task 0 Step 3)
**Tool:** `ClassicLib-rs/validate_stubs.py --fail-on-warnings`
**Purpose:** Surface pre-existing stub holes BEFORE row authoring per Plan 08 Rule 2 precedent.

## Scope limitation (M11 fix)

`validate_stubs.py` at line 318 sets `bindings_dir = rust_dir / "python-bindings"` and walks only `ClassicLib-rs/python-bindings/classic-*-py/` crates (see `validate_stubs.py` L318, L333-352). It does NOT walk `ClassicLib-rs/foundation/classic-shared-py/`.

Therefore:
- This audit covers all currently tier1-enrolled crates under `python-bindings/` (config, file_io, scanlog, version_registry).
- It does NOT cover `classic_shared` stubs.
- `classic_shared` stub coverage is guaranteed by the explicit `mypy --strict ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi` step in Plan 09b Task 4 Step 1, NOT by this audit.
- After Task 1 row authoring, validate_stubs.py will pick up the 14 new owner crates too (they live under python-bindings/), so the Task 1 re-audit will cover them.

## Pre-Task 1 audit results

Raw output from `validate_stubs.py`:

```
[INFO] Validating 4 Python binding crates...


======================================================================
VALIDATION SUMMARY
======================================================================
[OK] Crates passed: 4/4
[ERROR] Total errors: 0
[WARN] Total warnings: 0
======================================================================
```

## Pre-existing stub holes to fix in Task 1

**None.** All 4 currently-audited crates (config, file_io, scanlog, version_registry) pass `--fail-on-warnings` cleanly at audit time.

This means Task 1's inline Rule 2 fixes will be limited to gaps surfaced by the 14 newly-enrolled owner crates WHEN validate_stubs.py picks them up after Task 1 row authoring. Any ERRORs or WARNINGs reported at that time will need a .pyi update in the same atomic commit as the contract row additions.

## Validator scope extension after Task 1

After Task 1 adds tier1 rows for 14 new owner modules, validate_stubs.py will start walking:

- classic-scangame-py
- classic-path-py
- classic-constants-py
- classic-message-py
- classic-database-py
- classic-resource-py
- classic-xse-py
- classic-settings-py
- classic-registry-py
- classic-yaml-py
- classic-web-py
- classic-version-py
- classic-perf-py
- classic-update-py

That re-audit in Task 1 Step 3 is the authoritative check for pre-existing stub holes across all 18 enrolled owners.

## Notes for Plan 09b

Plan 09b Task 4 Step 1 runs `mypy --strict` on the full 19-stub surface (including `classic_shared.pyi`). Any stub issues surfaced post-09a that validate_stubs.py cannot detect (because it skips `foundation/`) will be caught there.

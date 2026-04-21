# Quick Task Research: pytest failures from removed `--deferred-registry`

**Researched:** 2026-04-10
**Confidence:** HIGH (reproduced failures, located removal commit, matched fix pattern to sibling test updated in the same commit)

## Exact Identifier Removed

**CLI flag:** `--deferred-registry` (kebab-case) / `deferred_registry` (snake_case argparse dest)

Removed from all four parity-gate scripts:
- `tools/python_api_parity/check_parity_gate.py`
- `tools/python_api_parity/generate_baseline.py`
- `tools/node_api_parity/check_parity_gate.py`
- `tools/node_api_parity/generate_baseline.py`

Also removed as a keyword parameter from `build_coverage_summary()` in `tools/binding_parity_runtime_coverage.py`, and the `"deferred"` value was removed from `VALID_CLASSIFICATIONS`.

Note: The CXX parity gate (`tools/cxx_api_parity/check_parity_gate.py`) **intentionally never had** this flag (CXXG-04 / D-12). Its test `TestNoDeferredRegistry` is a negative-assertion regression guard and is unrelated to this failure.

## Removal Commit

- **Hash:** `12acb63e72e85d225ef93dad46cf37e1a061dfad` (amended/rebased duplicate at `01995fca` with identical message)
- **Date:** 2026-04-10 00:35:37 -0700 (today)
- **Message:** `Refactor(06-01): Remove deferred-registry logic from parity gate scripts and refresh baselines`
- **Diff scope:** 9 files, -787/+9 lines. Deleted `generate_wave_manifest.py` (Python/Node) and `generate_deferred_backlog.py` (Node).

## Why Removed

Part of the `v9.1.0-bindings` Phase 6 (documentation-reset) / `06-01` plan: the Tier-1/Tier-2 parity split was collapsed into a single enforced tier. With `deferred_total == 0` mandated across both Node and Python parity contracts (PROJECT.md Validated requirements), the entire "deferred" classification became dead weight. The commit removes the concept everywhere: CLI flag, function parameter, classification enum value, markdown column, and the now-orphaned Tier-2 governance scripts. The companion test file `test_binding_coverage_tooling.py` was updated in the same commit, but `test_parity_gate_tooling.py` was **missed** — that is the entire root cause of the failures.

## Failing Tests

Command used to reproduce (from repo root, Python venv at `ClassicLib-rs/python-bindings/.venv`):

```
ClassicLib-rs/python-bindings/.venv/Scripts/python.exe -m pytest ClassicLib-rs/python-bindings/tests/test_parity_gate_tooling.py -q
```

Result: **2 failed, 1 passed**. Both failures are in a single parametrized test:

| Test ID | Failure mode |
|---|---|
| `test_parity_gate_tooling.py::test_update_baseline_flag_refreshes_stale_baseline[node-module_path0-node_check_parity_gate]` | `SystemExit: 2` — argparse rejects `unrecognized arguments: --deferred-registry deferred_registry.json` |
| `test_parity_gate_tooling.py::test_update_baseline_flag_refreshes_stale_baseline[python-module_path1-python_check_parity_gate]` | Same — argparse `SystemExit: 2` inside `module.main()` at line 189 |

**Failure mode classification:** Runtime assertion failure (test body constructs `argv` that the real `check_parity_gate.py` no longer accepts). **Not** a collection error — the test imports cleanly; it explodes when `monkeypatch.setattr(sys, "argv", argv)` hits `parser.parse_args()`.

**Specific offending lines in `ClassicLib-rs/python-bindings/tests/test_parity_gate_tooling.py`:**

- Line 102: `"deferred_total": 0,` — fine; this key still exists in diff-report summaries produced by the scripts (verified via grep hit on `deferred_total` in the gate script's docstring/runtime output). **Keep as-is.**
- Line 131: `deferred_rel = "deferred_registry.json"` — orphan variable; delete.
- Line 137: `write_json(tmp_path / deferred_rel, {"entries": []})` — writes a fixture file the script no longer reads; delete.
- Lines 178-179: `"--deferred-registry", deferred_rel,` in the `argv` list — **the actual cause of SystemExit**; delete both list entries.

No other references in the file (grep confirmed: only lines 102, 131, 137, 178-179).

## Replacement / Migration

**There is no replacement.** The concept of a "deferred" parity entry was eliminated entirely — every binding surface is now Tier-1, enforced, with `deferred_total == 0`. The `--runtime-registry` flag (already present at line 176-177 of the test) is the sole remaining registry input to the parity gate scripts. Nothing needs to be added to the `argv` list; the flag and its fixture file simply go away.

The sibling test file `test_binding_coverage_tooling.py` shows the exact migration pattern (seen in commit `12acb63e`): remove the `deferred_registry=` kwarg from `build_coverage_summary()` calls and adjust classification expectations. But `test_parity_gate_tooling.py` drives the CLI via `argv` rather than calling `build_coverage_summary()` directly, so the fix is even simpler — just strip the flag.

## Recommended Fix Approach

**Single file, ~4 line deletions. Update, do not delete the test.**

Edit `ClassicLib-rs/python-bindings/tests/test_parity_gate_tooling.py`:

1. **Line 131:** Delete `deferred_rel = "deferred_registry.json"`
2. **Line 137:** Delete `write_json(tmp_path / deferred_rel, {"entries": []})`
3. **Lines 178-179:** Delete the two-element `"--deferred-registry", deferred_rel,` pair from the `argv` list

Do **not** touch line 102 (`"deferred_total": 0` is still a legitimate field in the minimal diff-report fixture — the downstream script still emits this key with value 0, and removing it may cause unrelated assertions to break).

**Verification:**
```
ClassicLib-rs/python-bindings/.venv/Scripts/python.exe -m pytest ClassicLib-rs/python-bindings/tests/test_parity_gate_tooling.py -q
```
Expected: `3 passed`.

**Scope of fix:** 1 file, 4 deletions, no new code, no API changes. No parity-gate regeneration needed — baselines were already refreshed in commit `12acb63e`. This is a pure test-maintenance catch-up that was missed in the original refactor commit.

## Open Questions

None. The removal commit message explicitly calls out "Update tests to remove deferred_registry usage" as an intended line item, and the sibling test file was updated correctly — this is an unambiguous oversight, not a design question.

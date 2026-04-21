---
phase: 260410-wsw
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - ClassicLib-rs/python-bindings/tests/test_parity_gate_tooling.py
autonomous: true
requirements:
  - QUICK-260410-wsw
must_haves:
  truths:
    - "test_parity_gate_tooling.py collects and runs cleanly"
    - "The parametrized test_update_baseline_flag_refreshes_stale_baseline passes for both node and python bindings"
    - "No reference to --deferred-registry or deferred_registry.json remains in the test file"
  artifacts:
    - path: "ClassicLib-rs/python-bindings/tests/test_parity_gate_tooling.py"
      provides: "Updated parity gate tooling tests without removed --deferred-registry flag"
      contains: "test_update_baseline_flag_refreshes_stale_baseline"
  key_links:
    - from: "test_parity_gate_tooling.py"
      to: "tools/{node,python}_api_parity/check_parity_gate.py"
      via: "argv-based CLI invocation via module.main()"
      pattern: "--runtime-registry"
---

<objective>
Fix 2 pytest failures in test_parity_gate_tooling.py caused by the removal of the `--deferred-registry` flag from parity gate scripts in commit 12acb63e.

Purpose: Catch up a test file that was missed when the deferred-registry concept was eliminated in the v9.1.0 Phase 6 Tier-1/Tier-2 collapse. The sibling test (test_binding_coverage_tooling.py) was updated in the same commit but this file was overlooked.

Output: A passing test file with 4 lines deleted — no new code, no API changes, no parity gate regeneration.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/quick/260410-wsw-fix-pytest-failures-related-to-removed-d/260410-wsw-RESEARCH.md
@ClassicLib-rs/python-bindings/tests/test_parity_gate_tooling.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Delete --deferred-registry references from test_parity_gate_tooling.py</name>
  <files>ClassicLib-rs/python-bindings/tests/test_parity_gate_tooling.py</files>
  <action>
Delete exactly 4 lines from `ClassicLib-rs/python-bindings/tests/test_parity_gate_tooling.py` per the locked RESEARCH.md findings:

1. **Line 131:** Delete `    deferred_rel = "deferred_registry.json"`
2. **Line 137:** Delete `    write_json(tmp_path / deferred_rel, {"entries": []})`
3. **Lines 178-179:** Delete these two consecutive entries from the `argv` list:
   ```
           "--deferred-registry",
           deferred_rel,
   ```

DO NOT touch line 102 (`"deferred_total": 0,`) — the downstream script still emits this key with value 0 in its coverage summary, and the minimal_coverage_summary fixture must retain it. The RESEARCH.md explicitly flags this as "keep as-is."

DO NOT add any replacement code. There is no replacement flag — `--runtime-registry` at lines 176-177 is now the sole registry input to the parity gate scripts. The fix is pure deletion.

DO NOT rename variables, reorder argv, or otherwise refactor. Keep the diff minimal so it mirrors the pattern used in commit 12acb63e for test_binding_coverage_tooling.py.

Use the Edit tool for each deletion (4 targeted edits, or combine into one multi-edit). Verify no other `deferred_registry` / `deferred-registry` substrings exist in the file after edits — per RESEARCH.md grep, only lines 102 (keep), 131, 137, 178, 179 contained matches.
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "Set-Location 'J:\CLASSIC-Fallout4'; uv run pytest ClassicLib-rs/python-bindings/tests/test_parity_gate_tooling.py -q"</automated>
  </verify>
  <done>
    - `uv run pytest ClassicLib-rs/python-bindings/tests/test_parity_gate_tooling.py -q` reports `3 passed` (up from 2 failed, 1 passed).
    - `grep -n "deferred-registry\|deferred_rel" ClassicLib-rs/python-bindings/tests/test_parity_gate_tooling.py` returns no hits.
    - Line 102 (`"deferred_total": 0,`) is still present and unchanged.
    - Exactly 4 lines deleted from the file; no additions.
  </done>
</task>

</tasks>

<verification>
Run the affected test file (PowerShell, per project rule; `uv run` per CLAUDE.md Python venv guidance):

```
pwsh -ExecutionPolicy Bypass -Command "Set-Location 'J:\CLASSIC-Fallout4'; uv run pytest ClassicLib-rs/python-bindings/tests/test_parity_gate_tooling.py -q"
```

Expected: `3 passed` — both previously-failing parametrized cases (`[node-...]` and `[python-...]`) plus the pre-existing passing `test_load_module_restores_import_state`.

Negative check: Confirm no stray references remain:
```
pwsh -Command "Select-String -Path 'ClassicLib-rs/python-bindings/tests/test_parity_gate_tooling.py' -Pattern 'deferred-registry|deferred_rel'"
```
Expected: no output.
</verification>

<success_criteria>
- test_parity_gate_tooling.py: 3 tests pass, 0 failures
- No references to `--deferred-registry` or `deferred_rel` in the file
- Line 102 (`deferred_total` in coverage summary fixture) preserved
- Diff is pure deletion, exactly 4 lines removed, no additions
</success_criteria>

<output>
After completion, create `.planning/quick/260410-wsw-fix-pytest-failures-related-to-removed-d/260410-wsw-SUMMARY.md` documenting the fix (4 line deletions, test now 3/3 passing, root cause: missed test-file update in commit 12acb63e).
</output>

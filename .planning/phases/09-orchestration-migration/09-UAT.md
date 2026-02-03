---
status: diagnosed
phase: 09-orchestration-migration
source: 09-01-SUMMARY.md, 09-02-SUMMARY.md
started: 2026-02-03T16:30:00Z
updated: 2026-02-03T17:30:00Z
---

## Current Test

[testing complete - gaps diagnosed, closure plans created]

## Tests

### 1. Python Orchestrator Files Removed
expected: The old Python orchestrator files (orchestrator_core.py, hybrid_orchestrator.py) should NOT exist in ClassicLib/scanning/logs/
result: pass

### 2. CLI Scanning Works with Rust
expected: Running CLI scanner processes crash logs successfully using Rust orchestrator. Execute: `uv run python CLASSIC_ScanLogs.py` and confirm it scans logs without errors.
result: issue
reported: "CLI crashes on startup with RuntimeError: yaml_settings() called from async context. The CLI runs in asyncio.run() but ScanLogsExecutor.__init__ calls crashlogs_get_files() which calls classic_settings() - a sync function that detects async context and fails."
severity: blocker

### 3. GUI Scanning Works with Rust
expected: GUI application launches and can scan crash logs. The scanning process uses the Rust orchestrator (no Python fallback). Run: `uv run python CLASSIC_Interface.py`
result: issue
reported: "Generated report/log files contain no analysis data - just a message that the log was scanned, no errors/suspects/mods analysis"
severity: major

### 4. Progress Callback Fires During Batch
expected: When scanning multiple logs, progress updates appear in the console/GUI showing current file and progress (e.g., "Processing 2/5: crash-log-name")
result: pass

### 5. Cancellation Token Stops Processing
expected: If you initiate a batch scan and cancel it mid-way (via GUI cancel button or Ctrl+C in CLI), processing stops and partial results are returned.
result: skipped
reason: No cancellation button in GUI progress window, CLI is broken. Rust cancellation token API exists but no UI exposes it yet.

### 6. Factory Returns Rust Orchestrator
expected: Run: `uv run python -c "from ClassicLib.integration.factory import get_orchestrator; o = get_orchestrator(); print(type(o))"` - Should show ClassicOrchestrator (Rust wrapper), not OrchestratorCore
result: pass

## Summary

total: 6
passed: 3
issues: 2
pending: 0
skipped: 1

## Gaps

- truth: "CLI scanner starts and processes crash logs without errors"
  status: diagnosed
  reason: "User reported: CLI crashes on startup with RuntimeError: yaml_settings() called from async context. The CLI runs in asyncio.run() but ScanLogsExecutor.__init__ calls crashlogs_get_files() which calls classic_settings() - a sync function that detects async context and fails."
  severity: blocker
  test: 2
  root_cause: "ScanLogsExecutor.__init__ (line 83) calls crashlogs_get_files(), which calls classic_settings() and yaml_settings(). These sync functions detect async context and raise RuntimeError. The CLI creates ScanLogsExecutor inside run_scan() which is inside asyncio.run()."
  artifacts:
    - "CLASSIC_ScanLogs.py:173 - executor creation inside async context"
    - "ClassicLib/scanning/logs/executor.py:83 - crashlogs_get_files() call"
    - "ClassicLib/scanning/logs/util_legacy.py:301-302 - classic_settings/yaml_settings calls"
    - "ClassicLib/io/yaml/convenience.py:156-159 - async context detection"
  missing:
    - "Move ScanLogsExecutor creation to sync context (before asyncio.run)"
  debug_session: ""
  closure_plan: "09-03-PLAN.md"

- truth: "Generated report files contain crash log analysis data (errors, suspects, mods)"
  status: diagnosed
  reason: "User reported: Generated report/log files contain no analysis data - just a message that the log was scanned, no errors/suspects/mods analysis"
  severity: major
  test: 3
  root_cause: "Rust OrchestratorCore::process_log() (lines 712-931) builds a minimal debug-style report with 'Analysis of:', 'Segments found:', and basic summary. It does NOT use the proper ReportGenerator to create the full markdown report with all analysis sections (Header, Main Error, System Info, Crashgen Info, Suspects, Mods, Plugins, FormIDs, Records, Settings, Footer)."
  artifacts:
    - "rust/business-logic/classic-scanlog-core/src/orchestrator.rs:712-931 - minimal report generation"
    - "rust/business-logic/classic-scanlog-core/src/report.rs - ReportGenerator not used"
  missing:
    - "Integrate ReportGenerator into process_log() for full report output"
    - "Use ReportComposer to assemble all analysis sections"
    - "Match the output format that Python's report generation produced"
  debug_session: ""
  closure_plan: "09-04-PLAN.md"

## Closure Plans

Gap closure plans created:
- **09-03-PLAN.md**: Fix CLI async context issue (Gap 1 - Blocker)
- **09-04-PLAN.md**: Fix empty report data issue (Gap 2 - Major)

Both plans can execute in parallel (Wave 1).

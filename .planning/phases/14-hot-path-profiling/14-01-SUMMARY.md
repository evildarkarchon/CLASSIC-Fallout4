---
phase: 14-hot-path-profiling
plan: 01
subsystem: profiling-infrastructure
tags: [flamegraph, py-spy, profiling, cargo-aliases, powershell]
dependency-graph:
  requires: [13-benchmark-infrastructure]
  provides: [flamegraph-scripts, pyspy-scripts, cargo-profiling-aliases]
  affects: [14-02-cache-instrumentation, 16-performance-optimization]
tech-stack:
  added: []
  patterns: [quick-thorough-modes, timestamped-output, cargo-aliases]
key-files:
  created:
    - rust/.cargo/config.toml
    - scripts/profile/run_flamegraph.ps1
    - scripts/profile/run_pyspy.ps1
  modified:
    - .gitignore
decisions:
  - id: PROFILE-01
    summary: "Force-add rust/.cargo/config.toml despite .cargo/ gitignore"
    context: "Project-level cargo config should be tracked for team sharing"
    alternatives: ["Modify gitignore pattern", "Keep file untracked"]
    rationale: "Force-add ensures file is tracked; negation patterns unreliable"
  - id: PROFILE-02
    summary: "Native frames enabled by default in py-spy"
    context: "Combined Python+Rust stacks require --native flag"
    alternatives: ["Require explicit flag", "Disable by default"]
    rationale: "Primary use case is Rust hot path analysis; native frames essential"
metrics:
  duration: "~4m"
  completed: "2026-02-05"
---

# Phase 14 Plan 01: Profiling Infrastructure Setup Summary

**One-liner:** Cargo flamegraph and py-spy scripts with quick/thorough modes for Rust hot path profiling.

## What Was Done

### Task 1: Cargo Profiling Aliases
- Created `rust/.cargo/config.toml` with aliases: `flame`, `flame-bench`, `profile-build`
- Updated `.gitignore` to allow tracking project-level cargo config
- Verified `[profile.release-with-debug]` already exists in `rust/Cargo.toml`

### Task 2: Flamegraph Script
- Created `scripts/profile/run_flamegraph.ps1` (267 lines)
- Quick mode: 99 Hz sampling, 10s duration
- Thorough mode: 997 Hz sampling, 60s duration
- Features: `-Crate`, `-Bench`, `-BenchFilter`, `-Frequency`, `-Duration`, `-Open`
- Output: `target/profiling/flamegraphs/flamegraph-{timestamp}.svg`

### Task 3: py-spy Script
- Created `scripts/profile/run_pyspy.ps1` (370 lines)
- Native frames enabled by default for combined Python+Rust stacks
- Quick mode: 10s duration; Thorough mode: 60s duration
- Multiple formats: flamegraph (SVG), speedscope (JSON), raw (text)
- Features: `-EntryPoint`, `-NoNative`, `-Format`, `-Duration`, `-Pid`, `-Open`
- Output: `target/profiling/pyspy/pyspy-{timestamp}.{ext}`
- Includes Administrator privilege warning on Windows

## Verification Results

| Check | Status |
|-------|--------|
| `cargo flame --help` works | Pass |
| `rust/.cargo/config.toml` exists with aliases | Pass |
| `run_flamegraph.ps1` exists (267 lines > 50) | Pass |
| `run_pyspy.ps1` exists (370 lines > 50) | Pass |
| Both scripts have help text | Pass |

## Key Artifacts

| Artifact | Purpose |
|----------|---------|
| `rust/.cargo/config.toml` | Cargo aliases for profiling commands |
| `scripts/profile/run_flamegraph.ps1` | Flamegraph generation with quick/thorough modes |
| `scripts/profile/run_pyspy.ps1` | py-spy profiling with native Rust frame support |

## Commits

| Hash | Type | Description |
|------|------|-------------|
| `7747bd47` | chore | Configure Cargo profiling aliases |
| `dec483c0` | feat | Add flamegraph PowerShell runner script |
| `12b1b144` | feat | Add py-spy PowerShell runner for combined Python+Rust profiling |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] .cargo/ directory was gitignored**
- **Found during:** Task 1
- **Issue:** `.cargo/` pattern in `.gitignore` prevented tracking `rust/.cargo/config.toml`
- **Fix:** Added negation pattern `!rust/.cargo/config.toml` and used `git add -f`
- **Files modified:** `.gitignore`
- **Commit:** `7747bd47`

## Next Phase Readiness

Plan 14-02 (Cache Hit Rate Instrumentation) is ready to proceed:
- Profiling infrastructure is in place
- Scripts follow established patterns from Phase 13
- Output directories are consistent with benchmark infrastructure

## Usage Examples

```powershell
# Generate flamegraph for Rust code
.\scripts\profile\run_flamegraph.ps1

# Thorough flamegraph for specific crate
.\scripts\profile\run_flamegraph.ps1 -Mode thorough -Crate classic-yaml-core -Open

# Profile Python+Rust with py-spy
.\scripts\profile\run_pyspy.ps1

# Profile CLI entry point with speedscope output
.\scripts\profile\run_pyspy.ps1 -EntryPoint CLASSIC_ScanLogs.py -Format speedscope -Open
```

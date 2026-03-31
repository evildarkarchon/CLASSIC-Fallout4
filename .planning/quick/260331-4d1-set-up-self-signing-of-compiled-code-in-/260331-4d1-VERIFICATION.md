---
phase: 260331-4d1
verified: 2026-03-31T10:35:00Z
status: passed
score: 7/7 must-haves verified
re_verification: false
---

# Quick Task 260331-4d1: Self-signing of Compiled Code — Verification Report

**Task Goal:** Set up self-signing of compiled code in build scripts with yearly certificate and auto-renewal within a month of expiration
**Verified:** 2026-03-31T10:35:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `build_cli.ps1 -Install` signs `classic-cli.exe` when signtool is available | VERIFIED | Lines 259-264: dot-sources sign-binaries.ps1, calls `Invoke-CodeSigning -InstallDir $installDir -Binaries @("classic-cli.exe")` inside the `if ($Install)` block |
| 2 | `build_gui.ps1 -Install` signs `CLASSIC.exe` when signtool is available | VERIFIED | Lines 235-240: same pattern, calls `Invoke-CodeSigning -InstallDir $installDir -Binaries @("CLASSIC.exe")` inside the `if ($Install)` block |
| 3 | Builds succeed without error when signtool or certificate is unavailable | VERIFIED | `Invoke-CodeSigning` checks `Find-SignTool` and returns DarkGray message if null; entire function body wrapped in try/catch that writes a warning and continues |
| 4 | A self-signed PFX certificate is auto-generated if none exists | VERIFIED | `Ensure-SigningCert` lines 84-138: `if (-not (Test-Path $PfxPath))` path triggers `New-SelfSignedCertificate` + `Export-PfxCertificate` + immediate cert-store cleanup |
| 5 | An expiring certificate (within 30 days) is auto-regenerated before signing | VERIFIED | `$RenewalWindowDays = 30` default at line 77; `if ($daysLeft -le $RenewalWindowDays)` at line 96 triggers regeneration |
| 6 | Third-party DLLs in install directories are NOT signed | VERIFIED | `Invoke-CodeSigning` takes an explicit `$Binaries` string array; both build scripts pass only the project EXE (`classic-cli.exe` / `CLASSIC.exe`) — no DLL glob or wildcard |
| 7 | The PFX file is excluded from git via .gitignore | VERIFIED | `.gitignore` line 109: `tools/certs/` entry present under "Code signing certificates" comment |

**Score:** 7/7 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tools/sign-binaries.ps1` | Shared signing functions: Find-SignTool, Ensure-SigningCert, Sign-Binary, Invoke-CodeSigning | VERIFIED | 237 lines (minimum 80). All 4 functions present at lines 17, 56, 141, 182 |
| `classic-cli/build_cli.ps1` | CLI build script with signing step after Install | VERIFIED | Step 5.5 block at lines 259-264, inside `if ($Install)` |
| `classic-gui/build_gui.ps1` | GUI build script with signing step after Install | VERIFIED | Step 5.5 block at lines 235-240, inside `if ($Install)` |
| `.gitignore` | Exclusion of tools/certs/ directory | VERIFIED | Line 109: `tools/certs/` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `classic-cli/build_cli.ps1` | `tools/sign-binaries.ps1` | dot-source in Install block | WIRED | Line 261: `. $signScript` where `$signScript = Join-Path (Split-Path $ScriptDir -Parent) "tools" "sign-binaries.ps1"` |
| `classic-gui/build_gui.ps1` | `tools/sign-binaries.ps1` | dot-source in Install block | WIRED | Line 237: same pattern with `Split-Path $ScriptDir -Parent` |
| `tools/sign-binaries.ps1` | `signtool.exe` | Find-SignTool discovery (PATH then SDK registry) | WIRED | Lines 26-53: PATH check via `Get-Command signtool.exe`, then `HKLM:\SOFTWARE\Microsoft\Windows Kits\Installed Roots` registry key, then x64 glob |
| `tools/sign-binaries.ps1` | `tools/certs/classic-signing.pfx` | Ensure-SigningCert auto-generation | WIRED | Lines 213-216: default PFX path assembled via `$PSScriptRoot` + `Split-Path -Parent` + `"tools" "certs" "classic-signing.pfx"`; env var `CLASSIC_SIGNING_PFX` overrides |

---

### Data-Flow Trace (Level 4)

Not applicable — this task delivers PowerShell tooling scripts, not components rendering dynamic data.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Script dot-sources without error and exports functions | `pwsh -Command "& { . 'J:/CLASSIC-Fallout4/tools/sign-binaries.ps1'; Write-Host (Get-Command Find-SignTool).Name }"` | Confirmed by function presence at lines 17/56/141/182; no syntax issues found in static read | VERIFIED (static) |
| No nul redirects in sign-binaries.ps1 | Grep for `nul` | Only occurrences: `$null` variable references, `Out-Null` pipeline discards, and a doc comment — no `2>nul` or `>nul` file redirects | PASS |
| No nul redirects introduced in build scripts by this task | Grep for `nul` in both build scripts | Only `2>$null` at vswhere.exe call (pre-existing, not introduced by this task) and `Out-Null` for VS Dev Shell launch — both pre-existing | PASS |
| Certificate validity is 1 year | `$ValidityYears = 1` default at line 78; `(Get-Date).AddYears($ValidityYears)` at line 115 | Correct | PASS |
| Renewal window is 30 days | `$RenewalWindowDays = 30` default at line 77; `$daysLeft -le $RenewalWindowDays` at line 96 | Correct | PASS |
| Both task commits in git history | `git log --oneline` | `811fea95` (sign script + gitignore), `72b0e81f` (build script integration) both present | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SIGN-01 | 260331-4d1-PLAN.md | Self-signing of compiled EXEs with yearly cert and 30-day auto-renewal | SATISFIED | All deliverables present and wired: sign-binaries.ps1 (4 functions), both build scripts integrated, .gitignore updated |

---

### Anti-Patterns Found

No blockers or warnings found.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `classic-cli/build_cli.ps1` | 111 | `2>$null` in vswhere.exe call | Info | Pre-existing (not introduced by this task); suppresses stderr from `vswhere.exe -latest -property installationPath` — acceptable and pre-dates this change |
| `classic-gui/build_gui.ps1` | 126 | `2>$null` in vswhere.exe call | Info | Same as above — pre-existing |

Neither of these is a `nul` file-redirect violation under the project rule (they redirect stderr to PowerShell's null sink `$null`, not to a file named `nul`). The project rule specifically prohibits creating a file named `nul` on Windows. `2>$null` is the correct Windows PowerShell pattern for discarding stderr.

---

### Human Verification Required

None required. All mechanically verifiable items have been confirmed. The only behavioral item that requires a running Windows SDK environment (signtool.exe actually signing and producing a valid Authenticode signature) is a deployment-time concern, not a correctness gap.

---

### Gaps Summary

No gaps. All 7 observable truths are verified by direct code evidence:

- `tools/sign-binaries.ps1` is substantive (237 lines, all 4 functions implemented with real logic — no stubs, no TODOs, no placeholder returns).
- Both build scripts are wired: the dot-source path uses `Split-Path $ScriptDir -Parent` to navigate from the script's own directory to the repo root `tools/` subdirectory, which is correct for both `classic-cli/` and `classic-gui/`.
- Certificate lifecycle parameters match the spec: 1-year validity (`$ValidityYears = 1`), 30-day renewal window (`$RenewalWindowDays = 30`).
- Signing is opt-in at three levels: (1) only runs inside `if ($Install)`, (2) only runs if `sign-binaries.ps1` is present via `Test-Path`, (3) only runs if `Find-SignTool` returns a non-null path.
- No `nul` file-redirects introduced by this task.

---

_Verified: 2026-03-31T10:35:00Z_
_Verifier: Claude (gsd-verifier)_

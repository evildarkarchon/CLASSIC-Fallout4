# Phase 5: CI Enforcement - Research

**Researched:** 2026-04-09
**Domain:** GitHub Actions CI workflows, branch protection, parity gate enforcement
**Confidence:** HIGH

## Summary

Phase 5 is a CI/infrastructure phase that wires three existing parity gate scripts into GitHub Actions workflows so every PR is blocked on parity drift. The phase creates one new CI job (CXX parity gate in `ci-cpp.yml`), one new local assertion script (`tools/test_triple_gate_failure.py`), and configures branch protection to list all three gate jobs as required status checks.

The technical risk is low: all three gate scripts already exist and work, the two existing CI workflows (`ci-python-bindings.yml`, `ci-typescript.yml`) already have parity gate jobs that serve as templates, and the new CXX gate job is the simplest of the three (only requires Python 3.12 + checkout, no Rust build). The triple-gate assertion script is a local-only test that temporarily injects a canary function and runs the three gates, requiring careful cleanup via `try/finally`.

**Primary recommendation:** Mirror the existing `ci-python-bindings.yml::parity-gates` job structure for the new CXX gate job, add `needs: [cxx-parity-gate]` to the existing `cli-tests` and `gui-tests` jobs, and include manual branch protection setup instructions in the PR description.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** CXX parity gate runs as a new `cxx-parity-gate` job in `.github/workflows/ci-cpp.yml`. It runs BEFORE `cli-tests` and `gui-tests` -- both existing jobs gain `needs: [cxx-parity-gate]` so parity drift blocks the expensive MSVC builds.
- **D-02:** The job is lightweight: only requires `actions/checkout@v6` + `actions/setup-python@v6` (Python 3.12) + one `run:` step. No Rust toolchain, no MSVC, no vcpkg. Target timeout: 10 minutes.
- **D-03:** The job runs only `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` -- CXX-only, no Python stub validation.
- **D-04:** No modifications to `ci-python-bindings.yml`, `ci-typescript.yml`, or `ci-rust.yml`.
- **D-05:** CI-06 is satisfied by the existing `check_parity_gate.py` stale-artifact detection (Phase 1 D-14). No separate freshness step or script needed.
- **D-06:** CXX-generated headers are NOT committed and do NOT get a freshness gate.
- **D-07:** The single CI step covers both CI-03 (drift detection) and CI-06 (freshness) in one invocation.
- **D-08:** A checked-in Python script at `tools/test_triple_gate_failure.py` proves the triple-gate invariant by injecting `pub fn _ci05_canary() {}` into `classic-shared-core/src/lib.rs`, running all three gates, asserting all exit non-zero, and reverting.
- **D-09:** The canary function is injected into `classic-shared-core` because it is the foundation crate tracked by all three gates.
- **D-10:** The script is local-only -- no CI workflow dispatch job. Run once during verification and on-demand by maintainers.
- **D-11:** Branch protection is configured manually via GitHub Settings. The PR description includes step-by-step instructions. No `gh api` automation.
- **D-12:** All three parity gate jobs are verified as required status checks: "Python Parity Gates", "Node Parity Gates", and "CXX Parity Gate".
- **D-13:** The CXX gate check is added to branch protection AFTER the first successful CI run. GitHub requires a status check to have completed at least once before it can be registered as required.
- **D-14:** CI-01/CI-02 verification is observational: confirm Python and Node gate jobs pass on a recent CI run, no code changes needed.

### Claude's Discretion
- The exact wording of the PR description's branch protection checklist
- Whether to add a diagnostic upload step (artifact) to the CXX gate job on failure (mirrors the pattern in Python/Node gate jobs)
- The exact structure and CLI flags of `test_triple_gate_failure.py` (e.g., `--repo-root`, `--verbose`, output format)
- Whether the triple-gate test script saves its output to a file or just prints to stdout

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CI-01 | Python parity gate runs in CI on every PR and blocks merges (verify stays green after PYT promotion) | Existing `ci-python-bindings.yml::parity-gates` job already runs. Observational verification only. |
| CI-02 | Node parity gate runs in CI on every PR and blocks merges (verify stays green after NODE promotion) | Existing `ci-typescript.yml::parity-gates` job already runs. Observational verification only. |
| CI-03 | A new CI job runs `tools/cxx_api_parity/check_parity_gate.py` on every PR | New `cxx-parity-gate` job in `ci-cpp.yml` mirroring Python gate job structure |
| CI-04 | CXX parity gate is added to branch-protection required checks in the same PR | Manual GitHub Settings update with step-by-step PR description checklist |
| CI-05 | All three gates wired so adding a new public Rust API fails CI until all bindings expose it (verified by explicit assertion test) | `tools/test_triple_gate_failure.py` canary injection script |
| CI-06 | `.gitignore`-respecting freshness gate for committed CXX artifacts | Already satisfied by `check_parity_gate.py` stale-artifact detection (Phase 1 D-14); no new work |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Never output to `nul` on Windows** -- creates undeletable file on system drives.
- **Use PowerShell wrappers for C++ tests** -- never raw ctest. (Not directly relevant to this phase since no C++ builds are run.)
- **Commit prefix convention:** `Feat:`, `Fix:`, `Docs:`, `Refactor:`, `Chore:`, `Update:`.
- **Prefer PowerShell over Bash** for tool execution on Windows, though the CI workflow itself uses GitHub Actions YAML syntax.
- **When fixing tests, focus on fixing the underlying issue** rather than just making the test pass.

## Standard Stack

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| GitHub Actions | N/A | CI/CD platform | Already used by all 4 existing workflow files |
| actions/checkout | v6 | Repository checkout | Used by every existing CI job in the project |
| actions/setup-python | v6 | Python 3.12 setup | Used by `ci-python-bindings.yml::parity-gates` job |
| Python | 3.12 | Gate script runtime | All three gate scripts are Python; CI pins 3.12 |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| actions/upload-artifact | v6 | Diagnostic upload on failure | Optional for CXX gate job (mirrors Python/Node pattern) |
| `subprocess` (stdlib) | N/A | Run gate scripts from triple-gate test | Triple-gate assertion script invokes all three gates |

### No New Dependencies
This phase adds NO new Python packages, no new GitHub Actions marketplace actions beyond what the project already uses, and no new Rust/C++ dependencies. Everything is stdlib Python + existing GitHub Actions.

## Architecture Patterns

### CI Workflow Job Dependency Graph (After Phase 5)

```
ci-cpp.yml:
  cxx-parity-gate (new, ~5-10min)
    |
    +-- cli-tests (existing, needs: [cxx-parity-gate])
    +-- gui-tests (existing, needs: [cxx-parity-gate])

ci-python-bindings.yml (UNCHANGED):
  parity-gates (~5min)
    |
    +-- build-and-test (needs: [parity-gates])

ci-typescript.yml (UNCHANGED):
  parity-gates (~30min, includes Rust build for NAPI binary)
    |
    +-- build-and-test (matrix: [bun, node], needs: [parity-gates])
```

### Pattern 1: Lightweight Parity Gate Job

**What:** A CI job that only checks out the repo and runs a Python source-parsing script -- no Rust build, no MSVC, no vcpkg.
**When to use:** When the gate script only needs to parse source files and compare against a committed baseline.
**Example (from existing `ci-python-bindings.yml::parity-gates`):**

```yaml
parity-gates:
  name: Python Parity Gates
  runs-on: windows-latest
  timeout-minutes: 30
  steps:
    - uses: actions/checkout@v6
    - name: Set up Python
      uses: actions/setup-python@v6
      with:
        python-version: "3.12"
    - name: Run parity gate
      run: python tools/python_api_parity/check_parity_gate.py --repo-root .
```

**CXX gate follows the same pattern** but is even simpler (one `run:` step vs two).

### Pattern 2: Gate-Before-Build Dependency

**What:** Expensive build jobs declare `needs: [gate-job]` so they only run when parity checks pass.
**When to use:** When the gate is cheap (~5min) and the builds are expensive (~90-120min).
**Existing usage:** Both Python and Node CI workflows use this pattern.

```yaml
cli-tests:
  name: CLI Tests
  needs: [cxx-parity-gate]    # <-- NEW: added dependency
  runs-on: windows-latest
  # ... rest unchanged
```

### Pattern 3: Diagnostic Artifact Upload on Failure

**What:** On gate failure, upload the `parity-artifacts/` directory as a CI artifact for debugging.
**Existing usage:** Both Python and Node workflows upload `parity-artifacts/` on failure.

```yaml
- name: Upload parity diagnostics
  if: failure()
  uses: actions/upload-artifact@v6
  with:
    name: cxx-parity-diagnostics
    path: ClassicLib-rs/cpp-bindings/classic-cpp-bridge/parity-artifacts/
    if-no-files-found: warn
    retention-days: 7
```

**Recommendation:** Include this step (Claude's discretion per D-11). It costs nothing when the gate passes and provides immediate debugging value on failure.

### Pattern 4: Canary Injection Test Script

**What:** A Python script that temporarily modifies source code, runs validation tools, asserts expected failures, and restores the original state.
**Critical safety:** Must use `try/finally` or `atexit` to guarantee file restoration even if a gate script crashes or times out.

```python
import subprocess
import sys
from pathlib import Path

def main():
    lib_rs = Path("ClassicLib-rs/foundation/classic-shared-core/src/lib.rs")
    original = lib_rs.read_text(encoding="utf-8")
    canary = "\npub fn _ci05_canary() {}\n"
    
    try:
        lib_rs.write_text(original + canary, encoding="utf-8")
        # Run all three gates, collect results
        results = {}
        for name, cmd in [
            ("CXX", [...]),
            ("Python", [...]),
            ("Node", [...]),
        ]:
            result = subprocess.run(cmd, capture_output=True, text=True)
            results[name] = result.returncode
    finally:
        lib_rs.write_text(original, encoding="utf-8")
    
    # Assert all three failed
    for name, rc in results.items():
        assert rc != 0, f"{name} gate should have failed but returned {rc}"
```

### Anti-Patterns to Avoid

- **Hardcoding workflow job IDs as status check names:** The status check name is the job's `name:` field, NOT the job ID. Using `cxx-parity-gate` (the ID) instead of `CXX Parity Gate` (the name) in branch protection will silently fail to match.
- **Running triple-gate test in CI:** The script modifies source files, which would dirty the checkout. It is local-only (D-10).
- **Forgetting to add `needs:` to BOTH downstream jobs:** Both `cli-tests` AND `gui-tests` must depend on the new gate job. Missing one would allow merge with broken parity on that path.
- **Using `--deferred-registry` flag for CXX gate:** The CXX gate intentionally has NO deferred registry concept (Phase 1 D-12).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CI workflow syntax | Custom shell-based CI | GitHub Actions YAML | Project standard; all 4 existing workflows use it |
| Parity gate invocation | New wrapper scripts | Existing `check_parity_gate.py --repo-root .` | Scripts are complete from Phases 1, 3, 4 |
| Branch protection automation | `gh api` scripts or PAT-based automation | Manual GitHub Settings UI | D-11 locks this as manual; avoids PAT security complexity |
| CXX artifact freshness gate | Separate freshness script | Existing `check_parity_gate.py` stale-artifact detection | D-05/D-07; already built in Phase 1 (D-14) |

**Key insight:** This phase is pure wiring -- every gate script and detection mechanism already exists. The new code is limited to one CI job definition, one test script, and branch protection configuration.

## Common Pitfalls

### Pitfall 1: Status Check Name Mismatch
**What goes wrong:** The job `name:` field in the workflow YAML does not match what is entered in GitHub branch protection settings, so the required check never becomes "passing" and all PRs are blocked.
**Why it happens:** GitHub status check matching uses the `name:` field (e.g., "CXX Parity Gate"), not the job ID (e.g., `cxx-parity-gate`). Users often search for the wrong string.
**How to avoid:** After the first successful CI run, go to GitHub Settings > Branches > main > Edit and search for "CXX Parity Gate" (the exact `name:` value from the YAML). Verify it appears in the dropdown before adding it.
**Warning signs:** The check shows as "Pending" forever on new PRs despite the workflow succeeding.

### Pitfall 2: Branch Protection Timing Gap (CI-04)
**What goes wrong:** The CXX gate CI job is merged but branch protection is not updated yet, creating a window where the gate exists but does not block merge.
**Why it happens:** GitHub requires a status check to have completed at least once before it can be listed as required. The check only completes when the PR that adds it runs CI.
**How to avoid:** D-13 defines the sequence: merge the CI job PR, then immediately configure branch protection before any other PRs are merged. Include step-by-step instructions in the PR description.
**Warning signs:** After merging the CI job PR, other PRs can be merged without the CXX gate passing.

### Pitfall 3: Triple-Gate Test Leaves Dirty Source
**What goes wrong:** The `test_triple_gate_failure.py` script crashes partway through and leaves the canary function in `lib.rs`, corrupting the working tree.
**Why it happens:** A gate script might raise an unexpected exception, or the user interrupts the script with Ctrl+C.
**How to avoid:** The script MUST use `try/finally` to restore `lib.rs` to its original content. Read the original content BEFORE injection and write it back in the `finally` block. Handle `KeyboardInterrupt` explicitly.
**Warning signs:** `git diff` shows unexpected changes in `classic-shared-core/src/lib.rs` after running the script.

### Pitfall 4: Node Gate Requires Rust Build
**What goes wrong:** The triple-gate test script tries to run the Node gate locally, but the Node gate's `check_parity_gate.py` only parses source files (no Rust build needed). However, the CI workflow for Node builds the NAPI binary before running gates.
**Why it happens:** Confusion between what the gate script needs (only source parsing) vs what the full CI workflow does (build + gate + test). The `check_parity_gate.py` scripts for all three gates are source-only parsers.
**How to avoid:** The triple-gate test script invokes `python tools/{gate}/check_parity_gate.py --repo-root .` directly, NOT the full CI workflow. All three gate scripts are source-only and need no build.
**Warning signs:** The test script takes too long or fails with "NAPI binary not found" (this would be wrong -- the gate script does not need the binary).

### Pitfall 5: Windows Path Issues in subprocess
**What goes wrong:** The triple-gate test script fails on Windows because `subprocess.run(["python", ...])` resolves to the wrong Python or because paths use forward slashes that Windows `cmd.exe` rejects.
**Why it happens:** Windows path handling and Python executable resolution can be fragile.
**How to avoid:** Use `sys.executable` instead of `"python"` to ensure the same Python interpreter is used. Use `Path` objects and convert to `str()` for subprocess arguments.
**Warning signs:** `FileNotFoundError` or `ModuleNotFoundError` when running gate scripts via subprocess.

## Code Examples

### CXX Gate Job (ci-cpp.yml addition)

```yaml
# Source: Modeled after ci-python-bindings.yml::parity-gates
cxx-parity-gate:
  name: CXX Parity Gate
  runs-on: windows-latest
  timeout-minutes: 10
  steps:
    - uses: actions/checkout@v6

    - name: Set up Python
      uses: actions/setup-python@v6
      with:
        python-version: "3.12"

    - name: Run CXX parity gate
      run: python tools/cxx_api_parity/check_parity_gate.py --repo-root .

    - name: Upload CXX parity diagnostics
      if: failure()
      uses: actions/upload-artifact@v6
      with:
        name: cxx-parity-diagnostics
        path: ClassicLib-rs/cpp-bindings/classic-cpp-bridge/parity-artifacts/
        if-no-files-found: warn
        retention-days: 7
```

### Existing Jobs Gain `needs:` Dependency

```yaml
cli-tests:
  name: CLI Tests
  needs: [cxx-parity-gate]
  runs-on: windows-latest
  timeout-minutes: 90
  # ... rest unchanged

gui-tests:
  name: GUI Tests
  needs: [cxx-parity-gate]
  runs-on: windows-latest
  timeout-minutes: 120
  # ... rest unchanged
```

### Triple-Gate Assertion Script Structure

```python
#!/usr/bin/env python3
"""Prove the triple-gate invariant (CI-05).

Injects a canary function into classic-shared-core and asserts that
all three parity gates (CXX, Python, Node) detect the undeclared API.

Usage:
    python tools/test_triple_gate_failure.py --repo-root .
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

CANARY_LINE = "\npub fn _ci05_canary() {}\n"

GATE_SCRIPTS = [
    ("CXX", "tools/cxx_api_parity/check_parity_gate.py"),
    ("Python", "tools/python_api_parity/check_parity_gate.py"),
    ("Node", "tools/node_api_parity/check_parity_gate.py"),
]

def main() -> int:
    parser = argparse.ArgumentParser(description="Triple-gate canary test (CI-05)")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--verbose", action="store_true", help="Print gate stdout/stderr")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    lib_rs = repo_root / "ClassicLib-rs" / "foundation" / "classic-shared-core" / "src" / "lib.rs"
    original_content = lib_rs.read_text(encoding="utf-8")

    results: dict[str, int] = {}
    try:
        lib_rs.write_text(original_content + CANARY_LINE, encoding="utf-8")
        for name, script in GATE_SCRIPTS:
            result = subprocess.run(
                [sys.executable, str(repo_root / script), "--repo-root", str(repo_root)],
                capture_output=True,
                text=True,
                cwd=str(repo_root),
            )
            results[name] = result.returncode
            if args.verbose:
                print(f"--- {name} gate (rc={result.returncode}) ---")
                if result.stdout:
                    print(result.stdout)
                if result.stderr:
                    print(result.stderr, file=sys.stderr)
    finally:
        lib_rs.write_text(original_content, encoding="utf-8")

    # Report results
    all_passed = True
    for name, rc in results.items():
        status = "FAIL (expected)" if rc != 0 else "PASS (UNEXPECTED)"
        print(f"  {name}: rc={rc} -> {status}")
        if rc == 0:
            all_passed = False

    if all_passed:
        print("\nTRIPLE-GATE TEST: PASS -- all three gates detected the canary")
        return 0
    else:
        print("\nTRIPLE-GATE TEST: FAIL -- not all gates detected the canary")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

### Gate Script Invocation Commands (Uniform Interface)

All three gate scripts share the same `--repo-root .` convention and exit-code semantics (0 = pass, 1 = drift):

```bash
# CXX gate
python tools/cxx_api_parity/check_parity_gate.py --repo-root .

# Python gate
python tools/python_api_parity/check_parity_gate.py --repo-root .

# Node gate
python tools/node_api_parity/check_parity_gate.py --repo-root .
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual parity checking | Automated gate scripts + committed baselines | Phase 1/3/4 (2026-04) | Gates exist and work; Phase 5 just wires them into CI |
| CXX bridge had no gate | `check_parity_gate.py` with source parsing | Phase 1 (2026-04) | Baseline-driven drift detection operational |
| Python/Node had Tier-2 deferrals | All entries promoted to Tier-1 | Phase 3/4 (2026-04) | No deferred entries; gates enforce full surface |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (via uv) |
| Config file | none -- pytest discovers via conftest.py in each test directory |
| Quick run command | `python -m pytest tools/cxx_api_parity/tests -q` |
| Full suite command | `python -m pytest tools/cxx_api_parity/tests tools/python_api_parity/tests tools/node_api_parity/tests -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CI-01 | Python gate stays green in CI | observational | Check CI run status via `gh run list` | N/A (manual verification) |
| CI-02 | Node gate stays green in CI | observational | Check CI run status via `gh run list` | N/A (manual verification) |
| CI-03 | CXX gate job exists in ci-cpp.yml | integration | Validate YAML structure + local gate run | Wave 0: YAML lint |
| CI-04 | Branch protection includes CXX gate | manual | GitHub Settings UI verification | N/A (manual) |
| CI-05 | Triple-gate canary detects undeclared API | integration | `python tools/test_triple_gate_failure.py --repo-root .` | Wave 0 |
| CI-06 | CXX freshness gate works | unit | `python -m pytest tools/cxx_api_parity/tests/test_gate.py -q` | Exists (Phase 1) |

### Sampling Rate
- **Per task commit:** `python tools/cxx_api_parity/check_parity_gate.py --repo-root .`
- **Per wave merge:** All three gate scripts + triple-gate test
- **Phase gate:** All gates green + CI run successful + branch protection verified

### Wave 0 Gaps
- [ ] `tools/test_triple_gate_failure.py` -- the triple-gate assertion script (CI-05), new file
- No framework install needed -- pytest already available via project's Python environment

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Gate scripts, CI job | Yes | 3.14.3 (local), 3.12 (CI) | -- |
| gh CLI | CI verification | Yes | 2.89.0 | Manual GitHub UI |
| GitHub Actions | CI workflows | Yes | N/A | -- |
| actions/checkout | CI job | Yes | v6 | -- |
| actions/setup-python | CI job | Yes | v6 | -- |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

## Open Questions

1. **Exact CXX gate job `name:` field value**
   - What we know: Must be searchable in GitHub branch protection settings. Convention from Python/Node is "X Parity Gates" (plural).
   - What's unclear: Should it be "CXX Parity Gate" (singular, since it's one gate) or "CXX Parity Gates" (plural, matching Python/Node naming)?
   - Recommendation: Use "CXX Parity Gate" (singular) since the CXX gate runs a single script (no stub validation step), unlike Python which runs two steps. This matches the CONTEXT.md D-12 wording.

2. **Whether Python 3.14 (local) vs 3.12 (CI) causes any gate script behavior differences**
   - What we know: Gate scripts use basic stdlib features (argparse, json, pathlib, subprocess). No 3.13+ features used.
   - What's unclear: Any edge cases with path handling or JSON serialization between versions.
   - Recommendation: LOW risk. The scripts are tested against 3.12 in CI; local 3.14 is only used for the triple-gate test which is not run in CI.

3. **Whether the Node gate's `--deferred-registry` default path will cause issues**
   - What we know: The file at `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json` exists. Phase 6 will make this argument optional.
   - What's unclear: After Phase 4 (Node Tier Collapse), is the deferred registry file empty or does it still contain entries?
   - Recommendation: LOW risk. The file exists and the gate runs green in CI. The triple-gate test uses `--repo-root .` which triggers default paths, so the file must be present.

## Sources

### Primary (HIGH confidence)
- `.github/workflows/ci-cpp.yml` -- current workflow structure, job names, step patterns (verified by reading file)
- `.github/workflows/ci-python-bindings.yml` -- existing parity gate job template (verified by reading file)
- `.github/workflows/ci-typescript.yml` -- existing Node parity gate job template (verified by reading file)
- `tools/cxx_api_parity/check_parity_gate.py` -- CXX gate script CLI interface and exit codes (verified by reading file)
- `tools/python_api_parity/check_parity_gate.py` -- Python gate CLI interface (verified by reading file)
- `tools/node_api_parity/check_parity_gate.py` -- Node gate CLI interface (verified by reading file)
- `ClassicLib-rs/foundation/classic-shared-core/src/lib.rs` -- canary injection target (verified by reading file)
- `.planning/phases/01-cxx-parity-gate-tooling/01-CONTEXT.md` -- Phase 1 decisions D-14, D-16 (verified by reading file)
- `.planning/phases/05-ci-enforcement/05-CONTEXT.md` -- Phase 5 locked decisions (verified by reading file)

### Secondary (MEDIUM confidence)
- [GitHub community discussion on status check naming](https://github.com/orgs/community/discussions/26668) -- confirms status check name is the job `name:` field
- [GitHub Docs: Managing a branch protection rule](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule) -- branch protection setup procedure
- [GitHub Docs: Troubleshooting required status checks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks) -- check must complete once before it can be required

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all tools/actions already in use by the project
- Architecture: HIGH -- directly mirrors existing Python/Node CI patterns with verified source
- Pitfalls: HIGH -- documented from official GitHub docs and established project patterns

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (stable -- CI workflow syntax and GitHub branch protection are mature)

# Phase 5: CI Enforcement - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-09
**Phase:** 05-ci-enforcement
**Areas discussed:** CXX gate job placement, Triple-gate assertion test (CI-05), CXX artifact freshness (CI-06), Branch protection mechanics (CI-04)

---

## CXX Gate Job Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Add to ci-cpp.yml | New 'cxx-parity-gate' job in ci-cpp.yml before cli-tests/gui-tests. Only Python + checkout (~5min). cli-tests and gui-tests gain needs: [cxx-parity-gate]. | Yes |
| New ci-parity-gates.yml | Consolidate all three gates into one workflow. Requires extracting jobs from existing files. | |
| Standalone ci-cxx-parity.yml | Dedicated single-job workflow file. Most isolated but adds a 5th workflow file. | |

**User's choice:** Add to ci-cpp.yml
**Notes:** Mirrors how Python/Node gates are the first job in their respective workflow files.

### Follow-up: CXX job scope

| Option | Description | Selected |
|--------|-------------|----------|
| CXX-only | Only runs check_parity_gate.py for CXX surface. Clean separation. | Yes |
| CXX + baseline freshness | Run CXX gate AND a separate freshness step. | |

**User's choice:** CXX-only

---

## Triple-Gate Assertion Test (CI-05)

| Option | Description | Selected |
|--------|-------------|----------|
| Local test script | Checked-in Python script that injects canary, runs 3 gates, asserts all fail, reverts. | Yes |
| CI job with temp branch | Dedicated CI workflow with workflow_dispatch. More realistic but complex. | |
| Manual verification + docs | Run locally, screenshot, commit evidence. Simplest but no automation. | |

**User's choice:** Local test script

### Follow-up: Canary crate

| Option | Description | Selected |
|--------|-------------|----------|
| classic-shared-core | Foundation crate tracked by all three gates. Broadest coverage. | Yes |
| classic-config-core | Business-logic crate. More complex injection path. | |
| You decide | Claude picks based on cleanest injection/revert path. | |

**User's choice:** classic-shared-core

### Follow-up: CI job for re-verification

| Option | Description | Selected |
|--------|-------------|----------|
| Local-only | Script checked in but only run manually. No extra CI workflow. | Yes |
| Local + workflow_dispatch | Also add a ci-triple-gate-test.yml for periodic re-verification. | |
| You decide | | |

**User's choice:** Local-only

---

## CXX Artifact Freshness (CI-06)

| Option | Description | Selected |
|--------|-------------|----------|
| Baseline JSON freshness only | Existing stale-artifact check covers CI-06. No committed headers needed. | Yes |
| Commit + freshness-check headers | Snapshot CXX headers and add freshness script. Requires Rust build. | |
| You decide | | |

**User's choice:** Baseline JSON freshness only

### Follow-up: Separate freshness step

| Option | Description | Selected |
|--------|-------------|----------|
| Existing behavior sufficient | check_parity_gate.py already exits non-zero on stale artifacts. One step covers both. | Yes |
| Separate freshness step | Explicit second step. Redundant but more visible in CI output. | |

**User's choice:** Existing behavior sufficient

---

## Branch Protection Mechanics (CI-04)

| Option | Description | Selected |
|--------|-------------|----------|
| Manual + documented | PR description includes instructions. Maintainer applies setting when merging. | Yes |
| gh CLI in workflow | Workflow step uses gh api. Requires PAT with admin:repo scope. | |
| gh CLI script (local) | Checked-in script using gh api. Run once by maintainer. | |

**User's choice:** Manual + documented

### Follow-up: Verify all three gates

| Option | Description | Selected |
|--------|-------------|----------|
| Verify all three | Ensure Python, Node, and CXX are all listed as required checks. | Yes |
| CXX only | Only add CXX. Assume Python/Node already configured. | |
| You decide | | |

**User's choice:** Verify all three

### Follow-up: Existing CI workflow modifications

| Option | Description | Selected |
|--------|-------------|----------|
| Leave as-is | No changes to ci-python-bindings.yml or ci-typescript.yml. | Yes |
| Minor normalization | Normalize job/step names across workflows for consistency. | |

**User's choice:** Leave as-is

### Follow-up: Branch protection timing

| Option | Description | Selected |
|--------|-------------|----------|
| After first successful run | Add to branch protection after PR merges and check name exists. | Yes |
| Before merge (pre-register) | Use gh api to pre-register check name before merge. Riskier. | |

**User's choice:** After first successful run

---

## Claude's Discretion

- PR description wording for branch protection checklist
- Whether to add diagnostic artifact upload step on CXX gate failure
- CLI flags and output format for test_triple_gate_failure.py
- Whether the triple-gate test saves output to a file or prints to stdout

## Deferred Ideas

None -- discussion stayed within phase scope.

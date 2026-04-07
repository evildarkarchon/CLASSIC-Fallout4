# Phase 09: Deprecated API Verification Closure - Research

**Researched:** 2026-04-06
**Domain:** Verification-artifact refresh for Phase 1 deprecated API migration evidence
**Confidence:** HIGH

## Summary

Phase 09 is not a redesign phase. The code-level deprecated API migration work for DEBT-05, DEBT-06, DEBT-07, and DEBT-10 was already implemented in Phase 1 and is still reflected by Phase 1 plan summaries, test coverage, and the current roadmap. The blocker is audit traceability: `01-VERIFICATION.md` still carries an initial `gaps_found` status and old assumptions, while the roadmap and milestone audit now treat this as a dedicated closure phase.

The established repo pattern for closing this kind of blocker is a **re-verification refresh**, not new implementation work. Phase 05 and Phase 06 already show the house style: preserve the original phase artifact, add `re_verification` metadata with `previous_status`, explicitly list `gaps_closed`, rerun the phase’s declared targeted commands, and rewrite the requirements-coverage table so the audit can see all requirements satisfied in one place.

For this phase, the best approach is to update `01-VERIFICATION.md` so it matches the current planning state, explicitly covers DEBT-05/06/07/10, and distinguishes between evidence that can be rerun now versus any runtime proof that must remain called out as human-required. Do not invent a new closure format, and do not treat old narrative claims about `.planning/REQUIREMENTS.md` as authoritative without re-checking the current file.

**Primary recommendation:** Refresh `01-VERIFICATION.md` as a repo-standard re-verification artifact, using the existing Phase 1 validation commands and explicit requirement coverage for DEBT-05, DEBT-06, DEBT-07, and DEBT-10.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEBT-05 | Migrate Python binding `parse_segments_parallel` caller to wrapper over `parse_all_sections_arc`, update `.pyi` contract | Re-verify via targeted `pytest.warns` coverage, `.pyi` evidence, and explicit requirements table entries in `01-VERIFICATION.md` |
| DEBT-06 | Migrate Python `generate_suspect_section` legacy method to call `generate_suspect_section_header` + `generate_suspect_found_footer` separately | Re-verify via targeted warning tests and delegation evidence in the refreshed verification artifact |
| DEBT-07 | Rewrite tests using `#[allow(deprecated)]` on `CrashgenVersion::is_outdated` to exercise `check_version_status()` instead | Re-verify via targeted `cargo test` and explicit removal-of-deprecated-test-usage evidence |
| DEBT-10 | Add deprecation warning via `PyErr::warn` when `PyFormIDAnalyzerCore::new` receives legacy `PyDict` format for `mods_single` | Re-verify via targeted warning tests plus parity gate evidence and explicit coverage accounting |
</phase_requirements>

## Project Constraints (from AGENTS.md)

- Prioritize active work in `classic-cli/`, `classic-gui/`, and `ClassicLib-rs/`.
- Keep all business logic in Rust; non-interface layers stay thin.
- Maintain a single shared Tokio runtime from Rust core facilities; do not introduce independent runtimes.
- Keep docs synchronized with architecture or workflow changes, especially `README.md` and `AGENTS.md`.
- Never write to `NUL` or `nul` as a file path on Windows.
- Consult `docs/api/README.md` before changing public Rust, bridge, GUI-consumer, or binding-facing APIs; update affected `docs/api/` pages in the same change if contract-shaping changes occur.
- Never run C++ tests via raw binaries or raw `ctest`; use the repo PowerShell wrappers.
- For Rust/MSVC-targeted commands from Git Bash, source `tools/use_msvc_from_git_bash.sh` first or run through it.
- Python bindings should stay in sync with Rust core logic.
- Node bindings should stay in sync with Rust core logic.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Phase verification artifact (`01-VERIFICATION.md`) | repo schema, current | Canonical audit-facing evidence record | Milestone audit keys off phase verification status, not summary text alone |
| Rust targeted verification via `cargo test` | cargo 1.94.0 available | Re-prove DEBT-07 on the canonical Rust test surface | Repo guide declares cargo test as the Rust verification path |
| Python warning verification via `pytest.warns` | pytest API current; repo installs via `requirements-ci.txt` | Verify real `DeprecationWarning` emission for DEBT-05/06/10 | Official pytest guidance makes this the standard warning assertion pattern |
| Python parity gate `tools/python_api_parity/check_parity_gate.py` | repo current | Refresh parity artifacts and gate Tier-1 drift | Repo guide requires the local Python parity gate for Python binding contract work |
| Node local parity gate `bun run parity:gate:local` | bun 1.3.10 available | Reconfirm no collateral Node parity drift in the closure artifact | Repo guide names this as the Node parity workflow |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyO3 warning API (`PyErr::warn`, `#[pyo3(warn)]`) | workspace `pyo3 = 0.27.2` | Source of truth for warning-emission behavior | Use for understanding what runtime proof the Python tests must validate |
| Phase `01-VALIDATION.md` | repo current | Reuse the already-declared commands and requirement-to-test mapping | Use as the execution contract for re-verification |
| Phase 05/06 re-verification frontmatter pattern | repo current | House style for gap-closure verification updates | Use as the template for `re_verification` metadata |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Refreshing `01-VERIFICATION.md` | Writing a new ad hoc closure note | Loses audit compatibility; milestone gating looks at phase verification artifacts |
| `pytest.warns(..., match=...)` | Custom `warnings.catch_warnings` assertions | More boilerplate and easier to get wrong; pytest already provides the standard abstraction |
| Targeted phase commands from `01-VALIDATION.md` | Full workspace CI rerun | Higher cost and noisier evidence; not necessary for closing this specific stale-verification gap |

**Installation:**
```bash
uv pip install --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe -r ClassicLib-rs/python-bindings/requirements-ci.txt
```

**Version verification:**
- Workspace pins `pyo3 = 0.27.2` in `ClassicLib-rs/Cargo.toml`.
- The repo does not pin `pytest` in `requirements-ci.txt`; treat the installed version as environment-resolved and rely on the documented `pytest.warns` API rather than a repo-locked minor version.

## Architecture Patterns

### Recommended Project Structure
```text
.planning/
├── ROADMAP.md                                   # Phase 09 success criteria and required requirements
├── REQUIREMENTS.md                              # Current requirement ownership / traceability
├── v1.0-MILESTONE-AUDIT.md                      # Why Phase 09 exists
└── phases/
    ├── 01-deprecated-api-migration/
    │   ├── 01-VALIDATION.md                     # Reuse commands and test map
    │   ├── 01-01-SUMMARY.md                     # DEBT-07 completion claim
    │   ├── 01-02-SUMMARY.md                     # DEBT-05/06/10 completion claim
    │   └── 01-VERIFICATION.md                   # Artifact to refresh in Phase 09
    └── 09-deprecated-api-verification-closure/
        ├── 09-RESEARCH.md
        ├── 09-PLAN.md                           # to be created
        └── 09-SUMMARY.md                        # to be created
```

### Pattern 1: Re-Verification Artifact Closure
**What:** Update the original phase verification file instead of creating a parallel audit note.

**When to use:** A phase is implemented, but the audit still fails because the existing verification artifact is stale or incomplete.

**Example:**
```yaml
# Source: .planning/phases/05-pattern-caching-and-performance/05-VERIFICATION.md
re_verification:
  previous_status: gaps_found
  previous_score: 4/5
  gaps_closed:
    - "..."
  gaps_remaining: []
  regressions: []
```

### Pattern 2: Requirements Triangle Reconciliation
**What:** Reconcile four sources together: `ROADMAP.md`, `REQUIREMENTS.md`, plan summaries, and the verification report.

**When to use:** The blocker is traceability or bookkeeping rather than implementation uncertainty.

**Example:**
```markdown
| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DEBT-07 | 01-01-PLAN.md | Rewrite deprecated tests to use check_version_status() | SATISFIED | cargo test output + source evidence |
| DEBT-05 | 01-02-PLAN.md | Delegate parse_segments_parallel to parse_all_sections_arc | SATISFIED | pytest warning test + stub evidence |
```

### Pattern 3: Runtime-Proof Split
**What:** Separate static/source verification from executable runtime proof, and mark any unrun runtime proof explicitly.

**When to use:** A verification pass can inspect code and artifacts immediately, but some proof depends on rebuilt extensions or external runtimes.

**Example:**
```markdown
### Human Verification Required

- Run targeted Python warning tests against the built binding
- Run `bun run parity:gate:local` if Node parity proof was not rerun during closure
```

### Anti-Patterns to Avoid
- **Creating a Phase 09-only verification file for Phase 1 truth:** the roadmap explicitly says success requires updating `01-VERIFICATION.md`.
- **Narrative-only closure:** audit tooling needs explicit requirement coverage, frontmatter status, and gap-closure metadata.
- **Assuming unchanged Node files means verified:** unchanged code can justify low risk, but not an executed-gate claim unless the gate was actually rerun.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Python warning capture | Custom `warnings` harness | `pytest.warns(..., match=...)` | Official pytest support is simpler and verifies warning type and message |
| Python parity accounting | Manual diff of Rust and Python exports | `tools/python_api_parity/check_parity_gate.py` | The repo already generates diff and runtime coverage artifacts |
| Node parity confirmation | Manual reasoning from unchanged files | `bun run parity:gate:local` | The repo’s contract freshness and parity checks are already scripted |
| Gap-closure reporting | Bespoke markdown note | Existing `*-VERIFICATION.md` schema with `re_verification` block | Matches the milestone audit’s expected evidence model |

**Key insight:** The hard part here is not proving behavior; it is proving behavior in the exact artifact shape the milestone audit consumes.

## Common Pitfalls

### Pitfall 1: Repeating obsolete verification claims
**What goes wrong:** The refreshed report reuses old claims like “`REQUIREMENTS.md` is now checked off” without re-reading the current planning files.
**Why it happens:** The old `01-VERIFICATION.md` was accurate for a transient bookkeeping gap, but Phase 09 now exists precisely because the planning state changed.
**How to avoid:** Treat `ROADMAP.md`, `REQUIREMENTS.md`, `v1.0-MILESTONE-AUDIT.md`, `01-VALIDATION.md`, and both Phase 1 summaries as fresh inputs.
**Warning signs:** Verification text contradicts current requirement ownership or audit notes.

### Pitfall 2: Promoting “low-risk” to “verified” without execution
**What goes wrong:** The report marks Node parity or Python runtime warnings as fully verified even though the gate/tests were not rerun.
**Why it happens:** The surfaces appear unchanged, so it is tempting to infer the result.
**How to avoid:** Either rerun the command and record the result, or leave it explicitly in “Human Verification Required” / residual proof.
**Warning signs:** Evidence column cites absence of file changes instead of command output.

### Pitfall 3: Using summaries as verification
**What goes wrong:** `01-01-SUMMARY.md` and `01-02-SUMMARY.md` are treated as sufficient proof by themselves.
**Why it happens:** Summaries already list completed requirements.
**How to avoid:** Use summaries as claims, then independently confirm them with source evidence and executable commands.
**Warning signs:** Requirements coverage rows cite only summary frontmatter.

### Pitfall 4: Forgetting repo-standard re-verification metadata
**What goes wrong:** `01-VERIFICATION.md` status changes, but there is no `re_verification.previous_status` or `gaps_closed` trace.
**Why it happens:** Phase 1 originally used `re_verification: false`.
**How to avoid:** Copy the structure used by Phase 05 and Phase 06 closure artifacts.
**Warning signs:** Audit readers cannot tell what changed between the failing and passing verification states.

## Code Examples

Verified patterns from official and repo sources:

### Pytest warning assertion for deprecated bindings
```python
# Source: /pytest-dev/pytest docs + ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py
with pytest.warns(DeprecationWarning, match="parse_segments_parallel is deprecated"):
    result = parser.parse_segments_parallel(sample_lines)
```

### Repo-standard re-verification frontmatter
```yaml
# Source: .planning/phases/06-mmap-toctou-safety/06-VERIFICATION.md
status: passed
re_verification:
  previous_status: gaps_found
  previous_score: 6/7
  gaps_closed:
    - "Declared Phase 6 crate validation commands pass cleanly"
  gaps_remaining: []
  regressions: []
```

### Python parity gate execution path
```bash
# Source: .opencode/skills/classic-project-guide/references/repo-guide.md
python tools/python_api_parity/check_parity_gate.py --repo-root .
```

### Node local parity gate execution path
```bash
# Source: ClassicLib-rs/node-bindings/classic-node/package.json
bun run parity:gate:local
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-pass verification artifact with no closure metadata | Explicit re-verification block (`previous_status`, `gaps_closed`, `gaps_remaining`) | Seen in repo closure artifacts dated 2026-04-06 (Phases 05 and 06) | Makes gap closure auditable instead of implicit |
| Manual or narrative warning checks | `pytest.warns(..., match=...)` as the standard assertion mechanism | Current pytest docs; unmatched warnings re-emitted since pytest 8+ | Warning proofs should be executable and message-specific |
| Only manual `PyErr::warn` reasoning | PyO3 0.27 docs also expose declarative `#[pyo3(warn(...))]` for supported cases | Current PyO3 docs | Useful context, but Phase 09 should verify existing behavior rather than refactor warning emission |
| Summary-driven completion claims | Verification-driven requirement satisfaction | Current milestone audit | Passing the audit depends on refreshed verification evidence, not summary prose |

**Deprecated/outdated:**
- Reusing the original `01-VERIFICATION.md` gap narrative about `.planning/REQUIREMENTS.md` sync as if it were still the live blocker.
- Treating “no files changed” as equivalent to rerunning a parity gate.

## Open Questions

1. **Should Node parity be rerun or left as residual proof?**
   - What we know: Bun and Node are available locally, and the repo standard script is `bun run parity:gate:local`.
   - What's unclear: Whether the closure plan should spend time rerunning Node parity for a Python-focused stale-verification fix.
   - Recommendation: Prefer rerunning it if execution time is reasonable; otherwise keep it explicitly called out as residual proof, not silently assumed.

2. **Should the refreshed verification mark all four requirements satisfied even if some runtime proof remains manual?**
   - What we know: The roadmap requires Phase 1 requirement coverage to be explicit and current.
   - What's unclear: Whether the repo’s verification bar for this closure demands fresh runtime execution or only honest documentation of remaining proof.
   - Recommendation: Only mark a requirement fully satisfied when its claimed evidence is actually present in the refreshed report; otherwise mark the overall status conservatively.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| cargo | DEBT-07 Rust re-verification | ✓ | 1.94.0 | — |
| python | parity scripts and pytest execution | ✓ | 3.14.3 | — |
| uv | Python bindings env + pytest invocation | ✓ | 0.11.3 | direct Python invocation if env already prepared |
| bun | Node local parity gate | ✓ | 1.3.10 | none for the repo-standard local gate |
| node | Node runtime-backed binding checks | ✓ | 25.9.0 | none |

**Missing dependencies with no fallback:**
- None found.

**Missing dependencies with fallback:**
- None found.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Rust `cargo test` + Python `pytest` + repo parity gate scripts |
| Config file | `ClassicLib-rs/Cargo.toml`, `ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py`, `tools/python_api_parity/check_parity_gate.py`, `ClassicLib-rs/node-bindings/classic-node/package.json` |
| Quick run command | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml -- version::tests` |
| Full suite command | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml -- version::tests && uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py -q -k "parse_segments_parallel or generate_suspect_section or formid_analyzer_legacy_dict_deprecation_warning" && python tools/python_api_parity/check_parity_gate.py --repo-root .` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEBT-05 | Deprecated parser binding warns and matches current dict-returning API | binding/runtime | `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py -q -k "parse_segments_parallel_deprecation_warning"` | ✅ |
| DEBT-06 | Deprecated report binding warns and delegates to header+footer output | binding/runtime | `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py -q -k "generate_suspect_section_deprecation_warning"` | ✅ |
| DEBT-07 | Deprecated `is_outdated` tests replaced by `check_version_status()` coverage | unit | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml -- version::tests` | ✅ |
| DEBT-10 | FormID analyzer warns on legacy dict input | binding/runtime | `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py -q -k "formid_analyzer_legacy_dict_deprecation_warning"` | ✅ |

### Sampling Rate
- **Per task commit:** Rerun only the targeted command for the requirement whose evidence text changed.
- **Per wave merge:** Run the full suite command above.
- **Phase gate:** `01-VERIFICATION.md` updated with current command results and explicit residual-proof handling before `/gsd-verify-work`.

### Wave 0 Gaps
None — existing Phase 1 validation and parity infrastructure already covers all four requirements.

## Sources

### Primary (HIGH confidence)
- `.planning/ROADMAP.md` - Phase 09 goal, requirements, and success criteria
- `.planning/v1.0-MILESTONE-AUDIT.md` - Exact audit failure mechanism for the four blocked requirements
- `.planning/phases/01-deprecated-api-migration/01-VERIFICATION.md` - Current stale verification artifact and obsolete gap narrative
- `.planning/phases/01-deprecated-api-migration/01-VALIDATION.md` - Existing Phase 1 validation commands and requirement/test map
- `.planning/phases/01-deprecated-api-migration/01-01-SUMMARY.md` - DEBT-07 completion claim
- `.planning/phases/01-deprecated-api-migration/01-02-SUMMARY.md` - DEBT-05/06/10 completion claim
- `.planning/phases/05-pattern-caching-and-performance/05-VERIFICATION.md` - Repo-standard re-verification metadata pattern
- `.planning/phases/06-mmap-toctou-safety/06-VERIFICATION.md` - Repo-standard re-verification metadata pattern
- `.opencode/skills/classic-project-guide/references/repo-guide.md` - Repo-approved Rust, Python, and Node verification commands
- `/pytest-dev/pytest` - `pytest.warns` warning assertion API and `match` semantics
- `/pyo3/pyo3` - Current warning-emission docs including `#[pyo3(warn)]`

### Secondary (MEDIUM confidence)
- `ClassicLib-rs/node-bindings/classic-node/package.json` - Local parity gate script wiring
- `ClassicLib-rs/Cargo.toml` - Workspace `pyo3 = 0.27.2` pin and `deprecated = "deny"` lint context
- `ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py` - Existing concrete warning-test implementation pattern

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - repo-specific command surfaces and warning-test patterns are directly documented in repo artifacts and official docs.
- Architecture: HIGH - Phase 05/06 provide concrete, current re-verification templates in the same planning system.
- Pitfalls: HIGH - the milestone audit and stale Phase 1 verification report show the exact failure modes already encountered.

**Research date:** 2026-04-06
**Valid until:** 2026-05-06

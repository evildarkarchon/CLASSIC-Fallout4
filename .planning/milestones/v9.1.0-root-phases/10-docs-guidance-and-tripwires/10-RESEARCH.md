# Phase 10: Docs, Guidance, and Tripwires - Research

**Researched:** 2026-04-13
**Domain:** Active contributor docs, agent guidance, and deterministic regression tripwires for repo-root workspace guidance
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
## Implementation Decisions

### Contributor Documentation
- **D-01:** Phase 10 updates the active onboarding, index, and testing pages plus the active `docs/api/*.md` reference pages those entrypoints route contributors into. Archival or legacy docs remain out of scope.
- **D-02:** Active contributor docs should route through a small maintained set of source-of-truth pages and link to one shared migration reference instead of duplicating old/new path translations page-by-page.

### Agent Guidance
- **D-03:** Treat `AGENTS.md`, the mirrored `classic-project-guide` skill files, and `.planning/codebase/*.md` as active agent guidance that must be corrected and kept synchronized in this phase.

### Migration Reference
- **D-04:** Publish one dedicated migration matrix page as the primary old-to-new workspace translation artifact for Phase 10.
- **D-05:** The matrix must map changed commands, path roots, and key artifact/report locations, then be linked from active docs and skills rather than re-explained separately in each page.

### Regression Guards
- **D-06:** Add hybrid regression protection: keep a strict file-listed audit for must-read docs, skills, and codebase maps, and add a scoped stale-path sweep across active docs, guidance, scripts, and tests with explicit exclusions for planning/history surfaces.
- **D-07:** In active docs and agent guidance, `ClassicLib-rs` is allowed only inside clearly labeled historical or migration notes. It must never be taught as a live workspace root, command root, or active path instruction.

### the agent's Discretion
- Exact matrix file name and placement, as long as it is easy to discover from the top-level docs and skills.
- Exact must-read file list and scoped-sweep exclusion list, as long as the hybrid guard and historical-note policy above are preserved.
- Exact split between `tests/planning/` and `tests/powershell/`, as long as the tripwires stay deterministic and file-backed.

### Deferred Ideas (OUT OF SCOPE)
## Deferred Ideas

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOCS-01 | Contributor can follow active docs, skills, and agent context files without being routed to `ClassicLib-rs/` as the live workspace root | Use a small source-of-truth doc set, fix mirrored skill/codebase guidance together, and add deterministic audits over the must-read surfaces |
| DOCS-02 | Contributor can use milestone migration notes or a verification matrix to map the old workspace-root workflows to the new repository-root workflows | Publish one dedicated migration matrix page using GitHub-flavored Markdown tables and relative links; link to it from active docs and skills instead of duplicating translations |
| DOCS-03 | Contributor gets regression protection against newly introduced active `ClassicLib-rs/` workspace-root references in validation-critical docs, scripts, or tests | Implement hybrid tripwires: explicit file-list assertions plus a scoped stale-path sweep, with PowerShell AST/text checks where scripts need structure-aware validation |
</phase_requirements>

## Summary

This phase should not introduce a docs framework or a new linting stack. The established pattern in this repo is simpler and stronger: keep a small set of high-traffic docs and agent-entrypoint files as the source of truth, route them to one shared migration matrix, and protect them with file-backed tests. Existing Phase 06 and Phase 09 validation already show the repo's preferred enforcement style: Python `unittest` content audits for exact must-read surfaces plus targeted PowerShell script checks for contract-sensitive scripts.

The biggest hidden risk is overcorrecting with a blunt `ClassicLib-rs` ban. That string still appears widely, and some mentions are historical or reference old residue intentionally. The guard must reject `ClassicLib-rs` as a live workspace root, command root, or active path instruction, not every literal occurrence everywhere. Use explicit must-read files, explicit exclusions, and precise phrase-level assertions.

The docs side should also stay centralized. GitHub Markdown already gives you headings, relative links, anchors, and tables; use that to publish one migration matrix and link to it from `README.md`, `docs/README.md`, `docs/RUST_DOCUMENTATION_INDEX.md`, `docs/testing/TESTING_GUIDE_INDEX.md`, `docs/api/README.md`, `docs/api/QUICK_START.md`, `binding-contract-refresh-note.md`, `AGENTS.md`, mirrored `classic-project-guide` skills, and `.planning/codebase/*.md`.

**Primary recommendation:** Use one migration-matrix page plus hybrid file-backed tripwires: Python `unittest` for must-read docs/guidance and PowerShell AST/text checks for script-sensitive stale-path regressions.

## Project Constraints (from AGENTS.md)

- Prioritize active work in `classic-cli/`, `classic-gui/`, and `ClassicLib-rs/`.
- Keep all business logic in Rust; non-interface layers stay thin.
- Maintain a single shared Tokio runtime; do not introduce another runtime.
- Keep docs synchronized with architecture/workflow changes, especially `README.md` and `AGENTS.md`.
- Never write to `NUL` or `nul` as a Windows file path.
- Consult `docs/api/README.md` before changing public Rust, bridge, GUI-consumer, or binding-facing APIs; update affected `docs/api/` pages if contracts change.
- Never run C++ tests via raw `ctest` or test binaries; use the repo PowerShell wrappers.
- The canonical Cargo workspace shell now lives at repo root; active guidance must reflect repo-root Cargo commands.

## Standard Stack

### Core
| Library / Tool | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| GitHub Flavored Markdown (repo `.md` files) | Current GitHub Docs syntax (2026) | Migration matrix, source-of-truth pages, relative links, headings, code fences, tables | Native to the repo surface; no generator or custom format needed |
| Python `unittest` (stdlib) | Python 3.14.3 | Deterministic file-backed audits for must-read docs/skills/codebase maps | Already used by `tests/planning/test_phase06_validation.py` and `test_phase09_validation.py`; supports `subTest()` for compact matrix-style assertions |
| Python `pathlib` (stdlib) | Python 3.14.3 | Stable repo-relative file addressing in planning audits | Standard, cross-platform path API; already matches repo test style |
| PowerShell `System.Management.Automation.Language.Parser.ParseFile` | PowerShell 7.6.0 / System.Management.Automation 7.4 docs | Structure-aware validation for script contracts | Better than regex-only parsing when asserting script metadata or param blocks |

### Supporting
| Library / Tool | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | 9.0.3 | Test runner for targeted planning-audit execution | Use to run `tests/planning/test_phase10_validation.py -q` quickly |
| Repo grep/text sweep via Python/PowerShell | existing repo tooling | Scoped stale-path regression scan | Use only with explicit allow/exclude lists; not as the sole guard |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| File-backed Python `unittest` audits | markdownlint/docs-site tooling | Extra tooling does not solve repo-specific policy assertions as directly |
| PowerShell AST parse for script structure | regex-only parsing | Regex is fine for narrow string checks, but brittle for parameter/metadata contract checks |
| Single migration matrix page | duplicate old/new translations in each page | Duplication drifts quickly and multiplies review burden |

**Installation:**
```bash
# No new packages required for Phase 10 research recommendations.
# Uses Python stdlib, existing pytest, and built-in PowerShell parser APIs.
```

**Version verification:**
- Verified locally: `python --version` → **3.14.3**
- Verified locally: `pwsh --version` → **7.6.0**
- Verified locally: `pytest --version` → **9.0.3**
- No new third-party package recommendation in this phase, so registry version checks are not applicable.

## Architecture Patterns

### Recommended Project Structure
```text
docs/
├── README.md                        # Top-level docs hub; links to matrix
├── RUST_DOCUMENTATION_INDEX.md      # Rust-facing docs entrypoint; links to matrix
├── testing/TESTING_GUIDE_INDEX.md   # Active testing command map; links to matrix
└── api/
    ├── README.md                    # API index; routes readers onward
    ├── QUICK_START.md               # Contributor quick-start
    ├── binding-contract-refresh-note.md
    └── [migration-matrix].md        # Single old→new workflow translation page

AGENTS.md                             # Always-on agent entrypoint
.agent[s]/skills/classic-project-guide/**
.opencode/skills/classic-project-guide/**
.claude/skills/classic-project-guide/**
.planning/codebase/*.md              # Agent-consumed codebase maps

tests/
├── planning/test_phase10_validation.py   # Must-read audit + scoped stale-path sweep
└── powershell/[phase10].test.ps1         # Script-sensitive tripwire(s)
```

### Pattern 1: Single Source Of Truth + Fan-Out Links
**What:** Keep command/path translations in one migration matrix page, then link to it from entrypoint docs and agent guidance.
**When to use:** Any page currently duplicating old `ClassicLib-rs/...` versus new repo-root instructions.
**Example:**
```markdown
## Workspace Migration Matrix

| Old workflow | New workflow | Notes |
| --- | --- | --- |
| `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` | `cargo test --workspace` | Run from repo root |
| `ClassicLib-rs/python-bindings/.venv` | `python-bindings/.venv` | Binding-local venv still lives outside repo-root `.venv` |

See also: [Testing Guide](../testing/TESTING_GUIDE_INDEX.md)
```
Source: GitHub Docs on [tables](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/organizing-information-with-tables) and [relative links](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax#relative-links).

### Pattern 2: File-Listed Planning Audit For Must-Read Surfaces
**What:** Create one explicit list of guidance-critical files and assert required/forbidden fragments in each.
**When to use:** `README.md`, `docs/README.md`, `docs/api/*.md`, `AGENTS.md`, skill mirrors, and `.planning/codebase/*.md`.
**Example:**
```python
from pathlib import Path
import unittest

REPO_ROOT = Path(__file__).resolve().parents[2]
MUST_READ = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "docs/README.md",
]

class TestPhase10Validation(unittest.TestCase):
    def test_active_guidance_uses_repo_root_contract(self) -> None:
        for path in MUST_READ:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=str(path)):
                self.assertIn("cargo test --workspace", text)
                self.assertNotIn("--manifest-path ClassicLib-rs/Cargo.toml", text)
```
Source: Python docs for [`unittest.subTest()`](https://docs.python.org/3/library/unittest.html#distinguishing-test-iterations-using-subtests) and [`pathlib.Path`](https://docs.python.org/3/library/pathlib.html); repo pattern in `tests/planning/test_phase06_validation.py` and `tests/planning/test_phase09_validation.py`.

### Pattern 3: Hybrid Tripwire = Explicit File Audit + Scoped Sweep
**What:** Combine exact file assertions with a narrower sweep for stale workspace-root phrases.
**When to use:** When one bad string can reappear in many active surfaces, but historical/planning areas must stay allowed.
**Example:**
```python
FORBIDDEN_ACTIVE_PHRASES = [
    "--manifest-path ClassicLib-rs/Cargo.toml",
    "uv venv ClassicLib-rs/python-bindings/.venv",
    "working-directory: ClassicLib-rs",
]

ALLOWED_SCOPES = [
    "migration note",
    "historical note",
]
```
Use exact file assertions for critical pages first; use the sweep only for phrases that unambiguously indicate live workspace-root guidance.

### Pattern 4: PowerShell AST First, Regex Second
**What:** Parse scripts with `Parser.ParseFile(...)` before asserting script metadata; use text regex only for targeted stale-string checks.
**When to use:** Any new PowerShell tripwire that needs to validate parameters, switch defaults, or structural blocks.
**Example:**
```powershell
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $resolvedScriptPath.Path,
    [ref]$tokens,
    [ref]$parseErrors
)

if ($parseErrors -and $parseErrors.Count -gt 0) {
    throw "Script has parse errors: $($parseErrors[0].Message)"
}
```
Source: Microsoft docs for [`Parser.ParseFile`](https://learn.microsoft.com/dotnet/api/system.management.automation.language.parser.parsefile?view=powershellsdk-7.4.0); repo pattern in `tests/powershell/rebuild_rust.general_target.test.ps1`.

### Anti-Patterns to Avoid
- **Page-by-page translation duplication:** It guarantees drift because every future workflow edit must be repeated everywhere.
- **Global ban on the raw string `ClassicLib-rs`:** Too blunt; some historical/migration mentions are allowed, and broad repo sweeps will catch intentional archival references.
- **Regex-only script validation:** Fine for one literal string, weak for script structure.
- **Unbounded whole-repo sweeps with no exclusions:** They produce noisy failures from planning/history/legacy material and train contributors to ignore the guard.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Navigation between updated docs | custom docs router/generator | GitHub Markdown headings + relative links | Native to repo hosting and easier to review |
| Migration comparison view | ad hoc prose repeated in many files | one GFM table-based migration matrix | Easier to diff, verify, and link |
| Script structure detection | custom regex parser for PowerShell syntax | `Parser.ParseFile()` AST + token/errors | Official parser handles syntax boundaries correctly |
| Guidance regression detection | manual review checklist only | deterministic Python `unittest` + targeted PowerShell tests | Review alone will miss mirrored skill/codebase drift |
| Broad stale-path detection | naive `ClassicLib-rs` string ban | scoped phrase sweeps + explicit allow/exclude lists | The raw string can appear in valid historical notes |

**Key insight:** The hard part here is policy precision, not rendering. Hand-rolled general parsers or docs systems add complexity without improving the core outcome: deterministic detection of forbidden live workspace-root guidance.

## Common Pitfalls

### Pitfall 1: Repeating the same migration mapping in many pages
**What goes wrong:** One page gets updated and the others keep stale commands.
**Why it happens:** Each page becomes its own source of truth.
**How to avoid:** Put all old→new command/path/artifact translations in one matrix page and link to it.
**Warning signs:** Slight command differences across `README.md`, `docs/README.md`, `docs/testing/TESTING_GUIDE_INDEX.md`, and skill mirrors.

### Pitfall 2: Treating every `ClassicLib-rs` mention as forbidden
**What goes wrong:** The guard becomes noisy and blocks valid historical or migration notes.
**Why it happens:** The repo still contains legacy residue, mirrored skills, planning artifacts, and historical references.
**How to avoid:** Fail on live-root instructions (`--manifest-path ClassicLib-rs/Cargo.toml`, `working-directory: ClassicLib-rs`, old binding paths), not on every literal occurrence.
**Warning signs:** Tripwire failures in planning/history surfaces or clearly labeled migration notes.

### Pitfall 3: Missing mirrored guidance surfaces
**What goes wrong:** `AGENTS.md` is fixed, but `.agents/`, `.opencode/`, `.claude/`, or `.agent/` skill mirrors still teach stale paths.
**Why it happens:** These mirrors are easy to forget because they sit outside `docs/`.
**How to avoid:** Put all mirrored skill entrypoints and references in the must-read audit list.
**Warning signs:** Same repo guide text diverges across agent environments.

### Pitfall 4: Regex-only PowerShell checks
**What goes wrong:** A script passes a stale regex scan but has broken parameter structure or parse errors.
**Why it happens:** Text matching ignores syntax.
**How to avoid:** Parse first with `Parser.ParseFile`, then apply narrow regex/text assertions.
**Warning signs:** Tests depend on fragile multiline regex against script structure.

### Pitfall 5: Using absolute GitHub links inside repo docs
**What goes wrong:** Links are harder to maintain and work worse for clones/branch switching.
**Why it happens:** Absolute URLs feel explicit but drift with branch/file moves.
**How to avoid:** Use relative links for in-repo docs and matrix routing.
**Warning signs:** Hardcoded GitHub blob URLs to files that exist in the same repo.

### Pitfall 6: Letting legacy residue mask active-guidance regressions
**What goes wrong:** Old paths still appear to “work” because `ClassicLib-rs/` residue still exists in the tree.
**Why it happens:** File existence is not the same as policy correctness.
**How to avoid:** Assert the repo-root workflow contract explicitly; do not infer correctness from path existence.
**Warning signs:** Docs/tests point to old paths that still happen to resolve locally.

## Code Examples

Verified patterns from official sources:

### Migration Matrix Page
```markdown
# Workspace Migration Matrix

| Old | New | Why |
| --- | --- | --- |
| `cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml -- --check` | `cargo fmt --all -- --check` | Repo root is the live workspace shell |
| `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` | `cargo test --workspace` | No legacy workspace manifest |
| `ClassicLib-rs/python-bindings/.venv` | `python-bindings/.venv` | Binding-local venv remains, path root changed |

Back to the [Testing Guide](../testing/TESTING_GUIDE_INDEX.md).
```
Source: GitHub Docs on [tables](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/organizing-information-with-tables) and [relative links](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax#relative-links).

### Python Planning Audit
```python
from pathlib import Path
import unittest

REPO_ROOT = Path(__file__).resolve().parents[2]

class TestPhase10Validation(unittest.TestCase):
    def test_required_matrix_links_present(self) -> None:
        files = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "docs/README.md",
            REPO_ROOT / "AGENTS.md",
        ]
        for path in files:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=str(path)):
                self.assertIn("Workspace Migration Matrix", text)

    def test_no_live_workspace_manifest_path_guidance(self) -> None:
        text = (REPO_ROOT / "docs/testing/TESTING_GUIDE_INDEX.md").read_text(encoding="utf-8")
        self.assertNotIn("--manifest-path ClassicLib-rs/Cargo.toml", text)
```
Source: Python docs for [`unittest`](https://docs.python.org/3/library/unittest.html) and [`pathlib`](https://docs.python.org/3/library/pathlib.html); repo pattern in `tests/planning/test_phase06_validation.py`.

### PowerShell Script Parse Guard
```powershell
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $resolvedScriptPath.Path,
    [ref]$tokens,
    [ref]$parseErrors
)

if ($parseErrors -and $parseErrors.Count -gt 0) {
    throw "Script has parse errors: $($parseErrors[0].Message)"
}

$scriptText = Get-Content -Path $resolvedScriptPath.Path -Raw
if ($scriptText -match 'ClassicLib-rs[\\/]python-bindings') {
    throw "Expected repo-root python-bindings/ guidance only."
}
```
Source: Microsoft docs for [`Parser.ParseFile`](https://learn.microsoft.com/dotnet/api/system.management.automation.language.parser.parsefile?view=powershellsdk-7.4.0); repo pattern in `tests/powershell/rebuild_rust.general_target.test.ps1`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Active docs taught repo commands through `ClassicLib-rs/Cargo.toml` and `--manifest-path` | Active docs should teach plain repo-root Cargo commands | Phase 6+ decisions, April 2026 | Any active guidance still teaching old manifest-path flows is a regression |
| Page-local prose repeated old/new translations | One dedicated migration matrix linked from source-of-truth pages | Locked in Phase 10 context | Lowers drift and review burden |
| Manual review of stale guidance | Deterministic file-backed planning and PowerShell tripwires | Established by Phase 06 and Phase 09 tests | Regression protection becomes auditable and repeatable |
| Skill/docs updates treated independently | `AGENTS.md`, mirrored skills, and `.planning/codebase/*.md` must stay synchronized | Locked in Phase 10 context | Planner must treat guidance mirrors as one maintenance unit |

**Deprecated/outdated:**
- `cargo ... --manifest-path ClassicLib-rs/Cargo.toml` in active guidance
- `working-directory: ClassicLib-rs` in active CI/doc instructions
- `ClassicLib-rs/python-bindings/.venv` and `ClassicLib-rs/node-bindings/classic-node` as active root paths in maintained docs/skills
- Duplicated per-page migration prose instead of one shared matrix

## Open Questions

1. **What exact filename/location should the migration matrix use?**
   - What we know: It must be easy to discover from top-level docs and skills.
   - What's unclear: Best final home under `docs/` and final filename.
   - Recommendation: Put it under `docs/api/` or `docs/` near current contributor entrypoints and link it from every source-of-truth page.

2. **Should `.agent/skills/classic-project-guide/**` be included in the must-read sync list?**
   - What we know: It exists in the repo and Phase 06 validation already referenced it.
   - What's unclear: Phase 10 context explicitly names `.agents/`, `.opencode/`, and `.claude/`, but not `.agent/`.
   - Recommendation: Include `.agent/` in the audit unless the planner confirms it is intentionally dead.

3. **What exact exclusions should the scoped stale-path sweep honor?**
   - What we know: Planning/history surfaces must be excluded, and historical/migration notes may keep clearly labeled legacy mentions.
   - What's unclear: Final file glob list for allowed legacy references.
   - Recommendation: Start from the active file list in the phase context, then add explicit excludes for planning/history/archival surfaces instead of trying to infer them dynamically.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | planning audit implementation | ✓ | 3.14.3 | — |
| pytest | fast targeted execution of planning audits | ✓ | 9.0.3 | `python -m unittest ...` |
| PowerShell (`pwsh`) | AST/text tripwire scripts | ✓ | 7.6.0 | Windows PowerShell may work, but no need because `pwsh` is present |

**Missing dependencies with no fallback:**
- None

**Missing dependencies with fallback:**
- None

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 running Python `unittest` planning audits + standalone PowerShell script tests |
| Config file | none — targeted file execution is already the repo pattern |
| Quick run command | `python -m pytest tests/planning/test_phase10_validation.py -q` |
| Full suite command | `python -m pytest tests/planning/test_phase10_validation.py -q && pwsh -ExecutionPolicy Bypass -File tests/powershell/phase10_docs_guidance_tripwire.test.ps1` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOCS-01 | Active docs, skills, and codebase maps teach repo-root workflows and stop routing contributors to `ClassicLib-rs` as the live workspace root | unit/content audit | `python -m pytest tests/planning/test_phase10_validation.py -q -k active_guidance` | ❌ Wave 0 |
| DOCS-02 | One migration matrix exists, maps old→new commands/paths/artifacts, and is linked from source-of-truth pages | unit/content audit | `python -m pytest tests/planning/test_phase10_validation.py -q -k migration_matrix` | ❌ Wave 0 |
| DOCS-03 | Hybrid regression protection catches stale live-root guidance in critical docs, skills, scripts, and tests while honoring exclusions | unit + script contract | `python -m pytest tests/planning/test_phase10_validation.py -q -k tripwire && pwsh -ExecutionPolicy Bypass -File tests/powershell/phase10_docs_guidance_tripwire.test.ps1` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/planning/test_phase10_validation.py -q`
- **Per wave merge:** `python -m pytest tests/planning/test_phase10_validation.py -q && pwsh -ExecutionPolicy Bypass -File tests/powershell/phase10_docs_guidance_tripwire.test.ps1`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/planning/test_phase10_validation.py` — must-read file list, migration-matrix link coverage, active-guidance forbidden phrase assertions, scoped exclusion checks
- [ ] `tests/powershell/phase10_docs_guidance_tripwire.test.ps1` — script-sensitive stale-path guard using `Parser.ParseFile()` plus targeted string checks
- [ ] Add explicit fixture constants for source-of-truth files and exclusion globs so future edits stay centralized

## Sources

### Primary (HIGH confidence)
- Python docs: `unittest` — https://docs.python.org/3/library/unittest.html — `TestCase`, `subTest()`, command-line execution, discovery
- Python docs: `pathlib` — https://docs.python.org/3/library/pathlib.html — `Path`, repo-relative file addressing
- GitHub Docs: Basic writing and formatting syntax — https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax — headings, relative links, anchors, code fences
- GitHub Docs: Organizing information with tables — https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/organizing-information-with-tables — migration-matrix table syntax
- Microsoft Learn: `Parser.ParseFile` — https://learn.microsoft.com/dotnet/api/system.management.automation.language.parser.parsefile?view=powershellsdk-7.4.0 — AST parse API for PowerShell scripts
- Microsoft Learn: `about_Comments` — https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_comments?view=powershell-7.6 — comment semantics and block-comment limits
- Repo source patterns: `tests/planning/test_phase06_validation.py`, `tests/planning/test_phase09_validation.py`, `tests/powershell/rebuild_rust.general_target.test.ps1`
- Repo context: `README.md`, `docs/README.md`, `docs/RUST_DOCUMENTATION_INDEX.md`, `docs/testing/TESTING_GUIDE_INDEX.md`, `docs/api/README.md`, `docs/api/QUICK_START.md`, `docs/api/binding-contract-refresh-note.md`, `AGENTS.md`, mirrored `classic-project-guide` skill files, `.planning/codebase/*.md`

### Secondary (MEDIUM confidence)
- `.planning/codebase/STACK.md`, `STRUCTURE.md`, `CONVENTIONS.md`, `TESTING.md` — useful for spotting stale guidance and existing test conventions, but themselves need Phase 10 cleanup

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - uses official docs plus already-established repo test patterns; no speculative package choice
- Architecture: HIGH - directly constrained by Phase 10 context and evidenced by Phase 06/09 validation style
- Pitfalls: HIGH - based on current stale guidance in active docs/skills/codebase maps plus official Markdown/PowerShell/Python behavior

**Research date:** 2026-04-13
**Valid until:** 2026-05-13

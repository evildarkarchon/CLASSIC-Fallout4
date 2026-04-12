---
phase: 6
reviewers: [gemini, claude]
requested_reviewers: [gemini, claude, codex]
interrupted_reviewers: [codex]
reviewed_at: 2026-04-12T01:42:27.8270450-07:00
plans_reviewed: [06-00-PLAN.md, 06-01-PLAN.md, 06-02-PLAN.md, 06-03-PLAN.md]
---

# Cross-AI Plan Review - Phase 6

## Gemini Review

### Summary
This is a highly systematic and well-structured set of plans. Separating the workspace-anchor cutover from the physical crate relocation in Phase 7 keeps the blast radius small. The four-wave structure, especially the Wave 0 validation bootstrap and the Cargo-native proof via `cargo metadata` and `cargo locate-project`, is well chosen.

### Strengths
- Wave 0 creates `phase06_clean_run.ps1` and the validation scaffold before later waves depend on them.
- Omitting `workspace.default-members` and relying on Cargo's virtual-workspace default behavior is the correct call.
- The plans intentionally remove `--manifest-path` and establish plain repo-root Cargo as the new contract.
- Keeping crates under `ClassicLib-rs/` for Phase 6 while only moving the workspace shell is a good scope boundary.

### Concerns
- **HIGH**: `06-02-PLAN.md` moves `benches/` to repo root, but crate-level benchmark files may still rely on relative `#[path = "../../benches/common/mod.rs"]` includes. That path will break after the move unless those references are updated.
- **LOW**: `.github/workflows/benchmarks.yml` may still rely on `working-directory: ClassicLib-rs` and relative `benchmark-config.yaml` lookups. If those are not updated explicitly, the workflow could silently use fallback behavior or dead paths.

### Suggestions
- Add an explicit sweep in `06-02-PLAN.md` for crate-level benchmark `#[path = "..."]` references that target shared benchmark helpers under `benches/common/`.
- Make the `benchmarks.yml` path updates explicit in `06-03-PLAN.md`, especially `working-directory` and `benchmark-config.yaml` lookup behavior.
- Preserve structural comments when copying the workspace member list into the new repo-root `Cargo.toml` so the manifest stays readable.

### Risk Assessment
**MEDIUM**. The strategy is sound, but the benchmark-path fallout in `06-02` is a likely execution trap if it is not called out directly.

---

## the agent Review

### Overall Assessment
The four plans form a well-sequenced execution path for the repo-root workspace cutover. The dependency graph is sound, the phase boundary is respected, and the validation strategy is strong. The main concerns are a `validate_stubs.py` semantic gap in `06-01`, factual errors in `06-02` artifact assertions, and missing doc-sync scope in `06-03`.

### 06-00-PLAN.md

#### Summary
Creates the Wave 0 validation scaffold and clean-run helper before any cutover work begins. Straightforward bootstrap plan with little execution risk.

#### Strengths
- Correctly patterns the planning audit after the existing phase-validation tests.
- Freezes the placeholder test names early so later waves do not need to rename the validation contract.
- Encodes the intended clean-run proof sequence up front.

#### Concerns
- **LOW**: `clean_target_guard` appears in the verify command even though it will still be a placeholder in Wave 0, so the verification passes somewhat vacuously.
- **LOW**: The helper cannot actually run until after `06-01` creates the repo-root workspace shell, though the plan is only asking to create it here.

#### Suggestions
- No material changes needed.

#### Risk Assessment
**LOW**.

### 06-01-PLAN.md

#### Summary
This is the core cutover plan. It establishes repo-root `Cargo.toml`, moves lock/config files, deletes the old manifest, relocates `validate_stubs.py`, and rewires `rebuild_rust.ps1`.

#### Strengths
- Preserves `resolver = "2"` and explicitly forbids `default-members`.
- Correctly prefixes member paths with `ClassicLib-rs/` for this phase.
- Acceptance criteria are concrete and testable.
- Correctly aims to remove `--manifest-path` from `rebuild_rust.ps1`.

#### Concerns
- **HIGH**: `validate_stubs.py` path semantics are under-specified after the move. If the script now defaults to repo root while still internally targeting `ClassicLib-rs/python-bindings`, the meaning of `--rust-dir` changes and old invocation patterns may break.
- **MEDIUM**: The `must_haves` entry that expects `Join-Path $ProjectRoot "Cargo.toml"` may misdirect execution. If the script uses plain repo-root `cargo`, it may not need an explicit `Cargo.toml` path at all.
- **MEDIUM**: `rebuild_rust.ps1` likely has more `ClassicLib-rs`-rooted call sites than the plan currently enumerates, including `cargo clean` and bindings rebuild paths.
- **LOW**: Task 1 says to create `tests/planning/test_phase06_validation.py`, but `06-00` already created the scaffold; the plan should say to fill it in.

#### Suggestions
- Clarify whether `--rust-dir` now means repo root and whether backward-compatible fallback behavior is needed.
- Rephrase or remove the `rebuild_rust.ps1` `Join-Path ... "Cargo.toml"` must-have if plain repo-root Cargo is the actual goal.
- Enumerate the remaining `ClassicLib-rs` call sites in `rebuild_rust.ps1` so execution does not miss any.
- Change "Create" to "fill in" for the test-file wording.

#### Risk Assessment
**MEDIUM**.

### 06-02-PLAN.md

#### Summary
Moves the benchmark-owned support files to repo root and removes the old `ClassicLib-rs` copies. The scope is appropriate, but the plan needs tighter benchmark handling.

#### Strengths
- Keeps benchmark support-file relocation within the phase without turning benchmark CI green status into a closure gate.
- Depends cleanly on `06-01`.
- Maintains the intended phase boundary.

#### Concerns
- **HIGH**: The `must_haves.artifacts` assertions appear factually wrong for the actual benchmark config files. The plan references strings like `output_format` and `thresholds:` that Claude reported are not present in the current source files.
- **MEDIUM**: The plan assumes `benches/common/mod.rs` exists at the new location, but that specific file path may not have been verified before making it part of the acceptance criteria.
- **LOW**: Benchmark relative-path references may break when `benches/` moves to repo root.

#### Suggestions
- Verify the real contents of `criterion.toml` and `benchmark-config.yaml` and update the `contains:` assertions to match actual file content before execution.
- Confirm the exact `benches/common/` structure before locking `benches/common/mod.rs` into the acceptance criteria.
- Add a benchmark include/path sweep so shared benchmark helpers do not break when `benches/` moves.

#### Risk Assessment
**HIGH**.

### 06-03-PLAN.md

#### Summary
This is the closure plan: rewire `ci-rust.yml`, apply minimum viable `benchmarks.yml` path fixes, add Cargo-native root-detection audits, run the clean proof, and sync contributor and agent docs.

#### Strengths
- Correctly makes `ci-rust.yml` rewiring mandatory while keeping benchmark workflow work minimal.
- Uses `cargo locate-project` and `cargo metadata` as the phase-proof primitives.
- Includes a clean-state proof that avoids relying on stale `ClassicLib-rs/target` outputs.
- Covers the skill directories across multiple agent surfaces.

#### Concerns
- **HIGH**: `CLAUDE.md` is not included in the doc-sync scope even though it is an always-loaded instruction file and may still teach old `--manifest-path ClassicLib-rs/Cargo.toml` commands.
- **HIGH**: Active contributor docs such as `docs/api/QUICK_START.md` may also still contain old-root instructions if they are not included in the audit scope.
- **MEDIUM**: The plan says to apply "minimum path fixes" to `benchmarks.yml`, but it does not enumerate the specific steps or path assumptions that need to change.
- **MEDIUM**: Task 3 touches a wide set of doc/skill files, which raises the risk of inconsistent edits if the executor does not inventory everything first.
- **LOW**: Some cache-key references to `ClassicLib-rs/**/*.rs` will remain valid in Phase 6 but should stay visible as a later-phase concern.

#### Suggestions
- Add `CLAUDE.md` to the file list, acceptance criteria, and planning audits.
- Audit any active quick-start or setup docs that still teach old manifest-path workflows.
- Enumerate exactly which `benchmarks.yml` steps need repo-root path changes.
- Consider splitting CI/workflow rewiring from broad doc/skill sync if the edit set becomes too large.

#### Risk Assessment
**HIGH**.

### Summary of Findings by Severity

| Severity | Plan | Issue |
|---|---|---|
| **HIGH** | 06-01 | `validate_stubs.py` post-move `--rust-dir` semantics are under-specified |
| **HIGH** | 06-02 | Benchmark support-file assertions may not match the real file contents |
| **HIGH** | 06-03 | `CLAUDE.md` likely remains out of sync with the new repo-root Cargo contract |
| **HIGH** | 06-03 | Active setup docs may still teach old-root commands if not explicitly audited |
| **MEDIUM** | 06-01 | `rebuild_rust.ps1` may have more old-root call sites than the plan enumerates |
| **MEDIUM** | 06-02 | Benchmark helper paths and `benches/common/mod.rs` assumptions need verification |
| **MEDIUM** | 06-03 | `benchmarks.yml` minimum-fix scope is too implicit |

### Risk Assessment
**MEDIUM-HIGH**.

---

## Codex Review

Codex did not produce a final review in this environment.

- The initial run started, read the requested planning artifacts, and then stalled before emitting a final answer.
- A second retry with a reduced, file-scoped prompt also ran until timeout without writing a final message.
- Per the workflow, the review process continued with the completed external reviewers instead of blocking Phase 6 entirely on one CLI.

---

## Consensus Summary

The completed external reviews agree that the overall Phase 6 structure is good: the work is properly wave-ordered, the scope boundary between workspace-shell cutover and later crate relocation is correct, and Cargo-native root detection is the right proof strategy. The shared execution risk is not the root-manifest move itself, but the benchmark-related fallout and the need to keep every active workflow/doc surface aligned with the new repo-root contract.

### Agreed Strengths
- The phase is sequenced sensibly: validation scaffold first, workspace-shell cutover next, benchmark support-file relocation after that, and CI/docs closure last.
- The plans correctly make repo-root Cargo the canonical contract and avoid dual-root compatibility hacks.
- Using `cargo locate-project --workspace` and `cargo metadata --format-version 1 --no-deps` as proof mechanisms is a strong design choice.

### Agreed Concerns
- **Top concern:** `06-02` needs tighter benchmark relocation handling. Gemini flags likely broken crate-level benchmark include paths after moving `benches/`, and Claude separately flags that the plan's benchmark artifact assertions may not even match the real files.
- **Second concern:** `06-03` needs more explicit `benchmarks.yml` path rewiring. Both successful reviewers think the benchmark workflow's `ClassicLib-rs` assumptions are too implicit and should be enumerated concretely.
- **Third concern:** No other concern was shared by both completed reviewers at the same priority, but Claude raised additional high-value execution gaps around `validate_stubs.py` semantics and doc-sync scope.

### Divergent Views
- **Gemini** sees the plan set as structurally strong and mostly wants the benchmark-move details tightened, rating the overall risk **MEDIUM**.
- **Claude** agrees with the architecture and sequencing but rates the set **MEDIUM-HIGH** because of the `validate_stubs.py` semantic gap, likely incorrect benchmark-file assertions, and missing always-on doc surfaces such as `CLAUDE.md`.
- **Codex** could not be included in the consensus because both retries timed out before a final answer was produced.

### Recommended Replan Inputs
1. Amend `06-02-PLAN.md` so its artifact assertions match the real benchmark config files, confirm the exact `benches/common/` layout, and explicitly sweep/update any crate-level benchmark includes that target moved shared helpers.
2. Make `06-03-PLAN.md` concrete about `benchmarks.yml`: enumerate the exact steps, working directories, and config/target paths that must change after the repo-root move.
3. Resolve Claude's `06-01` helper-script concern before execution: document the post-move `validate_stubs.py` `--rust-dir` contract and inventory all remaining `ClassicLib-rs`-rooted call sites in `rebuild_rust.ps1`.
4. Extend the `06-03` doc-sync and audit scope to any always-on agent or contributor docs that still teach old manifest-path workflows, especially `CLAUDE.md` and any active quick-start/setup pages.

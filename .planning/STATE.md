---
gsd_state_version: 1.0
milestone: v9.1.0
milestone_name: milestone
status: executing
stopped_at: Completed 11-01-PLAN.md
last_updated: "2026-04-14T13:03:32.076Z"
last_activity: 2026-04-14
progress:
  total_phases: 7
  completed_phases: 5
  total_plans: 30
  completed_plans: 28
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-11)

**Core value:** The Rust workspace has minimal, well-bounded crates with no redundant boundaries -- every crate earns its compilation unit, and all binding surfaces remain at full parity with zero drift.
**Current focus:** Phase 11 — relocation-proof-and-verification-closure

## Current Position

Phase: 11 (relocation-proof-and-verification-closure) — EXECUTING
Plan: 2 of 3
Status: Ready to execute
Last activity: 2026-04-14

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**

- Total plans completed: 7
- Average duration: tracked in phase summaries
- Total execution time: tracked in phase summaries

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 06 | 4 | tracked | tracked |
| 07 | 3 | tracked | tracked |

**Recent Trend:**

- Last 5 plans: `06-02`, `06-03`, `07-01`, `07-02`, `07-03`
- Trend: Phase 6 and Phase 7 are complete; next work shifts to Phase 8 integration rewiring.

*Updated after each plan completion*
| Phase 06 P00 | 0min | 1 tasks | 2 files |
| Phase 06 P01 | 5 min | 2 tasks | 6 files |
| Phase 06 P02 | 1 min | 2 tasks | 13 files |
| Phase 06 P03 | 1h 19m | 3 tasks | 32 files |
| Phase 07 P01 | session | 2 tasks | 2 files |
| Phase 07 P02 | session | 2 tasks | 10+ files |
| Phase 07 P03 | session | 2 tasks | 6 files |
| Phase 10 P00 | 3min | 2 tasks | 2 files |
| Phase 10 P01 | 11 min | 2 tasks | 6 files |
| Phase 10 P03 | 5min | 1 tasks | 5 files |
| Phase 10 P07 | 12min | 2 tasks | 6 files |
| Phase 10-docs-guidance-and-tripwires P06 | 1 min | 2 tasks | 7 files |
| Phase 10 P05 | 15 min | 2 tasks | 6 files |
| Phase 10 P04 | 4m 5s | 2 tasks | 6 files |
| Phase 10 P02 | 20 min | 2 tasks | 8 files |
| Phase 10 P09 | 4min | 2 tasks | 8 files |
| Phase 10-docs-guidance-and-tripwires P08 | 15 min | 2 tasks | 5 files |
| Phase 11 P01 | 2 min | 1 tasks | 5 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Treat v9.1.0-root as a workspace-location migration only, not a crate-graph or API redesign.
- [Roadmap]: Keep continuous numbering from the prior milestone, so this roadmap starts at Phase 6.
- [Roadmap]: Sequence the work as root cutover → crate move → integration rewiring → clean validation → docs/tripwires.
- [Roadmap]: Three merges are independent -- execute sequentially (Phases 1-3) then validate gates together (Phase 4)
- [Roadmap]: Constants merge (Phase 3) has widest import fanout but does not depend on the other merges
- [Phase 01]: 01-02: Bridge D-09 expansion and rename landed in same commit; CMakeLists 5th-place registration added to project knowledge; parity gate failures deferred to 01-03
- [Phase 01]: Parity generator scripts now scan sub-module files recursively (tools/*_api_parity/generate_baseline.py) — the root-cause fix for struct methods declared outside lib.rs. Durable for future phase 2+3 merges
- [Phase 01]: Added tools/parity_contract_merge_owner.py as a reusable deterministic owner-group merge helper (delta-only collision check, schema auto-detection, --dry-run support). Reusable in Phase 2 constants+crashgen-settings merge and Phase 3 shared-helpers merge
- [Phase 02]: 02-01: Workspace crate merges need intermediate stub lib.rs between git mv and directory deletion — cargo parses full workspace manifest even for package-scoped builds. Pattern reusable for phase 3 constants merge.
- [Phase 02]: 02-01: *.bak files are gitignored (.gitignore line 47) so D-17's separate Chore commit for yamldata.rs.bak was mechanically impossible — resolved via filesystem delete without a git commit.
- [Phase 03]: Wave 1 removes every live workspace Cargo edge to classic-constants-core before later binding source rewrites land.
- [Phase 03]: classic-resource-core had no live constants usage, so its dependency was deleted instead of replaced.
- [Phase 03]: Retire the standalone constants API doc and document Fallout4Version, YamlFile/settings constants, and GameId under their surviving owners.
- [Phase 03]: Keep Python parity scanning both classic-shared-core and classic-shared-py so GameId redistribution and shared PyO3 wrappers both remain visible to the gate.
- [Phase 03]: Track Node version-core rust-only proxy rows with an explicit runtime-coverage selector after NULL_VERSION moved out of the retired constants owner.
- [Phase 04]: Use bun run parity:gate as the canonical active-doc Node audit command; reserve parity:gate:update-baseline for intentional refreshes.
- [Phase 04]: Keep retired crate names in active docs only as short historical notes attached to surviving owners.
- [Phase 04]: Keep CXX, Python, and Node checked-in parity baselines unchanged when the first plain gate pass already shows zero drift.
- [Phase 04]: Refresh Python stub validation evidence after Node runtime verification so Phase 4 closure uses current 16-crate binding counts.
- [Phase 04]: Record the heavy closure suite in the dedicated verification artifact first, then finalize the artifact as the single auditable milestone proof.
- [Phase 04]: Treat historical deferred_total wording as satisfied by current one-tier gate semantics and state that explicitly in the closure checklist.
- [Phase 05]: Refresh 03-VERIFICATION.md in place so Phase 3 keeps a single canonical verifier artifact.
- [Phase 05]: Use docs/api/README.md owner routing to repair the top-level Rust documentation index instead of adding replacement pages.
- [Phase 05]: Treat 705 rows as the live Node parity floor because the committed contract and diff report already show a 705/705 one-tier baseline.
- [Phase 05]: Enforce the passed Phase 3 closure claim with a live-path absence assertion instead of rewriting the Phase 3 artifact again.
- [Phase 05]: Treat the empty classic-constants-core directory as live-tree audit debt: remove it from disk and prevent recurrence through the Phase 5 test.
- [Phase 05]: Keep scope to the stale markdown contract and existing Phase 5 audit instead of refreshing any Node parity baselines.
- [Phase 05]: Treat parity_contract.json as the source of truth and require the markdown contract to name the live one-tier 705-row floor explicitly.
- [Phase 05]: Keep scope to the JSON contract description and existing audit/tripwire surfaces instead of refreshing any parity baselines.
- [Phase 05]: Require both audit surfaces to read the committed parity_contract.json description so stale hybrid-tier wording fails immediately.
- [Phase 06]: Reserved the full Phase 6 audit hook surface up front with skipped tests so later plans can fill the contract without renaming it. — Creates a stable validation contract before workspace-cutover tasks depend on it.
- [Phase 06]: Rename ClassicLib-rs/target during clean proof runs so stale legacy artifacts cannot mask repo-root Cargo failures. — Forces Phase 6 proof to use the new repo-root workspace outputs instead of legacy caches.
- [Phase 06]: Keep the promoted root manifest as a virtual workspace with resolver = "2" and no default-members.
- [Phase 06]: Normalize repo-root and explicit ClassicLib-rs --rust-dir inputs to the live python-bindings tree during Phase 6
- [Phase 06]: Use plain repo-root cargo commands in rebuild_rust.ps1 instead of legacy manifest-path calls
- [Phase 06]: Keep benchmark support files owned only at repo root so Criterion config and shared helper discovery have one canonical location during Phase 6.
- [Phase 06]: Standardize crate-level benchmark helper imports before relocation so the later repo-root move only needs a minimal include-path rebase.
- [Phase 06]: Keep Rust CI on plain repo-root cargo commands and repo-root target caching with no --manifest-path compatibility shim.
- [Phase 06]: Use cargo locate-project --workspace plus cargo metadata --format-version 1 --no-deps as the authoritative Phase 6 root proof.
- [Phase 06]: Limit benchmark workflow changes in Phase 6 to the minimum repo-root path/config fixes needed to keep moved benchmark assets viable.
- [Phase 06]: Treat active always-on docs and quick-start surfaces as closure-critical and audit them for stale ClassicLib-rs workspace guidance.
- [Phase 07]: Move `foundation/`, `business-logic/`, `cpp-bindings/`, `node-bindings/`, `python-bindings/`, and `ui-applications/` intact to repo root and strip only the `ClassicLib-rs/` prefix from root workspace members.
- [Phase 07]: Preserve crate-manifest `path =` relationships where the moved layer geometry keeps them valid; only rebase repo-relative include/helper paths proven broken by the move.
- [Phase 07]: Treat remaining `ClassicLib-rs` residue as non-authoritative only; no live `Cargo.toml` files or owned Rust sources remain there outside legacy `target/` output.
- [Phase 07]: Use the checked-in relocation audit plus Cargo root/member proof as the Phase 7 closure contract.
- [Phase 10]: Use named Phase 10 audit groups so later plans can target stable tests without renaming validation hooks.
- [Phase 10]: Scope stale-path enforcement to explicit active-surface allowlists plus line-based historical markers instead of a repo-wide ClassicLib-rs ban.
- [Phase 10]: Parse wrapper scripts before applying stale-path assertions so guidance tripwires fail on syntax drift as well as forbidden phrases.
- [Phase 10]: Keep old-to-new command, path, and artifact translations centralized in one matrix page instead of duplicating them across entry docs.
- [Phase 10]: Limit the current verification selector to the plan-owned top-level doc surfaces so later Phase 10 plans can extend coverage without blocking this plan.
- [Phase 10]: Keep deep API reference pages focused on repo-root source links and treat old ClassicLib-rs locations as historical context only.
- [Phase 10]: Use root-level crate, binding, and UI paths directly in plan-owned API guides instead of duplicating migration routing.
- [Phase 10]: Keep AGENTS.md policy text intact while swapping live location examples to the repo-root layer directories.
- [Phase 10]: Route always-on agent entrypoints to docs/workspace-migration-matrix.md instead of duplicating old-to-new translations.
- [Phase 10-docs-guidance-and-tripwires]: Updated the remaining runtime-group D API docs to repo-root crate and bridge paths instead of ClassicLib-rs workspace-root links.
- [Phase 10-docs-guidance-and-tripwires]: Kept historical rename and absorbed-crate notes only as labeled history, not live operational guidance.
- [Phase 10]: Keep workflow narratives intact and only rewrite active source, binding, and artifact locations to the repo-root tree.
- [Phase 10]: Treat the final stale classic-xse-core link as an inline doc bugfix and correct it in a follow-up fix commit rather than reopening task scope.
- [Phase 10]: Use repo-root relative links throughout active API reference pages because Phase 7 made root-level layer directories authoritative.
- [Phase 10]: Keep absorbed-crate notes only when clearly marked historical so contributors are not taught stale operational paths.
- [Phase 10]: Keep migration guidance centralized by linking active API and binding docs back to docs/workspace-migration-matrix.md.
- [Phase 10]: Teach Node parity through the package-local bun workflow while keeping Python and CXX parity commands repo-root-first.
- [Phase 10]: Treat all seven active .planning/codebase/*.md files as one audited guidance surface in test_phase10_validation.py.
- [Phase 10]: Keep ClassicLib-rs mentions in codebase maps residue-only, never as live workspace-root instructions.
- [Phase 10-docs-guidance-and-tripwires]: Keep all four repo-guide mirrors textually synchronized so validation and agent behavior stay aligned.
- [Phase 10-docs-guidance-and-tripwires]: Point parity workflow checklists back to docs/api binding guidance and the workspace migration matrix instead of duplicating legacy-path explanations.
- [Phase 11]: Replace the obsolete Phase 11 infra audit wholesale instead of patching legacy assertions in place.
- [Phase 11]: Make Phase 11 prove direct MOVE-01/MOVE-02 evidence and the missing 07-VERIFICATION artifact through deterministic file-backed tests.

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

### Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
|---|-------------|------|--------|--------|-----------|
| 260410-wsw | Fix pytest failures related to removed --deferred-registry flag | 2026-04-11 | f0b6aa17 | Verified | [260410-wsw-fix-pytest-failures-related-to-removed-d](./quick/260410-wsw-fix-pytest-failures-related-to-removed-d/) |
| 260411-m7y | Amend ROADMAP.md, REQUIREMENTS.md, and PROJECT.md for Phase 3 three-target redistribution per 03-CONTEXT.md D-01 | 2026-04-11 | d644da8e |  | [260411-m7y-amend-roadmap-md-requirements-md-and-pro](./quick/260411-m7y-amend-roadmap-md-requirements-md-and-pro/) |

## Session Continuity

Last session: 2026-04-14T13:03:32.073Z
Stopped at: Completed 11-01-PLAN.md
Resume file: None
Next action: Plan or execute Phase 08 wrapper/parity rewiring

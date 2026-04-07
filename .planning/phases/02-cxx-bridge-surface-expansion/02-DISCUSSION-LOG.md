# Phase 2: CXX Bridge Surface Expansion - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents. Authoritative decisions live in `02-CONTEXT.md`.

**Discussed:** 2026-04-07
**Mode:** discuss (no advisor mode — USER-PROFILE.md absent)
**Phase argument:** `2`
**Workflow:** discuss-phase

---

## Selected Gray Areas

User selected ALL FOUR offered gray areas via multiselect:

1. Module/file layout
2. Scangame DTO design
3. Baseline refresh cadence
4. Frontend update scope

---

## Round 1 — Module / File Layout

### Q1: Where should XSE helpers live in the bridge crate?

**Options presented:**
- New `xse.rs` file (Recommended) — dedicated `classic::xse` namespace; existing string helpers move from `game.rs`
- Widen `game.rs` in place — keep multi-domain bridge file
- Hybrid (new file + shims) — new file for typed surfaces, leave string helpers in `game.rs`

**User selected:** New `xse.rs` file (Recommended) → **D-01**

### Q2: Where should classic-version-registry-core helpers live?

**Options presented:**
- New `version_registry.rs` (Recommended) — `classic::version_registry` namespace; existing `registry.rs` stays for `classic-registry-core` KV
- Widen `game.rs` in place — keep version-registry mixed with PE/path/XSE
- Reuse existing `registry.rs` name — rename current `registry.rs` to `kv.rs`, put VR under `registry.rs` (forces consumer rename sweep)

**User selected:** New `version_registry.rs` (Recommended) → **D-02**

### Q3: How should `src/path.rs` be brought into `build.rs`?

**Options presented:**
- Add as-is, then widen in subsequent plans (Recommended)
- Widen first, then add — single commit with full surface
- Replace entirely — rewrite from scratch

**User selected:** Add as-is, then widen in subsequent plans (Recommended) → **D-03**

### Q4: How should `classic-constants-core` enums cross the FFI boundary?

**Options presented:**
- CXX shared enums + helpers (Recommended) — declared inside `#[cxx::bridge]`, type-safe
- Flat string getter functions — fail-soft, mirrors registry.rs / game.rs string style
- Round-tripped via i32 + helpers — opaque, awkward

**User selected:** CXX shared enums + helpers (Recommended) → **D-04**

---

## Round 2 — Scangame DTO Design (CXXS-04)

### Q1: Default DTO shape for "list of issues" results?

**Options presented:**
- Flat CXX shared struct per issue type (Recommended) — Pitfall 6 compliant
- Parallel `Vec<String>` columns — like config mod_conf
- Tab-delimited batch strings — like database batch
- Combined-output text summary only — like existing `run_setup_checks`

**User selected:** Flat CXX shared struct per issue type (Recommended) → **D-05**

### Q2: How should nested `GameScanResult` be flattened?

**Options presented:**
- One bridge fn per sub-domain (Recommended) — caller composes
- One "summary" shared struct with parallel `Vec<IssueDto>` fields
- Single unified `Vec<ScanIssueDto>` — stringly-typed dispatch

**User selected:** One bridge fn per sub-domain (Recommended) → **D-06**

### Q3: How should severity / category enums cross the boundary?

**Options presented:**
- CXX shared enums (Recommended) — consistent with D-04
- String fields ("ERROR" / "WARNING" / "INFO") — fail-soft
- i32 codes with helper accessors — compact but opaque

**User selected:** CXX shared enums (Recommended) → **D-07**

### Q4: Keep core-side combined-output summary helpers alongside structured DTOs?

**Options presented:**
- Expose both: structured + summary string (Recommended) — preserves CXXS-10 no-breakage
- Structured only — drop combined() shims, force consumer migration
- Summary string only — defer structured to future phase, likely fails CXXS-04

**User selected:** Expose both: structured + summary string (Recommended) → **D-08**

---

## Round 3 — Baseline Refresh Cadence

### Q1: When should `--update-baseline` run during Phase 2?

**Options presented:**
- Per-plan, same commit (Recommended) — atomic, bisectable, repo always gate-green
- Per-file refresh — multiplies commit count
- Phase-end single refresh — repo gate-RED for the duration

**User selected:** Per-plan, same commit (Recommended) → **D-09**

### Q2: When should clean MSVC builds run to catch Pitfall 5?

**Options presented:**
- After every new module added to `build.rs` (Recommended) — at least 5 mandatory cycles
- Per-plan, one clean build at plan close — masks which module broke header generation
- Phase-end only — defers all header-order risk to phase close

**User selected:** After every new module added to `build.rs` (Recommended) → **D-10**

---

## Round 4 — Frontend Update Scope (CXXS-10)

### Q1: How aggressively should `classic-cli` / `classic-gui` call sites be migrated?

**Options presented:**
- Surface-only — zero consumer changes (Recommended for scope discipline)
- Migrate currently-narrowed call sites — proves widening with at least one production caller
- Full consumer sweep — replace any C++ helper with a Rust counterpart

**User selected:** Migrate currently-narrowed call sites (NOT the recommended option) → **D-11**

**Note:** This is a deliberate scope expansion. The user explicitly chose the production-caller-validation path over the safer surface-only default. Recorded in CONTEXT.md as "the user wants the widening proven by real callers, not just compile-clean." Researcher must enumerate qualifying call sites before planner decomposes tasks.

### Q2: How should new bridge functions be tested within Phase 2?

**Options presented:**
- Rust-side `#[cfg(test)]` tests in each new bridge file (Recommended) — fast, hermetic, no MSVC needed
- Catch2 C++ tests in classic-cli/classic-gui — slower, validates actual CXX boundary
- Both tiers — highest confidence, doubles maintenance

**User selected:** Rust-side `#[cfg(test)]` tests (Recommended) → **D-12**

---

## Closing

**Question:** Anything else to explore before writing CONTEXT.md?
**User selected:** "I'm ready for context" — proceed to write `02-CONTEXT.md`.

**Total decisions captured:** 12 (D-01 through D-12)
**Deviations from recommendation:** 1 (D-11 — frontend migration scope)
**Folded todos:** None (`gsd-tools todo match-phase 2` returned 0 matches)
**Deferred ideas captured:** 9 (see CONTEXT.md `<deferred>` section)

---

*Audit log written: 2026-04-07*

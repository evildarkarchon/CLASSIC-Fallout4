# Phase 6: Documentation Reset - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

All Tier-2 governance files are deleted; `binding-parity-overview.md` is rewritten as the harmony-achieved reference; a single source-of-truth parity policy doc exists; per-binding error-contract conventions are documented; gate scripts are cleaned of dead deferred-registry logic; `binding-contract-refresh-note.md` is updated to cover the C++ refresh workflow.

**Requirements:** DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06, DOC-07, HARM-05

</domain>

<decisions>
## Implementation Decisions

### Promotion audit trail (DOC-04)
- **D-01:** Raw file archive — copy full content of each governance file into the audit doc as-is, preserving exact state at deletion time
- **D-02:** One combined document at `.planning/milestones/v9.1.0-bindings-promotion-audit.md` with sections for Python (3 files) and Node (5 files)
- **D-03:** Governance files only — baseline JSON/md files are not included (they survive deletion and are gate-refreshed)
- **D-04:** Brief context header (2-3 sentences: why Tier-2 existed, which phases promoted entries, date of deletion)
- **D-05:** Cleanup scope is docs/ only — baseline JSON files and .planning/ artifacts are not modified for stale governance references (machine-generated baselines refresh naturally on next gate run)

### Gate script cleanup (DOC-01)
- **D-06:** Remove the `--deferred-registry` CLI argument entirely from both `tools/python_api_parity/check_parity_gate.py` and `tools/node_api_parity/check_parity_gate.py` — the concept is dead after this milestone
- **D-07:** Full cleanup — remove `--deferred-registry` arg, all `deferred_registry` variables, any `_lookup_maps(deferred_entries)` calls, and `deferred_total`/`deferred` fields from summary output in both scripts. Dead code should be dead.
- **D-08:** Delete `generate_wave_manifest.py` from both `tools/python_api_parity/` and `tools/node_api_parity/`. Delete `generate_deferred_backlog.py` from `tools/node_api_parity/`. These exist solely to manage Tier-2 artifacts that no longer exist.
- **D-09:** Keep `check_parity_gate.py`, `generate_baseline.py` (both dirs), and `check_dts_freshness.py` (Node only) — those are the live gate scripts.

### Parity overview rewrite (DOC-05)
- **D-10:** Full rewrite from scratch with a "harmony achieved" framing — not an in-place update. The current doc's structure ("current narrowing, current omissions") does not match the post-Phase-2/3/4 reality.
- **D-11:** Per-crate table with columns: Rust Crate | C++ Bridge Module | Node Module | Python Module. Each cell links to the source file. Quick visual proof that every crate has all three surfaces.
- **D-12:** Brief FFI adaptation section — 1 paragraph per binding on how Rust types are adapted at the edge (CXX DTOs, NAPI objects, PyO3 wrappers). Links to per-crate API docs for details.
- **D-13:** Gate commands are NOT in the overview — link to the new `binding-parity-policy.md` (DOC-06) for gate run instructions and ownership.

### Parity policy doc (DOC-06)
- **D-14:** New `docs/api/binding-parity-policy.md` — the single source-of-truth: one-tier policy statement, when gate refreshes happen, who owns each gate, how to add a new public Rust API across all three bindings.

### Contract refresh note update (DOC-07)
- **D-15:** Update `docs/api/binding-contract-refresh-note.md` to cover the C++ refresh workflow alongside the existing Node/Python guidance. Remove references to deleted governance files.

### Error-contract doc (HARM-05)
- **D-16:** Per-binding sections — three main sections: C++ (`rust::Error` exceptions + empty-string sentinels), Node (`error.code` strings, null returns), Python (typed exception classes). Each section documents the convention with 2-3 concrete code examples from actual crate wrappers.
- **D-17:** "Why They Differ" section explaining why each binding chose its error shape. Prevents future contributors from "fixing" intentional design choices (e.g., C++ empty-string sentinel for `db_pool_get_entry` because Qt callers depend on it).
- **D-18:** Conversion helper mentions with source links — reference key functions like `config_error_to_napi_err` and `classic-shared-py` error converters by name, linking to source files. No code duplication.

### Governance file deletion (DOC-02, DOC-03)
- **D-19:** Ordering constraint: D-06/D-07 (gate cleanup) and D-01/D-02 (audit trail) MUST land before governance files are deleted. This is explicit in DOC-01's requirement.
- **D-20:** Delete all files under `docs/implementation/python_api_parity/governance/` (3 files: `tier2_backlog_and_governance.md`, `deferred_runtime_backlog.json`, `tier2_wave_manifest.json`)
- **D-21:** Delete all files under `docs/implementation/node_api_parity/governance/` (5 files: `per_wave_acceptance_template.md`, `tier2_wave_manifest.json`, `tier2_backlog_and_governance.md`, `gate_contract_baseline.md`, `deferred_runtime_backlog.json`)
- **D-22:** Post-deletion verification: `grep -r "tier2" docs/` across all committed docs files returns zero results referencing deleted files

### Claude's Discretion
- Exact prose and structure of the parity policy doc (DOC-06) — user specified the topics (one-tier policy, gate refresh schedule, gate ownership, new-API workflow) but not the wording
- Exact error-contract code examples to include — user specified 2-3 per binding, Claude picks the most illustrative ones
- Ordering of plans within the phase — user locked the constraint (gate cleanup before governance deletion) but plan decomposition is Claude's call
- Whether `docs/api/node-python-contract-map.md` needs updating for deleted governance references (likely yes, but Claude verifies during planning)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Parity gate scripts (DOC-01 targets)
- `tools/python_api_parity/check_parity_gate.py` — Python gate script; `--deferred-registry` arg at line 190, `deferred_registry` usage at lines 231/237/241
- `tools/node_api_parity/check_parity_gate.py` — Node gate script; `--deferred-registry` arg at line 294, `deferred_registry` usage at lines 368/374/378

### Dead scripts to delete (D-08)
- `tools/python_api_parity/generate_wave_manifest.py` — Tier-2 wave manifest generator (dead)
- `tools/node_api_parity/generate_wave_manifest.py` — Tier-2 wave manifest generator (dead)
- `tools/node_api_parity/generate_deferred_backlog.py` — deferred backlog generator (dead)

### Governance files to archive then delete (DOC-02, DOC-03, DOC-04)
- `docs/implementation/python_api_parity/governance/tier2_backlog_and_governance.md`
- `docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json`
- `docs/implementation/python_api_parity/governance/tier2_wave_manifest.json`
- `docs/implementation/node_api_parity/governance/per_wave_acceptance_template.md`
- `docs/implementation/node_api_parity/governance/tier2_wave_manifest.json`
- `docs/implementation/node_api_parity/governance/tier2_backlog_and_governance.md`
- `docs/implementation/node_api_parity/governance/gate_contract_baseline.md`
- `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json`

### Docs to rewrite or create (DOC-05, DOC-06, DOC-07, HARM-05)
- `docs/api/binding-parity-overview.md` — current doc with outdated narrowing language; to be rewritten (DOC-05)
- `docs/api/binding-parity-policy.md` — does not exist yet; to be created (DOC-06)
- `docs/api/binding-contract-refresh-note.md` — references governance files that will be deleted; to be updated (DOC-07)
- `docs/api/error-contract.md` — does not exist yet; to be created (HARM-05)

### Existing API docs (for error-contract examples and overview cross-refs)
- `docs/api/classic-cpp-bridge-data-entrypoints.md` — C++ bridge error handling patterns
- `docs/api/classic-cpp-bridge-game-entrypoints.md` — C++ bridge error handling patterns
- `docs/api/node-python-contract-map.md` — may reference governance files; verify during planning
- `docs/api/cxx-parity-gate.md` — CXX gate contributor doc; may need cross-ref from policy doc

### Prior phase context (ordering dependencies)
- `.planning/phases/03-python-tier-collapse/03-CONTEXT.md` — Python governance file deferral to Phase 6
- `.planning/phases/04-node-tier-collapse/04-CONTEXT.md` — Node governance file deferral to Phase 6
- `.planning/phases/05-ci-enforcement/05-CONTEXT.md` — CI enforcement in place before governance deletion

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Gate scripts already have clean argparse structure — removing `--deferred-registry` is a surgical deletion of arg definition + downstream usage
- `docs/api/README.md` already indexes all API docs — new docs (error-contract, parity-policy) need index entries added

### Established Patterns
- Phase 3/4 CONTEXT files explicitly deferred governance cleanup to Phase 6 with specific file lists
- Gate scripts follow a consistent pattern: argparse → load files → run checks → emit summary JSON + markdown
- API docs follow a consistent structure: Purpose → Scope → Details → References to AGENTS.md

### Integration Points
- `docs/api/README.md` — must add entries for `error-contract.md` and `binding-parity-policy.md`
- `docs/api/binding-contract-refresh-note.md` — must update references from governance files to the new policy doc
- `docs/api/node-python-contract-map.md` — must verify/update governance references
- CI workflows reference gate scripts by path — no path changes needed since scripts stay in place

</code_context>

<specifics>
## Specific Ideas

- User wants the deferred-registry concept to be fully dead — no tolerance wrappers, no deprecation warnings, just deleted
- The overview rewrite should be a clean-slate "harmony achieved" doc, not a patched version of the old narrowing-focused doc
- Error-contract doc explicitly documents why the three shapes differ, to prevent future "standardization" attempts — the Out of Scope section in REQUIREMENTS.md already blocks this

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-documentation-reset*
*Context gathered: 2026-04-09*

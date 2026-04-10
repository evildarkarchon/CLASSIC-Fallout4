# Phase 6: Documentation Reset - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-09
**Phase:** 06-documentation-reset
**Areas discussed:** Promotion audit trail, Gate script tolerance, Parity overview rewrite, Error-contract doc

---

## Promotion Audit Trail

### How comprehensive should the promotion audit trail be?

| Option | Description | Selected |
|--------|-------------|----------|
| Raw file archive (Recommended) | Copy full content of each governance file into the audit doc as-is. Simple, lossless, fast. | ✓ |
| Summarized promotion log | Extract entry names/counts with table showing which Phase/Plan promoted each batch. Readable but lossy. | |
| Annotated per-plan history | Cross-reference each promoted entry with the specific plan and commit. Most thorough but significant effort. | |

**User's choice:** Raw file archive
**Notes:** None

### One combined doc or separate?

| Option | Description | Selected |
|--------|-------------|----------|
| One combined doc (Recommended) | Single .planning/milestones/v9.1.0-bindings-promotion-audit.md with Python and Node sections. | ✓ |
| Two separate docs | One per binding surface. More modular but splitting adds overhead. | |

**User's choice:** One combined doc
**Notes:** None

### Scope — governance files only or also baselines?

| Option | Description | Selected |
|--------|-------------|----------|
| Governance files only (Recommended) | Only the files being deleted (3 Python + 5 Node governance files). Baseline files survive. | ✓ |
| Governance + baseline snapshot | Also snapshot baseline files at deletion time. Complete but git-recoverable. | |
| Governance + docs referencing them | Also capture current state of docs that reference governance files. | |

**User's choice:** Governance files only
**Notes:** None

### Non-docs file cleanup scope

| Option | Description | Selected |
|--------|-------------|----------|
| Docs only (Recommended) | Clean up references in docs/ only. Baseline JSON files refresh naturally on next gate run. | ✓ |
| Docs + baseline files | Also update baseline JSON/md files to remove governance references. | |
| Everything referencing tier2 | Clean all references project-wide including .planning/ artifacts. | |

**User's choice:** Docs only
**Notes:** None

### Audit trail header

| Option | Description | Selected |
|--------|-------------|----------|
| Brief context header (Recommended) | 2-3 sentence intro: why Tier-2 existed, when promoted, date of deletion. | ✓ |
| Raw files only, no preamble | Just file contents with section dividers. | |

**User's choice:** Brief context header
**Notes:** None

---

## Gate Script Tolerance

### How should gate scripts handle missing --deferred-registry?

| Option | Description | Selected |
|--------|-------------|----------|
| Skip when missing (Recommended) | If file doesn't exist, treat as empty. Log info message. No crash. | |
| Remove the argument entirely | Delete --deferred-registry from argparse and all deferred_registry logic. Concept is dead. | ✓ |
| Make it optional with warning | Keep arg but make optional (default=None). Log deprecation warning. | |

**User's choice:** Remove the argument entirely
**Notes:** None

### Downstream consumer cleanup

| Option | Description | Selected |
|--------|-------------|----------|
| Full cleanup (Recommended) | Remove arg, all deferred_registry variables, _lookup_maps(deferred_entries) calls, deferred_total/deferred fields from output. | ✓ |
| Arg only, leave internals | Remove just argparse entry and load_json_file call. Internal logic gets empty-dict default. | |

**User's choice:** Full cleanup
**Notes:** None

### Script deletion inventory

| Option | Description | Selected |
|--------|-------------|----------|
| Delete wave/deferred only (Recommended) | Delete generate_wave_manifest.py (both) + generate_deferred_backlog.py (Node). Keep gate + baseline + dts freshness. | ✓ |
| Delete all except gate scripts | Keep only check_parity_gate.py in each dir. | |
| You decide | Claude determines which are still referenced. | |

**User's choice:** Delete wave/deferred only
**Notes:** None

---

## Parity Overview Rewrite

### How should the rewrite be framed?

| Option | Description | Selected |
|--------|-------------|----------|
| Harmony reference (Recommended) | Rewrite from scratch with "what's now exposed everywhere" framing. Crate table all green. | ✓ |
| Update in-place | Keep current structure but update rows. Faster but framing won't match reality. | |
| Minimal delta | Only fix factually wrong statements. | |

**User's choice:** Harmony reference
**Notes:** None

### Per-crate table?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, with source links (Recommended) | Table: Rust Crate | C++ | Node | Python with source file links. | ✓ |
| Yes, names only | Same table, no links. Simpler to maintain. | |
| No table, prose only | Describe harmony state in paragraphs. Gate reports are authoritative. | |

**User's choice:** Yes, with source links
**Notes:** None

### FFI type adaptation section?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep brief section (Recommended) | 1 paragraph per binding on Rust type adaptation. Links to per-crate docs for details. | ✓ |
| Remove, link to API docs | Per-crate API docs already cover this. | |
| Detailed per-crate notes | Current detail level but reframed from "narrowing" to "adaptation." | |

**User's choice:** Keep brief section
**Notes:** None

### Cross-reference parity gates?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, brief pointers (Recommended) | Section listing all three gate scripts with run commands. | |
| No, link to policy doc | New binding-parity-policy.md will cover gate commands. Overview just links to it. | ✓ |
| You decide | Claude determines balance during planning. | |

**User's choice:** No, link to policy doc
**Notes:** None

---

## Error-Contract Doc

### How should the doc be organized?

| Option | Description | Selected |
|--------|-------------|----------|
| Per-binding sections (Recommended) | Three main sections: C++ (rust::Error + sentinels), Node (error.code + null), Python (typed exceptions). With examples. | ✓ |
| Per-crate matrix | Table: rows = crates, columns = bindings, cells = error shapes. Exhaustive but large. | |
| Per-ClassicError variant | Organized by Rust error enum variants. Most precise but ties doc to Rust internals. | |

**User's choice:** Per-binding sections
**Notes:** None

### Detail level per binding section?

| Option | Description | Selected |
|--------|-------------|----------|
| Pattern + examples (Recommended) | General pattern + 2-3 concrete code examples from actual wrappers + edge cases. | ✓ |
| Pattern only | Just the general convention per binding (1 paragraph each). | |
| Full variant mapping | Every ClassicError variant and its representation per binding. | |

**User's choice:** Pattern + examples
**Notes:** None

### Intentional divergences section?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, with rationale (Recommended) | "Why They Differ" section explaining each binding's error shape choice. | ✓ |
| Yes, list only | List divergences without explaining rationale. | |
| No, just document what exists | Describe current shapes without editorializing. | |

**User's choice:** Yes, with rationale
**Notes:** None

### Conversion helper coverage?

| Option | Description | Selected |
|--------|-------------|----------|
| Mention with source links (Recommended) | Reference key conversion helpers by name with source file links. | ✓ |
| Document the mapping logic | Show how each helper maps Rust errors. More detail but duplicates code. | |
| Skip helpers entirely | Focus on consumer-visible contract shapes only. | |

**User's choice:** Mention with source links
**Notes:** None

---

## Claude's Discretion

- Exact prose and structure of the parity policy doc (DOC-06)
- Exact error-contract code examples to include (2-3 per binding)
- Plan decomposition and ordering (constraint: gate cleanup before governance deletion)
- Whether `docs/api/node-python-contract-map.md` needs updating for deleted governance references

## Deferred Ideas

None — discussion stayed within phase scope

# Phase 6: mmap TOCTOU Safety - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `06-CONTEXT.md`.

**Date:** 2026-04-06
**Phase:** 06-mmap-toctou-safety
**Areas discussed:** Mapping mode conflict, Benchmark home, Benchmark coverage, Rollout policy

---

## Mapping mode conflict

| Option | Description | Selected |
|--------|-------------|----------|
| `map_copy_read_only()` | Read-only COW snapshot; matches the roadmap direction and a read-only scan path. | ✓ |
| `map_copy()` | Writable COW mapping; isolates external changes, but adds mutability the scan path does not need. | |
| `Mmap::map()` | Keeps the current zero-copy behavior, but does not close the TOCTOU race. | |

**User's choice:** `map_copy_read_only()`
**Notes:** This resolves the current roadmap vs `PROJECT.md` / `REQUIREMENTS.md` mismatch in favor of the safer read-only copy mapping.

---

## Benchmark home

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse `file_io_benchmarks.rs` | Extend the existing `classic-file-io-core` Criterion harness in the same crate as `read_file_mmap()`. | ✓ |
| New mmap-only harness | Create a separate bench file dedicated to the Phase 6 proof. | |
| Reuse scanlog harness | Put mmap proof beside the Phase 5 proof even though the changed code lives in `classic-file-io-core`. | |

**User's choice:** Reuse `file_io_benchmarks.rs`
**Notes:** Keep the proof in the crate that owns the code instead of coupling Phase 6 to the scanlog benchmark harness.

---

## Benchmark coverage

| Option | Description | Selected |
|--------|-------------|----------|
| Near-threshold + large synthetic | Use sizes around the 1 MB cutoff plus larger synthetic files so the mmap path is guaranteed and scaling is visible. | ✓ |
| Synthetic + padded fixtures | Mix deterministic synthetic inputs with crash-log-like content expanded beyond the mmap threshold. | |
| Real fixtures only | Use repo crash-log fixtures only, even though current fixtures are mostly below the mmap cutoff. | |

**User's choice:** Near-threshold + large synthetic
**Notes:** Representative evidence should guarantee the mmap branch runs instead of relying on current crash-log fixtures that are usually too small.

---

## Rollout policy

| Option | Description | Selected |
|--------|-------------|----------|
| All platforms | Keep one core code path and switch `read_file_mmap()` everywhere, while validating Windows as the risky platform. | ✓ |
| Windows only | Apply the safer mapping only on Windows and keep the current path elsewhere. | |
| Decide after benchmarks | Treat the benchmark as a go/no-go gate before locking rollout scope. | |

**User's choice:** All platforms
**Notes:** Windows is the platform that must be benchmarked explicitly, but the implementation should not fork into separate platform-specific behavior by default.

---

## the agent's Discretion

- Exact benchmark sizes above and around the 1 MB threshold.
- Exact Criterion group names and baseline labels.
- Exact wording and placement of the planning/API doc alignment updates.

## Deferred Ideas

None.

# Phase 7: Consistency Sweep - Research

**Researched:** 2026-04-06
**Domain:** Rust standard-library lazy initialization migration (`once_cell` -> `std::sync::{LazyLock, OnceLock}`)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
### Sweep Breadth
- **D-01:** Phase 7 should cover production source, Cargo manifests, and affected `docs/api` pages together. Do not leave stale `once_cell` references behind in touched docs or dependency declarations.
- **D-02:** Remove stale `once_cell` dependency declarations from crates that no longer use it, including already-converted crates such as `classic-yaml-core`, `classic-settings-core`, and `classic-scangame-core`, plus workspace/root declarations if the final audit shows no remaining `once_cell` APIs.

### once_cell Exit Strategy
- **D-03:** Treat full `once_cell` removal as the desired end state for Phase 7, not merely `Lazy` replacement.
- **D-04:** Migrate the remaining `OnceCell` usage in `ClassicLib-rs/business-logic/classic-scanlog-core/src/record_scanner.rs` to `std::sync::OnceLock` if the semantics stay one-for-one, so the dependency can leave the workspace entirely after the sweep.
- **D-05:** If execution discovers any additional non-`Lazy` `once_cell` APIs beyond the current audit, review them before removal rather than keeping `once_cell` by default.

### Verification Bar
- **D-06:** Verification should include targeted tests for touched crates with global/static behavior, plus a workspace-level build to catch manifest and integration breakage.
- **D-07:** Binding parity gates are not required by default for this phase unless execution unexpectedly changes a binding-visible contract.

### Churn Style
- **D-08:** Reuse the established Phase 4/5 `LazyLock` style instead of redesigning modules during the sweep.
- **D-09:** Small cleanup is allowed only when it stays adjacent to the touched files or modules and directly improves the migration result; no broader crate-wide refactors.

### the agent's Discretion
- Exact ordering and grouping of touched files and crates.
- Exact import style and constructor expressions for `LazyLock` and `OnceLock`, as long as semantics stay unchanged.
- Exact targeted test list and command sequencing, as long as it satisfies the locked verification bar above.

### Deferred Ideas (OUT OF SCOPE)
None - discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CONS-01 | Replace `once_cell::sync::Lazy` with `std::sync::LazyLock` across all crates still using `once_cell` | Confirms `LazyLock` is stable in std since Rust 1.80, `OnceLock` is stable since 1.70 for the remaining `OnceCell` site, identifies all direct manifest/docs cleanup targets, and defines the minimal validation set plus the critical caveat that transitive `once_cell` will still remain in `Cargo.lock`. |
</phase_requirements>

## Project Constraints (from AGENTS.md)

- Prioritize active work in `classic-cli/`, `classic-gui/`, and `ClassicLib-rs/`.
- Keep all business logic in Rust; shared behavior, state transitions, mutation, persistence rules, and validation belong in Rust core crates unless the task is explicitly interface-only.
- Keep non-interface layers thin; bindings and UI surfaces should wrap Rust APIs rather than reimplement logic.
- Maintain a single shared Tokio runtime from Rust core runtime facilities; do not introduce independent runtimes.
- Keep docs synchronized with architecture or workflow changes, especially `README.md` and `AGENTS.md`.
- Never write to `NUL` or `nul` as a file path on Windows.
- Consult `docs/api/README.md` before changing public Rust, bridge, GUI-consumer, or binding-facing APIs; if a contract-shaping change occurs, update affected `docs/api/` pages in the same change.
- Never run C++ tests via raw binaries or raw `ctest`; use the repo PowerShell wrappers.
- Rust/MSVC-targeted commands run from Git Bash must go through `tools/use_msvc_from_git_bash.sh`; PowerShell-native commands avoid that issue.
- Python and Node bindings should stay in sync with Rust core logic, but this phase does not need parity gates unless the contract changes unexpectedly.

## Summary

Phase 7 should be implemented as a narrow Rust-core consistency migration: replace every remaining direct `once_cell::sync::Lazy` with `std::sync::LazyLock`, replace `RecordScanner`'s remaining `once_cell::sync::OnceCell` fields with `std::sync::OnceLock`, then remove now-unused direct `once_cell` declarations from the workspace and touched crate manifests in the same change. Update the affected `docs/api` pages immediately after source changes so contributor docs stop describing stale `once_cell` internals.

The repo already established the target style in Phases 4 and 5: `use std::sync::LazyLock;` plus `static NAME: LazyLock<T> = LazyLock::new(|| ...)`. Reuse that pattern verbatim. For `RecordScanner`, `OnceLock::get_or_init` is the correct one-for-one replacement because the initialization closure still needs access to `self.lower_records` / `self.lower_ignore` at call time; `LazyLock` is not the right primitive for those per-instance fields.

The biggest planning trap is success criteria wording. Direct `once_cell` usage can leave the workspace source and direct manifests entirely, but `once_cell` will still remain in `Cargo.lock` and the overall dependency graph transitively through crates such as `dashmap`, `pyo3`, `quick_cache`, and `serial_test` (`cargo tree -i once_cell` proves this locally). So the phase should treat success as **no direct code or direct manifest dependency on `once_cell` in this repo's owned crates**, not “`once_cell` vanishes from the lockfile.”

**Primary recommendation:** Migrate owned code to `std::sync::{LazyLock, OnceLock}`, remove only direct `once_cell` declarations, sync touched `docs/api` pages, and validate with targeted crate tests plus `cargo build --workspace`.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `std::sync::LazyLock` | std stable since 1.80.0; current docs 1.94.1 | Process-wide lazy statics | In std, matches the repo's Phase 4/5 pattern, and replaces `once_cell::sync::Lazy` without keeping a direct third-party dependency. |
| `std::sync::OnceLock` | std stable since 1.70.0; current docs 1.94.1 | Per-instance one-time initialization | Best one-for-one replacement for `RecordScanner` field-level `OnceCell` usage where init still depends on runtime `self` data. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `serial_test` | 3.4.0 (verified via `cargo search serial_test --limit 1`) | Serialize tests touching process-global mutable state | Keep for registry/perf/global-state test isolation; do not remove in this phase. |
| Cargo workspace manifests | repo uses Rust 1.85.0 minimum; local toolchain is rustc 1.94.0 / cargo 1.94.0 | Direct dependency cleanup and workspace verification | Remove direct `once_cell` entries only after source migration, then rebuild workspace to catch stale manifest wiring. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `std::sync::LazyLock` | `once_cell::sync::Lazy` | No benefit here; both support the same role, but `LazyLock` is already stable in std and is the locked repo direction. |
| `std::sync::OnceLock` | `once_cell::sync::OnceCell` | `OnceLock` is already in std and exposes the same core `new`/`get`/`get_or_init`/`set`/`take` model needed by `record_scanner.rs`. |
| `OnceLock` for `RecordScanner` fields | `LazyLock` field rewrite | Wrong fit: `LazyLock::new` stores the initializer up front, while `RecordScanner` needs a per-instance closure that reads `self` fields later. |

**Installation:**
```bash
# No new crates are needed for Phase 7.
# Remove direct `once_cell` entries after source migration succeeds.
```

**Version verification:**
- `LazyLock` stabilized in Rust 1.80.0 (2024-07-25) and is present in current std docs 1.94.1.
- `OnceLock` stabilized in Rust 1.70.0 (2023-06-01) and is present in current std docs 1.94.1.
- Repo minimum Rust version is `1.85.0`/`1.85`, so both std primitives are safely available everywhere in scope.
- `once_cell` latest registry version is `1.21.4` (`cargo search once_cell --limit 1`), but the recommended stack is to remove direct usage rather than upgrade it.

## Architecture Patterns

### Recommended Project Structure
```text
ClassicLib-rs/
├── business-logic/
│   ├── classic-scanlog-core/src/      # Replace remaining Lazy statics; migrate RecordScanner OnceCell -> OnceLock
│   ├── classic-registry-core/src/     # Replace process-global registry static with LazyLock
│   └── classic-perf-core/src/         # Replace process-global metrics static with LazyLock
├── business-logic/*/Cargo.toml        # Remove direct `once_cell` where no longer used
├── Cargo.toml                         # Remove workspace `once_cell` only after final direct-use audit
└── docs/api/*.md                      # Update contributor docs in the same change
```

### Pattern 1: Static global migration with `LazyLock`
**What:** Replace `once_cell::sync::Lazy<T>` statics with `std::sync::LazyLock<T>` using the existing Phase 4/5 initialization style.
**When to use:** Module-level or function-local `static` values whose initializer is known up front and does not need extra call-time inputs.
**Example:**
```rust
// Source: https://doc.rust-lang.org/std/sync/struct.LazyLock.html
use std::sync::LazyLock;

static REGISTRY: LazyLock<DashMap<String, RegistryValue>> =
    LazyLock::new(DashMap::new);
```

### Pattern 2: Per-instance deferred builder with `OnceLock`
**What:** Replace `OnceCell` fields with `OnceLock` fields and keep `get_or_init(|| ...)` at the point where `self` is available.
**When to use:** Struct fields initialized once from instance data on first use, like `RecordScanner` matchers.
**Example:**
```rust
// Source: https://doc.rust-lang.org/std/sync/struct.OnceLock.html
use std::sync::OnceLock;

struct RecordScanner {
    record_matcher: OnceLock<AhoCorasick>,
}

impl RecordScanner {
    fn matcher(&self, patterns: &[String]) -> &AhoCorasick {
        self.record_matcher.get_or_init(|| {
            AhoCorasickBuilder::new().ascii_case_insensitive(true).build(patterns).unwrap()
        })
    }
}
```

### Pattern 3: Source + manifest + docs move together
**What:** Treat the migration as one consistency sweep across source, direct manifests, and touched `docs/api` pages.
**When to use:** Every crate converted in this phase.
**Example:**
```text
1. Convert imports and statics in source.
2. Re-run a repo audit for remaining direct `once_cell` uses.
3. Remove only now-unused direct `once_cell` entries from Cargo.toml files.
4. Update touched `docs/api/*.md` lines that still describe `once_cell` internals.
5. Run targeted crate tests, then `cargo build --workspace`.
```

### Anti-Patterns to Avoid
- **Treating `Cargo.lock` absence as success:** `once_cell` remains transitively via third-party crates even after direct usage is gone.
- **Using `LazyLock` for `RecordScanner` fields:** that would force a broader redesign because the initializer needs instance data.
- **Broad “cleanup while here” refactors:** locked scope allows only adjacent cleanup that directly improves the migration.
- **Changing binding or public API behavior accidentally:** this phase is internal consistency work, not contract redesign.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Lazy process-global initialization | Custom `static mut`, manual `Option<T>` + `Mutex`, or ad hoc double-checked locking | `std::sync::LazyLock` | Handles one-time init and thread synchronization safely in std. |
| Per-instance one-time cached construction | Manual `Option<T>` cache with interior mutability | `std::sync::OnceLock` | Same `get_or_init` model as `once_cell::sync::OnceCell` with std support. |
| Panic-recovery wrapper around lazy statics | Custom retry/reset logic around poisoned lazy statics | Keep init closures infallible and deterministic | `LazyLock` poisoning is unrecoverable; retry layers add risk and are out of scope. |
| Success audit for dependency removal | Manual eyeballing of one touched file or one manifest | Repo-wide direct-use audit + `cargo build --workspace` | Prevents stale imports/manifests/docs and catches integration breakage. |

**Key insight:** This phase is not about inventing a new initialization strategy; it is about standardizing on already-stable std primitives and removing only the repo-owned direct `once_cell` dependency surface.

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None in runtime datastores or persisted app data. `once_cell` appears in source/manifests/docs and in `ClassicLib-rs/Cargo.lock` as a dependency record. | **Code edit only** for source/manifests/docs. **No data migration.** Do **not** require lockfile-wide `once_cell` disappearance; transitive dependencies still keep it present. |
| Live service config | None — verified by repo audit of config/manifests and the phase scope. This dependency name is not used as a service-side identifier. | None. |
| OS-registered state | None — no OS registrations, task names, service units, or installers use `once_cell` as a runtime identifier. | None. |
| Secrets/env vars | None — no `.env`/CI/env-var names in scope reference `once_cell`. | None. |
| Build artifacts | `ClassicLib-rs/target/` contains old fingerprints and compiled artifacts that reference prior direct `once_cell` use. | **Code edit + rebuild**, not data migration. Run targeted tests and `cargo build --workspace` so fresh artifacts reflect the new direct dependency graph. |

## Common Pitfalls

### Pitfall 1: Misreading the `RecordScanner` field conversion
**What goes wrong:** Replacing `OnceCell` fields with `LazyLock` forces awkward redesign or breaks instance-based initialization.
**Why it happens:** `LazyLock` stores its initializer when the cell is constructed; `RecordScanner` builds matchers later from `self.lower_records` / `self.lower_ignore`.
**How to avoid:** Use `OnceLock` for those fields and keep the existing `get_or_init(|| ...)` shape.
**Warning signs:** You start adding extra wrapper structs, `Arc`s, or constructor plumbing just to make `LazyLock` compile.

### Pitfall 2: Assuming `LazyLock` panic semantics are harmless
**What goes wrong:** A panic inside a `LazyLock::new` initializer permanently poisons that lazy value.
**Why it happens:** `std::sync::LazyLock` poisoning is unrecoverable by design.
**How to avoid:** Keep migration closures simple and deterministic; preserve existing `Regex::new(...).unwrap()` / `DashMap::new` / `Mutex::new(...)` style without adding fallible runtime work.
**Warning signs:** New initializer code does I/O, lock acquisition, or depends on mutable external state.

### Pitfall 3: Defining success as “`once_cell` no longer appears anywhere”
**What goes wrong:** The phase becomes impossible or balloons into unrelated dependency churn because transitive crates still depend on `once_cell`.
**Why it happens:** `cargo tree -i once_cell` shows `dashmap`, `pyo3`, `quick_cache`, `serial_test`, and other third-party crates still pull it in transitively.
**How to avoid:** Gate success on removal of **direct** repo-owned uses and declarations, not lockfile-wide eradication.
**Warning signs:** Planning starts discussing replacing `dashmap`, `pyo3`, or test infrastructure just to remove transitive `once_cell`.

### Pitfall 4: Leaving docs or manifests behind after code compiles
**What goes wrong:** Source migrates, but stale `Cargo.toml` or `docs/api` text still says `once_cell`.
**Why it happens:** The migration is small per file, so cleanup feels “optional.”
**How to avoid:** Make manifest cleanup and `docs/api` alignment part of the same wave as the source edit.
**Warning signs:** `grep once_cell docs/api` or `grep once_cell Cargo.toml` still finds touched pages/crates after code conversion.

### Pitfall 5: Global-state tests become flaky after touched static changes
**What goes wrong:** Registry/perf/FCX tests fail intermittently or depend on run order.
**Why it happens:** These crates expose process-global state and already rely on reset helpers plus `serial_test`.
**How to avoid:** Keep existing reset/clear patterns and run the touched crate suites, not just one narrow unit test.
**Warning signs:** Tests pass individually but fail in grouped runs.

## Code Examples

Verified patterns from official sources:

### Static lazy global with std
```rust
// Source: https://doc.rust-lang.org/std/sync/struct.LazyLock.html
use std::sync::LazyLock;

static GLOBAL: LazyLock<String> = LazyLock::new(|| "ready".to_string());

fn read_global() -> &'static str {
    GLOBAL.as_str()
}
```

### One-time field initialization with std
```rust
// Source: https://doc.rust-lang.org/std/sync/struct.OnceLock.html
use std::sync::OnceLock;

struct Holder {
    value: OnceLock<u32>,
}

impl Holder {
    fn get(&self) -> &u32 {
        self.value.get_or_init(|| 92)
    }
}
```

### Equivalent legacy behavior being removed
```rust
// Source: https://docs.rs/once_cell/latest/once_cell/sync/struct.Lazy.html
use once_cell::sync::Lazy;

static LEGACY: Lazy<u32> = Lazy::new(|| 92);
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `once_cell::sync::Lazy` | `std::sync::LazyLock` | Rust 1.80.0 (2024-07-25) | Standard-library lazy statics remove the need for direct `once_cell` in owned code. |
| `once_cell::sync::OnceCell` | `std::sync::OnceLock` | Rust 1.70.0 (2023-06-01) | Standard-library one-time init covers the `record_scanner.rs` use case directly. |
| “Maybe remove `once_cell` later” | Repo-standardize on std primitives now | Phase 4/5 already moved new work to `LazyLock` | Phase 7 should finish the consistency sweep instead of keeping mixed patterns. |

**Deprecated/outdated:**
- Direct `once_cell` usage for new repo-owned lazy statics.
- Using lockfile-wide `once_cell` disappearance as the success criterion for this phase.

## Open Questions

1. **How should planners phrase “full `once_cell` removal”?**
   - What we know: Direct repo-owned imports and direct manifest entries can be removed if `RecordScanner` moves to `OnceLock`.
   - What's unclear: The phrase can be misread as “no `once_cell` anywhere in `Cargo.lock`,” which is false because transitive dependencies still require it.
   - Recommendation: Define success explicitly as **no direct source imports and no direct `Cargo.toml` declarations in owned crates/workspace**, while allowing transitive lockfile presence.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `rustc` | std primitive availability and crate compilation | ✓ | 1.94.0 | — |
| `cargo` | targeted tests, workspace build, dependency audit | ✓ | 1.94.0 | — |

**Missing dependencies with no fallback:**
- None.

**Missing dependencies with fallback:**
- None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Rust built-in `#[test]` + crate-local test modules + `serial_test` 3.4.0 |
| Config file | none — crate-local tests only |
| Quick run command | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml && cargo test -p classic-registry-core --manifest-path ClassicLib-rs/Cargo.toml && cargo test -p classic-perf-core --manifest-path ClassicLib-rs/Cargo.toml` |
| Full suite command | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml && cargo test -p classic-registry-core --manifest-path ClassicLib-rs/Cargo.toml && cargo test -p classic-perf-core --manifest-path ClassicLib-rs/Cargo.toml && cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONS-01 | Scanlog, registry, and perf crates still behave correctly after std lazy primitive migration | unit/integration | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml` | ✅ |
| CONS-01 | Global registry semantics remain correct after static migration | unit | `cargo test -p classic-registry-core --manifest-path ClassicLib-rs/Cargo.toml` | ✅ |
| CONS-01 | Global metrics semantics remain correct after static migration | unit | `cargo test -p classic-perf-core --manifest-path ClassicLib-rs/Cargo.toml` | ✅ |
| CONS-01 | Manifest cleanup does not break workspace integration | build | `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` | ✅ |

### Sampling Rate
- **Per task commit:** `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml && cargo test -p classic-registry-core --manifest-path ClassicLib-rs/Cargo.toml && cargo test -p classic-perf-core --manifest-path ClassicLib-rs/Cargo.toml`
- **Per wave merge:** `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml`
- **Phase gate:** Targeted crate tests green plus workspace build green before `/gsd-verify-work`

### Wave 0 Gaps
- None — existing crate-local tests already cover the touched global/static surfaces in `classic-scanlog-core`, `classic-registry-core`, and `classic-perf-core`.

## Sources

### Primary (HIGH confidence)
- Rust std docs: `https://doc.rust-lang.org/std/sync/struct.LazyLock.html` - `LazyLock` API, poisoning semantics, and stability (`1.80.0`)
- Rust std docs: `https://doc.rust-lang.org/std/sync/struct.OnceLock.html` - `OnceLock` API, `get_or_init` semantics, no-poisoning behavior, and stability (`1.70.0`)
- Rust blog: `https://blog.rust-lang.org/2024/07/25/Rust-1.80.0/` - stabilization announcement for `LazyLock`
- Rust blog: `https://blog.rust-lang.org/2023/06/01/Rust-1.70.0/` - stabilization announcement for `OnceLock`
- once_cell docs: `https://docs.rs/once_cell/latest/once_cell/sync/struct.Lazy.html` - legacy `Lazy` API being replaced
- once_cell docs: `https://docs.rs/once_cell/latest/once_cell/sync/struct.OnceCell.html` - legacy `OnceCell` API being replaced
- Local once_cell source: `C:\Users\evild\.cargo\registry\src\index.crates.io-1949cf8c6b5b557f\once_cell-1.21.4\src\lib.rs` - confirms legacy `Lazy` poison behavior is explicit in source (`"Lazy instance has previously been poisoned"`)
- Local repo manifests/source/docs in `ClassicLib-rs/` and `docs/api/` - exact migration targets and stale docs/manifests
- `cargo tree --manifest-path ClassicLib-rs/Cargo.toml -i once_cell` - proves `once_cell` remains transitive even if direct repo-owned usage is removed

### Secondary (MEDIUM confidence)
- `docs/api/classic-registry-core.md`, `docs/api/classic-perf-core.md`, `docs/api/classic-settings-core.md` - contributor-doc drift inventory for touched pages

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - std docs and Rust release notes directly verify the recommended primitives and their stabilization versions.
- Architecture: HIGH - repo context, existing Phase 4/5 patterns, local source, and manifest audit all agree on the migration shape.
- Pitfalls: HIGH - backed by official std docs, once_cell source/docs, and local `cargo tree` evidence.

**Research date:** 2026-04-06
**Valid until:** 2026-05-06

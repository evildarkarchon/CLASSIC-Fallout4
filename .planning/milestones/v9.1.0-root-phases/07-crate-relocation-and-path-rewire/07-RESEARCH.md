# Phase 7: Crate Relocation and Path Rewire - Research

**Researched:** 2026-04-12
**Domain:** Rust workspace crate relocation and manifest/path rewiring
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

## Implementation Decisions

### Repo-Root Layout
- **D-01:** Move the six existing Rust layer directories intact from `ClassicLib-rs/` to the repository root: `foundation/`, `business-logic/`, `cpp-bindings/`, `node-bindings/`, `python-bindings/`, and `ui-applications/`.
- **D-02:** Treat the move as layout preservation, not taxonomy cleanup: keep current crate ownership boundaries and each crate's internal files/directories intact.

### Manifest And Path Rewiring
- **D-03:** Keep crate-manifest rewrites minimal. Preserve existing `path =` relationships wherever the preserved layer topology keeps them valid.
- **D-04:** Rewrite only workspace member entries and manifest `path =` edges that actually break because of the move; do not use Phase 7 for broader manifest modernization or dependency-style cleanup.

### Legacy `ClassicLib-rs` Boundary
- **D-05:** By the end of Phase 7, `ClassicLib-rs/` must no longer contain live Rust crates or workspace-owned Rust files.
- **D-06:** If any residue remains under `ClassicLib-rs/` after the move, it must be clearly non-authoritative and must not be required by the live build graph.

### Closure Evidence
- **D-07:** Phase 7 closure must include Cargo root/member proof using `cargo locate-project --workspace` and `cargo metadata --format-version 1 --no-deps`.
- **D-08:** Phase 7 closure must also include an explicit relocation audit that maps old crate locations to new ones and a stale-manifest/member-path sweep.
- **D-09:** Phase 7 proof stays cargo-and-layout focused; wrapper/parity smoke remains later-phase work unless a path contract is inseparable from proving the crate move itself.

### the agent's Discretion
- Exact file-move sequencing and mechanical rewrite method, as long as the preserved-layer layout and minimal-rewrite policy above hold.
- Exact validation script/report shape, as long as it produces the Cargo proof and relocation audit required above.

### Deferred Ideas (OUT OF SCOPE)

## Deferred Ideas

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MOVE-01 | Contributor can find every crate previously under `ClassicLib-rs/` at its new repository-root-relative location with each crate's internal directory structure preserved | Use whole-layer relocation, preserve crate directories intact, and produce an explicit old→new crate mapping audit. |
| MOVE-02 | Contributor can resolve all workspace members and local crate path dependencies after the relocation without keeping a second active workspace under `ClassicLib-rs/` | Rewire only root `members` and broken local `path =` edges, then prove the graph with `cargo locate-project --workspace` and `cargo metadata --format-version 1 --no-deps`. |
</phase_requirements>

## Project Constraints (from AGENTS.md)

- Prioritize active work in `classic-cli/`, `classic-gui/`, and `ClassicLib-rs`-owned Rust surfaces.
- Keep all business logic in Rust; do not use this move to shift behavior into C++, Python, or Node layers.
- Keep non-interface layers thin; wrappers stay wrappers.
- Maintain the single shared Tokio runtime; do not introduce runtime changes during relocation.
- Keep docs synchronized with architecture/workflow changes when later phases touch them.
- Never write to `NUL` or `nul` on Windows.
- Consult `docs/api/README.md` only if public API contracts change; Phase 7 should avoid API-shaping changes.
- Never run raw `ctest` or C++ test binaries directly.
- Repo-root Cargo is already canonical; Phase 7 must preserve that contract.
- Windows/MSVC constraints remain in force for any native validation.

## Summary

This phase should be executed as a pure filesystem-and-manifest migration, not as a workspace redesign. Official Cargo behavior strongly favors one virtual workspace root, exact local `path` targets, and metadata-based verification. In this repo, that means stripping the `ClassicLib-rs/` prefix from root workspace member paths, moving the six layer directories intact, and leaving member-local relative `path =` entries alone unless the preserved geometry actually breaks them.

The live repository already proves the root workspace shell works: `cargo locate-project --workspace` resolves to `J:\CLASSIC-Fallout4\Cargo.toml`, and `cargo metadata --format-version 1 --no-deps` reports `workspace_root=J:\CLASSIC-Fallout4` with 37 workspace members. The remaining job is mechanical relocation. Current manifests contain 107 explicit local `path =` entries, but member manifests currently contain zero literal `ClassicLib-rs/` strings, which is a strong signal that most intra-crate path edges should survive unchanged if the six layer directories move intact.

The highest-risk mistake is doing extra work: blanket path rewrites, resolver upgrades, compatibility shims, or wrapper/parity rewires in the same phase. Cargo-root proof plus an explicit relocation audit is the right closure surface here. Keep this phase narrowly scoped to crate moves and manifest/member rewiring; defer downstream consumers to later phases exactly as the roadmap intends.

**Primary recommendation:** Move the six layer directories intact, rewrite only root `members` plus any actually-broken local `path =` edges, and prove success with Cargo metadata plus a deterministic old→new mapping audit.

## Standard Stack

### Core
| Library / Tool | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Cargo virtual workspace | Cargo 1.94.0 locally; official Cargo workspace model | Canonical workspace root and member graph | Cargo defines the workspace root by the manifest location and shares one `Cargo.lock` and `target/` there. This is the standard mechanism for repo-root workspaces. |
| Explicit root `[workspace].members` | Current repo `Cargo.toml` | Authoritative list of relocated crates | Minimal-risk relocation: rewrite member paths from `ClassicLib-rs/...` to root-relative paths and keep the existing member inventory. |
| Member-local `path =` dependencies | 107 explicit local path entries in live manifests | Cross-crate wiring | Cargo path dependencies are relative to the manifest that declares them and must point at the exact crate directory. Preserving layer geometry minimizes churn. |
| Git moves | Git 2.53.0.windows.2 locally | Preserve rename history during directory relocation | This is the safest standard way to perform bulk crate relocation in a tracked repo. |

### Supporting
| Library / Tool | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `cargo locate-project --workspace` | Cargo 1.94.0 | Detect the effective workspace root | Use for closure proof and to catch accidental dual-root behavior. |
| `cargo metadata --format-version 1 --no-deps` | Cargo 1.94.0 | Machine-readable workspace/member audit | Use to confirm workspace root, target directory, and member manifest paths after the move. |
| `pytest` running unittest-style planning audits | pytest 9.0.3 locally | Repo contract verification | Use for a Phase 7 audit file under `tests/planning/` that checks mapping, stale references, and root/member state. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Single live root manifest + moved layer directories | Keep a live `ClassicLib-rs` compatibility workspace | Not acceptable here; it preserves two sources of truth and weakens the closure proof. |
| Minimal rewrites | Rewrite every `path =` entry proactively | Adds noise and break risk; current manifests already avoid literal `ClassicLib-rs/` anchors. |
| Repo-root member list rewrite | `package.workspace` overrides in members | Unnecessary because all relocated crates stay under the repo root tree, and none use `package.workspace` today. |

**Installation:** No new packages should be introduced for Phase 7.

## Architecture Patterns

### Recommended Project Structure
```text
J:\CLASSIC-Fallout4\
├── Cargo.toml
├── foundation/        # Shared/runtime crates moved intact
├── business-logic/    # Domain core crates moved intact
├── cpp-bindings/      # CXX bridge crate moved intact
├── node-bindings/     # NAPI crate moved intact
├── python-bindings/   # PyO3 crates/tests/artifacts moved intact
├── ui-applications/   # Rust TUI crate moved intact
├── classic-cli/       # Not rewired in this phase
├── classic-gui/       # Not rewired in this phase
└── ClassicLib-rs/     # No live crates/workspace-owned Rust files by phase end
```

### Pattern 1: Whole-Layer Strip-Prefix Relocation
**What:** Move each of the six top-level Rust layer directories up one level and preserve every crate's internal subtree exactly.
**When to use:** For all workspace members in this phase.
**Example:**
```toml
# Source: https://doc.rust-lang.org/cargo/reference/workspaces.html
[workspace]
members = [
    "foundation/classic-shared-core",
    "business-logic/classic-scanlog-core",
    "python-bindings/classic-config-py",
    "node-bindings/classic-node",
    "cpp-bindings/classic-cpp-bridge",
    "ui-applications/classic-tui",
]
```

### Pattern 2: Preserve Member-Local Relative Paths
**What:** Keep existing `path =` edges when the moved directories keep the same relative geometry.
**When to use:** Default behavior for member manifests after the move.
**Example:**
```toml
# Source: https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html#specifying-path-dependencies
[dependencies]
hello_utils = { path = "hello_utils" }

# Repo-specific analogue after relocation:
classic-shared-core = { path = "../../foundation/classic-shared-core" }
```

### Pattern 3: Metadata-First Closure Proof
**What:** Verify the effective workspace graph with Cargo itself, then layer repo-specific audits on top.
**When to use:** At every milestone checkpoint and final Phase 7 closure.
**Example:**
```bash
# Source: https://doc.rust-lang.org/cargo/commands/cargo-locate-project.html
cargo locate-project --workspace --message-format plain

# Source: https://doc.rust-lang.org/cargo/commands/cargo-metadata.html
cargo metadata --format-version 1 --no-deps
```

### Anti-Patterns to Avoid
- **Blanket path rewrites:** current member manifests already have zero literal `ClassicLib-rs/` anchors; changing every `path =` entry increases risk for little gain.
- **Dual-root compatibility shell:** do not reintroduce a live `ClassicLib-rs/Cargo.toml` or any workspace-owned Rust authority under that tree.
- **Resolver/toolchain modernization during the move:** Phase 7 is relocation-only; do not bundle resolver, edition, or dependency cleanup.
- **Wrapper/parity/CI rewiring in this phase:** those surfaces are intentionally deferred to later phases unless needed only for proving the crate move itself.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Workspace-root detection | Custom parent-directory scanners | `cargo locate-project --workspace` | Cargo already knows the effective root and handles member/workspace search semantics. |
| Workspace graph verification | Regex-only `Cargo.toml` parsing as proof | `cargo metadata --format-version 1 --no-deps` | Metadata reports `workspace_root`, `target_directory`, and member manifests in one authoritative JSON surface. |
| Path rewrite strategy | Manual crate-by-crate judgment | Mechanical inventory + preserved topology | There are 107 local path entries; ad hoc edits are where misses happen. |
| Compatibility routing | A second active workspace under `ClassicLib-rs/` | One canonical repo-root workspace | Dual roots are exactly the failure mode this milestone is eliminating. |
| Closure evidence | “Cargo builds on my machine” | Cargo proof + mapping audit + stale sweep | This phase needs auditable relocation evidence, not just a green command. |

**Key insight:** The hard part is not Cargo syntax; it is resisting unnecessary churn and proving that the new graph is the only live graph.

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None verified for workspace ownership state. Repo scan found no `.db` or `.sqlite` files under `ClassicLib-rs/`; Cargo membership/path state lives in manifests, not a datastore. | Code edit only — relocate crates/manifests. No data migration identified. |
| Live service config | None identified for this Cargo-only phase. Wrapper/parity/CI/service consumers are explicitly later-phase work. | None in Phase 7. Do not invent service rewires here. |
| OS-registered state | None identified. Cargo workspace resolution depends on filesystem layout and manifests, not OS registration. | None. |
| Secrets/env vars | None tied to the `ClassicLib-rs` crate tree as a required Phase 7 key. Existing env vars like `VCPKG_ROOT` are unrelated to crate relocation. | None for Phase 7. |
| Build artifacts | `ClassicLib-rs/target/` exists; `ClassicLib-rs/python-bindings/` contains `.venv/`, `.pytest_cache/`, `dist-rust/`, and `parity-artifacts/`. These become stale or misleading after the move. | Generated-artifact cleanup/rebuild, not data migration. Phase 7 must not treat these as proof; Phase 9 should quarantine/regenerate them cleanly. |

## Common Pitfalls

### Pitfall 1: Treating Every `path =` Entry as Broken
**What goes wrong:** Large noisy manifest rewrites create new mistakes in crates that would have kept working unchanged.
**Why it happens:** People confuse workspace-root movement with member-local relative path movement.
**How to avoid:** Inventory all 107 local path entries, then only change edges that stop resolving after the preserved directory move.
**Warning signs:** Big manifest diffs in business-logic or binding crates that only changed path strings with no actual geometric reason.

### Pitfall 2: Leaving a Live Rust Subtree Under `ClassicLib-rs`
**What goes wrong:** The repo appears relocated, but humans and tools can still discover live crates under the old path.
**Why it happens:** Temporary compatibility thinking becomes permanent.
**How to avoid:** Remove or tombstone all live crates/workspace-owned Rust files under `ClassicLib-rs` in the same phase.
**Warning signs:** `cargo metadata` member manifests still point into `ClassicLib-rs/`, or `ClassicLib-rs/` still contains live crate `Cargo.toml` files.

### Pitfall 3: Using Cargo Success as the Only Closure Signal
**What goes wrong:** `cargo check` passes, but some members were silently omitted or stale paths remain in manifests.
**Why it happens:** Cargo success does not by itself prove complete relocation coverage.
**How to avoid:** Require three artifacts together: `cargo locate-project --workspace`, `cargo metadata --format-version 1 --no-deps`, and an explicit old→new mapping plus stale-manifest/member sweep.
**Warning signs:** No auditable list of moved crates; no assertion that all root members are root-relative.

### Pitfall 4: Opportunistic Modernization During a Mechanical Move
**What goes wrong:** Resolver, dependency, lint, or manifest-style changes create unrelated failures and make root cause attribution hard.
**Why it happens:** The workspace is already open, so cleanup feels cheap.
**How to avoid:** Keep Phase 7 diffs limited to filesystem moves, root member rewrites, and only truly-broken local path edges.
**Warning signs:** Diffs include dependency upgrades, resolver changes, or lint policy changes.

### Pitfall 5: Trusting Stale Generated Outputs
**What goes wrong:** Old `target`, `.venv`, parity artifacts, or cached outputs make the relocation look healthy.
**Why it happens:** Generated folders under `ClassicLib-rs/` remain present and can shadow missing rewires.
**How to avoid:** Treat these as stale by default and keep them out of Phase 7 proof; later clean-state validation must rebuild from the new paths.
**Warning signs:** New files continue appearing under `ClassicLib-rs/` after the move.

## Code Examples

Verified patterns from official sources:

### Virtual Workspace Root
```toml
# Source: https://doc.rust-lang.org/cargo/reference/workspaces.html
[workspace]
members = ["hello_world"]
resolver = "3"
```

### Exact Local Path Dependency
```toml
# Source: https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html#specifying-path-dependencies
[dependencies]
regex-lite   = { path = "../regex/regex-lite" }
regex-syntax = { path = "../regex/regex-syntax" }
```

### Canonical Relocation Proof Commands
```bash
# Source: https://doc.rust-lang.org/cargo/commands/cargo-locate-project.html
cargo locate-project --workspace --message-format plain

# Source: https://doc.rust-lang.org/cargo/commands/cargo-metadata.html
cargo metadata --format-version 1 --no-deps
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Use `ClassicLib-rs/Cargo.toml` as the live workspace root | Use repo-root `Cargo.toml` as the only live workspace root | Locked in Phase 6 | Phase 7 must relocate crates to match the already-promoted root shell, not re-litigate root ownership. |
| Keep local workflows on `--manifest-path ClassicLib-rs/Cargo.toml` | Use plain repo-root Cargo commands plus metadata proof | Current repo contract, verified 2026-04-12 | Phase 7 validation should stay repo-root-native. |
| Older mental model: virtual workspaces commonly shown with `resolver = "2"` | Current Cargo docs show a virtual-workspace example with `resolver = "3"` | Current official docs | Do **not** treat this as a cue to upgrade resolver here; the repo has a locked `resolver = "2"` relocation-only contract. |

**Deprecated/outdated:**
- Live dual-workspace steady state — outdated for this repo and directly contrary to the milestone.
- Blanket manifest modernization during relocation — outdated migration practice; use minimal rewiring instead.

## Open Questions

1. **Should Phase 7 delete non-Rust residue under `ClassicLib-rs/` or only remove live Rust authority?**
   - What we know: Locked decisions require no live crates or workspace-owned Rust files there by phase end.
   - What's unclear: Whether non-authoritative files like historical reports or caches should be deleted immediately or left for later cleanup.
   - Recommendation: Enforce “no live Rust authority” in Phase 7 and treat extra residue deletion as optional unless it interferes with proof.

2. **What exact artifact format should record the old→new crate mapping?**
   - What we know: The audit is mandatory; the exact report shape is discretionary.
   - What's unclear: Whether the repo prefers a generated markdown table, JSON, or a pytest-produced assertion report.
   - Recommendation: Implement the simplest deterministic artifact that can be diffed and reviewed, preferably a planning test plus a checked-in markdown/json summary.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Cargo | Workspace root/member/path verification | ✓ | 1.94.0 | — |
| rustc | Cargo metadata/build compatibility | ✓ | 1.94.0 | — |
| Git | History-preserving directory moves | ✓ | 2.53.0.windows.2 | Manual move possible but not recommended |
| Python | Planning audit scripts/tests | ✓ | 3.14.3 | PowerShell-only audit if necessary |
| pytest | `tests/planning` validation | ✓ | 9.0.3 | `python -m unittest` for unittest-style tests |

**Missing dependencies with no fallback:**
- None.

**Missing dependencies with fallback:**
- None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 running unittest-style planning audits |
| Config file | none — direct invocation |
| Quick run command | `python -m pytest tests/planning/test_phase07_validation.py -q` |
| Full suite command | `cargo fmt --all -- --check && cargo clippy --workspace --all-targets --all-features -- -D warnings && cargo test --workspace --release -- --nocapture && python -m pytest tests/planning -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MOVE-01 | All 37 workspace members are relocated out of `ClassicLib-rs/` with preserved crate-internal layout and auditable old→new mapping | planning/integration audit | `python -m pytest tests/planning/test_phase07_validation.py -q` | ❌ Wave 0 |
| MOVE-02 | Root workspace members and local `path =` edges resolve after relocation with no second live workspace under `ClassicLib-rs/` | planning/integration audit + Cargo proof | `cargo locate-project --workspace --message-format plain && cargo metadata --format-version 1 --no-deps && python -m pytest tests/planning/test_phase07_validation.py -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cargo metadata --format-version 1 --no-deps && python -m pytest tests/planning/test_phase07_validation.py -q`
- **Per wave merge:** `cargo fmt --all -- --check && cargo clippy --workspace --all-targets --all-features -- -D warnings && cargo test --workspace --release -- --nocapture && python -m pytest tests/planning -q`
- **Phase gate:** Full suite green plus explicit relocation audit artifact.

### Wave 0 Gaps
- [ ] `tests/planning/test_phase07_validation.py` — assert all root workspace members are root-relative, all moved crates are absent from `ClassicLib-rs/`, and required audit artifacts exist.
- [ ] Relocation audit fixture/helper (PowerShell or Python) — generate deterministic old→new crate mapping and stale-member/path sweep results for the test to consume.
- [ ] Targeted assertions for high-fanout manifests (`classic-cpp-bridge`, `classic-node`, representative `classic-*-py`, `classic-tui`) — ensure broken path edges are caught early.

## Sources

### Primary (HIGH confidence)
- `/websites/doc_rust-lang_cargo` - workspace membership, parent search, `package.workspace`, path-dependency semantics, `cargo metadata`, `cargo locate-project`
- https://doc.rust-lang.org/cargo/reference/workspaces.html - virtual workspaces, members, root discovery, shared lockfile/target
- https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html#specifying-path-dependencies - exact local path semantics
- https://doc.rust-lang.org/cargo/commands/cargo-metadata.html - machine-readable workspace proof surface
- https://doc.rust-lang.org/cargo/commands/cargo-locate-project.html - canonical workspace-root discovery
- `Cargo.toml` - current live root workspace member inventory
- `.planning/phases/06-repo-root-workspace-cutover/06-VERIFICATION.md` - current repo-root proof contract
- `.planning/research/STACK.md` and `.planning/research/PITFALLS.md` - milestone-level relocation guidance aligned with current repo

### Secondary (MEDIUM confidence)
- `tests/planning/test_phase06_validation.py` - reusable audit pattern for phase-level contract tests
- `.planning/codebase/STRUCTURE.md` and `.planning/codebase/STACK.md` - current repo topology and toolchain assumptions
- Live manifest inventory across `ClassicLib-rs/**/Cargo.toml` - 37 manifests and 107 explicit local path entries

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - grounded in official Cargo docs plus the live repo-root workspace contract.
- Architecture: HIGH - locked decisions match Cargo-standard relocation patterns and current manifest topology.
- Pitfalls: HIGH - based on official workspace/path semantics plus concrete repo inventory and existing Phase 6 verification patterns.

**Research date:** 2026-04-12
**Valid until:** 2026-05-12

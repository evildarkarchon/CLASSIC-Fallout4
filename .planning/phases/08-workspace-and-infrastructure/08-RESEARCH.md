# Phase 8: Workspace and Infrastructure - Research

**Researched:** 2026-04-06
**Domain:** Rust workspace hygiene, Linux Proton path discovery, Node contract artifact governance
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
### Linux docs-path behavior
- **D-01:** Make Proton awareness part of the shared Linux docs-path workflow in `classic-path-core`, not a Fallout 4-specific wrapper and not binding-specific duplication.
- **D-02:** On Linux, after any cached-path success check, a valid Proton documents path should win over the existing `~/.local/share/<relative_path>` path.
- **D-03:** If Steam metadata lookup fails or the Proton documents path is invalid/missing, fall back to the existing `~/.local/share/<relative_path>` Linux path before returning not found.
- **D-04:** Fallout 4 VR Linux Proton support is out of scope for this phase. Phase 8 should target standard Fallout 4 Proton docs-path detection only.

### Linux proof strength
- **D-05:** The required proof should live in `classic-path-core` as crate-level integration coverage for the shared workflow, not as per-binding Linux tests.
- **D-06:** Required Linux Proton coverage includes all of the following:
  - a happy-path Proton case using a mock Proton prefix structure
  - a case where Steam metadata resolves but the Proton docs path is invalid, forcing local-share fallback
  - a case where Steam metadata lookup fails entirely, forcing local-share fallback
  - a regression test proving the legacy non-Proton Linux `~/.local/share/<relative_path>` path still works when it is the only valid candidate

### `zerovec` workaround policy
- **D-07:** Force removal of the `zerovec` workaround rather than keeping it as a documented historical workaround.
- **D-08:** If removing the workaround exposes stale Slint/gui-bridge code that directly blocks the removal, Phase 8 may remove that adjacent blocker code too.
- **D-09:** This adjacent cleanup allowance is narrow: remove only the Slint/gui-bridge pieces directly blocking workaround removal, not a broad repo-wide Slint purge.
- **D-10:** Remove or rewrite stale comments/docs that still describe the workaround after removal. Do not preserve historical workaround notes unless some active feature still truly requires them.

### Node type freshness enforcement
- **D-11:** `ClassicLib-rs/node-bindings/classic-node/index.d.ts` is a required tracked contract artifact and should no longer be gitignored.
- **D-12:** Any public Node binding export change must refresh and commit `index.d.ts` in the same change unit. Do not rely on CI to catch stale declarations later.
- **D-13:** The same-change workflow also includes the existing Node freshness/parity validation path rather than treating declaration refresh as a standalone file update.
- **D-14:** Contributor guidance should stop implying a build-first requirement just to inspect Node types. The committed `index.d.ts` snapshot becomes the first-class inspection artifact; builds are for regeneration and verification.

### the agent's Discretion
- Exact internal helper/API shape used to make Linux docs-path discovery Proton-aware, as long as the shared `classic-path-core` workflow stays the source of truth and existing public call patterns remain stable.
- Exact test helper structure, temp-directory layout, and environment injection used to exercise the Linux Proton and fallback paths.
- Exact command wiring and file-update sequencing for the Node declaration freshness workflow, as long as `index.d.ts` is tracked and same-change refresh remains enforced.
- Exact implementation steps used to remove direct Slint/gui-bridge blockers revealed by `zerovec` removal, as long as the cleanup stays tightly adjacent to that goal.

### Deferred Ideas (OUT OF SCOPE)
- Broader repo-wide removal of all remaining Slint integration code beyond the direct blockers adjacent to `zerovec` removal. Phase 8 only allows narrow blocker cleanup tied to the workaround-removal goal.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | Promote `winreg` to `[workspace.dependencies]` in root `Cargo.toml` | Use Cargo workspace dependency inheritance plus target-scoped `workspace = true` in `classic-path-core` |
| INFRA-02 | Promote `phf` to `[workspace.dependencies]` in root `Cargo.toml` | Use root workspace pin and crate-local `workspace = true` in `classic-constants-core` |
| INFRA-03 | Wire `construct_proton_docs_path` into Linux docs-path discovery workflow with unit tests using mock Proton prefix | Use shared `DocsPathFinder` Linux workflow with Proton-first ordering and tempdir-backed integration coverage |
| INFRA-04 | Document or resolve `zerovec` workaround dependency in `classic-shared-core` (check if Slint 1.15+ resolved it) | Validate removal against `gui-bridge`/all-features build; only keep a tracking comment if proof fails |
| INFRA-05 | Commit generated `index.d.ts` snapshot for Node bindings with CI freshness check | Treat NAPI-RS generated `index.d.ts` as tracked contract artifact; keep same-change regeneration + check-only CI gate |
| TEST-03 | Add integration test for Linux Proton docs-path discovery with mock Proton prefix structure | Add crate-level integration test file covering happy path plus both fallbacks and legacy local-share regression |
</phase_requirements>

## Summary

Phase 8 is mostly alignment work, not new architecture. The repo already has the right primitives: Cargo workspace dependency inheritance, a dormant Proton helper in `classic-path-core`, a tracked `classic-node/index.d.ts`, an existing freshness script, and a CI freshness job. The real work is making those pieces internally consistent and making the Linux path workflow authoritative in one shared Rust location.

The highest-risk area is Linux proof strategy. Current Rust CI is Windows-only, while the Proton helper lives behind Linux-specific modules. If planning assumes a Linux-only test without considering current CI shape, the phase will finish with code but weak proof. The safest pattern is: keep the public Linux behavior in `DocsPathFinder`, but extract the Linux candidate-ordering logic into a small pure helper that crate-level integration tests can drive with temp directories and injected inputs.

`zerovec` should be treated as a proof obligation, not a comment-edit task. Current dependency inspection shows the direct dev-dependency is the only visible source of the `zerovec/alloc` feature for `classic-shared-core`'s `gui-bridge` path. That makes removal desirable but not yet proven safe. Plan removal first, but gate it with `classic-shared-core`/workspace all-features validation; only fall back to a tracking comment if build proof says it is still required.

**Primary recommendation:** Centralize Phase 8 around shared Rust workflows: workspace-inherit `winreg`/`phf`, make `DocsPathFinder` Proton-aware with extracted testable Linux candidate logic, and treat `index.d.ts` as a tracked NAPI-RS snapshot enforced by the existing freshness gate.

## Project Constraints (from AGENTS.md)

- Prioritize active work in `classic-cli/`, `classic-gui/`, and `ClassicLib-rs/`.
- Keep all business logic in Rust core crates.
- Keep C++, Python, and Node layers thin wrappers over Rust APIs.
- Maintain a single shared Tokio runtime; do not introduce another runtime.
- Keep docs synchronized with architecture or workflow changes.
- Never write to `NUL` or `nul` as a file path.
- Consult `docs/api/README.md` before changing public Rust, bridge, GUI-consumer, or binding-facing APIs; update affected `docs/api/` pages in the same change if contracts change.
- Never run C++ tests via raw binaries or raw `ctest`; use the repo PowerShell wrappers.
- For Node binding changes, parity artifacts and binding tests belong in the same change.
- For Linux/cloud validation, prefer portable Rust-only subsets when Windows-native surfaces are impractical.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Cargo `[workspace.dependencies]` | stable feature set (Cargo docs current 2026-04) | Single source of truth for shared crate versions | Official Cargo pattern for shared dependency inheritance across members |
| `winreg` | repo pin `0.52` (latest `0.56.0`, published 2026-03-14) | Windows registry access for docs-path discovery | Already the repo's Windows-specific dependency; Phase 8 only promotes ownership to workspace scope |
| `phf` | `0.13.1` (published 2025-08-23) | Perfect hash maps in constants crate | Already current in repo and current on crates.io |
| `tempfile` | `3.24.0` | Tempdir-backed filesystem fixtures | Existing repo-standard Rust test fixture library for path-heavy crates |
| NAPI-RS + generated `index.d.ts` | Rust `napi = "3"`, `napi-derive = "3"`; CLI `@napi-rs/cli 3.6.0` (published 2026-03-28) | Generate and verify Node JS/TS contract artifacts | Official NAPI-RS flow generates `.node`, `index.js`, and `index.d.ts`; repo already uses it |
| Slint | workspace pin `1.15.0` (latest `1.15.1`, published 2026-02-12) | Optional `gui-bridge` feature surface in `classic-shared-core` | Existing repo pin; Phase 8 should validate workaround removal against this branch, not redesign UI stack |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Bun | `1.3.10` | Node parity/freshness/test runner | Run `parity:gate:local`, `dts:freshness:*`, and Bun tests |
| Node | `25.9.0` | Runtime smoke tests and consumer contract surface | Run `bun run test:node` and inspect generated public exports |
| Python | `3.14.3` | Existing freshness/parity helper scripts | Runs `check_dts_freshness.py` and parity tooling |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Workspace-inherited `winreg` / `phf` | Keep crate-local pins | Violates repo's shared-deps policy and reintroduces drift risk |
| Shared Proton-aware `DocsPathFinder` | Fallout 4-specific wrapper logic in bindings/bridge | Violates D-01 and duplicates path rules across surfaces |
| Generated committed `index.d.ts` snapshot | Handwritten `.d.ts` or build-first-only docs | Handwritten types drift; build-first hides contract from contributors |
| Proof-based `zerovec` removal | Permanent workaround comment only | Leaves fragility in place without answering whether Slint 1.15.x still needs it |

**Installation / verification:**
```bash
# npm registry verification used during research
npm view @napi-rs/cli version
npm view typescript version

# crates.io verification used during research
# winreg latest: 0.56.0 (2026-03-14)
# phf latest: 0.13.1 (2025-08-23)
# slint latest: 1.15.1 (2026-02-12)
```

## Architecture Patterns

### Recommended Project Structure
```text
ClassicLib-rs/
├── Cargo.toml                                      # root workspace dependency source of truth
├── business-logic/classic-path-core/
│   ├── src/docs_path.rs                            # shared docs-path workflow owner
│   ├── src/platform/linux.rs                       # Steam/Proton helpers
│   └── tests/linux_proton_docs_path.rs             # new crate-level integration proof
├── business-logic/classic-constants-core/Cargo.toml
├── foundation/classic-shared-core/Cargo.toml       # zerovec workaround removal point
└── node-bindings/classic-node/
    ├── package.json                                # freshness/parity command source
    ├── index.d.ts                                  # tracked contract snapshot
    └── .gitignore                                  # must stop contradicting tracked contract policy
```

### Pattern 1: Workspace dependency inheritance with target gating
**What:** Put the version in root `[workspace.dependencies]`; inherit it from member manifests with `workspace = true`, including inside target-specific dependency blocks.
**When to use:** Shared dependencies used by more than one crate, or dependencies the repo wants centrally governed.
**Example:**
```toml
# Source: Cargo docs - https://doc.rust-lang.org/cargo/reference/workspaces.html
[workspace.dependencies]
phf = { version = "0.13.1", features = ["macros"] }
winreg = "0.52"

[dependencies]
phf = { workspace = true }

[target.'cfg(windows)'.dependencies]
winreg = { workspace = true }
```

### Pattern 2: Linux docs-path candidate ordering in one shared Rust workflow
**What:** Keep cached path first, then on Linux try Steam metadata + Proton documents path, then fall back to `~/.local/share/<relative_path>`.
**When to use:** Any caller using `DocsPathFinder`; never duplicate this logic in a binding or Fallout-4-specific wrapper.
**Example:**
```rust
// Source: repo decisions + classic-path-core source
fn find_docs_path_linux(&self) -> DocsPathResult<PathBuf> {
    let proton_candidate = parse_steam_library_vdf(377160)
        .map(|library| construct_proton_docs_path(&library, 377160, &self.relative_path));

    if let Ok(path) = proton_candidate {
        if self.validate_docs_path(&path).is_ok() {
            return Ok(path);
        }
    }

    let local_share = get_home_directory()?.join(".local/share").join(&self.relative_path);
    self.validate_docs_path(&local_share)?;
    Ok(local_share)
}
```

### Pattern 3: Extract pure candidate-selection logic for cross-platform proof
**What:** Keep the public Linux branch in `DocsPathFinder`, but move path-selection logic into a helper that accepts injected library/home inputs so integration tests can drive it with tempdirs.
**When to use:** When behavior is Linux-specific but current CI/local environment is Windows-heavy.
**Example:**
```rust
// Source: prescriptive repo-fit pattern derived from current CI + D-05/D-06
fn choose_linux_docs_path(
    relative_path: &str,
    steam_library: Result<PathBuf, DocsPathError>,
    home: &Path,
) -> DocsPathResult<PathBuf> {
    if let Ok(library) = steam_library {
        let proton = construct_proton_docs_path(&library, 377160, relative_path);
        if proton.is_dir() {
            return Ok(proton);
        }
    }
    Ok(home.join(".local/share").join(relative_path))
}
```

### Pattern 4: Tracked generated contract artifact + check-only CI gate
**What:** `index.d.ts` is generated by NAPI-RS, committed to git, refreshed in the same change as public export changes, and checked in CI without mutating files.
**When to use:** Any public Node binding contract change.
**Example:**
```json
// Source: classic-node/package.json + NAPI-RS docs
{
  "scripts": {
    "dts:freshness:check": "python ../../../tools/node_api_parity/check_dts_freshness.py --repo-root ../../.. --check-only",
    "dts:freshness:local": "python ../../../tools/node_api_parity/check_dts_freshness.py --repo-root ../../..",
    "parity:gate:local": "bun run dts:freshness:local && bun run parity:gate:update-baseline"
  }
}
```

### Anti-Patterns to Avoid
- **Binding-specific Proton logic:** violates D-01 and will drift across Node/Python/C++ surfaces.
- **Version-bump creep while promoting deps:** INFRA-01/02 are about workspace ownership, not opportunistic dependency upgrades.
- **Linux-only proof hidden behind unrun CI paths:** if tests only execute on Linux but CI is Windows-only, proof is weaker than it looks.
- **Hand-editing `index.d.ts`:** NAPI-RS owns generation; the repo owns snapshot freshness.
- **Treating `zerovec` as docs-only cleanup:** D-07 requires removal first, with comment fallback only if proof fails.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Shared dependency governance | Per-crate duplicate version pins | Cargo `[workspace.dependencies]` + `workspace = true` | Official Cargo solution; prevents drift and duplicate upgrades |
| Linux Proton path assembly | Manual string concatenation in bindings | `construct_proton_docs_path()` in `classic-path-core` | Existing shared helper already encodes the expected Proton prefix layout |
| Steam library discovery | New ad-hoc parser or hard-coded Steam path guesses | Existing `parse_steam_library_vdf()` helper | Partial implementation already exists; Phase 8 is wiring, not reinvention |
| Node TS contract maintenance | Handwritten `.d.ts` | NAPI-RS generated `index.d.ts` snapshot | NAPI-RS is the authoritative generator; handwritten snapshots drift |
| Filesystem fixtures | Real user directories or checked-in fake prefixes | `tempfile::TempDir` integration fixtures | Isolated, deterministic, and already standard in `classic-path-core` tests |

**Key insight:** Every hard part in this phase already has a canonical primitive in-tree. The safe plan is to compose and govern those primitives, not invent replacements.

## Common Pitfalls

### Pitfall 1: Getting Linux docs-path precedence backwards
**What goes wrong:** The planner preserves the existing `~/.local/share` path as primary and only checks Proton second.
**Why it happens:** Current `DocsPathFinder` already returns local-share on non-Windows builds, so it is easy to patch Proton in as a late fallback.
**How to avoid:** Enforce D-02/D-03 exactly: cached path first, then valid Proton path, then local-share fallback.
**Warning signs:** Happy-path Proton fixture passes only when local-share is absent.

### Pitfall 2: Writing proof that current CI never executes
**What goes wrong:** The repo adds Linux-only `#[cfg(target_os = "linux")]` tests, but Rust CI is `windows-latest` only.
**Why it happens:** Source ownership is Linux-specific, but validation infrastructure is currently Windows-centric.
**How to avoid:** Extract candidate-selection logic into a testable helper and drive it with tempdirs from crate-level integration tests; optionally add future Linux CI later.
**Warning signs:** New test file exists but never runs in local Windows or current CI jobs.

### Pitfall 3: Turning workspace promotion into version-upgrade work
**What goes wrong:** `winreg` is promoted and upgraded in the same step, expanding scope.
**Why it happens:** Research shows `winreg 0.52` is behind crates.io latest `0.56.0`.
**How to avoid:** Separate ownership cleanup from dependency upgrade work unless a version bump is required to compile.
**Warning signs:** Lockfile churn or new API edits appear while only moving manifests.

### Pitfall 4: Assuming the Node freshness workflow is missing
**What goes wrong:** New scripts or CI jobs get added unnecessarily.
**Why it happens:** The repo still has a `.gitignore` contradiction, so it looks like the whole workflow is unfinished.
**How to avoid:** Reuse the existing `dts:freshness:*` scripts and CI job; Phase 8 should align tracking/docs/ignore rules, not replace the gate.
**Warning signs:** Duplicate freshness scripts appear alongside the current `check_dts_freshness.py` path.

### Pitfall 5: Removing `zerovec` without build proof
**What goes wrong:** The workaround is deleted because Slint is already on 1.15.x, but `gui-bridge` or workspace all-features builds regress.
**Why it happens:** Current dependency tree still shows the direct dev-dependency providing the visible `zerovec/alloc` feature.
**How to avoid:** Attempt removal, then immediately validate with `classic-shared-core` `gui-bridge` and workspace all-features test/build commands.
**Warning signs:** `icu_properties`/`zerovec` feature-resolution failures after manifest cleanup.

## Code Examples

Verified patterns from official sources and repo source:

### Workspace-inherited target dependency
```toml
# Source: Cargo docs - https://doc.rust-lang.org/cargo/reference/workspaces.html
[workspace.dependencies]
winreg = "0.52"

[target.'cfg(windows)'.dependencies]
winreg = { workspace = true }
```

### NAPI-RS generated contract artifact model
```text
# Source: NAPI-RS docs
build output:
- .node    compiled native addon
- index.js generated JS loader
- index.d.ts generated TypeScript declarations
```

### Repo-standard Node freshness gate usage
```bash
# Source: docs/implementation/node_api_parity/governance/gate_contract_baseline.md
bun run parity:gate:local
bun run test:bun
bun run test:node
bun run dts:freshness:check
```

### Tempdir-backed Proton fixture layout
```text
# Source: prescriptive fixture pattern based on existing tempfile usage in classic-path-core
<temp>/
├── SteamLibrary/
│   └── steamapps/compatdata/377160/pfx/drive_c/users/steamuser/My Documents/My Games/Fallout4/
└── home/.local/share/My Games/Fallout4/
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Crate-local shared dependency pins | Cargo workspace dependency inheritance | Stable Cargo workspace feature; repo already uses it broadly | Centralizes version governance and keeps manifests consistent |
| Local-share-only Linux docs-path fallback | Proton-aware shared docs-path workflow with explicit fallback | Needed now because helper already exists but is unused | Makes Linux Proton support real instead of partial dead code |
| Build-first-only Node type inspection | Commit generated `index.d.ts` snapshot and verify freshness in CI | NAPI-RS v2+ generation model; repo parity docs codified by 2026-02 | Contributors can inspect public Node contract without building first |
| Open-ended workaround comments | Proof-based dependency cleanup against current Slint/ICU stack | Current repo pin is Slint 1.15.0 / latest 1.15.1 | Forces the phase to answer whether workaround is still needed |

**Deprecated/outdated:**
- “Inspect Node types only after a local build” — outdated for this repo once `.gitignore` is fixed, because `index.d.ts` is already a tracked public artifact.
- “Proton helper exists but may stay unused” — outdated given locked decision D-01/D-02.

## Open Questions

1. **Can Proton workflow proof be made fully cross-platform without weakening confidence?**
   - What we know: current CI is Windows-only, and Linux platform helpers are target-specific.
   - What's unclear: whether maintainers want Linux-only execution proof or will accept injected shared-workflow tests in `classic-path-core`.
   - Recommendation: plan for extracted candidate-selection helper + crate integration tests now; treat native Linux CI as follow-up, not a Phase 8 blocker.

2. **Will `zerovec` removal pass immediately on current Slint 1.15.x?**
   - What we know: current dependency tree shows direct `zerovec/alloc` feature injection from `classic-shared-core` dev-deps.
   - What's unclear: whether the direct dependency is still strictly required or merely historical.
   - Recommendation: make removal the first implementation attempt, but gate it with `classic-shared-core` `gui-bridge` and workspace `--all-features` validation before deleting comments/docs.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Cargo | Rust manifest/test work | ✓ | 1.94.0 | — |
| rustc | Rust compile/test work | ✓ | 1.94.0 | — |
| Bun | Node parity/freshness workflow | ✓ | 1.3.10 | none practical for repo-standard scripts |
| Node | Node runtime smoke tests | ✓ | 25.9.0 | limited: Bun covers some tests, not Node runtime smoke |
| Python | `check_dts_freshness.py` and parity helpers | ✓ | 3.14.3 | — |
| Native Linux execution surface | True target_os=linux runtime proof | ✗ on this machine | — | Use extracted pure-helper integration tests; otherwise require Linux CI/manual run |

**Missing dependencies with no fallback:**
- None for code/config work in this phase.

**Missing dependencies with fallback:**
- Native Linux runner: fallback is tempdir/injected shared-workflow tests that avoid requiring an actual Linux environment.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Mixed: Rust `cargo test` + Bun/Node parity gates |
| Config file | `ClassicLib-rs/Cargo.toml`, `ClassicLib-rs/node-bindings/classic-node/package.json`, `.github/workflows/ci-rust.yml`, `.github/workflows/ci-typescript.yml` |
| Quick run command | `cargo test -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml` and `bun run dts:freshness:check` |
| Full suite command | `cargo test --workspace --release --all-features --manifest-path ClassicLib-rs/Cargo.toml` and from `ClassicLib-rs/node-bindings/classic-node`: `bun run parity:gate:local && bun run test:bun && bun run test:node && bun run dts:freshness:check` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | `winreg` is inherited from workspace under `cfg(windows)` | build/config | `cargo check -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml` | ✅ |
| INFRA-02 | `phf` is inherited from workspace in constants crate | build/config | `cargo check -p classic-constants-core --manifest-path ClassicLib-rs/Cargo.toml` | ✅ |
| INFRA-03 | Linux docs-path prefers Proton then falls back correctly | integration | `cargo test -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml proton` | ❌ Wave 0 |
| INFRA-04 | `gui-bridge` still builds/tests after `zerovec` cleanup | build/test | `cargo test -p classic-shared-core --features gui-bridge --manifest-path ClassicLib-rs/Cargo.toml` | ✅ |
| INFRA-05 | committed `index.d.ts` matches generated output | contract/freshness | `bun run dts:freshness:check` | ✅ |
| TEST-03 | mock Proton prefix happy path + both fallbacks + legacy local-share regression | integration | `cargo test -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml proton` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cargo test -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml` for Rust path work; `bun run dts:freshness:check` for Node contract work
- **Per wave merge:** `cargo test --workspace --release --all-features --manifest-path ClassicLib-rs/Cargo.toml` plus full Node parity/test gate sequence
- **Phase gate:** Full Rust all-features suite and Node parity/freshness gates green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `ClassicLib-rs/business-logic/classic-path-core/tests/linux_proton_docs_path.rs` — crate-level integration proof for INFRA-03 / TEST-03
- [ ] If tests remain target-linux-only, add a Linux execution path in CI; otherwise keep tests pure/injected so current Windows CI can execute them

## Sources

### Primary (HIGH confidence)
- Cargo docs / Context7 (`/websites/doc_rust-lang_cargo`) - workspace dependency inheritance and target-scoped `workspace = true`
- NAPI-RS docs / Context7 (`/napi-rs/website`) - generated `.node`, `index.js`, and `index.d.ts` model
- `ClassicLib-rs/business-logic/classic-path-core/src/docs_path.rs` - current docs-path strategy order
- `ClassicLib-rs/business-logic/classic-path-core/src/platform/linux.rs` - existing Steam VDF and Proton path helpers
- `ClassicLib-rs/node-bindings/classic-node/package.json` - current freshness/parity command wiring
- `tools/node_api_parity/check_dts_freshness.py` - actual freshness behavior
- `.github/workflows/ci-typescript.yml` - existing CI freshness gate
- `.github/workflows/ci-rust.yml` - current Windows-only Rust CI shape
- `cargo tree -p classic-shared-core --features gui-bridge -e features -i zerovec` - current `zerovec` feature source inspection

### Secondary (MEDIUM confidence)
- crates.io API - latest published versions/dates for `winreg`, `phf`, and `slint`
- repo docs: `docs/api/classic-path-core.md`, `docs/api/game-setup-workflow.md`, `docs/api/binding-contract-refresh-note.md`, `docs/implementation/node_api_parity/governance/gate_contract_baseline.md`

### Tertiary (LOW confidence)
- Web search for Slint/zerovec discussions in 2026 - useful for currency, but not authoritative for whether this repo can remove the workaround without build proof

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - based on official Cargo/NAPI-RS docs plus current repo manifests/scripts
- Architecture: MEDIUM-HIGH - repo constraints are clear, but Linux proof shape requires a repo-fit testing extraction choice
- Pitfalls: HIGH - directly observed from source, CI workflows, and dependency tree inspection

**Research date:** 2026-04-06
**Valid until:** 2026-05-06

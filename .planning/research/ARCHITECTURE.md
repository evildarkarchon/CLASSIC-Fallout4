# Architecture Research

**Domain:** Workspace-root migration for CLASSIC's Rust core and binding ecosystem
**Researched:** 2026-04-11
**Confidence:** HIGH

## Standard Architecture

### System Overview

This milestone should **move the workspace anchor, not redesign the system**. The Rust crate graph, layering, and thin-wrapper rule stay intact; only the physical workspace root and every path contract that depends on it change.

```
┌───────────────────────────────────────────────────────────────────────┐
│ REPOSITORY ROOT (new Rust workspace root)                            │
├───────────────────────────────────────────────────────────────────────┤
│ Cargo.toml  Cargo.lock  .cargo/  benches/  criterion.toml            │
│ benchmark-config.yaml  validate_stubs.py                             │
├───────────────────────────────────────────────────────────────────────┤
│ foundation/        business-logic/        cpp-bindings/              │
│ node-bindings/     python-bindings/       ui-applications/           │
├───────────────────────────────────────────────────────────────────────┤
│ classic-cli/       classic-gui/           docs/  tools/  .github/    │
│ .planning/         tests/                                             │
└───────────────────────────────────────────────────────────────────────┘
           │                    │                      │
           │                    │                      │
           ▼                    ▼                      ▼
   CMake/Corrosion       Bun/NAPI + PyO3       parity/docs/CI/tooling
   native wrappers       binding wrappers      read repo-root paths
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Repo-root workspace manifest | Canonical Cargo workspace root, shared lockfile, shared target dir, shared profiles/deps/lints | New root `Cargo.toml` plus moved `Cargo.lock`, `.cargo/config.toml`, benchmark config files |
| Layer directories | Preserve current crate ownership boundaries | Root-level `foundation/`, `business-logic/`, `cpp-bindings/`, `node-bindings/`, `python-bindings/`, `ui-applications/` |
| Native wrappers | Consume `classic-cpp-bridge` through Corrosion/CMake without knowing old `ClassicLib-rs/` prefix | `classic-cli/CMakeLists.txt`, `classic-gui/CMakeLists.txt`, wrapper PowerShell scripts |
| Binding wrappers | Keep Node/Python/C++ adapters thin and path-correct after relocation | `node-bindings/classic-node`, `python-bindings/*-py`, `cpp-bindings/classic-cpp-bridge` |
| Repo tooling | Parse source/build outputs using repo-root-relative contracts | `rebuild_rust.ps1`, parity tools, `validate_stubs.py`, benchmarks workflow, planning tests |
| Docs/planning/skills | Describe the new root layout so future work does not reintroduce stale paths | `README.md`, `AGENTS.md`, docs under `docs/`, planning artifacts, project skills |

## Recommended Project Structure

### 1. Cache Eviction Flow (YAML_CACHE, SETTINGS_CACHE, HASH_CACHE)

**Current flow:**
```
./
├── Cargo.toml                  # new authoritative workspace manifest
├── Cargo.lock                  # shared lockfile moves to repo root
├── .cargo/
│   └── config.toml             # workspace-scoped cargo aliases/config
├── benches/                    # workspace benchmark entrypoints
├── criterion.toml              # criterion output config (root target/criterion)
├── benchmark-config.yaml       # benchmark CI thresholds
├── validate_stubs.py           # python stub validator; should live with workspace root
├── foundation/                 # unchanged internal crate layout
├── business-logic/             # unchanged internal crate layout
├── cpp-bindings/               # unchanged internal crate layout
├── node-bindings/              # unchanged internal crate layout
├── python-bindings/            # unchanged internal crate layout
├── ui-applications/            # unchanged internal crate layout
├── classic-cli/                # native wrapper over classic-cpp-bridge
├── classic-gui/                # native wrapper over classic-cpp-bridge
├── docs/
├── tools/
├── .github/
├── .planning/
└── tests/
```

### Structure Rationale

- **Repo root becomes the only workspace root:** Cargo workspaces share a single lockfile and target directory at the workspace root; leaving those concepts split between repo root and `ClassicLib-rs/` would create a confusing half-migrated architecture. Source: Cargo workspace docs.
- **Layer directories stay exactly layer-based:** the milestone is explicitly a location migration, so `foundation/`, `business-logic/`, bindings, and TUI should move intact rather than being flattened by crate type.
- **Workspace-owned support files move with the workspace:** `.cargo/config.toml`, `Cargo.lock`, `criterion.toml`, `benchmark-config.yaml`, `benches/`, and `validate_stubs.py` are path contracts for tooling and should not be stranded in a no-longer-authoritative `ClassicLib-rs/` directory.

## Architectural Patterns

### Pattern 1: Root manifest as single source of truth

**What:** Put the authoritative `[workspace]`, `[workspace.dependencies]`, `[workspace.lints]`, and `[profile.*]` tables in `./Cargo.toml` and remove `ClassicLib-rs/Cargo.toml` as the workspace anchor.

**When to use:** Immediately, for this milestone. Do not keep dual manifests.

**Trade-offs:**
- Pro: Aligns Cargo behavior with user expectation: run Cargo from repo root.
- Pro: Eliminates `--manifest-path ClassicLib-rs/Cargo.toml` everywhere.
- Pro: Makes CI/cache/benchmark paths deterministic (`./target`, `./Cargo.lock`).
- Con: Requires broad path cleanup in tooling and docs.

**Example:**
```toml
[workspace]
members = [
  "foundation/classic-shared-core",
  "foundation/classic-shared-py",
  "business-logic/classic-config-core",
  "cpp-bindings/classic-cpp-bridge",
  "node-bindings/classic-node",
  "python-bindings/classic-config-py",
  "ui-applications/classic-tui",
]
resolver = "2"
```

### Pattern 2: Preserve crate internals, rewrite only path edges

**What:** Keep every crate's own `src/`, tests, examples, and package metadata intact; only update workspace-member paths and inter-crate `path =` edges that depended on the old `ClassicLib-rs/` container.

**When to use:** For all member manifests and all non-Rust consumers.

**Trade-offs:**
- Pro: Minimal behavioral risk.
- Pro: Preserves parity contracts and public APIs.
- Con: Many relative paths must be rewritten carefully.

**Example:**
```toml
# before, in node-bindings/classic-node/Cargo.toml
classic-shared-core = { path = "../../foundation/classic-shared-core" }

# after root move
classic-shared-core = { path = "../../foundation/classic-shared-core" }
```

### Pattern 3: Repo-root-relative tooling contracts

**What:** Every repo tool should take `--repo-root .` and derive current locations from that root, not from a hardcoded `ClassicLib-rs/...` prefix.

**When to use:** parity generators/gates, stub validation, rebuild scripts, benchmark workflows, planning tests.

**Trade-offs:**
- Pro: Future directory moves become cheaper.
- Pro: Reduces duplicated string constants.
- Con: Requires a one-time audit of default arguments and fixture paths.

**Example:**
```python
parser.add_argument(
    "--index-dts",
    default="node-bindings/classic-node/index.d.ts",
)
```

## Data Flow

### Build / Validation Flow After Migration

```
[repo root cargo command]
    ↓
[root Cargo.toml workspace]
    ↓
[shared target/ and Cargo.lock at repo root]
    ↓
┌──────────────────────┬──────────────────────┬─────────────────────────┐
│ classic-cpp-bridge   │ classic-node         │ classic-*-py            │
│ (Corrosion/CXX)      │ (napi build)         │ (maturin / PyO3)        │
└──────────┬───────────┴──────────┬───────────┴──────────┬──────────────┘
           ↓                      ↓                      ↓
      classic-cli/gui        Node parity/tests      Python parity/stubs/tests
           ↓                      ↓                      ↓
      docs/artifacts refresh and CI caches keyed off repo-root paths
```

### State Management

The runtime/data architecture does **not** change:

```
shared Tokio runtime in classic-shared-core
    ↓
business-logic crates
    ↓
thin binding/native wrappers
```

This milestone changes path discovery and build orchestration only.

### Key Data Flows

1. **Cargo flow:** commands now start at repo root and use root `target/` and root `Cargo.lock`.
2. **Native wrapper flow:** CMake/Corrosion points to `./Cargo.toml` and `cpp-bindings/classic-cpp-bridge/include` instead of `../ClassicLib-rs/...`.
3. **Parity/report flow:** generators still write into binding-local `parity-artifacts/` and docs baselines, but the embedded source paths and default output locations all shift to root-level directories.

## Migration-Specific Integration Points

### New integration points

| Integration point | Why it is new/load-bearing | Required action |
|-------------------|----------------------------|-----------------|
| `./Cargo.toml` | New authoritative workspace root | Create root manifest and move workspace tables here |
| `./Cargo.lock` | Cargo lockfile must live at workspace root | Move from `ClassicLib-rs/Cargo.lock` |
| `./.cargo/config.toml` | Workspace cargo aliases/config now belong to root | Move from `ClassicLib-rs/.cargo/config.toml` |
| `./criterion.toml`, `./benchmark-config.yaml`, `./benches/` | Bench workflows currently assume old workspace directory | Move so benchmark jobs run from repo root without split config |

### Modified integration points

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Root workspace manifest ↔ member crates | Cargo workspace membership and path deps | Update `members` list and all `path =` edges; Cargo path dependencies must point to the exact crate directory |
| `cpp-bindings/classic-cpp-bridge` ↔ core crates | Relative path dependencies | Current `../../foundation/...` and `../../business-logic/...` paths must be rewritten for the new parent depth |
| `node-bindings/classic-node` ↔ core crates/tools | Cargo deps + package.json scripts | Manifest path deps change; package scripts using `../../../tools/...` and `--repo-root ../../..` become one level shorter |
| `python-bindings/*-py` ↔ core crates/shared-py | Relative path dependencies | All `../../business-logic/...` / `../../foundation/...` paths change |
| `ui-applications/classic-tui` ↔ core crates | Relative path dependencies | TUI manifest paths change even though behavior does not |
| `classic-cli` / `classic-gui` ↔ Rust bridge | Corrosion `MANIFEST_PATH` + include dirs | `../ClassicLib-rs/Cargo.toml` and `../ClassicLib-rs/cpp-bindings/.../include` must point at root workspace and root bridge include dir |
| `rebuild_rust.ps1` ↔ workspace/bindings | Script-owned path contracts | `$WorkspaceManifest`, `$PythonBindingsRoot`, module discovery roots, and any assumptions about `ClassicLib-rs` must move together |
| `validate_stubs.py` ↔ Python bindings | Rust-dir and stub path resolution | Prefer moving script to repo root and changing callers to `--rust-dir .`; otherwise callers still depend on a stale subdirectory |
| parity tools under `tools/` ↔ source trees | Hardcoded crate/module paths | `RUST_TARGET_CRATES`, `PYTHON_TARGET_MODULES`, output-dir defaults, runtime-registry defaults, and CXX bridge path defaults all need path-prefix rewrites |
| CI workflows ↔ caches/artifacts | `working-directory`, `manifest-path`, cache key globs, upload paths | Replace `ClassicLib-rs/target`, `ClassicLib-rs/**/*.rs`, and `ClassicLib-rs/...` artifact paths with root equivalents |
| docs / skills / AGENTS / planning ↔ contributors | Human path contract | Update commands, architecture maps, and trigger examples so future work uses the new root layout |
| generated parity/report files ↔ docs baselines | Embedded source paths | Regenerate Node/Python/CXX surface artifacts because source file paths and artifact paths change even if API shape does not |
| planning tests / audit fixtures ↔ repo layout | Path assertions | Update tests under `tests/planning/` and similar audit surfaces that assert `ClassicLib-rs/...` paths |

## Expected Build-Flow Changes

| Surface | Before | After |
|---------|--------|-------|
| Rust workspace commands | `cargo ... --manifest-path ClassicLib-rs/Cargo.toml` | `cargo ...` from repo root |
| Cargo output directory | `ClassicLib-rs/target` | `target` at repo root |
| Benchmarks workflow | `working-directory: ClassicLib-rs` | `working-directory: .` or no override |
| Node package scripts | repo-root is `../../..` from `classic-node` | repo-root is `../..` from `node-bindings/classic-node` |
| Python rebuild/stub flow | points at `ClassicLib-rs/python-bindings` and `ClassicLib-rs/validate_stubs.py` | points at `python-bindings` and root `validate_stubs.py` |
| C++ Corrosion imports | `../ClassicLib-rs/Cargo.toml` | `../Cargo.toml` |

## Verification Surfaces

These are the highest-value checks because they cross the most path-sensitive boundaries.

1. **Workspace health**
   - `cargo fmt --all -- --check`
   - `cargo clippy --workspace --all-targets --all-features -- -D warnings`
   - `cargo test --workspace --release -- --nocapture`

2. **C++ bridge and native wrappers**
   - `python tools/cxx_api_parity/check_parity_gate.py --repo-root .`
   - `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test`
   - `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test`

3. **Node binding flow**
   - from `node-bindings/classic-node`: `bun install`
   - `bun run build`
   - `bun run parity:gate`
   - `bun run dts:freshness:check`
   - `bun run test:bun`
   - `bun run test:node`

4. **Python binding flow**
   - `uv venv python-bindings/.venv`
   - `uv pip install --python python-bindings/.venv/Scripts/python.exe -r python-bindings/requirements-ci.txt`
   - `python tools/python_api_parity/check_parity_gate.py --repo-root .`
   - `python validate_stubs.py --rust-dir . --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings`
   - `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_config classic_scanlog classic_version_registry`
   - `uv run --python python-bindings/.venv/Scripts/python.exe python -m pytest python-bindings/tests -q`

5. **Path-audit surfaces**
   - CI workflow YAMLs
   - README / docs / AGENTS / skill docs
   - `tests/planning/*` and any hardcoded-path repo audits
   - parity baseline JSON/MD files whose `source_paths` or emitted source-file fields changed

## Build Order

1. **Create the new root workspace shell first**
   - Add root `Cargo.toml`
   - move `Cargo.lock`, `.cargo/config.toml`, `criterion.toml`, `benchmark-config.yaml`, `benches/`
   - rationale: everything else depends on there being a real workspace root

2. **Move the crate directories without changing internals**
   - `foundation/`, `business-logic/`, `cpp-bindings/`, `node-bindings/`, `python-bindings/`, `ui-applications/`
   - rationale: establishes final filesystem layout before rewriting consumers

3. **Rewrite all member-manifest path edges**
   - every `Cargo.toml` with a local `path =`
   - rationale: until these compile, no consumer can build reliably

4. **Update first-order consumers of the workspace root**
   - `classic-cli/CMakeLists.txt`
   - `classic-gui/CMakeLists.txt`
   - `rebuild_rust.ps1`
   - `validate_stubs.py` location/call sites
   - `node-bindings/classic-node/package.json`

5. **Update repo tooling and generated-artifact producers**
   - `tools/python_api_parity/*`
   - `tools/node_api_parity/*`
   - `tools/cxx_api_parity/*`
   - benchmark workflow assumptions
   - rationale: these are verification and reporting layers built on top of the final layout

6. **Refresh CI, docs, skills, and planning/audit surfaces**
   - `.github/workflows/*`
   - `README.md`, `docs/README.md`, `docs/api/*`, `AGENTS.md`, project skill references
   - `.planning/*`, `tests/planning/*`

7. **Regenerate and verify**
   - parity artifacts, runtime coverage summaries, any path-bearing baselines
   - then run the verification surface list above

## Anti-Patterns

### Anti-Pattern 1: Dual-root workspace state

**What people do:** add a new root `Cargo.toml` but leave `ClassicLib-rs/Cargo.toml`, `Cargo.lock`, and config files effectively active.

**Why it's wrong:** Cargo root behavior, cache paths, and contributor docs drift immediately. People will run commands in both places and get inconsistent lockfiles/targets.

**Do this instead:** make repo root the only authoritative workspace root and demote/remove the old anchor.

### Anti-Pattern 2: Updating commands but not generated/report paths

**What people do:** fix build scripts and stop there.

**Why it's wrong:** parity generators and docs baselines embed source paths; stale generated files will keep CI or audits red even though builds pass.

**Do this instead:** regenerate Node/Python/CXX parity artifacts and any path-bearing reports as part of the same change.

### Anti-Pattern 3: Treating docs and skills as optional cleanup

**What people do:** postpone README/AGENTS/skill/planning updates because runtime behavior did not change.

**Why it's wrong:** this repo uses docs, skills, and planning files as active workflow contracts; stale path guidance will re-break future work.

**Do this instead:** update human-facing path contracts in the same milestone.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Cargo | Root workspace discovery via parent search and explicit root manifest | Official docs confirm shared lockfile/target live at workspace root |
| Corrosion/CMake | Import `classic-cpp-bridge` from root manifest | Native wrappers are the most obvious place path drift will show up |
| Bun / NAPI-RS | Build from `node-bindings/classic-node` against root workspace | package.json relative tool paths must shrink by one level |
| uv / maturin / PyO3 | Build Python bindings against root workspace and local `.venv` | Keep `.venv` under `python-bindings/`, not repo root |
| GitHub Actions cache/artifacts | Repo-root cache keys and upload paths | `target` and `**/*.rs` globs must follow the new layout |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| workspace root ↔ crates | Cargo members and path deps | highest-risk migration surface |
| workspace root ↔ wrapper scripts | manifest path / working directory | must change before CI can be trusted |
| tooling ↔ generated artifacts | repo-root-relative defaults | regenerate after path rewrite |
| docs/skills/planning ↔ contributors | textual commands and links | stale guidance is operational drift in this repo |

## Sources

- `J:\CLASSIC-Fallout4\.planning\PROJECT.md`
- `J:\CLASSIC-Fallout4\ClassicLib-rs\Cargo.toml`
- `J:\CLASSIC-Fallout4\classic-cli\CMakeLists.txt`
- `J:\CLASSIC-Fallout4\classic-gui\CMakeLists.txt`
- `J:\CLASSIC-Fallout4\rebuild_rust.ps1`
- `J:\CLASSIC-Fallout4\ClassicLib-rs\node-bindings\classic-node\package.json`
- `J:\CLASSIC-Fallout4\ClassicLib-rs\validate_stubs.py`
- `J:\CLASSIC-Fallout4\tools\python_api_parity\*.py`
- `J:\CLASSIC-Fallout4\tools\node_api_parity\*.py`
- `J:\CLASSIC-Fallout4\tools\cxx_api_parity\*.py`
- `J:\CLASSIC-Fallout4\.github\workflows\ci-rust.yml`
- `J:\CLASSIC-Fallout4\.github\workflows\ci-python-bindings.yml`
- `J:\CLASSIC-Fallout4\.github\workflows\ci-typescript.yml`
- `J:\CLASSIC-Fallout4\.github\workflows\ci-cpp.yml`
- `J:\CLASSIC-Fallout4\.github\workflows\benchmarks.yml`
- `https://doc.rust-lang.org/cargo/reference/workspaces.html` (official Cargo workspace behavior)
- `https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html` (official Cargo path-dependency behavior)

---
*Architecture research for: CLASSIC workspace-root migration*
*Researched: 2026-04-11*

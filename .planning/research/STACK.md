# Stack Research

**Domain:** Brownfield Rust workspace relocation to repository root
**Researched:** 2026-04-11
**Confidence:** HIGH

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Cargo virtual workspace at repo root | Current Cargo stable / Rust 2024 workspace | Canonical workspace entrypoint | Cargo defines the workspace root as the directory containing the workspace manifest. Moving the virtual manifest to `J:\CLASSIC-Fallout4\Cargo.toml` is the clean, standard way to make `cargo build/test/fmt/clippy` run from repo root without creating a fake wrapper workspace. |
| Existing layer directories preserved at root (`foundation/`, `business-logic/`, `cpp-bindings/`, `node-bindings/`, `python-bindings/`, `ui-applications/`) | Current repo layout, relocated only | Keep crate topology identical after move | This preserves relative crate-to-crate paths. Most `path = "../..."` and `path = "../../..."` entries inside member `Cargo.toml` files should remain unchanged if these layer folders move intact from `ClassicLib-rs/` to repo root. |
| Existing multi-language build stack (Corrosion + CXX, PyO3, NAPI-RS, Bun, uv, PowerShell wrappers) | Keep current pinned versions | Preserve native/frontend/binding workflows | This milestone is relocation, not toolchain redesign. The repo already has validated wrapper and parity flows; retarget paths, do not replace the stack. |
| Root-level Cargo support files (`Cargo.lock`, `.cargo/config.toml`, `validate_stubs.py`) | Move with workspace root | Keep lockfile, aliases, and validation aligned with new workspace root | `Cargo.lock` and `.cargo/config.toml` belong with the workspace root. `validate_stubs.py` currently assumes a Rust root containing `python-bindings/`; after relocation that root should be the repo root. |

### Supporting Libraries / Mechanisms

| Library / Mechanism | Version | Purpose | When to Use |
|---------------------|---------|---------|-------------|
| `[workspace.dependencies]` inheritance | Current Cargo | Keep all shared Rust dependency pins centralized | Keep exactly as-is when moving the workspace manifest to repo root. This is already working and should not be redesigned during relocation. |
| Path dependencies relative to member manifests | Current Cargo | Connect crates across foundation/business-logic/bindings layers | Keep current `path =` entries unless the relative relationship actually changes. In this repo, preserving the existing layer folders means most crate-to-crate `path` entries do **not** need to change. |
| Corrosion `MANIFEST_PATH` + CXX include paths | Corrosion v0.6.1 in CMake files | Build `classic-cpp-bridge` for CLI/GUI | Update only the repo-relative paths in `classic-cli/CMakeLists.txt` and `classic-gui/CMakeLists.txt`; do not change the CXX bridge model itself. |
| Repo-root-aware parity tooling | Existing Python tools under `tools/` | Keep Node/Python/CXX parity gates working after move | All tool defaults and fixtures that hard-code `ClassicLib-rs/...` must be updated to new root-level paths. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Cargo from repo root | Build, test, fmt, clippy | After the move, the canonical commands should be plain `cargo ...` from repo root. `--manifest-path ClassicLib-rs/Cargo.toml` should disappear from active workflows. |
| PowerShell wrapper scripts | Preserve repo-native workflows | `rebuild_rust.ps1`, `classic-cli/build_cli.ps1`, and `classic-gui/build_gui.ps1` should stay as the public entrypoints; only retarget their internal paths. |
| GitHub Actions caches and working directories | CI preservation | Cache paths must move from `ClassicLib-rs/target` to `target`; working directories like `ClassicLib-rs/node-bindings/classic-node` must become `node-bindings/classic-node`. |
| Planning/doc/skill references | Contributor correctness | This repo has many agent and documentation references to `ClassicLib-rs/`; if missed, future work will be routed to the wrong paths immediately. |

---

## Concrete Layout Recommendation

Recommended post-move layout:

```text
J:\CLASSIC-Fallout4\
├── Cargo.toml                 # moved workspace virtual manifest
├── Cargo.lock                 # moved workspace lockfile
├── .cargo\config.toml         # moved cargo aliases/config
├── validate_stubs.py          # moved workspace-owned helper
├── foundation\
├── business-logic\
├── cpp-bindings\
├── node-bindings\
├── python-bindings\
├── ui-applications\
├── classic-cli\
├── classic-gui\
├── tools\
└── docs\
```

**Important:** this is a relocation of the existing Rust workspace tree, not a new taxonomy. Keep the six Rust layer directories intact; just move them up one level.

---

## Required Stack / Layout Changes

### 1) Cargo workspace root

**Do this:**
- Move `ClassicLib-rs/Cargo.toml` to repo root as `Cargo.toml`.
- Keep it as a **virtual workspace** (`[workspace]` only), with explicit `resolver = "2"`.
- Keep the current `members = [...]`, `workspace.dependencies`, lints, and profiles.
- Move `ClassicLib-rs/Cargo.lock` to repo root.
- Move `ClassicLib-rs/.cargo/config.toml` to repo root `.cargo/config.toml`.

**Why:** Cargo’s canonical workspace root is the directory containing the workspace manifest. That is the standard, lowest-friction way to make repo-root Cargo commands work.

### 2) Move the Rust-owned directories, not just the manifest

**Move intact:**
- `ClassicLib-rs/foundation/` → `foundation/`
- `ClassicLib-rs/business-logic/` → `business-logic/`
- `ClassicLib-rs/cpp-bindings/` → `cpp-bindings/`
- `ClassicLib-rs/node-bindings/` → `node-bindings/`
- `ClassicLib-rs/python-bindings/` → `python-bindings/`
- `ClassicLib-rs/ui-applications/` → `ui-applications/`

**Also move workspace-owned helpers:**
- `ClassicLib-rs/validate_stubs.py` → `validate_stubs.py`

**Why:** the milestone says move all crates currently under `ClassicLib-rs/` to the repo root while preserving each crate’s internal structure. Moving the layer folders intact preserves relative crate topology.

### 3) Path dependencies inside crate manifests

**Recommendation:** treat these as a verification task, not a mass rewrite.

Because the relative relationships between moved crates stay the same, examples like these should usually remain valid after the move:

- `node-bindings/classic-node` → `../../foundation/classic-shared-core`
- `python-bindings/classic-config-py` → `../../business-logic/classic-config-core`
- `business-logic/classic-config-core` → `../classic-settings-core`

**What to actually change:**
- Only update crate `path =` entries that point to something whose relative location really changed.
- Expect **external consumer paths** to break much more than intra-workspace crate paths.

### 4) C++ wrapper integration points

These will break if missed:

- `classic-cli/CMakeLists.txt`
  - `MANIFEST_PATH ../ClassicLib-rs/Cargo.toml` → `../Cargo.toml`
  - include dir `../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include` → `../cpp-bindings/classic-cpp-bridge/include`
- `classic-gui/CMakeLists.txt`
  - same `MANIFEST_PATH` change
  - same include-dir change

**Why:** Corrosion is not discovering the workspace magically; it is pointed at the old manifest explicitly.

### 5) PowerShell wrappers and local developer scripts

`rebuild_rust.ps1` has hard-coded assumptions that must be retargeted:

- `$WorkspaceManifest = Join-Path $ProjectRoot "ClassicLib-rs/Cargo.toml"` → repo-root `Cargo.toml`
- `$PythonBindingsRoot = Join-Path $ProjectRoot "ClassicLib-rs/python-bindings"` → `python-bindings`
- `Push-Location (Join-Path $ProjectRoot "ClassicLib-rs")` → repo root
- node working dir `ClassicLib-rs/node-bindings/classic-node` → `node-bindings/classic-node`
- any output/error messages mentioning `ClassicLib-rs/...` should be updated

`tools/enter_vs_dev_shell.ps1` example/help text should also be updated from `ClassicLib-rs/node-bindings/classic-node` to `node-bindings/classic-node`.

### 6) Node binding package and parity tooling

`node-bindings/classic-node/package.json` will need path-hop fixes because the package moves one directory closer to repo root.

Examples:
- `python ../../../tools/node_api_parity/check_parity_gate.py --repo-root ../../..`
- should become repo-root-relative from `node-bindings/classic-node`, i.e. `../../tools/... --repo-root ../..`

This affects:
- `parity:gate`
- `parity:gate:update-baseline`
- `dts:freshness:check`
- `dts:freshness:local`
- VS dev-shell helper scripts

**Important nuance:** `napi build --manifest-path ./Cargo.toml` stays fine, because it is relative to the package itself.

### 7) Python stub validation and Python parity/tooling

`validate_stubs.py` is workspace-root-oriented. After the move, make repo root the `rust_dir`.

Commands/workflows that must change:
- `python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs ...`
- becomes something like `python validate_stubs.py --rust-dir . ...`

Output/input paths that must move:
- `ClassicLib-rs/python-bindings/parity-artifacts/...` → `python-bindings/parity-artifacts/...`
- `ClassicLib-rs/python-bindings/.venv/...` → `python-bindings/.venv/...`
- `ClassicLib-rs/python-bindings/tests/...` → `python-bindings/tests/...`

Tooling defaults that hard-code old paths also need rewiring, especially under:
- `tools/python_api_parity/`
- `tools/node_api_parity/`
- `tools/cxx_api_parity/`

The biggest break risk here is not Cargo; it is Python scripts with embedded string paths to `ClassicLib-rs/...`.

### 8) CI workflows

These path classes must change across workflows:

- `--manifest-path ClassicLib-rs/Cargo.toml` → plain root Cargo usage or `--manifest-path Cargo.toml`
- `ClassicLib-rs/target` → `target`
- `working-directory: ClassicLib-rs/...` → new root-level moved directory
- `hashFiles('ClassicLib-rs/**/*.rs')` → new moved directories, ideally explicit patterns for `foundation/**`, `business-logic/**`, `cpp-bindings/**`, `node-bindings/**`, `python-bindings/**`, `ui-applications/**`

Known workflow consumers from the live repo:
- `.github/workflows/ci-rust.yml`
- `.github/workflows/ci-python-bindings.yml`
- `.github/workflows/ci-typescript.yml`
- `.github/workflows/ci-cpp.yml`
- `.github/workflows/benchmarks.yml`

### 9) Docs, agent context, skills, tests, and planning artifacts

These are guaranteed stale after the move if not updated:

- `README.md`
- `AGENTS.md`
- `.opencode/skills/classic-project-guide/**`
- `.agents/skills/classic-project-guide/**`
- `.claude/skills/**` that reference `ClassicLib-rs`
- planning docs/tests under `.planning/` and `tests/planning/`
- API docs under `docs/api/` and repo indexes under `docs/`

This repo has many hard-coded path strings. Treat stale-reference cleanup as required integration work, not polish.

---

## Recommended Sequencing

1. **Move the workspace root artifacts first**
   - Root `Cargo.toml`, `Cargo.lock`, `.cargo/config.toml`, `validate_stubs.py`
   - Verify `cargo metadata` / `cargo build --workspace` works from repo root

2. **Move the six Rust layer directories intact**
   - `foundation`, `business-logic`, `cpp-bindings`, `node-bindings`, `python-bindings`, `ui-applications`
   - Verify workspace membership resolves

3. **Fix repo-external consumers next**
   - CMake/Corrosion
   - `rebuild_rust.ps1`
   - Node `package.json` scripts
   - parity tool defaults under `tools/`

4. **Fix CI and cache paths**
   - workflows, working directories, artifact paths, cache paths/hashes

5. **Fix docs/skills/agent references**
   - README, AGENTS, skill references, planning docs/tests

6. **Only then remove any temporary compatibility shims**
   - Do not keep permanent dual routing to both repo root and `ClassicLib-rs/`

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Root virtual workspace manifest | Keep `ClassicLib-rs/Cargo.toml` and add a thin root wrapper | Only as a very short-lived migration shim. Not recommended as the steady state because it preserves two workspace entrypoints and stale path assumptions. |
| Move the six layer directories intact | Flatten crates into a brand-new root taxonomy | Do not use for this milestone. That is repo redesign, not relocation. |
| Keep existing crate `path =` values where relative topology is unchanged | Rewrite all path dependencies proactively | Only if verification proves specific paths broke. Blanket rewrites add noise and risk for little value here. |
| Keep existing wrapper/parity entrypoints | Replace them with new tooling because paths changed | Do not do this in this milestone. The repo already has validated entrypoints; preserve them. |

---

## What NOT to Use / What NOT to Change

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Permanent dual workspace manifests (`Cargo.toml` at root plus active `ClassicLib-rs/Cargo.toml`) | Creates two sources of truth and guarantees stale docs/scripts survive | Make root `Cargo.toml` the single canonical workspace manifest |
| Crate renames, merges, splits, or ownership changes during the move | Turns a path migration into a crate-graph redesign and makes failures hard to attribute | Move crates as-is |
| Dependency/toolchain upgrades bundled into the relocation | Introduces unrelated failure modes in bindings, CXX, and CI | Keep current versions pinned |
| Replacing PowerShell wrappers/parity flows with new commands | Breaks established repo workflows and CI expectations | Retarget existing entrypoints to new paths |
| Keeping `ClassicLib-rs/` as a long-term compatibility shell | Leaves the old mental model alive and invites future drift | Remove it once the repo-root layout is verified |
| Adding `package.workspace` to every crate | Unnecessary if all moved crates remain under the root workspace tree | Let Cargo discover the root workspace normally |

---

## Stack Patterns by Variant

**If the command is a Cargo workspace command:**
- Run it from repo root
- Prefer `cargo build --workspace`, `cargo test --workspace`, `cargo fmt --all`, `cargo clippy --workspace`
- Because the whole point of the milestone is making repo-root Cargo the canonical flow

**If the command is binding-package-local:**
- Keep running from the binding package directory (`node-bindings/classic-node`)
- But fix relative hops to repo-root tools/artifacts
- Because package-local build commands still make sense; only the repo-root distance changed

---

## Version Compatibility / Behavior Notes

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| Cargo virtual workspace | Rust 2024 member crates | Keep `resolver = "2"` explicit in the virtual manifest |
| `[workspace.dependencies]` | Existing member manifests using `workspace = true` | No redesign needed; keep inheritance model intact |
| Path dependencies | Preserved layer-directory topology | Most member-to-member `path =` values should remain valid after the move because their relative geometry is unchanged |
| `validate_stubs.py` | Repo root as `--rust-dir` | Script logic expects `python-bindings/` under the Rust root; after the move that root is the repo root |
| Corrosion `MANIFEST_PATH` | Root `Cargo.toml` | CLI/GUI builds will fail until CMake points at the new manifest |

---

## Sources

- Context7 `/websites/doc_rust-lang_cargo` — verified Cargo workspace root behavior, virtual workspaces, workspace inheritance, and member/path semantics (HIGH)
- `J:\CLASSIC-Fallout4\.planning\PROJECT.md` — milestone scope and out-of-scope boundaries (HIGH)
- `J:\CLASSIC-Fallout4\ClassicLib-rs\Cargo.toml` — current workspace members, shared deps, resolver, lints, profiles (HIGH)
- `J:\CLASSIC-Fallout4\rebuild_rust.ps1` — current wrapper path assumptions (HIGH)
- `J:\CLASSIC-Fallout4\classic-cli\CMakeLists.txt` and `J:\CLASSIC-Fallout4\classic-gui\CMakeLists.txt` — current Corrosion/CXX integration points (HIGH)
- `J:\CLASSIC-Fallout4\.github\workflows\ci-rust.yml`, `ci-python-bindings.yml`, `ci-typescript.yml`, `ci-cpp.yml`, `benchmarks.yml` — CI path and cache assumptions (HIGH)
- `J:\CLASSIC-Fallout4\ClassicLib-rs\node-bindings\classic-node\package.json` — Node package-local relative tool paths (HIGH)
- `J:\CLASSIC-Fallout4\ClassicLib-rs\validate_stubs.py` and `J:\CLASSIC-Fallout4\tools\*_api_parity\*` — Python/Node/CXX parity tooling path assumptions (HIGH)
- `J:\CLASSIC-Fallout4\README.md`, `AGENTS.md`, skills under `.opencode/`, `.agents/`, `.claude/` — contributor/agent routing references that will become stale (HIGH)

---
*Stack research for: v9.1.0-root move crates to project root*
*Researched: 2026-04-11*

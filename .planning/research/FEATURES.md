# Feature Research

**Domain:** Brownfield Rust workspace relocation to repository root
**Researched:** 2026-04-11
**Confidence:** HIGH — findings are based on the live milestone definition in `.planning/PROJECT.md` plus current structure/testing artifacts in `.planning/codebase/STRUCTURE.md` and `.planning/codebase/TESTING.md`

---

## Feature Landscape

### Table Stakes (Contributors / CI Expect These)

These are the must-have outcomes for a workspace-relocation milestone. Missing any of these means the relocation is incomplete or unsafe.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Repository-root Cargo workspace entrypoint** | The milestone goal explicitly says Cargo work should happen from the repo root, not `ClassicLib-rs/`. | MEDIUM | Root `Cargo.toml` becomes the canonical workspace manifest. Existing commands that currently pass `--manifest-path ClassicLib-rs/Cargo.toml` need equivalent root behavior without changing crate ownership. |
| **All crates moved out of `ClassicLib-rs/` with internal crate layout preserved** | The milestone is relocation, not redesign. Contributors expect directory moves only, not crate graph churn. | HIGH | Preserve each crate's own `src/`, `tests/`, include/build files, and relative internals; only change the workspace parent location and path references. |
| **Workspace-member and path-reference rewiring across bindings, native wrappers, CI, and tooling** | Current scripts/docs/tests are path-heavy and point at `ClassicLib-rs/**`. A successful move must update every path consumer. | HIGH | Includes parity tooling, PowerShell rebuild scripts, CMake/Corrosion consumers, CI workflows, docs, skills, and planning/test artifacts that currently hard-code `ClassicLib-rs/`. |
| **Existing parity gates still pass from the relocated workspace** | Current repo policy requires Python, Node, and C++ parity gates to stay green; relocation cannot break the one-tier contract. | HIGH | The milestone should preserve `bun run parity:gate`, `python tools/python_api_parity/check_parity_gate.py --repo-root .`, and the CXX parity workflow without treating relocation drift as a feature change. |
| **Existing frontend and wrapper build/test workflows still work** | CLI/GUI/TUI and binding wrappers already depend on the Rust workspace. A root move is only acceptable if those workflows still build and test successfully. | HIGH | Must preserve `classic-cli/build_cli.ps1 -Test`, `classic-gui/build_gui.ps1 -Test`, Rust workspace tests, Node tests, and Python smoke/parity flows after path updates. |
| **Docs, skills, and agent context updated to the new layout** | `.planning/PROJECT.md` explicitly calls this out, and stale repo guidance will immediately misroute future work. | MEDIUM | Update planning docs, structure/testing/stack references, repo guidance, and any agent/skill material that still instructs contributors to work under `ClassicLib-rs/`. |
| **No functional or public-API drift introduced by the relocation** | This is a brownfield maintenance milestone. Callers expect location changes only, not behavior changes. | MEDIUM | Binding surfaces, crate responsibilities, runtime rules, and parity baselines should stay materially the same unless a path change forces a mechanical update. |

### Differentiators (Useful But Optional for This Milestone)

These are good quality improvements if they come cheaply after the relocation is stable, but they should not be allowed to expand the milestone into a redesign.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Path-regression tripwires for stale `ClassicLib-rs/` references** | Prevents future docs/scripts from silently reintroducing the old workspace root. | MEDIUM | Good follow-on tests for planning docs, CI files, build wrappers, and parity tooling. Valuable because the repo currently contains many hard-coded `ClassicLib-rs/` paths. |
| **Contributor-facing command simplification at repo root** | Makes the relocation visibly useful: `cargo test --workspace`, `cargo fmt --all`, and similar commands work naturally from the root. | LOW | Nice DX win, but only after the must-have workflows are already preserved. Do not let “nice root ergonomics” become a reason to rewrite unrelated scripts. |
| **Temporary compatibility shims or clear migration notes for moved paths** | Lowers churn for contributors while downstream docs/scripts catch up. | LOW | Acceptable only as a short bridge. Should be documented as transitional rather than becoming a second permanent routing layer. |
| **Verification matrix documenting old-path → new-path workflow equivalence** | Makes milestone closure easier and gives future maintainers a clear audit trail. | LOW | Especially useful for parity, CLI/GUI wrappers, Rust tests, Node bindings, Python bindings, and repo-level PowerShell tests. |

### Anti-Features (Tempting Scope Creep to Exclude)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Crate graph redesign (merge/split/rename crates while moving them)** | A root move feels like a good chance to “clean up structure.” | This turns a relocation milestone into an architecture milestone, multiplies path churn with semantic churn, and makes regressions hard to attribute. | Move crates as-is first. Plan any consolidation or renaming as a separate milestone. |
| **Binding API redesign or parity-contract reshaping** | Touching bindings and path tooling can tempt cleanup of API shape or contract schemas. | The current parity system is already an enforced one-tier contract. API redesign during relocation would create intentional drift unrelated to the move. | Keep public binding surfaces and parity semantics unchanged; only update paths and build references. |
| **Build/test workflow replacement instead of preservation** | Root relocation can make people want to replace repo-native wrappers with new commands. | The repo explicitly relies on PowerShell wrappers and parity tools. Swapping those out would break established contributor and CI behavior. | Preserve existing entrypoints; retarget them internally to the new workspace paths. |
| **Moving non-Rust product directories into the Rust workspace effort** | Once moving directories starts, it is tempting to reorganize `classic-cli/`, `classic-gui/`, docs, or data assets too. | The milestone goal is narrowly about crates currently under `ClassicLib-rs/`. Pulling other repo areas into the move increases risk without improving the workspace relocation outcome. | Limit filesystem moves to Rust workspace-owned crates and their supporting Rust-workspace artifacts. |
| **Dependency/version upgrades bundled with the relocation** | A move sometimes looks like a convenient time to “freshen everything.” | Upgrades create independent failure modes and can invalidate parity/build baselines for reasons unrelated to path changes. | Keep versions stable unless a move forces a mechanical path-related change. Track upgrades separately. |
| **Permanent dual-layout support for both root and `ClassicLib-rs/` workspace paths** | Seems safer during transition. | Long-term dual routing guarantees stale docs/scripts survive, increases maintenance cost, and obscures the new single source of truth. | Allow only short-lived migration helpers if needed, then remove them and standardize on the repo root. |

---

## Feature Dependencies

```
[Repo-root Cargo workspace entrypoint]
    └──required by──> [Rust test / fmt / clippy workflows at repo root]
    └──required by──> [Wrapper and binding path rewiring]

[All crates relocated with structure preserved]
    └──required by──> [Docs/skills/context updates]
    └──required by──> [Parity and wrapper verification]

[Path-reference rewiring]
    └──required by──> [Parity gates still pass]
    └──required by──> [CLI/GUI/TUI and binding workflows still work]

[Parity + wrapper verification]
    └──required by──> [Milestone closure evidence]

[Path-regression tripwires]
    └──enhances──> [Docs/skills/context updates]
    └──enhances──> [Workflow preservation]

[Crate graph redesign]
    ──conflicts──> [Relocation-only milestone]

[Binding API redesign]
    ──conflicts──> [No functional/API drift goal]
```

### Dependency Notes

- **Root workspace entrypoint comes first:** until the repo has a working root-level Cargo manifest and member paths, wrapper scripts and parity tooling cannot be rewired safely.
- **Filesystem relocation must stabilize before doc cleanup:** otherwise docs and agent files will be updated against paths that may still change.
- **Parity and workflow verification depend on path rewiring, not vice versa:** the parity gates and native wrappers are the proof that relocation preserved behavior.
- **Path-regression tests are additive, not foundational:** useful after the move is working, but not a substitute for actually fixing the paths.
- **Existing parity policy is a hard dependency:** this milestone must preserve the current one-tier Python/Node/C++ parity behavior rather than redefining it.

---

## MVP Definition

For this milestone, MVP means “the workspace now lives at the repo root and the existing repo behaviors still work.”

### Launch With (milestone must-have)

- [ ] Repo-root Cargo workspace is the canonical Rust entrypoint
- [ ] Every crate currently under `ClassicLib-rs/` is relocated to the repository root with internal crate structure preserved
- [ ] All workspace-member references and path-based tooling are updated to the new layout
- [ ] Rust tests/builds, parity gates, and native wrapper workflows still pass after relocation
- [ ] Docs, skills, and agent context files no longer route contributors to `ClassicLib-rs/` as the workspace root
- [ ] No intentional API, crate-boundary, or behavior changes are bundled into the move

### Add After Validation (good follow-up if cheap)

- [ ] Path-regression tripwires that fail on newly introduced `ClassicLib-rs/` workspace-root references
- [ ] Explicit migration notes / old-path-to-new-path contributor guide
- [ ] Verification matrix tying each preserved workflow to its new root-based path

### Future Consideration (separate milestone)

- [ ] Crate renames, merges, or broader directory taxonomy cleanup
- [ ] Binding API redesign or parity schema redesign
- [ ] Broader repo reorganization outside the relocated Rust workspace

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Repo-root Cargo workspace entrypoint | HIGH | MEDIUM | P1 |
| Relocate all crates while preserving internal layout | HIGH | HIGH | P1 |
| Path-reference rewiring across scripts/docs/CI/tooling | HIGH | HIGH | P1 |
| Preserve parity gates after relocation | HIGH | HIGH | P1 |
| Preserve CLI/GUI/TUI and binding workflows | HIGH | HIGH | P1 |
| Update docs, skills, and agent context | HIGH | MEDIUM | P1 |
| Prevent functional/API drift during move | HIGH | MEDIUM | P1 |
| Path-regression tripwires | MEDIUM | MEDIUM | P2 |
| Root-level contributor command simplification | MEDIUM | LOW | P2 |
| Temporary compatibility shims / migration notes | LOW | LOW | P2 |
| Crate graph redesign | LOW | HIGH | P3 / EXCLUDE |
| Binding API redesign | LOW | HIGH | P3 / EXCLUDE |
| Bundled dependency upgrades | LOW | MEDIUM | P3 / EXCLUDE |

**Priority key:**
- P1: Must be true for the relocation milestone to count as done
- P2: Helpful polish if it does not delay P1 outcomes
- P3 / EXCLUDE: Keep out of scope for this milestone

---

## Scope Framing for Requirements Writing

### In Scope

- Moving the Rust workspace root from `ClassicLib-rs/` to the repository root
- Relocating every crate currently under `ClassicLib-rs/` without changing each crate's internal directory structure
- Updating path-dependent scripts, manifests, CMake/Corrosion consumers, parity tooling, tests, docs, and agent guidance
- Re-validating existing parity, wrapper, and native frontend workflows against the new layout

### Explicitly Out of Scope

- New user-facing product functionality
- Crate responsibility changes, graph redesign, or binding surface redesign
- Non-relocation cleanup that is not required to make the new root layout work
- Broad repo reorganization outside the Rust workspace move
- Opportunistic dependency upgrades unrelated to relocation blockers

---

## Sources

- `.planning/PROJECT.md` — active milestone goal, target features, constraints, and out-of-scope boundaries (HIGH)
- `.planning/codebase/STRUCTURE.md` — current Rust workspace layout and path-heavy consumers that relocation will affect (HIGH)
- `.planning/codebase/TESTING.md` — current validation commands and workflow entrypoints that must continue working after relocation (HIGH)
- `AGENTS.md` — repo rules requiring thin non-Rust layers, preserved Rust-core ownership, and wrapper/test command conventions (HIGH)

---

*Feature research for: v9.1.0-root move crates to project root*
*Researched: 2026-04-11*

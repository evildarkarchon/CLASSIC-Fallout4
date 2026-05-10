# Phase 6: Repo-Root Workspace Cutover - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-11T23:52:58.1211586-07:00
**Phase:** 06-repo-root-workspace-cutover
**Areas discussed:** Workspace files, Old root behavior, Root command set, Phase-6 proof

---

## Workspace files

### Which workspace-owned files should move with the repo-root `Cargo.toml` during Phase 6?

| Option | Description | Selected |
|--------|-------------|----------|
| Full set (Recommended) | Move `Cargo.toml`, `Cargo.lock`, `.cargo/config.toml`, `validate_stubs.py`, `criterion.toml`, `benchmark-config.yaml`, and `benches/` | ✓ |
| Core Cargo only | Move `Cargo.toml`, `Cargo.lock`, and `.cargo/config.toml` now; leave stub and benchmark helpers for later | |
| Manifest only | Move only `Cargo.toml` now and keep other workspace-owned files under `ClassicLib-rs` temporarily | |

**User's choice:** Full set (Recommended)
**Notes:** The root cutover should move the whole workspace-owned support set, not just the manifest.

### How should `validate_stubs.py` behave after that move?

| Option | Description | Selected |
|--------|-------------|----------|
| Root tool (Recommended) | Move it to repo root and treat repo root as the Rust workspace root for stub validation | ✓ |
| Wrapper shim | Move it later, or leave a thin compatibility wrapper under `ClassicLib-rs` temporarily | |
| Agent decide | No strong preference beyond keeping stub validation working | |

**User's choice:** Root tool (Recommended)
**Notes:** Stub validation should become repo-root-native in the same phase.

### What do you want to do with the benchmarking/profiling workspace assets in Phase 6 (`criterion.toml`, `benchmark-config.yaml`, `benches/`)?

| Option | Description | Selected |
|--------|-------------|----------|
| Move now (Recommended) | Treat them as workspace-owned and move them with the root cutover | ✓ |
| Defer to later | Leave them under `ClassicLib-rs` until the later validation or docs phases | |
| Agent decide | No strong preference as long as they do not block the cutover | |

**User's choice:** Move now (Recommended)
**Notes:** Benchmark/profiling assets are part of the Phase 6 workspace-owned move set.

### When `.cargo/config.toml` and the workspace profiles move to repo root, how closely should Phase 6 preserve the current Cargo behavior?

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve exactly (Recommended) | Keep the existing aliases and workspace profile behavior unchanged; only the root path changes | ✓ |
| Light cleanup | Allow small cleanup if it does not change contributor-facing Cargo behavior | |
| Agent decide | No strong preference beyond keeping the cutover stable | |

**User's choice:** Preserve exactly (Recommended)
**Notes:** Current alias/profile behavior is part of the repo-root cutover contract.

---

## Old root behavior

### Once repo root becomes canonical, what should happen to `ClassicLib-rs/Cargo.toml`?

| Option | Description | Selected |
|--------|-------------|----------|
| Retire it (Recommended) | Remove it as a live workspace manifest in Phase 6 | ✓ |
| Tombstone shim | Leave a short-lived non-authoritative file or note there to signal the new root | |
| Keep it live | Keep using it as a compatibility workspace until a later phase | |

**User's choice:** Retire it (Recommended)
**Notes:** The old workspace root should stop being authoritative in Phase 6.

### If someone runs Cargo from inside `ClassicLib-rs/` or one of its subdirectories after the cutover, what behavior do you want?

| Option | Description | Selected |
|--------|-------------|----------|
| Parent discovery (Recommended) | Let Cargo naturally discover the repo-root workspace from parent directories | |
| Hard fail old path | Treat the `ClassicLib-rs` subtree as a retired path and make old-root usage fail loudly | ✓ |
| No strong pref | As long as there is only one real workspace root, the exact old-path behavior is flexible | |

**User's choice:** Hard fail old path
**Notes:** This was the initial preference before the clarification question below refined the exact Phase 6 posture.

### How strict should Phase 6 be about active callers that still point at `ClassicLib-rs/Cargo.toml`?

| Option | Description | Selected |
|--------|-------------|----------|
| Zero active callers | Any live script or workflow still using the old manifest path should be fixed before Phase 6 closes | ✓ |
| Cargo-only strict | Retire the old manifest for direct Cargo use now; allow wrapper/CI rewiring in later phases | |
| Agent decide | No strong preference beyond ending with one authoritative root | |

**User's choice:** Zero active callers
**Notes:** Later clarification narrowed this to the cargo-first Phase 6 surface rather than forcing all wrapper/CMake rewires into this phase.

### When the old path fails, how do you want that failure to look?

| Option | Description | Selected |
|--------|-------------|----------|
| File gone (Recommended) | Remove the old manifest entirely so stale callers fail immediately on a missing path | ✓ |
| Explicit tombstone | Leave a non-authoritative note or stub there that clearly says the workspace moved | |
| Agent decide | No strong preference as long as old-root usage does not keep working | |

**User's choice:** File gone (Recommended)
**Notes:** The old manifest should be removed, not kept as a live or compatibility workspace.

### Clarification: Which cutover posture matters most for Phase 6?

| Option | Description | Selected |
|--------|-------------|----------|
| Clean root, cargo-first (Recommended) | Delete the old manifest, make repo-root Cargo and Rust CI canonical now, accept that subdir cargo may still discover the repo root, and leave wrapper/CMake rewires for later phases | ✓ |
| Hard block everything | Phase 6 must make any `ClassicLib-rs` cargo usage fail and eliminate all old-manifest callers now, even if that pulls wrapper/CMake work forward | |
| Clean root + blocker | Keep one canonical root, but leave a non-authoritative blocker/tombstone in `ClassicLib-rs` so old-path cargo fails immediately | |

**User's choice:** Clean root, cargo-first (Recommended)
**Notes:** This resolved the tension between “file gone”, “hard fail old path”, and the roadmap phase boundaries. Phase 6 stays cargo-first instead of adding blocker machinery or pulling wrapper rewires forward.

---

## Root command set

### Which repo-root Cargo commands should Phase 6 explicitly guarantee as first-class workflows?

| Option | Description | Selected |
|--------|-------------|----------|
| Fmt+clippy+build+test (Recommended) | Make all four first-class from repo root because they already anchor the live Rust CI/workflow surface | ✓ |
| Fmt+clippy+test only | Limit the explicit contract to the commands already named in `ROOT-02` | |
| Broader dev set | Also treat metadata/package-filtered commands as explicit Phase 6 contract items | |

**User's choice:** Fmt+clippy+build+test (Recommended)
**Notes:** The explicit root contract includes build alongside format, lint, and test.

### Should package-filtered repo-root commands also be part of the Phase 6 contract, such as `cargo build -p classic-scanlog-core`?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, include them (Recommended) | Phase 6 should preserve normal per-crate workflows from repo root, not just whole-workspace commands | ✓ |
| Workspace-level only | Only whole-workspace root commands need to be guaranteed in this phase | |
| Agent decide | No strong preference as long as normal root workflows stay practical | |

**User's choice:** Yes, include them (Recommended)
**Notes:** Per-crate repo-root Cargo usage is part of the convenience contract.

### After the cutover, what should be the preferred invocation style in active workflows?

| Option | Description | Selected |
|--------|-------------|----------|
| Plain cargo (Recommended) | Use plain cargo commands from repo root by default; no `ClassicLib-rs` manifest path in active workflows | ✓ |
| Root manifest path | Allow or prefer `--manifest-path Cargo.toml` even after the root cutover | |
| Either is fine | No strong preference as long as the old `ClassicLib-rs` manifest path disappears | |

**User's choice:** Plain cargo (Recommended)
**Notes:** Repo-root `cargo ...` becomes the normal style for active workflows.

### Should Phase 6 preserve the current Cargo alias/profile developer flows at repo root too, like the profiling aliases from `.cargo/config.toml`?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, preserve them (Recommended) | Root cutover should keep existing alias/profile-based developer commands working from repo root | ✓ |
| Not required now | Only build/test/lint commands matter in Phase 6; profiling aliases can catch up later | |
| Agent decide | No strong preference as long as day-to-day Cargo use improves | |

**User's choice:** Yes, preserve them (Recommended)
**Notes:** Profiling aliases stay part of the repo-root command contract.

---

## Phase-6 proof

### What should Phase 6 require before we call the root cutover done?

| Option | Description | Selected |
|--------|-------------|----------|
| Root cargo + Rust CI (Recommended) | Prove repo-root cargo commands locally and update cargo-based Rust CI/workflows that still point at the old manifest | ✓ |
| Local root cargo only | Only local repo-root cargo proof is required now; CI file rewrites can wait for later phases | |
| Broader proof | Also fold wrapper/rebuild-script proof into Phase 6 instead of leaving that mostly to later phases | |

**User's choice:** Root cargo + Rust CI (Recommended)
**Notes:** Phase 6 proof includes the cargo-based Rust automation surface, not just local commands.

### Should Phase 6 explicitly verify Cargo's view of the workspace root, for example with `cargo metadata` or equivalent root-detection checks?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, require it (Recommended) | Use Cargo's own workspace-root reporting to prove there is one canonical root | ✓ |
| Commands only | If the expected cargo commands work, that is enough proof | |
| Agent decide | No strong preference as long as the proof is convincing | |

**User's choice:** Yes, require it (Recommended)
**Notes:** The proof should include an explicit Cargo root-detection check.

### Should Phase 6 require at least one clean validation pass that does not rely on stale `ClassicLib-rs/target` outputs?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, clean pass (Recommended) | Force at least one proof run that is not masked by the legacy target directory | ✓ |
| No, existing outputs okay | Accept proof that reuses existing build outputs if the commands succeed | |
| Agent decide | No strong preference as long as old-target drift is not hidden | |

**User's choice:** Yes, clean pass (Recommended)
**Notes:** The cutover must be proven without stale `ClassicLib-rs/target` help.

### Do you want Phase 6 proof to include an explicit audit that active cargo-based workflows no longer mention `ClassicLib-rs/Cargo.toml`?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, audit it (Recommended) | Include a deliberate old-manifest-path check for cargo-based scripts/workflows in the Phase 6 proof | ✓ |
| No, command proof only | If the root commands and Rust CI pass, explicit old-path auditing is unnecessary | |
| Agent decide | No strong preference as long as stale cargo callers do not slip through | |

**User's choice:** Yes, audit it (Recommended)
**Notes:** The proof should explicitly check for stale cargo-based old-manifest references.

---

## the agent's Discretion

- Exact command choices for the Cargo root-detection proof (`cargo metadata`, `cargo locate-project --workspace`, or both)
- Exact audit commands used to detect stale cargo-based old-manifest references
- Exact clean-pass sequencing, as long as stale `ClassicLib-rs/target` outputs cannot mask the result

## Deferred Ideas

None.

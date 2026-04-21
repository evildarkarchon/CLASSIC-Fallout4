# Phase 8: Wrapper and Parity Rewire - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-12T00:00:00Z
**Phase:** 08-wrapper-and-parity-rewire
**Areas discussed:** Wrapper entrypoints, Legacy path support, Parity artifact cutover, Native flow proof depth

---

## Wrapper entrypoints

### Which entrypoints should Phase 8 treat as first-class workflows that must keep working after the rewire?

| Option | Description | Selected |
|--------|-------------|----------|
| All current entrypoints | Preserve `rebuild_rust.ps1`, `rebuild_node.ps1`, `build_cli.ps1`, `build_gui.ps1`, package-local Node scripts, and the TUI cargo flow. | ✓ |
| Canonical set only | Keep `rebuild_rust.ps1`, `build_cli.ps1`, `build_gui.ps1`, package-local Node scripts, and the TUI flow first-class; treat redundant wrappers as secondary. | |
| Minimal operational set | Focus only on the wrappers and gates needed for milestone proof, leaving redundant entrypoints for later cleanup. | |

**User's choice:** All current entrypoints.
**Notes:** The user wants migration continuity across the full existing wrapper surface, not just the minimum proof set.

### How should `rebuild_node.ps1` behave within that full entrypoint set?

| Option | Description | Selected |
|--------|-------------|----------|
| Thin alias | Keep the command, but make it delegate to the canonical Node rebuild flow so there is one implementation to maintain. | ✓ |
| Independent wrapper | Keep `rebuild_node.ps1` as its own maintained implementation. | |
| Package-local only | Keep the file only as a lightweight launcher into `node-bindings/classic-node`, with package scripts doing the real work. | |

**User's choice:** Thin alias.
**Notes:** `rebuild_node.ps1` remains supported, but duplicated implementation is not desired.

### When commands overlap, what should be the canonical command style underneath: repo-root wrappers, package-local commands, or co-equal support for both?

| Option | Description | Selected |
|--------|-------------|----------|
| Repo-root canonical | Keep package-local commands working, but make repo-root wrappers the primary user-facing path. | ✓ |
| Package-local canonical | Bindings are primarily maintained from their own directories; repo-root wrappers can stay as convenience entrypoints. | |
| Co-equal support | Treat repo-root and package-local entrypoints as equally canonical. | |

**User's choice:** Repo-root canonical.
**Notes:** This matches the Phase 6/7 repo-root direction while preserving package-local workflows as supported secondary paths.

### For the TUI specifically, what should count as the supported entrypoint after Phase 8?

| Option | Description | Selected |
|--------|-------------|----------|
| Repo-root cargo command | Treat direct repo-root Cargo invocation for `classic-tui` as the supported TUI entrypoint. | ✓ |
| Add a TUI wrapper script | Create a dedicated wrapper so the TUI matches the CLI/GUI script-driven experience. | |
| Workspace build only | It only needs to compile as part of broader workspace flows. | |

**User's choice:** Repo-root cargo command.
**Notes:** The user does not want a new TUI wrapper added just for parity with other surfaces.

---

## Legacy path support

### At a policy level, should Phase 8 still accept legacy `ClassicLib-rs` paths anywhere in active wrapper/parity workflows?

| Option | Description | Selected |
|--------|-------------|----------|
| No active legacy support | Phase 8 finishes the operational cutover: active wrappers and gates are root-only. | ✓ |
| One narrow exception | Allow one explicitly temporary legacy-path exception while making everything else root-only. | |
| Broad transition support | Keep several active commands accepting old paths for now. | |

**User's choice:** No active legacy support.
**Notes:** The user wants Phase 8 to complete the operational cutover instead of preserving a transition shim surface.

### When a user or script still passes an old `ClassicLib-rs/...` path, how should the tooling respond?

| Option | Description | Selected |
|--------|-------------|----------|
| Fail fast with fix-up hint | Exit clearly and tell the user the new repo-root-relative path to use. | ✓ |
| Warn then continue | Proceed if the tool can infer the intended new path, but emit a deprecation warning. | |
| Silent auto-fix | Normalize the old path automatically with no warning. | |

**User's choice:** Fail fast with fix-up hint.
**Notes:** The rejection path should still be helpful and self-correcting.

### How aggressive should Phase 8 be about steering users away from old paths in help text and wrapper output?

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit migration hints | Error/help text should show the replacement repo-root path or command. | ✓ |
| Short root-only messaging | Say the old path is unsupported, but keep the messaging brief without replacement examples. | |
| Minimal messaging | Let the failure stand on its own and rely on docs or later phases to teach the new path. | |

**User's choice:** Explicit migration hints.
**Notes:** The user wants the operational cutover to be self-teaching.

### Should Phase 8 add regression checks that active wrappers/gates reject legacy paths, or only prove the new root-based commands work?

| Option | Description | Selected |
|--------|-------------|----------|
| Check both success and rejection | Prove the root-based flow works and also lock in that old-path inputs now fail with the right guidance. | ✓ |
| Check new success only | Only validate the new root-based commands. | |
| Document only | Describe the rule, but do not add test coverage for it yet. | |

**User's choice:** Check both success and rejection.
**Notes:** Legacy-path rejection is part of the Phase 8 contract, not just documentation.

---

## Parity artifact cutover

### Should Phase 8 fully retarget active parity and freshness tooling defaults to the new root-level binding paths now?

| Option | Description | Selected |
|--------|-------------|----------|
| Full cutover now | Move Python, Node, CXX, and d.ts freshness defaults to the new root-level binding paths in this phase. | ✓ |
| Partial cutover | Retarget only the minimum needed for the gates to run. | |
| Override-only | Keep old defaults in code, but rely on command-line overrides or wrapper scripts. | |

**User's choice:** Full cutover now.
**Notes:** Phase 8 should fix the actual tooling defaults, not just paper over them at invocation time.

### If generated parity reports or freshness artifacts still embed old `ClassicLib-rs` paths, what should Phase 8 do with the checked-in artifacts?

| Option | Description | Selected |
|--------|-------------|----------|
| Refresh path-bearing artifacts now | Regenerate any checked-in reports whose content is wrong because of the move, while keeping parity contracts/API expectations unchanged. | ✓ |
| Keep baselines frozen | Only fix ephemeral outputs and gate logic; do not touch checked-in generated artifacts unless semantic parity changes. | |
| Defer artifact refresh | Leave path-bearing checked-in artifacts for Phase 9 or Phase 10. | |

**User's choice:** Refresh path-bearing artifacts now.
**Notes:** Path-bearing stale artifacts are part of the migration drift Phase 8 is meant to close.

### Where should the non-baseline parity outputs live after the cutover?

| Option | Description | Selected |
|--------|-------------|----------|
| Per-binding local dirs | Keep ephemeral outputs next to each binding at the new root-level locations. | ✓ |
| Centralized docs dir | Move generated gate outputs under `docs/implementation/...`. | |
| Temp-only outputs | Treat these as disposable outputs outside the repo tree. | |

**User's choice:** Per-binding local dirs.
**Notes:** The user wants to preserve the current artifact layout pattern while removing the old `ClassicLib-rs` prefix.

### How strict should Phase 8 be if a parity or freshness run still tries to write into a legacy `ClassicLib-rs/...` location?

| Option | Description | Selected |
|--------|-------------|----------|
| Hard failure | Treat any write/read to the legacy location as a regression and fail immediately. | ✓ |
| Warn then continue | Allow the run to continue if it can recover, but emit a visible warning. | |
| Ignore if gate passes | Only care about parity results, not where the tool read or wrote intermediate artifacts. | |

**User's choice:** Hard failure.
**Notes:** Legacy artifact I/O should be part of the enforced regression boundary.

---

## Native flow proof depth

### What should be the default proof bar for the native surfaces in Phase 8 overall?

| Option | Description | Selected |
|--------|-------------|----------|
| Build plus smoke-run | Each surface should build and pass a small operational proof that the migrated entrypoint actually starts or executes meaningfully. | ✓ |
| Build plus full tests | Treat full available test suites as the default bar for every native surface in this phase. | |
| Build only | If the wrappers and gates wire up, that is enough. | |

**User's choice:** Build plus smoke-run.
**Notes:** The user wants more than compilation, but not automatic promotion to full release-style validation.

### For `classic-cli` and `classic-gui`, should Phase 8 treat their existing `-Test` flows as part of that proof or keep them lighter?

| Option | Description | Selected |
|--------|-------------|----------|
| Include existing test flows | Use `build_cli.ps1 -Test` and `build_gui.ps1 -Test` as part of the Phase 8 proof. | ✓ |
| Smoke-run without tests | Build and launch/check the wrappers, but leave the scripted test flows for later phases. | |
| CLI tests yes, GUI lighter | Use full CLI test coverage now, but keep GUI proof to build/start-level checks. | |

**User's choice:** Include existing test flows.
**Notes:** Existing native `-Test` entrypoints are part of the supported surface and should be honored in this phase.

### For the TUI, what should count as the smoke-run proof after the path rewire?

| Option | Description | Selected |
|--------|-------------|----------|
| Repo-root run check | Use a direct repo-root Cargo invocation that actually runs the TUI entrypoint in a lightweight mode such as `--help` or `--version`. | ✓ |
| Build-only TUI proof | Let the TUI piggyback on workspace or package build success without a separate runtime check. | |
| Deeper TUI scenario | Require a more involved interactive or scenario-based TUI proof in this phase. | |

**User's choice:** Repo-root run check.
**Notes:** The TUI should prove runtime entrypoint health without forcing an interactive scenario suite into Phase 8.

### Should install/package flows for the native apps be part of Phase 8 closure, or left for later phases unless they break while doing the required proof?

| Option | Description | Selected |
|--------|-------------|----------|
| Defer unless needed | Focus Phase 8 on build, tests, parity, and smoke-run proof. Only touch install/package if a required native flow depends on it. | ✓ |
| Include install/package now | Make deployment-style install/package output part of the mandatory Phase 8 closure surface. | |
| Document only | Mention install/package as a future concern, but do not let it shape Phase 8 planning. | |

**User's choice:** Defer unless needed.
**Notes:** Packaging is not the default closure bar for this phase.

---

## the agent's Discretion

- Exact alias implementation for `rebuild_node.ps1`.
- Exact fix-up hint wording for rejected old paths.
- Exact TUI smoke flag choice (`--help` vs `--version`).
- Exact regression-test file placement and naming.

## Deferred Ideas

None — discussion stayed within phase scope.

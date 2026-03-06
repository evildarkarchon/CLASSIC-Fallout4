## Context

The maintained Node bindings already expose enough low-level capability to analyze logs, inspect runtime state, walk directories, load YAML-derived configuration, and write files. What they do not provide today is a packaged CLI that proves those exports can drive the full crash-log workflow the way the official `classic-cli` does.

The native C++ CLI currently serves as the clearest reference for the desired flow:
- resolve the `CLASSIC Data` root
- set game context and derive YAML-backed scan settings
- resolve the XSE/docs folder used for crash-log discovery
- search the managed `Crash Logs` location plus any custom scan directory
- process logs in batches
- write `-AUTOSCAN.md` reports next to the source logs
- print a summary and return stable exit codes (`0` success or no logs, `1` scan errors, `2` fatal startup/config failure)

If the Node CLI only wraps diagnostics or test cases, it will not be a true proof that the bindings can stand in for the native frontend. This change therefore rescopes the Node CLI as a real scanner first and a verification surface second.

Constraints:
- Keep the CLI inside `ClassicLib-rs/node-bindings/classic-node`; do not create a separate product outside the maintained Node package.
- Reuse the shared Tokio runtime through the existing bindings and avoid introducing an alternate runtime model.
- Stay as close as practical to `classic-cli/` behavior for scan flow, report creation, and exit semantics.
- Prefer deterministic local workflows for tests even if the runtime CLI remains generally useful outside the test environment.
- If the current Node export surface is missing a small piece needed for CLI parity, add a targeted binding helper instead of duplicating Rust behavior in fragile JavaScript glue.

## Goals / Non-Goals

**Goals:**
- Add a functional Node CLI that can scan crash logs end to end through the maintained Node bindings.
- Mirror the highest-value `classic-cli` options and runtime behavior closely enough that the Node CLI is a credible alternative frontend and a true binding test.
- Reuse the CLI flow in automated verification so contributors exercise the same path real Node users would invoke.
- Keep diagnostics and machine-readable output available for debugging and automation.

**Non-Goals:**
- Replacing the native C++ CLI as the primary shipped frontend for this repository.
- Achieving byte-for-byte parity with every native progress-rendering detail on the first implementation pass.
- Adding network-dependent update checks or unrelated app-management workflows to the default scan path.
- Redesigning the broader parity contract system beyond the updates required for any new public Node exports.

## Decisions

1. **Treat the Node CLI as a functional scanner, not a test-only shell**
   - Decision: The default CLI invocation should perform a real scan workflow. Diagnostics and self-check commands can exist, but they are secondary to the main scan path.
   - Rationale: The user goal is to prove the bindings can drive the same workflow as the official CLI, not just prove they load.
   - Alternatives considered:
     - Keep the CLI as a smoke-test harness only: rejected because it does not validate end-to-end scanning behavior.
     - Shell out from Node to the C++ CLI: rejected because that tests process wiring, not the Node bindings themselves.

2. **Mirror the native CLI scan pipeline in Node with bindings handling the heavy work**
   - Decision: The Node CLI should follow the same broad sequence as `classic-cli`: version/banner handling, path/data discovery, game-context setup, log discovery, bounded batch scanning, report writing, summary output, and stable exit codes.
   - Rationale: Reusing the native CLI's behavioral model keeps the Node CLI useful on its own and makes it a meaningful parity check for the binding layer.
   - Alternatives considered:
     - Expose a totally different Node-only command model: rejected because it weakens comparability with the existing CLI.
     - Implement only single-log scan commands: rejected because the native workflow is fundamentally batch-oriented.

3. **Align the primary flags with `classic-cli` and reserve only a few Node-specific additions**
   - Decision: Support the core native scan flags such as `--game`, `--game-version`, `--fcx-mode`, `--show-fid-values`, `--simplify-logs`, `--scan-path`, `--max-concurrent`, and `--version`, while keeping optional Node-specific helpers like `doctor` or `--json` narrowly scoped.
   - Rationale: Shared flags reduce cognitive overhead and make behavior easier to compare across frontends.
   - Alternatives considered:
     - Use an entirely different subcommand-heavy interface: rejected because the scan path should feel familiar to existing CLASSIC CLI users.
     - Omit concurrency or scan-path controls: rejected because they are part of the core scan workflow today.

4. **Add narrow CLI-oriented binding helpers where JavaScript glue would otherwise drift from Rust behavior**
   - Decision: If the current Node exports are insufficient for native-CLI parity, extend the binding surface with targeted helpers such as bounded batch-scan controls, log-discovery helpers, or report-path/report-writing helpers rather than reimplementing those rules ad hoc in JavaScript.
   - Rationale: Some native CLI behavior is policy, not just plumbing. Keeping that policy close to the Rust/core layer reduces drift and makes the CLI a better test of maintained APIs.
   - Alternatives considered:
     - Build everything with existing exports only: rejected if that would force poor parity for `--max-concurrent`, log discovery, or report naming.
     - Recreate all native helper logic in JavaScript: rejected because it is harder to keep aligned with the Rust and C++ frontends.

5. **Preserve native-style exit semantics and report generation**
   - Decision: The Node CLI should return `0` when scanning succeeds or no logs are found, `1` when one or more log scans fail but the run completes, and `2` for fatal startup/configuration failures. Successful scans should write `-AUTOSCAN.md` reports adjacent to each processed crash log.
   - Rationale: Matching native exit semantics makes automation and troubleshooting consistent across frontends.
   - Alternatives considered:
     - Collapse all failures into one generic non-zero code: rejected because it loses important operational meaning.
     - Print results only to stdout without writing reports: rejected because report generation is part of the real workflow being validated.

6. **Verify the Node CLI with fixture-driven integration tests, not only unit tests**
   - Decision: Add tests that execute the CLI against representative fixture logs and validate report creation, summaries, and exit codes, while keeping smaller unit tests for argument parsing and helper behavior.
   - Rationale: A functional CLI needs process-level verification to prove the packaged command works end to end.
   - Alternatives considered:
     - Unit-test argument parsing only: rejected because it does not exercise the real scan path.
     - Rely solely on manual verification: rejected because the CLI is meant to strengthen binding confidence automatically.

## Risks / Trade-offs

- **[Risk] The Node CLI drifts from `classic-cli` behavior over time** -> **Mitigation:** Treat `classic-cli/` as the reference for scan flow and flags, and add fixture-based regression tests around exit codes, report generation, and no-log behavior.
- **[Risk] New CLI-oriented exports expand the maintained Node public surface** -> **Mitigation:** Keep any new exports tightly scoped, regenerate `index.d.ts`, and update Node parity artifacts in the same implementation wave.
- **[Risk] Path discovery behaves differently across development and packaged layouts** -> **Mitigation:** Centralize data-root and docs/XSE resolution logic, and test both explicit override paths and convention-based discovery.
- **[Risk] Progress and summary rendering become noisy or platform-fragile** -> **Mitigation:** Make the first implementation prioritize correctness and stable summaries; richer terminal rendering can remain lightweight or optional.

## Migration Plan

1. Inventory the `classic-cli` scan path and identify the Node binding gaps that prevent feature parity.
2. Add or refine any targeted Node exports needed for bounded batch scanning, log discovery, or report generation.
3. Implement the packaged Node CLI entrypoint and wire it into `package.json` scripts/bin entries.
4. Add integration tests that execute the CLI against local fixture logs and verify reports, summaries, and exit codes.
5. Refresh typings, Node parity artifacts, and contributor docs to reflect the new public CLI and any supporting exports.

Rollback strategy:
- Remove the packaged CLI entrypoint and scripts while preserving the underlying binding improvements that remain useful to tests or downstream Node consumers.
- If a new helper export proves too unstable, keep the Node CLI on the simpler supported subset and defer parity with that native behavior until a later change.

## Open Questions

- Should the first implementation include the same progress-display behavior as `classic-cli`, or is a simpler summary-first output acceptable as long as scan semantics and exit codes match?
- Which native-CLI behaviors warrant dedicated Rust-side helpers immediately versus a thin JavaScript implementation built on the current Node exports?

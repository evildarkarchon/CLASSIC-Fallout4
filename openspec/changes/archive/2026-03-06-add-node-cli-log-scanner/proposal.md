## Why

A smoke-test-only CLI would prove that the addon loads, but it would not prove that the Node bindings can drive the real crash-log workflow end to end. We need a fully functional Node CLI that can discover logs, run scans, and write reports through the binding surface so contributors can validate the Node package against the same workflow the official C++ CLI performs.

## What Changes

- Add a functional Node CLI in `ClassicLib-rs/node-bindings/classic-node` that can scan crash logs end to end instead of only running smoke checks.
- Mirror the official `classic-cli` core workflow in Node: resolve data/config paths, discover logs, build analysis config, process batches, write `AUTOSCAN` reports, print summaries, and return stable exit codes.
- Expose the core scan flags expected from the native CLI, including game selection, game-version mode, scan path override, FCX mode, FormID display, log simplification, and concurrency control.
- Keep diagnostic and self-check workflows available so the CLI remains a strong binding-verification path in addition to being useful on its own.
- Update package scripts, docs, typings, and runtime verification to cover the new CLI behavior and any binding helpers needed to support it.

## Capabilities

### New Capabilities
- `node-binding-cli`: Defines a functional Node CLI that scans crash logs through the maintained Node bindings and mirrors the official C++ CLI's core workflow.

### Modified Capabilities
- None.

## Impact

- Affected code: `ClassicLib-rs/node-bindings/classic-node/` CLI entrypoints, shared runner utilities, package scripts, docs, and any Node binding exports added to support the CLI flow.
- APIs/interfaces: Node package CLI commands and flags, scan/report output behavior, exit-code semantics, and any CLI-oriented binding helper APIs.
- Tooling/tests: Node runtime suites, CLI integration coverage, and Node parity artifacts if public binding exports change.
- Reference systems: `classic-cli/` remains the behavioral reference for scan flow, report generation, and exit semantics that the Node CLI should match closely.

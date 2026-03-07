## 1. Native CLI Parity Mapping

- [x] 1.1 Inventory the current `classic-cli/` scan workflow, flags, exit semantics, and report-generation behavior that the Node CLI must mirror.
- [x] 1.2 Identify the gaps in `ClassicLib-rs/node-bindings/classic-node` for full CLI parity and add any targeted binding helpers needed for bounded batch scanning, log discovery, or report creation.
- [x] 1.3 Refresh `index.d.ts` and the required Node parity artifacts if the CLI work introduces or changes public Node exports.

## 2. Functional Node CLI Implementation

- [x] 2.1 Add the packaged Node CLI entrypoint and argument parsing so the default invocation performs a real scan and supports the core native-style flags (`--game`, `--game-version`, `--scan-path`, `--fcx-mode`, `--show-fid-values`, `--simplify-logs`, `--max-concurrent`, `--version`).
- [x] 2.2 Implement the end-to-end scan pipeline in Node: resolve data/config paths, derive docs/XSE scan locations, discover crash logs, process them through the bindings, write `-AUTOSCAN.md` reports, and print a native-style summary.
- [x] 2.3 Add diagnostic or machine-readable output support needed for binding verification without compromising the main scan workflow or native-style exit semantics.

## 3. Verification And Workflow Adoption

- [x] 3.1 Add fixture-driven CLI tests that cover version output, no-log behavior, successful scan/report generation, and fatal-versus-nonfatal exit codes.
- [x] 3.2 Update existing Node runtime verification to exercise the functional CLI path or shared helpers so the CLI becomes part of binding confidence, not a side utility.
- [x] 3.3 Wire the CLI into `ClassicLib-rs/node-bindings/classic-node/package.json`, update contributor-facing docs that currently assume no Node CLI exists, and verify the intended local build/test/parity commands pass.

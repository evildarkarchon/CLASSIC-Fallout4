# CXX Parity Gate

The CXX parity gate is a Python source-parsing tool that enumerates the CXX
bridge surface exposed by
[`ClassicLib-rs/cpp-bindings/classic-cpp-bridge`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/)
and compares it against a committed baseline. It runs on cross-platform Python
alone — no Rust build, no MSVC, no `cxx-build` invocation.

The gate is the acceptance criterion for any change that adds, removes, or
modifies a `#[cxx::bridge]` item. Phase 2 of the `v9.1.0-bindings` milestone
uses this gate to accept widened bridge entry points as they land.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Overview

- **Purpose:** detect drift between the committed CXX bridge contract and the
  current bridge source tree.
- **Scope:** every file listed in
  `classic-cpp-bridge/build.rs::cxx_build::bridges([...])` (14 files as of this
  milestone).
- **Single source of truth for the file list:**
  [`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs).
  The gate parses it dynamically — there is no hardcoded list to keep in sync.
- **Single source of truth for the contract:**
  [`docs/implementation/cxx_api_parity/baseline/parity_contract.json`](../implementation/cxx_api_parity/baseline/parity_contract.json).
- **Exit codes:** `0` = pass (no drift, no stale artifacts); `1` = drift
  detected, stale committed artifacts, or baseline file missing.

The gate is intentionally conservative: it compares only semantic contract
fields (`rustSymbol`, `kind`, `bridgeModule`, `blockOrigin`, `signature`,
`fields`, `variants`). `sourceFile` is NOT part of the comparison, so moving a
function across files inside the same `bridgeModule` is not reported as drift.

---

## Local Run

Run the gate from the repo root:

```bash
python tools/cxx_api_parity/check_parity_gate.py --repo-root .
```

A clean run prints `CXX parity gate passed.` and exits `0`. Drift is reported
to stderr with a summary of missing, added, and signature-mismatched rows.

The gate is **source-only** — it does not invoke Cargo, `cxx-build`, or MSVC.
All you need is Python 3.12+. The Python parser pulls from the repo's existing
bindings venv in CI; locally, any Python 3.12+ interpreter works because the
script depends only on the standard library (`re`, `json`, `hashlib`,
`argparse`, `shutil`).

To run the gate's own integration test suite (22 tests covering the parser,
the gate, and drift detection):

```bash
ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/ -q
```

---

## Refresh Workflow

After an intentional bridge change — adding, removing, or modifying a
`#[cxx::bridge]` item — refresh the committed baseline in the same commit that
touches the bridge source:

```bash
python tools/cxx_api_parity/check_parity_gate.py --repo-root . --update-baseline
git add docs/implementation/cxx_api_parity/baseline/
git commit -m "Docs: refresh CXX parity baseline"
```

`--update-baseline` copies the fresh generated artifacts into the committed
baseline directory and re-runs the comparison. A follow-up plain run should
then exit `0`.

**Never use `--update-baseline` to mask unintentional drift.** If you did not
mean to add or remove a bridge item, fix the source, not the baseline. The
diff report at
[`docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md`](../implementation/cxx_api_parity/baseline/cxx_diff_report.md)
is the human-readable summary of what changed — inspect it before staging
the refresh.

---

## Bootstrap From Scratch

If the committed baseline is ever missing or corrupted, regenerate it from
source with the bootstrap entry point:

```bash
python tools/cxx_api_parity/generate_baseline.py --repo-root . --write-baseline
```

This rewrites every file under `docs/implementation/cxx_api_parity/baseline/`
using a fresh parse of the bridge source tree. The bootstrap writes a
placeholder `cxx_gate_report.md` that the next `check_parity_gate.py` run
would flag as stale, so follow the bootstrap with exactly one reconciliation
run:

```bash
python tools/cxx_api_parity/check_parity_gate.py --repo-root . --update-baseline
```

After that, every subsequent plain gate run exits `0`. Review the diff before
committing.

---

## Contract Row Schema

Each row in `parity_contract.json` has these fields:

| Field | Kinds | Meaning |
|-------|-------|---------|
| `id` | all | Stable `sha256("{rustSymbol}:{kind}:{bridgeModule}")[:16]` hash |
| `rustSymbol` | all | Identifier name as it appears in the bridge source |
| `kind` | all | `function` \| `struct` \| `enum` \| `opaque` |
| `bridgeModule` | all | Filename stem (e.g. `scanner`, `scangame`, `yaml`) |
| `sourceFile` | all | Repo-relative path with forward slashes |
| `blockOrigin` | all | `Rust` for items in `extern "Rust"`/top-level structs/enums; `C++` for items inside `unsafe extern "C++"` |
| `signature` | function only | `{"args": [{"name", "type"}, ...], "returnType": str \| null}` |
| `fields` | struct only | Ordered list of `{"name", "type"}` — source order preserved |
| `variants` | enum only | Ordered list of variant name strings (discriminants stripped) |

Doc comments (`///` and `//!`) are NOT compared. Lifetimes, `&`/`&mut`,
`Pin<&mut T>`, `Box<T>`, and `UniquePtr<T>` wrappers ARE part of the signature
and ARE compared — they are ABI-relevant.

Entries are sorted by `(bridgeModule, kind, rustSymbol)` so the committed JSON
is byte-identical across runs on the same source tree. The contract file also
carries `schema_version: 1` so future schema migrations can branch without
breaking older gates.

---

## build.rs Relationship

The gate parses
[`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs)
for the `cxx_build::bridges([...])` array. This is the single source of truth
for which bridge files participate in the gate.

Adding a new bridge source file is a two-step workflow:

1. Add the new `src/foo.rs` file to the bridge crate and add its path to
   `build.rs::cxx_build::bridges([...])`.
2. Run
   `python tools/cxx_api_parity/check_parity_gate.py --repo-root . --update-baseline`
   to accept the new entries into the committed baseline.

Removing a bridge file uses the same `--update-baseline` workflow; the diff
report will list the removed entries as `missing_from_current` rows.

The parser also tolerates `#[cfg(windows)]` wrappers around the
`cxx_build::bridges([...])` call — the bridge crate is Windows-only, but the
gate itself runs on any platform.

---

## Ephemeral vs Committed Artifacts

The gate writes two sets of files:

- **Ephemeral (gitignored):**
  `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/parity-artifacts/` contains
  the output of the current run. These files are regenerated on every
  invocation and must not be committed. A local `.gitignore` in the bridge
  crate hides the directory so it never pollutes `git status`.
- **Committed (tracked):**
  [`docs/implementation/cxx_api_parity/baseline/`](../implementation/cxx_api_parity/baseline/)
  holds the golden baseline. `--update-baseline` is the only supported way
  to modify these files; manual edits will be detected as drift by the next
  gate run because `artifacts_match()` compares the committed baseline
  byte-for-byte (modulo `generated_at_utc` timestamps and `- Generated:` log
  lines) against a fresh regeneration.

---

## CI Integration

Phase 5 of the `v9.1.0-bindings` milestone wires a `cxx-parity-gate` job into
`.github/workflows/ci-cpp.yml` that runs before `cli-tests` and `gui-tests`.
The CI job requires only Python and a checkout — no Rust toolchain, no MSVC,
no vcpkg setup. It blocks merges on a non-zero exit just like the Python and
Node parity gates.

Until Phase 5 lands, contributors are expected to run the gate locally before
opening PRs that touch the bridge crate. The same command applies:

```bash
python tools/cxx_api_parity/check_parity_gate.py --repo-root .
```

---

## Troubleshooting

**"Contract file not found" error.** The committed baseline is missing from
`docs/implementation/cxx_api_parity/baseline/parity_contract.json`. Bootstrap
it with the command from the "Bootstrap From Scratch" section above.

**"Checked-in CXX parity artifacts are stale" error.** One or more files under
`docs/implementation/cxx_api_parity/baseline/` no longer match a fresh source
scan. If the change was intended, run `--update-baseline`. If not, investigate
what changed in the bridge source.

**"No `#[cxx::bridge] mod ffi` block found" error.** A file listed in
`build.rs` is missing its `#[cxx::bridge]` attribute. Add the attribute or
remove the file from `build.rs`.

**"build.rs does not contain a cxx_build::bridges([...]) call" error.** The
parser could not locate the bridge file list. Restore the standard
`cxx_build::bridges([...])` form or update the parser in
[`tools/cxx_api_parity/generate_baseline.py`](../../tools/cxx_api_parity/generate_baseline.py).

---

## Related Docs

- [`binding-parity-overview.md`](binding-parity-overview.md) — cross-binding
  surface comparison (C++, Node, Python)
- [`classic-cpp-bridge-game-entrypoints.md`](classic-cpp-bridge-game-entrypoints.md) —
  current path/game/scangame bridge entry points
- [`classic-cpp-bridge-data-entrypoints.md`](classic-cpp-bridge-data-entrypoints.md) —
  current config/file/database/scanner bridge entry points
- [`classic-cpp-bridge-scan-progress-callback.md`](classic-cpp-bridge-scan-progress-callback.md) —
  the batch scan progress callback contract that Phase 2 narrowing work will
  touch repeatedly

# Archived Documentation

Documents in this directory are **historical records**, not live guidance. They are kept because they explain how CLASSIC got to its current shape — dated migration reports, completed implementation write-ups, and design documents whose subject has since been replaced.

**Do not follow commands, paths, or architecture described here.** For anything current, start at [`../api/README.md`](../api/README.md) and [`../../AGENTS.md`](../../AGENTS.md).

Per rule D-07 in the [workspace migration matrix](../workspace-migration-matrix.md), the retired `ClassicLib-rs/...` path root may appear only inside clearly labeled migration or historical notes. Everything in this directory qualifies as such a note; that is a large part of why these files live here rather than under the active `docs/` tree.

## Contents

| Document | Why it is archived | Where to look instead |
| --- | --- | --- |
| `python_to_rust_migration_guide.md` | Self-labeled historical context for the v8.0.0 Python-to-Rust transition. | `../api/README.md` |
| `performance_optimization_complete.md` | Historical implementation report (2025-10-29) using the pre-split `classic_core` naming. | `../performance/` |
| `fcx_read_only_conversion.md` | Historical design document (2025-10-29) referencing the retired Python runtime structures. | `../api/classic-config-core.md` |
| `rust_scanlog_verification.md` | Historical verification record from the scanlog migration phases (2025-10-08). | `../api/classic-scanlog-core.md` |
| `python_bindings_optimization_propagation.md` | Dated propagation plan (2025-10-17) tied to a finished optimization phase. | `../implementation/python_api_parity/` |
| `ci_cd_guide.md` | Documents a single `.github/workflows/ci.yml` for a "hybrid Python-Rust" pipeline. That file no longer exists; CI is now seven split workflows. | The `CI And Platform Notes` section of `.agents/skills/classic-project-guide/references/repo-guide.md` |
| `CLASSIC_Ratatui_TUI_PRD.md` | Draft PRD for a TUI that has since shipped as `ui-applications/classic-tui/`. | `../guides/tui_user_guide.md` |
| `memory_profiling_guide.md` | Built around a paired Rust CLI + TUI cargo target. The Rust CLI was retired in favor of the C++ CLI, so its `cargo -p`/`--bin classic-cli` commands no longer resolve — `classic-cli/` is a CMake project, not a crate. | `../development/profiling_workflow.md` and `scripts/profile/run_dhat.ps1` |
| `pyinstaller_data_bundling.md` | Describes PyInstaller bundling for `ClassicLib/ResourceLoader.py`, part of the retired pure-Python application tree. PyInstaller is no longer used anywhere in the repo. | `classic-cli/build_cli.ps1 -Package`, `classic-gui/build_gui.ps1 -Package` |

## `python-era/`

Documentation for the **retired pure-Python application** (`ClassicLib/...`) and its pytest suite. That tree has been removed from the repository; CLASSIC is now Rust-core with C++ frontends and thin binding layers.

Every file in that subdirectory was verified to contain zero references to the current Rust workspace before being archived. It covers the async/AsyncBridge model, the YAML settings cache, the pytest fixture and test-pollution conventions, and per-module Python testing guides — none of which map onto the current `python-bindings/tests/` smoke-test layout.

For current Python binding testing, see `CLAUDE.md` and `../testing/rust_testing_guide.md`.

## Adding to this directory

Archive a document when its **subject** is retired — a finished migration, a superseded design, a pipeline that no longer exists. Do not archive a document merely because its paths are stale; fix the paths instead. A stale-but-current guide that gets archived silently stops being maintained, which is worse than a guide with an out-of-date path in it.

When you archive something, add a row above and update any inbound links.

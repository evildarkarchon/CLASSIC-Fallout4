# Phase 7 Relocation Audit

## Old to New Crate Mapping

| Old path | New path | Result |
| --- | --- | --- |
| ClassicLib-rs/foundation/classic-shared-core | foundation/classic-shared-core | Moved intact |
| ClassicLib-rs/foundation/classic-shared-py | foundation/classic-shared-py | Moved intact |
| ClassicLib-rs/business-logic/classic-database-core | business-logic/classic-database-core | Moved intact |
| ClassicLib-rs/business-logic/classic-file-io-core | business-logic/classic-file-io-core | Moved intact |
| ClassicLib-rs/business-logic/classic-scanlog-core | business-logic/classic-scanlog-core | Moved intact |
| ClassicLib-rs/business-logic/classic-config-core | business-logic/classic-config-core | Moved intact |
| ClassicLib-rs/business-logic/classic-scangame-core | business-logic/classic-scangame-core | Moved intact |
| ClassicLib-rs/business-logic/classic-registry-core | business-logic/classic-registry-core | Moved intact |
| ClassicLib-rs/business-logic/classic-perf-core | business-logic/classic-perf-core | Moved intact |
| ClassicLib-rs/business-logic/classic-settings-core | business-logic/classic-settings-core | Moved intact |
| ClassicLib-rs/business-logic/classic-message-core | business-logic/classic-message-core | Moved intact |
| ClassicLib-rs/business-logic/classic-path-core | business-logic/classic-path-core | Moved intact |
| ClassicLib-rs/business-logic/classic-version-core | business-logic/classic-version-core | Moved intact |
| ClassicLib-rs/business-logic/classic-resource-core | business-logic/classic-resource-core | Moved intact |
| ClassicLib-rs/business-logic/classic-xse-core | business-logic/classic-xse-core | Moved intact |
| ClassicLib-rs/business-logic/classic-web-core | business-logic/classic-web-core | Moved intact |
| ClassicLib-rs/business-logic/classic-update-core | business-logic/classic-update-core | Moved intact |
| ClassicLib-rs/business-logic/classic-version-registry-core | business-logic/classic-version-registry-core | Moved intact |
| ClassicLib-rs/python-bindings/classic-database-py | python-bindings/classic-database-py | Moved intact |
| ClassicLib-rs/python-bindings/classic-file-io-py | python-bindings/classic-file-io-py | Moved intact |
| ClassicLib-rs/python-bindings/classic-scanlog-py | python-bindings/classic-scanlog-py | Moved intact |
| ClassicLib-rs/python-bindings/classic-config-py | python-bindings/classic-config-py | Moved intact |
| ClassicLib-rs/python-bindings/classic-scangame-py | python-bindings/classic-scangame-py | Moved intact |
| ClassicLib-rs/python-bindings/classic-registry-py | python-bindings/classic-registry-py | Moved intact |
| ClassicLib-rs/python-bindings/classic-perf-py | python-bindings/classic-perf-py | Moved intact |
| ClassicLib-rs/python-bindings/classic-settings-py | python-bindings/classic-settings-py | Moved intact |
| ClassicLib-rs/python-bindings/classic-message-py | python-bindings/classic-message-py | Moved intact |
| ClassicLib-rs/python-bindings/classic-path-py | python-bindings/classic-path-py | Moved intact |
| ClassicLib-rs/python-bindings/classic-version-py | python-bindings/classic-version-py | Moved intact |
| ClassicLib-rs/python-bindings/classic-resource-py | python-bindings/classic-resource-py | Moved intact |
| ClassicLib-rs/python-bindings/classic-xse-py | python-bindings/classic-xse-py | Moved intact |
| ClassicLib-rs/python-bindings/classic-web-py | python-bindings/classic-web-py | Moved intact |
| ClassicLib-rs/python-bindings/classic-update-py | python-bindings/classic-update-py | Moved intact |
| ClassicLib-rs/python-bindings/classic-version-registry-py | python-bindings/classic-version-registry-py | Moved intact |
| ClassicLib-rs/node-bindings/classic-node | node-bindings/classic-node | Moved intact |
| ClassicLib-rs/ui-applications/classic-tui | ui-applications/classic-tui | Moved intact |
| ClassicLib-rs/cpp-bindings/classic-cpp-bridge | cpp-bindings/classic-cpp-bridge | Moved intact |

## Cargo Root Proof

### cargo locate-project --workspace --message-format plain

```text
J:\CLASSIC-Fallout4\Cargo.toml
```

### cargo metadata --format-version 1 --no-deps

```text
workspace_root=J:\CLASSIC-Fallout4
target_directory=J:\CLASSIC-Fallout4\target
members=37
J:\CLASSIC-Fallout4\foundation\classic-shared-core\Cargo.toml
J:\CLASSIC-Fallout4\foundation\classic-shared-py\Cargo.toml
J:\CLASSIC-Fallout4\business-logic\classic-database-core\Cargo.toml
J:\CLASSIC-Fallout4\business-logic\classic-file-io-core\Cargo.toml
J:\CLASSIC-Fallout4\business-logic\classic-scanlog-core\Cargo.toml
J:\CLASSIC-Fallout4\business-logic\classic-config-core\Cargo.toml
J:\CLASSIC-Fallout4\business-logic\classic-registry-core\Cargo.toml
J:\CLASSIC-Fallout4\business-logic\classic-settings-core\Cargo.toml
J:\CLASSIC-Fallout4\business-logic\classic-perf-core\Cargo.toml
J:\CLASSIC-Fallout4\business-logic\classic-version-registry-core\Cargo.toml
J:\CLASSIC-Fallout4\business-logic\classic-scangame-core\Cargo.toml
J:\CLASSIC-Fallout4\business-logic\classic-path-core\Cargo.toml
J:\CLASSIC-Fallout4\business-logic\classic-message-core\Cargo.toml
J:\CLASSIC-Fallout4\business-logic\classic-version-core\Cargo.toml
J:\CLASSIC-Fallout4\business-logic\classic-resource-core\Cargo.toml
J:\CLASSIC-Fallout4\business-logic\classic-xse-core\Cargo.toml
J:\CLASSIC-Fallout4\business-logic\classic-web-core\Cargo.toml
J:\CLASSIC-Fallout4\business-logic\classic-update-core\Cargo.toml
J:\CLASSIC-Fallout4\python-bindings\classic-database-py\Cargo.toml
J:\CLASSIC-Fallout4\python-bindings\classic-file-io-py\Cargo.toml
J:\CLASSIC-Fallout4\python-bindings\classic-scanlog-py\Cargo.toml
J:\CLASSIC-Fallout4\python-bindings\classic-config-py\Cargo.toml
J:\CLASSIC-Fallout4\python-bindings\classic-scangame-py\Cargo.toml
J:\CLASSIC-Fallout4\python-bindings\classic-registry-py\Cargo.toml
J:\CLASSIC-Fallout4\python-bindings\classic-perf-py\Cargo.toml
J:\CLASSIC-Fallout4\python-bindings\classic-settings-py\Cargo.toml
J:\CLASSIC-Fallout4\python-bindings\classic-message-py\Cargo.toml
J:\CLASSIC-Fallout4\python-bindings\classic-path-py\Cargo.toml
J:\CLASSIC-Fallout4\python-bindings\classic-version-py\Cargo.toml
J:\CLASSIC-Fallout4\python-bindings\classic-resource-py\Cargo.toml
J:\CLASSIC-Fallout4\python-bindings\classic-xse-py\Cargo.toml
J:\CLASSIC-Fallout4\python-bindings\classic-web-py\Cargo.toml
J:\CLASSIC-Fallout4\python-bindings\classic-update-py\Cargo.toml
J:\CLASSIC-Fallout4\python-bindings\classic-version-registry-py\Cargo.toml
J:\CLASSIC-Fallout4\node-bindings\classic-node\Cargo.toml
J:\CLASSIC-Fallout4\ui-applications\classic-tui\Cargo.toml
J:\CLASSIC-Fallout4\cpp-bindings\classic-cpp-bridge\Cargo.toml
```

## Stale Member and Manifest Sweep

- `Cargo.toml` now contains 37 root-relative workspace members and zero `ClassicLib-rs/` member entries.
- `cargo metadata --format-version 1 --no-deps` reports `workspace_root=J:\CLASSIC-Fallout4` and every package manifest under repo-root layer directories.
- `ClassicLib-rs/**/Cargo.toml` returned no files after the move.
- `ClassicLib-rs/**/*.rs` contains no files outside legacy `target/` residue after the move.
- Representative moved manifests kept their original relative `path =` geometry and still resolve from their new locations:
  - `cpp-bindings/classic-cpp-bridge/Cargo.toml` -> `../../foundation/...` and `../../business-logic/...`
  - `node-bindings/classic-node/Cargo.toml` -> `../../foundation/...` and `../../business-logic/...`
  - `python-bindings/classic-config-py/Cargo.toml` -> `../../foundation/...` and `../../business-logic/...`
  - `ui-applications/classic-tui/Cargo.toml` -> `../../foundation/...` and `../../business-logic/...`

## Legacy ClassicLib-rs Residue

The remaining `ClassicLib-rs/` directory is residue only. It no longer contains workspace member manifests or Rust source files.

| Residue | Why it is non-authoritative |
| --- | --- |
| `.cargo/` | Empty legacy directory; no `config.toml`, manifest, or Rust source remains. |
| `.gitignore` | Git housekeeping only; not consumed by Cargo workspace resolution. |
| `.idea/` | Local IDE metadata only. |
| `CLASSIC_Settings.yaml` | Runtime/user data, not part of the Rust build graph. |
| `clippy_full_report.txt` | Historical report artifact only. |
| `clippy_report.txt` | Historical report artifact only. |
| `coverage_report.ps1` | Legacy helper script outside the live Cargo graph. |
| `coverage_summary.ps1` | Legacy helper script outside the live Cargo graph. |
| `Crash Logs/` | User/runtime data only. |
| `target/` | Stale generated build output, including generated `.rs` files under build caches; not used as proof for Phase 7 closure. |

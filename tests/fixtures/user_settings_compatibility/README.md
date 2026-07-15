# User Settings compatibility corpus

This directory is the executable compatibility contract for ADR-0004. It records the persisted forms and decisions that `classic-user-settings-core` must preserve across read-only open, explicit update, migration planning, apply, and restore work. The corpus does not change production User Settings behavior by itself.

`expectations.json` is the machine-readable source of truth for compatibility cases and outcomes. Rust's `classic-user-settings-core` default registry is the sole authority for canonical labels, schema metadata, published defaults, and guidance; the defaults repeated here are compatibility evidence, not generator input. The integration test at `business-logic/classic-user-settings-core/tests/compatibility_contract.rs` verifies that every required case and outcome is represented, that valid inputs parse, that malformed input does not parse, and that preservation examples retain their semantic values and YAML types. Its operation scenarios also execute golden before/after checks for no-write outcomes, accepted-node patches, stale-revision conflicts, complete flat migrations, byte-exact backups, and restores.

Run the characterization with:

```powershell
cargo test -p classic-user-settings-core --test compatibility_contract
```

## Contract boundaries

- The first dedicated User Settings schema is characterized here as `schema_version: "1.0"`. Existing nested documents without that key are legacy/unversioned inputs; changing this baseline requires an intentional corpus update before implementation.
- An open is always read-only. A successful `read_only_open` does not by itself block a later explicit commit. `malformed_document` and `newer_major_schema` instead produce `degraded_fallback` views and block commits.
- `canonical_defaults` records the Rust-owned published defaults and identifies `CLASSIC_Info.default_settings` as their checked-in generated compatibility mirror. Production opens and bootstrap commits never read that mirror as a runtime defaults source.
- `degraded_fallbacks` is a separate safety policy. In particular, an untrusted Update Check value falls back to `false` even though its published default is `true`.
- Ordinary opens and commits do not canonicalize aliases, repair invalid values, or migrate locations. Those transformations require an explicit migration.
- Migration planning is read-only, deterministic, revision-anchored, and reversible in memory. A plan may describe an optional alias cleanup without marking a current document as migration-required.
- Applying a migration is explicit and revision-checked. It retains and rereads a byte-exact backup before atomically publishing and reopening the approved document; restore is an explicit conflict-checked operation on the resulting opaque receipt.
- Semantic losslessness preserves unknown keys and values, nested structures, scalar types, and untouched invalid values. Comments, quoting, and whitespace are outside this compatibility contract.

## Fixtures

| Fixture or case | Compatibility evidence |
| --- | --- |
| `canonical_current_nested.yaml` | Current nested document with the explicit schema version and published labels |
| `flat_classic_config.yaml` | Legacy snake_case `ClassicConfig`, nested `paths`, and `formid_databases` shape |
| `flat_migrated.yaml` | Expected explicit migration in which every flat scalar or sequence leaf has one canonical destination |
| `previous_location_nested.yaml` | Unversioned nested document from `<CLASSIC root>/CLASSIC Data/CLASSIC Settings.yaml` |
| `missing_document` | No file at either supported source location and no open-time creation |
| `malformed.yaml` | Syntax-invalid YAML, degraded view, and blocked commit |
| `invalid_known_values.yaml` | Per-setting fallbacks while invalid source nodes remain untouched |
| `alias_only.yaml` | A current document whose GUI-era alias can be reviewed as an optional explicit canonicalization plan |
| `canonical_alias_conflict.yaml` | Valid canonical path labels winning over conflicting GUI-era aliases, with optional explicit alias cleanup |
| `unknown_entries.yaml` | Unknown root and nested data across mapping, sequence, null, boolean, numeric, and string types |
| `unknown_entries_after_update.yaml` | Accepted one-field commit whose semantic diff proves every unrelated unknown node survived |
| `newer_major_schema.yaml` | Future-major document that remains degraded and read-only |
| `gui_geometry.yaml` | Remembered geometry for all maintained GUI tabs |
| `tui_state.json` | Separate legacy TUI remembered state available only to explicit import/migration |
| `concurrent_revision_conflict` | Stale open versus `concurrent_external_edit.yaml`, producing a conflict without overwrite |

The operation scenarios collectively distinguish and validate read-only open, degraded fallback, proposed update, accepted commit, rejected commit, conflict, migration, and restore. User Settings implementation tests consume the same fixtures through the public core interface and compare its typed views, diagnostics, preservation behavior, verified backups, and persistence decisions to these golden documents.

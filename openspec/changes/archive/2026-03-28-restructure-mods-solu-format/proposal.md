## Why

`Mods_SOLU` currently stores detection criteria and user-facing report text in a single `mapping[string] -> string` entry, where the YAML key is the only match criterion and the first line of the value doubles as the readable name. That shape prevents grouped `any`/`all` matching, explicit false-positive exceptions, and clean results-view rendering without relying on free-form text layout.

## What Changes

- Replace `Mods_SOLU` mapping entries with structured records that carry a stable `id`, grouped match `criteria`, `exceptions`, a readable `name`, and a separate `description`.
- Update YAML parsing and in-memory models so `Mods_SOLU` remains ordered but is represented as structured data across Rust core and binding-facing configuration APIs. **BREAKING**
- Update mods-with-solutions detection and report generation to use structured names and descriptions instead of splitting a free-form blob into title and body at render time.
- Add schema, fixture, and parity coverage for grouped criteria, exception filtering, and the new report-entry formatting path.

## Capabilities

### New Capabilities
- `structured-mods-solu-entries`: Define the YAML, parsing, detection, and report-generation contract for structured mods-with-solutions entries.

### Modified Capabilities
None.

## Impact

- `ClassicLib-rs/business-logic/classic-config-core` YAML parsing, types, fixtures, and schema documentation
- `ClassicLib-rs/business-logic/classic-scanlog-core` mods-with-solutions matching and report assembly
- `ClassicLib-rs/python-bindings`, `ClassicLib-rs/node-bindings`, and `ClassicLib-rs/cpp-bindings` config surfaces that currently expose `game_mods_solu` as key/value data
- `CLASSIC Data/databases/CLASSIC Fallout4.yaml`, parity fixtures, and `docs/api/` contract pages for config and scanlog behavior

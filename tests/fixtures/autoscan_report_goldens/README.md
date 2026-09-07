# Byte-exact Autoscan Report goldens

This immutable corpus drives complete `Crash Log Scan Run` requests through the
public Rust contract and compares each persisted Autoscan Report as exact bytes.
The test never calls report-fragment or formatting helpers.

The scenarios cover:

- `empty`: empty Crash Suspect and Mod Guidance findings plus explicit Plugin
  Evidence and Named Record no-match output.
- `populated`: both Crashgen Expectation placements, a Disabled Setting Notice,
  main-error/stack/DLL Crash Suspect sources, all four Mod Guidance groups,
  Plugin Evidence matches, resolved and unresolved FormIDs, FormID lookup hit
  and miss rows, and Named Record matches.
- `fcx`: a successful FCX-enabled full run with its public setup result and
  canonical setup text retained in the persisted report.

The populated YAML deliberately includes multiline guidance, Unicode, and
authored trailing spaces. Exact byte comparison also pins section separators,
ordering, and the report's final newline. FCX templates expand only absolute
fixture paths and the platform path separator before the byte comparison.

Golden mismatches are written under `target/autoscan-report-goldens/` for review.
There is intentionally no source-fixture auto-update mode.

The central `autoscan-report` conformance family at
`tests/conformance/packs/autoscan_report/v1.json` also uses these same immutable
inputs and `expected.md` files. Rust, Node, Python, and native CXX execute the
complete public Scan Run seam and return actual persisted bytes, byte length,
SHA-256, terminal facts, typed Display Content, and filesystem effects. The
central validator reads the existing Markdown oracle; adapter plans contain
only inputs and never contain expected reports. Adapter output must never
generate or refresh the oracle.

`formids.db` is a prebuilt SQLite input fixture containing the populated case's
`formidDatabaseEntries` from `manifest.json`, in the `Fallout4` table with
`formid`, `plugin`, and `entry` columns and a `(formid, plugin)` primary key.
Adapters copy it to `CLASSIC Data/databases/Fallout4 FormIDs Main.db`; they do
not reproduce database setup or lookup policy. The original Rust golden test
continues to construct its database from the manifest rows.

For conformance, FCX fixture paths live beneath each isolated execution root.
Only the central validator expands `{{FCX_GAME_ROOT}}`,
`{{FCX_DOCUMENTS_ROOT}}`, and `{{PATH_SEPARATOR}}` in expected bytes. Newline
style, Unicode, authored whitespace, section order, and all other report bytes
remain exact. See the
[conformance evidence map](../../../docs/implementation/autoscan_report_conformance_equivalence.md)
for commands, required receipts, and retained owner diagnostics.

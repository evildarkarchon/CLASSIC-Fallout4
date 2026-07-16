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

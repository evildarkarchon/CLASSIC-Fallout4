# Crash Log Scan Launch fixtures

Each fixture is one User Settings document. A runner copies it to `CLASSIC Settings.yaml` in a fresh Installation Root, launches through its own binding, and reports what the launch decided. No fixture names a host path: User Settings require absolute setup folders, so the FCX fixtures write them as `{{installationRoot}}/...`, and each runner replaces that placeholder with its fresh root written with `/` separators. Path-valued overrides, Targeted inputs and the empty `files` a scenario creates (game executables, XSE logs) are scenario inputs relative to the Installation Root, so every adapter observes the same root-relative paths.

- `managed_fallout4.yaml` — current schema, managed Fallout 4 with non-default saved values (NextGen, FormID values and simplify logs on, Unsolved Logs left in place, a limit of 3) and FormID rows for two games.
- `saved_options_off.yaml` — current schema with every supplied-as-on option off, for the override-turns-it-on case.
- `saved_custom_scan_folder.yaml` — managed Fallout 4 with only a saved custom scan folder under the root, for the "no custom scan folder" override (`noScanPath`) that withholds it.
- `managed_fallout4_game_specific.yaml` — managed Fallout 4 saving every game-specific value the game-differs rule withholds from another game: a game version, FCX Mode on, a custom scan folder, and all three setup folders. Its paths are absolute only because User Settings rejects relative ones; no scenario observes them, since they never apply to the non-managed game the scenarios scan.
- `vr_shared_and_legacy.yaml` — managed Fallout 4 VR with shared `Fallout4` rows, legacy `Fallout4VR` rows, and one row saved under both keys.
- `malformed.yaml` — a YAML parse failure; the launch uses User Settings' degraded fallbacks.
- `newer_major.yaml` — a newer major schema, untrusted the same way.
- `needs_migration.yaml` — an unversioned nested document; its values apply and it reports the migration diagnostic.
- `fcx_saved_setup.yaml` — managed Fallout 4 (NextGen) with FCX Mode on and saved game folder, game executable and documents folder under the root.
- `fcx_vr_setup.yaml` — managed Fallout 4 VR with FCX Mode on, saved game and documents folders, and no saved executable.
- `fcx_off_with_setup.yaml` — managed Fallout 4 with FCX Mode off and saved setup folders, for the FCX Mode override.
- `fcx_uninspectable_documents.yaml` — FCX Mode on with a documents folder holding a NUL (YAML `\0`), which no platform can inspect, for the typed XSE log error. It needs no placeholder.

Expectations live only in the pack and were written from the spec and User Settings' published defaults, not from any adapter's output.

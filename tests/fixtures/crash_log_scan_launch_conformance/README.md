# Crash Log Scan Launch fixtures

Each fixture is one User Settings document. A runner copies it to `CLASSIC Settings.yaml` in a fresh Installation Root, launches through its own binding, and reports what the launch decided. No fixture names an absolute path: path-valued overrides and Targeted inputs are scenario inputs relative to the Installation Root, so every adapter observes the same root-relative paths.

- `managed_fallout4.yaml` — current schema, managed Fallout 4 with non-default saved values (NextGen, FormID values and simplify logs on, Unsolved Logs left in place, a limit of 3) and FormID rows for two games.
- `saved_options_off.yaml` — current schema with every supplied-as-on option off, for the override-turns-it-on case.
- `managed_fallout4_game_specific.yaml` — managed Fallout 4 saving every game-specific value the game-differs rule withholds from another game: a game version, FCX Mode on, a custom scan folder, and all three setup folders. Its paths are absolute only because User Settings rejects relative ones; no scenario observes them, since they never apply to the non-managed game the scenarios scan.
- `vr_shared_and_legacy.yaml` — managed Fallout 4 VR with shared `Fallout4` rows, legacy `Fallout4VR` rows, and one row saved under both keys.
- `malformed.yaml` — a YAML parse failure; the launch uses User Settings' degraded fallbacks.
- `newer_major.yaml` — a newer major schema, untrusted the same way.
- `needs_migration.yaml` — an unversioned nested document; its values apply and it reports the migration diagnostic.

Expectations live only in the pack and were written from the spec and User Settings' published defaults, not from any adapter's output.

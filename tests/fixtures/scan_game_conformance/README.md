# Scan Game fixtures

These input-only fixtures supply every file, directory and game selection to fresh
temporary roots. `validate-ini` observes the public validator's report and structured
findings; `validate-enb` observes its binary/config statuses. Both record exact UTF-8
file inventories and directory inventories before and after the check.

The two console-command cases use identical `Fallout4.ini` bytes and different
`Fallout4` / `Fallout4VR` game-name selections. The particle cases distinguish a
warning from a corrected value. ENB covers absent, partial, complete and unreadable
configuration; unreadable is a directory named `enbseries.ini`, so no permissions,
installed game, registry, live discovery, or administrator privileges are needed.

Only the disposable absolute root and platform path separators are normalized in
path-bearing reports. Issue paths are root-relative. Files retain their exact bytes.
Expected results live in the scenario pack and are never passed to adapters.

This slice does not cover the full game-check orchestrator, Game Setup Intake,
installed-game discovery, BA2 archives, loose mods, executable hashing, crashgen
TOML, XSE, log scanning, Wrye parsing, or ENB presentation/helper result methods.
Those operations retain their existing tests and do not gain runtime credit here.

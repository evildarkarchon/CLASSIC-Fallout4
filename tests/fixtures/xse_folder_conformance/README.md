# XSE folder fixtures

Each runner seeds identical Version Registry YAML in an owned temporary directory before initializing the process singleton. OG and VR records carry controlled XSE metadata. A dedicated family process prevents an earlier registry initialization from changing the result.

The six cases observe explicit Local.yaml path precedence, local documents-root precedence, configured documents fallback, VR's `F4SE` folder name, malformed Local.yaml, and missing Local.yaml. The latter two use an unknown game, which returns before platform discovery. Known games always have a configured fallback and validated registry metadata. Relative path strings are returned values; discovery never visits those paths. The final YAML byte inventory detects unexpected writes.

The validator freezes the metadata digest and permits only the controlled game/version/path combinations. Changing registry metadata requires reviewing that digest because a missing XSE record can enable host discovery. No live game, user registry, home directory, or mutable user YAML supplies evidence.

The public resolver is exposed by Rust and CXX only. Node and Python are not enrolled for this capability. Platform fallback remains retained structural evidence rather than a synthetic successful receipt.

# Crash-generator configuration conformance

The `crashgen-check` family executes the native Scan Game checker and orchestrator
through Rust, Python, Node, and both C++ compiler configurations. Its input-only
fixtures cover a missing configuration, an Achievements plugin conflict, and the
same setting configured correctly. Expected messages and issue values are authored
from the public contract; adapters never receive expected observations.

Each adapter checks every issue field, configuration-path presence, crash-generator
name, installed entry names, and unchanged input bytes. The positive warning fixture
ensures the C++ bridge's fail-soft empty results cannot satisfy issue getters.
Python and Node convenience functions are executed independently and compared with
their class/orchestrator results. Node's optional-rules aliases exercise the absent
rules branch here; rule evaluation itself has separate `crashgen-settings` fixtures.

The diagnostic readiness inventory can identify matching predicates, but only a
current authenticated native receipt grants executable coverage. Run this family
with the same `run_semantic_conformance.py` and approved C++ wrapper entrypoints as
the other conformance families. Full retirement still requires the repository-wide
aggregate and retained source checks, rather than any one family's receipt.

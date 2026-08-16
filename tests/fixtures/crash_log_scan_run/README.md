# Crash Log Scan Run parity fixture

This immutable corpus is copied into a temporary directory by Rust, C++, Node,
and Python tests. `manifest.json` owns the normalized Standard and Targeted
expectations, the stable contract-variant inventory, and the evidence that each
adapter and native frontend acknowledges those facts.

The Installed YAML Data fixture also owns the malformed Local Ignore recovery
corpus. Its Reset To Default expectations cover retained Main/game selection,
single-use continuation resume, typed conflict, operational failures, and the
post-replacement durability-unknown recovery receipt,
pre-reset and post-critical-section cancellation, byte-exact backup bytes, reset
diagnostics, and byte-identical Autoscan Report content across Rust, C++, Node,
and Python.

`malformed-local-ignore.yaml` is the input-only malformed file used by the
executable conformance pack. The pack observes the paused result, applies declared
post-pause mutations, and then claims and replays the same opaque continuation so
rediscovery and duplicate durable effects cannot pass unnoticed.

Tests compare paths relative to their temporary root and ignore processing
timings and exact concurrent event interleavings. They compare discovery,
effective concurrency, discovery-order terminal outcomes, structured failures,
and durable artifact existence. Targeted runs additionally assert that no
`Unsolved Logs` directory is created.

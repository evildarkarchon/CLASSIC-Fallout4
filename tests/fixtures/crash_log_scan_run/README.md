# Crash Log Scan Run parity fixture

This immutable corpus is copied into a temporary directory by Rust, C++, Node,
and Python tests. `manifest.json` owns the normalized Standard and Targeted
expectations, the stable contract-variant inventory, and the evidence that each
adapter and native frontend acknowledges those facts.

Tests compare paths relative to their temporary root and ignore processing
timings and exact concurrent event interleavings. They compare discovery,
effective concurrency, discovery-order terminal outcomes, structured failures,
and durable artifact existence. Targeted runs additionally assert that no
`Unsolved Logs` directory is created.

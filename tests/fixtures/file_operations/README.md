# File operations conformance inputs

These input-only fixtures promote the deterministic text read/write portion of
the tier-1 file foundations checks into the shared scenario-pack lifecycle.
Expected values belong only to `tests/conformance/packs/file_operations/v1.json`.

Each participant creates a fresh temporary directory, materializes the authored
UTF-8 files, and calls its public Rust-backed read or write operation. Before and
after inventories record exact text bytes without newline translation. A missing
read remains an I/O failure; an existing empty file remains a successful empty
string. Creating and truncating writes are distinguished by their actual durable
file inventories. Failed reads and missing-parent writes must preserve all files.

CXX executes both `read_file_with_encoding` and its public `read_report_file`
alias, and rejects any disagreement. Error observations retain the Rust I/O
category while excluding operating-system-specific diagnostic prose. The pack
does not claim cache statistics, binary I/O, directory traversal, hashing,
backup, DDS analysis, or host filesystem discovery coverage. Existing tier-1
evidence for those operations remains in place.

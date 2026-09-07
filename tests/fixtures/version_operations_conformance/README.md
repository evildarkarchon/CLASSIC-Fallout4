# Version operations

These input-only cases exercise `classic-version-core` parsing, optional parsing,
comparison and formatting. They cover prefix removal, ignored fourth version
components, default patch zero, equal/less/greater comparisons and an empty-input
error. Rust and Node transport normalized strings; Python's public parser returns
triples, which its adapter transports as dotted strings after calling the real API.

The expected observations live only in
`tests/conformance/packs/version_operations/v1.json`. Comparison and formatting
are not called after a failed parse and receive no coverage fact for that case.
PE extraction and text extraction are separate capabilities, retaining existing
evidence rather than borrowing credit from these pure parsing operations.

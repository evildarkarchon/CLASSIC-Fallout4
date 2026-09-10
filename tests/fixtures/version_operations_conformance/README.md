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


The remaining version owner capabilities use separate applicability packs:
`version-extraction` (Rust/Node/Python), `version-f4se` (Rust/Python),
`version-pe` (Rust/CXX/Node/Python), and `version-pe-path` (Rust/Node/Python).
Text inputs exercise ordered duplicate extraction, empty results, and known/unknown
registry versions. PE fixtures encode a synthetic PE32 resource section containing
VS_VERSION_INFO with file version 1.10.163.7 as hexadecimal bytes; adapters materialize
those bytes only in fresh disposable directories. The fixture is not executable game
code and requires no installed game or system DLL. Missing paths, malformed DLL bytes,
and wrong extensions are independent negative inputs.

The common PE extraction observation deliberately matches the public CXX wrapper:
a four-part string on success and an empty string on documented domain failure.
It does not claim error-category equivalence. Path validity has a separate pack because
CXX does not expose that operation; a malformed existing DLL still has a valid path.

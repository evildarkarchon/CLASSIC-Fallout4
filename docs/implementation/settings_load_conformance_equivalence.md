# Generic settings loader conformance

The `settings-load` pack belongs to `classic-settings-core`. It is separate from
`config-operations`, whose strict application YAML loader belongs to
`classic-config-core`, and from installed data selection and User Settings.

Rust, CXX, Node/Bun and Python execute `load_settings_sync`,
`load_settings_async`, `load_batch_sync`, `load_batch_async` and cache presence
queries through their public adapters. CXX uses its existing async-blocking
wrappers, which delegate to the shared Tokio runtime. Python awaits its public
binding futures. No transport creates a Tokio runtime.

The common public result is document count for single loads and file count for
batch loads. CXX intentionally exposes counts instead of parsed YAML documents;
the pack therefore does not claim parsed-value transport coverage. Authored
fixtures contain multiple documents and an empty stream to make count semantics
observable. Missing and malformed members test attributed errors and the
absence of partial cache population. Presence after successful loads, absence
after clearing, and a complete final file inventory retain cache and filesystem
effects independently of the reported count.

Rust error variants map to `io` and `yaml-parse` plus the actual failing relative
path. The adapters that expose error text recognize only the exact core prefixes
and a declared absolute input path. Unknown errors fail the runner. OS prose and
YAML parser wording are not part of this common error contract; the error kind
and source path remain observable. Fixtures and expectations are separate, and
the receipt runner never receives expected values.

Coverage is restricted to the five listed operations. Cache clearing is exercised
for isolation and observed effects but does not enroll every unrelated
`clear_cache` alias. YAML operation classes, merging, schema validation, cache
performance metrics and other settings APIs retain their existing evidence.

Five retained Node mapping IDs are preserved while correcting their canonical
Rust metadata from old `config`/`aux` carrier labels to the actual settings-core
calls in `node-bindings/classic-node/src/settings.rs`. This makes applicability
source-driven without broad owner enrollment.

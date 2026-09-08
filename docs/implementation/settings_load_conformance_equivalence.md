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

The loader observations additionally retain cache keys and size, successful and
repeated invalidation, cache statistics, and statistics reset. Entries are refilled
before clearing so invalidation cannot make the clear assertion vacuous. The CXX
config aliases execute alongside their settings counterparts and must agree.

The cached-document pack inventories every remaining file after its final public
cache read. It compares exact replacement bytes, so a cached-value getter cannot
silently write the stale document back to disk or create an extra file.

The `settings-yaml` family executes YAML construction, parsing, typed getters,
string/bool/integer/vector mutation, dump/parse round trips, atomic file saves,
reloads, and cache reuse/clear. Saved bytes remain part of the common result.
Python's map accessor and CXX's individual mapped-string accessors project the
same authored mapping. Only the methods actually called are enrolled.

The `settings-yaml-batch` family executes batch get/set, ordered string maps and
string-vector maps in Rust and Node. Entry order is retained as an array, missing
batch keys stay absent, and non-string vector members are filtered by the core.
Python has no public batch/ordered-map counterparts. Two old `@rust` contract
rows incorrectly mapped these methods to the `YamlCacheStats` TypedDict; those
fictitious mappings were removed while preserving the real class mapping and
the Rust source inventory. The Python baseline generator reads that canonical
contract directly and does not regenerate the removed mappings. No production
binding was removed and no policy exception substitutes for executable evidence.

Merging, schema and other raw Rust exports without public adapter counterparts
retain their existing source inventory; these packs do not claim to execute them.

Five retained Node mapping IDs are preserved while correcting their canonical
Rust metadata from old `config`/`aux` carrier labels to the actual settings-core
calls in `node-bindings/classic-node/src/settings.rs`. This makes applicability
source-driven without broad owner enrollment.

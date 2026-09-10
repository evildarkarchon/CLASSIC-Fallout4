# Generic settings loader fixtures

Input-only temporary YAML files exercise public sync/async single-file and
batch loaders in `classic-settings-core`. The oracle lives separately in
`tests/conformance/packs/settings_load/v1.json`.

Multiple documents, an empty stream, a missing batch member and a malformed
batch member distinguish document counts from file counts. Failed batches
must not populate partial cache entries. Each operation starts with an empty
cache, observes presence after loading, clears it, and observes absence again.
The final file inventory detects any mutation of the input tree.

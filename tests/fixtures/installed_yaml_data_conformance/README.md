# Installed YAML Data conformance inputs

These JSON files contain only caller-controlled inputs: a public operation,
typed game, selected game version, exact UTF-8 file contents, and optional file
mutations made after the operation returns. The authenticated run plan selects
one fixture by `fixtureRef`. Expected observations live exclusively in
`tests/conformance/packs/installed_yaml_data/v1.json` and never enter adapter inputs.

Each case uses a fresh workspace. `installation/` is the CLASSIC installation
root and `cache/` is the isolated platform cache environment root. Updated and
previous candidates live under `cache/CLASSIC/yaml-cache/`; bundled files live
under `installation/CLASSIC Data/databases/`. The adapters call public APIs,
retain their returned handles, apply any requested mutations, and only then
project the returned state and inventory every surviving file.

Identities include relative forward-slash paths, byte lengths, and SHA-256 of
exact bytes. The CRLF Local Ignore input deliberately distinguishes copying
user bytes from reserializing equivalent YAML. Recovery default identities use
the canonical Local Ignore destination path. Diagnostics preserve ordered kind,
role, candidate, and path attribution; platform-sensitive prose is outside this
pack and remains covered by the existing focused tests. Error `role` identifies
an update-eligible Main/Game role, so a native `local_ignore` target becomes null.

The pack extends the direct config-owned inspection and preparation seams. It
does not duplicate the Crash Log Scan Run pack's continuation, proceed/reset,
cancellation, backup, conflict, or publication-fault facts. See the
[evidence map](../../../docs/implementation/installed_yaml_data_conformance_equivalence.md)
for remaining evidence ownership.

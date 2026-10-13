# URL operations

These input-only requests exercise `classic-web-core` URL validation, domain
extraction, relative joining and ordered query encoding. The executable pack is
`tests/conformance/packs/web_operations/v1.json`; its expected observations never
enter adapter inputs. HTTP URL strings are parsed locally; no network is used.

The success case fixes host normalization and reserved query-character encoding.
Failure cases preserve actual public parser and scheme errors. The Rust
participant calls every selected public operation, including after a
validation error, so one successful call cannot substitute for the others.

The same cases observe the default user agent, exact empty/Unicode/nested suffix
formatting, and the names and base URLs of all three ModSite variants. These
metadata values are authored in the pack and observed through the public API.
Game-specific URLs retain their existing evidence; common metadata observations
do not claim those operations.

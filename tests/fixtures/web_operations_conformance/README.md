# URL operations

These input-only requests exercise `classic-web-core` URL validation, domain
extraction, relative joining and ordered query encoding. The executable pack is
`tests/conformance/packs/web_operations/v1.json`; its expected observations never
enter adapter inputs. HTTP URL strings are parsed locally; no network is used.

The success case fixes host normalization and reserved query-character encoding.
Failure cases preserve actual public parser and scheme errors. Rust, CXX, Node
and Python adapters call every selected public operation, including after a
validation error, so one successful call cannot substitute for the others.

User-agent and ModSite helpers remain under their existing registry evidence;
this pack does not assign them URL-operation execution credit.

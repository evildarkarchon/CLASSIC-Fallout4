# Update and web controlled-service conformance

Issue #214 extends the executable umbrella from #185 with independently authored
notification responses and complete common web metadata observations. Existing
registry evidence, focused tests, source parity, declarations and stubs remain
required; this migration retires none of them.

| Pack | Executed public facts | Adapters |
| --- | --- | --- |
| `update-services` | Configured notification classification; Display Content and version fields; malformed response, protocol failure, real timeout, unsupported manifest and invalid installed version; absence; exact cache bytes and conditional revalidation | Rust, CXX, Node, Python |
| `web-operations` | URL validation, domain extraction, composition and errors; default user agent, exact suffix formatting, all three ModSite names and base URLs | Rust, CXX, Node, Python |

## Service and input ownership

The `update_services/v1.json` pack owns expected observations separately from
input-only fixtures under `tests/fixtures/update_services_conformance`. The
launcher in `tools/binding_compliance/controlled_update_service.py` serves exact
response sequences on an ephemeral IPv4 loopback port. It never proxies requests
or loads expected observations. Both Pages and Releases fallback point to this
listener through the public configured notification API. No token, internet
connection, user cache or mutable remote endpoint is required.

The service rejects unexpected requests, authentication headers, mismatched
conditional headers and unused responses. Timeout responses hold the connection
open until teardown so the client's configured timeout executes. Elapsed time and
the selected port are not common observations. Each adapter translates its actual
public result or error into status fields or a stable error code, and inventories
the invocation-owned cache with exact relative paths and bytes. A missing or
unexpected cache write is therefore a semantic mismatch.

Web operations parse authored URL strings locally. Suffix cases include empty
text, Unicode and nested parentheses, preserving the returned string without
normalization. Site metadata observes each exported constructor/enum variant and
name/base-URL helper. No browser or remote mod site is contacted.

## Coverage boundaries and retained evidence

Notification receipts credit `check_app_notification_configured` only. They do
not substitute for legacy release-list methods, first-party environment/cache
discovery, YAML installation/rollback, or other unexecuted update APIs. Existing
core tests remain responsible for the additional manifest fallback, cache and
durable installation branches.

Python exposes no ModSite game-URL method. Game-specific URL behavior retains its
existing Rust, CXX and Node evidence; Python representation/equality helpers also
retain their focused binding tests. Common name/base-URL facts cannot cover those
methods or future methods added to the same class. The existing `update-decisions`
pack continues to prove version comparisons independently.

## Execution

Use `python tools/binding_compliance/run_semantic_conformance.py --family
<update-services|web-operations> --participant <rust|node|python>` after building
the corresponding adapter. Refresh the managed Python environment and its native
wheels before Python execution. CXX uses
`tools/binding_compliance/conformance/adapters/run_cxx_conformance.ps1 -Family
<update-services|web-operations> -Compiler <msvc|clang-cl>` through the approved CLI
wrapper. Both packs are blocking in applicable scopes; missing, malformed,
incomplete or mismatching receipts fail the run. A local participant receipt
proves only that participant and revision.

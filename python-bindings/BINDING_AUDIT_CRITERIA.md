# Binding Audit Criteria

This document defines the Python binding audit standard for CLASSIC's maintained Rust-backed Python surface.

## Thin binding definition

A binding function is compliant when it only does the following:

1. Converts Python inputs into Rust types.
2. Delegates to Rust core logic.
3. Converts Rust outputs back into Python values.
4. Releases the GIL for long-running work when needed.
5. Maps Rust errors into Python exceptions.

A binding function is a violation when it adds business logic or legacy compatibility behavior such as:

- validation beyond structural type conversion
- cached state that belongs in core
- concurrency or scheduling decisions
- Python callback/import orchestration when a Rust implementation exists
- dead code, stub functions, compatibility-only shims, or ignored parameters

## Exemptions

The following patterns are acceptable when they only support the Python boundary:

- `#[pyclass]` wrapper types that compose a core type
- PyO3 enum mirrors with `From` conversions to/from core enums
- private conversion helpers that are not part of the public Python API
- best-effort callback invocation and cancellation glue that stays outside business rules

## Audit checklist

Status meanings:

- `Compliant` - no binding-layer violation identified after this audit
- `Updated in this change` - binding had a violation or shim removed here

| Crate | Scope | Status | Notes |
| --- | --- | --- | --- |
| `classic-shared-py` | Shared PyO3 helpers | Compliant | Boundary-only utilities and GIL helpers |
| `classic-yaml-py` | YAML access | Compliant | Wrapper surface only |
| `classic-database-py` | Database bindings | Updated in this change | Removed `batch_lookup` compatibility shim |
| `classic-file-io-py` | File I/O bindings | Compliant | Boundary-only wrapper layer |
| `classic-scanlog-py` | Scanlog bindings | Updated in this change | Removed dead shims, moved concurrency decision to core, rewired FCX path |
| `classic-config-py` | Config bindings | Compliant | Maintained wrapper surface |
| `classic-scangame-py` | Game scan bindings | Compliant | Core-backed orchestration wrappers |
| `classic-registry-py` | Registry bindings | Compliant | No audit violation identified |
| `classic-perf-py` | Perf bindings | Compliant | Wrapper-only diagnostics surface |
| `classic-settings-py` | Settings bindings | Compliant | Wrapper-only helpers |
| `classic-message-py` | Message bindings | Compliant | Wrapper-only helpers |
| `classic-path-py` | Path bindings | Compliant | Wrapper-only helpers |
| `classic-constants-py` | Constants/enums | Compliant | PyO3 enum/value projection only |
| `classic-version-py` | Version bindings | Compliant | Wrapper-only helpers |
| `classic-resource-py` | Resource bindings | Compliant | Wrapper-only helpers |
| `classic-xse-py` | XSE bindings | Compliant | Wrapper-only helpers |
| `classic-web-py` | Web bindings | Compliant | Wrapper-only helpers |
| `classic-update-py` | Update bindings | Compliant | Wrapper-only helpers |
| `classic-version-registry-py` | Version registry bindings | Compliant | Wrapper-only helpers |

## Audit outcomes captured by this change

- `classic-scanlog-py` no longer exports `parse_segments`, `ParallelReportProcessor.process_batch`, or the deprecated `crashgen_ignore` property.
- `classic-scanlog-py` `parse_complete()` now exposes only the parameters it actually uses.
- `classic-scanlog-core` now owns the batch concurrency decision through `resolve_batch_concurrency()`.
- `classic-scanlog-py` `fcx_handler.rs` now calls Rust core checks instead of importing legacy Python modules.
- `classic-database-py` no longer exports the `batch_lookup` compatibility wrapper.
- Obsolete `classic-pybridge-py` has been removed from the maintained workspace, CI, and parity toolchain.

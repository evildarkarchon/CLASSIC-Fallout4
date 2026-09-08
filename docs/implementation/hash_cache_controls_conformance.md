# Hash cache control evidence

The CXX surface exposes cache statistics, size, clear, and counter reset, but no
public operation that populates this particular cache. `hash-cache-controls`
therefore measures actual empty-cache idempotence through those four CXX calls
and the corresponding Rust APIs. It records every public statistics field and
separately returned cache sizes.

This family does not claim populated CXX execution. The focused Rust bridge
test `test_hash_cache_helpers_forward_core_surface` independently seeds the core
cache and checks bridge forwarding. The existing `file-fingerprint` family
executes populated-cache transitions in Rust, Node, and Python. Neither test
metadata nor synthetic CXX cache population is relabeled as a receipt.

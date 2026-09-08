# YAML lifecycle fixtures

Fixtures contain only YAML bytes and caller-authored typed mutations. The pack
separately authors typed observations, exact saved bytes and cache transitions.
All file writes use scenario-owned temporary directories.

The explicit update order is shared by every adapter. Unchanged `items` and
`mapping` precede updated `name`, `ready`, `size`, and `values`, making serialized
field order agree with the Node JSON transport's sorted-map representation.
This lifecycle pack still compares exact saved bytes. The separate batch pack
tests non-alphabetical ordered-map semantics without normalization.

# Resource operations

These fixtures exercise resource detection, support predicates, type parsing,
extensions, resource-info construction, directory enumeration, type counts and
file validation in `classic-resource-core`. Each adapter creates an isolated
temporary tree from the supplied UTF-8 files and removes it after observation.
Only returned absolute paths are made relative to that owned tree; ordered
resource and count lists are sorted by path/type for comparison.
After all public operations complete, a separate recursive inventory reads every
remaining file's actual bytes as lowercase hexadecimal, including unsupported
resources. Missing, changed, or extra files therefore fail conformance even when
classification and counts still match. Symlinks and special files fail execution.

Expected bytes, sizes, classifications, counts and hit/miss outcomes live only
in `tests/conformance/packs/resource_operations/v1.json`. Unknown extensions and
type names test the public `other` fallback. Validation failures become stable
codes only after observing the core error variant or its binding error carrier.

Rust, Node and Python expose the selected operations. CXX has no applicable
resource bridge. The type catalog observes every type-specific static Python
constructor against the equivalent canonical Rust/Node parse operation. Python
representation and equality methods retain existing evidence and receive no
classification credit from these calls.

# Installation discovery evidence boundary

Issue #215 adds the blocking `installation-paths` pack. Rust, CXX, Node and Python execute valid cached game/documents lookup and read-only checks against two disposable directory layouts, including paths with spaces. The pack compares both returned paths, all three ordered missing-INI messages, exact file bytes, and the complete directory inventory. Fixtures preload identical owned metadata for the CXX Fallout4-specific aliases; generic Rust/Node/Python classes execute directly. CXX traverses both public `find_game_path` namespaces and its Fallout4-specific game/documents aliases, with both MSVC and clang-cl required.

The input validator rejects missing executable markers, escaping paths, or changed registry metadata before launch. Each adapter validates its cache before calling discovery. Relative paths inside a dedicated serial receipt process keep host parent names such as OneDrive out of the document-checking contract. Current-directory restoration precedes temporary-directory cleanup. Expected messages and paths are independently authored; adapters receive only fixture inputs and serialize their public results.

The corrected Python smoke tests also retain focused local diagnostics, using validated temporary paths and propagating failures. These local tests remain in addition to the common conformance receipts.

The previous documents smoke invoked a nonexistent `find_documents_path` method, and the checker omitted its required path argument; broad exception handling concealed both failures. The corrected calls execute the actual public binding methods.

Platform fallback discovery currently has no public injected registry/home-directory provider. It belongs to the named `installation-discovery-source-boundary` retained structural analyzer. Its blocking Python source tests check valid-cache return ordering, native owner delegation, XSE configured-path precedence and unknown-version short-circuiting, and explicit fixture paths without swallowed failures. This evidence proves source structure only; it does not claim successful Windows registry, Steam, or home-directory discovery. Source/declaration/stub parity continues to own adapter transport shape.

Existing file, settings, registry, version-PE, and Scan Game conformance packs use disposable roots, seeded metadata or process-owned registry state. Python's additional FileIOCore operations retain their existing local runtime tests; they receive no new receipt coverage from this change. The diagnostic migration ledger names the discovery analyzer and its three structural obligations without granting runtime credit.


Node source metadata now identifies the three finder/checker classes' actual `classic-path-core` owner, derived from their `inner` fields and delegation in `src/path.rs`. The canonical generator owns that enrichment; existing mapping IDs remain stable. Coverage grants only the methods actually exercised. Exact known methods outside this pack and the unrelated legacy Python PathValidator carrier retain their existing evidence; future methods fail closed.

Tooling tests exercise applicability, input-only materialization, malformed or unsafe fixtures, missing/changed/extra/stale receipts, durable writes, unexpected directories and new unexecuted methods. Native validation uses `run_semantic_conformance.py --family installation-paths --participant <rust|node|python>` and the approved CXX launcher with `-Family installation-paths` for each compiler. CI requires each applicable participant and uploads diagnostics on failure.

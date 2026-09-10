# Version value conformance

These input-only fixtures exercise public GameVersion parsing, semantic distance,
same-major checks, and Fallout4Version metadata. All registry-backed calls use the
same authored CLASSIC Main.yaml bytes in dedicated adapter processes. No installed
game, working-tree registry, system DLL, or network data participates.

| Family | Public adapters | Credited Rust capability |
| --- | --- | --- |
| game-version-parse | Rust, CXX, Node, Python | parse and GameVersion carrier |
| game-version-distance | Rust, Node, Python | semantic_distance |
| game-version-order | Rust, Python | same_major |
| fallout4-identity | Rust, CXX, Node, Python | common is_vr/exe_name/steam_app_id and enum carrier |
| fallout4-paths | Rust, CXX, Python | as_str/docs_folder_name/is_standard/registry_id |
| fallout4-metadata | Rust, Python | game_version |

CXX parsing executes both legacy and modern public namespaces and rejects any
result disagreement. Its valid=false result intentionally limits common parse
failure observations to null; no error-text equivalence is claimed.

Additional ordering, equality, hash-consistency, repr, and metadata observations
are diagnostic. Python class-only methods without a separately mapped public core
operation retain their existing binding-local runtime evidence and receive no
new cross-adapter row credit. Hashes are compared for equal values rather than
publishing implementation-dependent hash numbers. Exact retained-operation lists
remain in operation_scope.py; an unknown new method is never automatically exempt.

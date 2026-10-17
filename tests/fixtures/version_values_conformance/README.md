# Version value conformance

These input-only fixtures exercise public GameVersion parsing, semantic distance,
same-major checks, and Fallout4Version metadata. All registry-backed calls use the
same authored CLASSIC Main.yaml bytes in dedicated adapter processes. No installed
game, working-tree registry, system DLL, or network data participates.

| Family | Public adapters | Credited Rust capability |
| --- | --- | --- |
| game-version-parse | Rust | parse and GameVersion carrier |
| game-version-distance | Rust | semantic_distance |
| game-version-order | Rust | same_major |
| fallout4-identity | Rust | common is_vr/exe_name/steam_app_id and enum carrier |
| fallout4-paths | Rust | as_str/docs_folder_name/is_standard/registry_id |
| fallout4-metadata | Rust | game_version |

Common parse failure observations are limited to null; no error-text
equivalence is claimed.

Additional ordering, equality, hash-consistency, repr, and metadata observations
are diagnostic. Hashes are compared for equal values rather than publishing
implementation-dependent hash numbers.

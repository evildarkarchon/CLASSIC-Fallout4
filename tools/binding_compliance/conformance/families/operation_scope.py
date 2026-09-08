"""Frozen phase-one dispositions for class methods retaining their existing tests.

These selectors are migration ownership, never semantic evidence. Unknown new
operations remain in central coverage derivation and therefore fail closed.
"""

from __future__ import annotations

from ..coverage import SourceParityRow

# Only operations already present in the retained parity contracts belong here.
# Keep participant and class identity explicit: similarly named unrelated methods
# must never inherit a disposition from this phase-one migration.
_RETAINED = {
    # Common site metadata executes constructors/name/base_url; Python display
    # and equality methods keep their focused binding tests as evidence.
    ("web-operations", "classic-web-core", "ModSite", "python"): frozenset(
        {"__eq__", "__repr__", "__str__"}
    ),
    # Parsing does not claim binding-only comparison/hash methods; existing
    # focused binding tests remain their evidence owner.
    (
        "game-version-parse",
        "classic-version-registry-core",
        "GameVersion",
        "python",
    ): frozenset({"__eq__", "__ge__", "__gt__", "__hash__", "__le__", "__lt__"}),
    # Common identity includes only the metadata also exported by Node.
    (
        "fallout4-identity",
        "classic-version-registry-core",
        "Fallout4Version",
        "python",
    ): frozenset(
        {
            "__eq__",
            "__hash__",
            "__repr__",
            "__str__",
            "display_name",
            "docs_folder_name",
            "from_str",
            "is_standard",
            "registry_id",
            "short_name",
            "xse_acronym",
        }
    ),
    # Binding-only representation/equality helpers retain their existing focused
    # smoke assertions; resource classification facts do not prove Python repr.
    (
        "resource-operations",
        "classic-resource-core",
        "ResourceType",
        "python",
    ): frozenset({"__repr__", "__str__", "__eq__"}),
    (
        "resource-operations",
        "classic-resource-core",
        "ResourceInfo",
        "python",
    ): frozenset({"__repr__", "__str__"}),
    ("update-decisions", "classic-update-core", "GithubClient", "python"): frozenset(
        {"get_all_releases", "get_latest_release", "repo_url"}
    ),
    ("xse-operations", "classic-xse-core", "XseType", "python"): frozenset(
        {"__eq__", "__repr__", "__str__", "f4sevr", "sfse", "skse", "skse64", "sksevr"}
    ),
    # The token pack observes the shared cross-adapter as_str surface. Python's
    # other GameId methods have no matching Node/CXX public operations.
    ("game-identity", "classic-shared-core", "GameId", "python"): frozenset(
        {"__eq__", "__hash__", "__repr__", "__str__", "exe_name", "is_vr"}
    ),
    (
        "version-registry",
        "classic-version-registry-core",
        "VersionInfo",
        "python",
    ): frozenset(
        {
            "__eq__",
            "__hash__",
            "get_compatible_crashgens",
            "get_crashgen_for_version",
            "get_crashgen_version_strings",
            "is_compatible_with",
        }
    ),
    (
        "version-registry",
        "classic-version-registry-core",
        "VersionRegistry",
        "python",
    ): frozenset(
        {
            "get_address_library_filename",
            "get_all_exe_hashes",
            "get_all_script_hashes",
            "get_by_short_name",
            "get_by_version",
            "get_correct_versions",
            "get_crashgen_versions",
            "get_script_hashes_for_version",
            "get_wrong_versions",
        }
    ),
    # These exact query methods execute in the extended Node/Python registry
    # pack; they cannot borrow facts from the common CXX-compatible query pack.
    (
        "version-registry",
        "classic-version-registry-core",
        "VersionRegistry",
        "node",
    ): frozenset(
        {
            "getAllExeHashes",
            "getAllScriptHashes",
            "getScriptHashesForVersion",
            "getVersionRegistry",
            "isVersionCompatible",
        }
    ),
    # The complementary common pack owns metadata, enumeration, configuration
    # and matching; no unknown future method receives an automatic disposition.
    (
        "version-registry-details",
        "classic-version-registry-core",
        "VersionRegistry",
        "python",
    ): frozenset(
        {
            "get_by_id",
            "get_all",
            "get_all_for_game",
            "get_crashgen_configs",
            "get_crashgen_for_version",
            "match_version",
            "match_version_string",
        }
    ),
    (
        "database-operations",
        "classic-database-core",
        "DatabasePool",
        "python",
    ): frozenset(
        {
            "get_cache_capacity",
            "get_cache_cleanup_interval",
            "get_cache_cleanup_threshold",
            "get_max_connections",
            "get_stats",
            "optimize",
            "rebalance_connections",
            "recalculate_max_connections",
            "set_cache_capacity",
            "set_cache_cleanup_interval",
            "set_cache_cleanup_threshold",
            "set_cache_ttl",
            "set_game_table",
            "set_max_connections",
            "get_batch_cache_ttl",
            "get_default_cache_cleanup_threshold",
            "get_default_cache_ttl",
            "get_default_query_cache_capacity",
            "get_max_cache_ttl",
        }
    ),
    ("scan-game", "classic-scangame-core", "EnbChecker", "python"): frozenset(
        {"format_message"}
    ),
    ("file-operations", "classic-file-io-core", "FileIOCore", "python"): frozenset(
        {
            "append_file",
            "clear_cache",
            "file_exists",
            "get_file_info",
            "get_file_size",
            "py_read_multiple_files",
            "py_walk_directory",
            "py_write_multiple_files",
            "read_bytes",
            "read_dds_header",
            "read_dds_headers_batch",
            "read_file_mmap",
            "read_lines",
            "stream_lines",
            "stream_lines_sync",
            "write_bytes",
            "write_lines",
        }
    ),
    ("message-operations", "classic-message-core", "Message", "python"): frozenset(
        {
            "__init__",
            "set_content",
            "set_details",
            "set_msg_type",
            "set_target",
            "set_title",
            "with_title",
        }
    ),
    # PathHandler's current Python contract is an aggregate class carrier only;
    # normalize/join/batch are exercised, and no unexecuted method rows are exempt.
    ("path-normalization", "classic-shared-core", "PathHandler", "python"): frozenset(),
}


def is_retained_operation(family_id: str, row: SourceParityRow) -> bool:
    """Identify a previously known deferred method without granting runtime credit."""
    # These exact existing carriers belong to different bridge operations;
    # a shared::GameId token read must not claim config/scanner/web execution.
    # Node's display-name helper likewise has no shared-core token equivalent.
    if (
        family_id == "game-identity"
        and row.rust_crate == "classic-shared-core"
        and row.obligation_id
        in {
            "parity:cxx:0f1ce653765981f0",
            "parity:cxx:17a9ae976a21c5f7",
            "parity:cxx:7aefe345782399f3",
            "parity:node:aux-phase4c-get-game-name",
        }
    ):
        return True
    return (
        row.mapping_origin == "canonical_rust"
        and row.runtime_operation
        in _RETAINED.get(
            (family_id, row.rust_crate, row.rust_symbol, row.participant_id),
            frozenset(),
        )
    )

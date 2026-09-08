"""Permanent family boundaries for operations exercised through sibling packs.

These selectors never grant evidence or remove a row from the full repository
inventory. Sibling executable packs or permanent analyzers must prove each row.
"""

from __future__ import annotations

from ..coverage import SourceParityRow

# Only operations already present in the source parity contracts belong here.
# Keep participant and class identity explicit: similarly named unrelated methods
# must never inherit another public wrapper's execution evidence.
_RETAINED = {
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
    ("update-decisions", "classic-update-core", "GithubClient", "python"): frozenset(
        {"get_all_releases", "get_latest_release", "repo_url"}
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
    ("file-operations", "classic-file-io-core", "FileIOCore", "python"): frozenset(
        {
            "read_dds_header",
            "read_dds_headers_batch",
        }
    ),
    # PathHandler's current Python contract is an aggregate class carrier only;
    # normalize/join/batch are exercised, and no unexecuted method rows are exempt.
    ("path-normalization", "classic-shared-core", "PathHandler", "python"): frozenset(),
}


def is_retained_operation(family_id: str, row: SourceParityRow) -> bool:
    """Exclude a sibling-owned operation from this family without granting credit."""
    # The static PathValidator namespace is source-owned; these scenarios prove
    # its individually mapped validation functions rather than constructing it.
    if (
        family_id == "installation-paths"
        and row.obligation_id == "parity:python:path.lib.PathValidator"
    ):
        return True
    # These exact existing carriers belong to different bridge operations;
    # a shared::GameId token read must not claim config/scanner/web execution.
    if (
        family_id == "game-identity"
        and row.rust_crate == "classic-shared-core"
        and row.obligation_id
        in {
            "parity:cxx:0f1ce653765981f0",
            "parity:cxx:17a9ae976a21c5f7",
            "parity:cxx:7aefe345782399f3",
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

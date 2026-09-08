"""Cached installation paths and read-only documents checks from public results."""

import json
from functools import partial

from ..coverage import CoveragePredicate, FamilyCoveragePolicy
from .file_operations import _files

REGISTRY_YAML = 'Version_Registry:\n  versions:\n    - id: FO4_OG\n      game: Fallout4\n      version: "1.10.163"\n      short_name: Fixture Standard\n      display_name: Fixture Standard Edition\n      docs_name: Fallout4\n      steam_id: 12345\n      is_vr: false\n      priority: 20\n      exe_hash: fixture-exe-hash\n      address_library:\n        filename: fixture-address.bin\n        format: bin\n        nexus_url: https://example.invalid/address\n      xse:\n        acronym: F4SE\n        full_name: Fixture Extender\n        compatible_version: "0.6.23"\n        loader: fixture_loader.exe\n        file_count: 1\n        script_hashes:\n          Fixture.pex: fixture-script-hash\n      crashgen_versions:\n        - version: "1.2.3"\n          name: Fixture Crashgen\n          acronym: FCG\n          dll_file: fixture.dll\n          description: Fixture diagnostics\n          download_url: https://example.invalid/crashgen\n    - id: FO4_VR\n      game: Fallout4\n      version: "1.2.72.0"\n      short_name: Fixture VR\n      display_name: Fixture VR Edition\n      docs_name: FixtureVRDocs\n      steam_id: 54321\n      is_vr: true\n      priority: 10\n      xse:\n        acronym: F4SEVR\n        full_name: Fixture VR Extender\n        compatible_version: "0.6.23"\n        loader: f4sevr_loader.exe\n        file_count: 0\n        script_hashes: {}\n  unknown_version_handling:\n    strategy: nearest_match\n    log_level: warning\n    defaults:\n      Fallout4: FO4_OG\n'


def _observed(operation, observation):
    """Require actual paths, ordered messages and the complete unchanged tree."""
    if set(observation) != {"gamePath", "docsPath", "checks", "files", "directories"}:
        return False
    game, docs = observation["gamePath"], observation["docsPath"]
    if (game, docs) not in {("game", "docs"), ("Game Folder", "Docs Folder")}:
        return False
    expected_files = [
        {"path": path, "content": content}
        for path, content in sorted(
            {
                "CLASSIC Main.yaml": REGISTRY_YAML,
                game + "/Fallout4.exe": "owned executable marker",
            }.items()
        )
    ]
    if not _files(observation["files"]) or observation["files"] != expected_files:
        return False
    if observation["directories"] != sorted([game, docs]):
        return False
    checks = observation["checks"]
    return (
        isinstance(checks, list)
        and len(checks) == 3
        and all(
            isinstance(message, str) and filename in message
            for filename, message in zip(
                ("Fallout4.ini", "Fallout4Custom.ini", "Fallout4Prefs.ini"), checks
            )
        )
    )


INSTALLATION_PATHS_COVERAGE_POLICY = FamilyCoveragePolicy(
    "installation-paths",
    tuple(
        CoveragePredicate(
            id="installation-paths." + name,
            capability_id="installation-paths.inspect",
            action="installation-paths.inspect",
            observation_family="installation-results",
            rust_symbols=symbols,
            matches=partial(_observed, name),
            runtime_operations=operations,
        )
        for name, symbols, operations in (
            (
                "game",
                ("GamePathFinder", "find_game_path", "parse_xse_log"),
                (
                    None,
                    "__init__",
                    "find_game_path",
                    "findGamePath",
                    "validate_game_path",
                    "validateGamePath",
                    "detect_fallout4_game_path",
                    "parse_xse_log",
                    "parseXseLog",
                ),
            ),
            (
                "docs",
                ("DocsPathFinder", "find_docs_path"),
                (
                    None,
                    "__init__",
                    "find_docs_path",
                    "findDocsPath",
                    "validate_docs_path",
                    "validateDocsPath",
                    "detect_fallout4_docs_path",
                    "set_steam_app_id",
                    "validate_ini_files",
                    "setSteamAppId",
                    "validateIniFiles",
                ),
            ),
            (
                "checks",
                (
                    "DocumentsChecker",
                    "run_all_checks",
                    "IniCheckResult",
                    "validate_ini_file",
                ),
                (
                    None,
                    "__init__",
                    "run_all_checks",
                    "runAllChecks",
                    "docs_checker_run_all_checks",
                    "validate_ini_file",
                    "docs_checker_validate_ini_file",
                    "validateIniFile",
                    "has_issue",
                    "check_onedrive_in_path",
                    "checkOnedriveInPath",
                ),
            ),
            (
                "validators",
                (
                    "validate_custom_scan_path",
                    "validate_settings_path",
                    "validate_settings_paths",
                    "check_drive_exists",
                    "check_read_permissions",
                    "check_write_permissions",
                    "validate_path_with_permissions",
                    "is_restricted_path",
                    "is_valid_executable_path",
                    "validate_path_exists",
                    "validate_is_directory",
                    "validate_is_file",
                    "remove_readonly",
                    "is_valid_path",
                    "validate_required_files",
                ),
                (
                    "PathValidator.validate_custom_scan_path",
                    "PathValidator.validate_settings_path",
                    "PathValidator.validate_settings_paths",
                    "PathValidator.check_drive_exists",
                    "PathValidator.check_read_permissions",
                    "PathValidator.check_write_permissions",
                    "PathValidator.validate_path_with_permissions",
                    "PathValidator.is_restricted_path",
                    "PathValidator.is_valid_executable_path",
                    "validateCustomScanPath",
                    "validateSettingsPath",
                    "validateSettingsPaths",
                    "checkDriveExists",
                    "checkReadPermissions",
                    "checkWritePermissions",
                    "validatePathWithPermissions",
                    "isRestrictedPath",
                    "isValidExecutablePath",
                    "check_restricted_path",
                    "is_restricted_path",
                    "path_validate_custom_scan",
                    "path_validate_exists",
                    "path_validate_is_directory",
                    "path_validate_is_file",
                    "path_validate_required_files",
                    "removeReadonly",
                    "remove_readonly",
                    "isValidPath",
                    "validateRequiredFiles",
                    "PathValidator.is_valid_path",
                    "PathValidator.validate_required_files",
                ),
            ),
        )
    ),
)


def validate_installation_paths_pack(document, root):
    """Reject invalid caches and metadata before any public discovery call can run."""
    paths = []
    fixture_root = (root / document["fixtureRoot"]).resolve()
    for case in document["scenarios"]:
        reference = case["input"].get("fixtureRef")
        if (
            case["input"] != {"fixtureRef": reference}
            or case["fixtureRefs"] != [reference]
            or case["action"] != "installation-paths.inspect"
        ):
            raise ValueError("installation paths requires one declared input")
        path = (fixture_root / document["fixtures"][reference]).resolve()
        if not path.is_relative_to(fixture_root):
            raise ValueError("installation paths fixture escapes root")
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if set(fixture) != {"gamePath", "docsPath", "registryYaml", "files"}:
            raise ValueError("unsupported installation paths fixture")
        if (fixture["gamePath"], fixture["docsPath"]) not in {
            ("game", "docs"),
            ("Game Folder", "Docs Folder"),
        }:
            raise ValueError("installation paths must be owned cache directories")
        if fixture["registryYaml"] != REGISTRY_YAML or fixture["files"] != {
            fixture["gamePath"] + "/Fallout4.exe": "owned executable marker"
        }:
            raise ValueError(
                "installation paths needs valid controlled caches and registry metadata"
            )
        if not _observed("all", case["expected"]):
            raise ValueError("installation paths requires complete public observations")
        paths.append(path)
    return tuple(paths)

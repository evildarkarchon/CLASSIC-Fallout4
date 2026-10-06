"""Cached installation paths, read-only documents checks and Installation Root location."""

import json
from functools import partial

from ..coverage import CoveragePredicate, FamilyCoveragePolicy
from .file_operations import _files

REGISTRY_YAML = 'Version_Registry:\n  versions:\n    - id: FO4_OG\n      game: Fallout4\n      version: "1.10.163"\n      short_name: Fixture Standard\n      display_name: Fixture Standard Edition\n      docs_name: Fallout4\n      steam_id: 12345\n      is_vr: false\n      priority: 20\n      exe_hash: fixture-exe-hash\n      address_library:\n        filename: fixture-address.bin\n        format: bin\n        nexus_url: https://example.invalid/address\n      xse:\n        acronym: F4SE\n        full_name: Fixture Extender\n        compatible_version: "0.6.23"\n        loader: fixture_loader.exe\n        file_count: 1\n        script_hashes:\n          Fixture.pex: fixture-script-hash\n      crashgen_versions:\n        - version: "1.2.3"\n          name: Fixture Crashgen\n          acronym: FCG\n          dll_file: fixture.dll\n          description: Fixture diagnostics\n          download_url: https://example.invalid/crashgen\n    - id: FO4_VR\n      game: Fallout4\n      version: "1.2.72.0"\n      short_name: Fixture VR\n      display_name: Fixture VR Edition\n      docs_name: FixtureVRDocs\n      steam_id: 54321\n      is_vr: true\n      priority: 10\n      xse:\n        acronym: F4SEVR\n        full_name: Fixture VR Extender\n        compatible_version: "0.6.23"\n        loader: f4sevr_loader.exe\n        file_count: 0\n        script_hashes: {}\n  unknown_version_handling:\n    strategy: nearest_match\n    log_level: warning\n    defaults:\n      Fallout4: FO4_OG\n'


# Installation Root location (#275). The executable folder and working directory
# are fixed so every candidate the locator derives (parent, grandparent and both
# `install` folders) stays inside the runner-owned temporary tree; no host folder
# can ever satisfy a lookup.
LOCATE_EXECUTABLE_DIR = "tree/build/bin"
LOCATE_WORKING_DIR = "tree/work"
# The six candidates in the documented search order.
LOCATE_CANDIDATES = (
    LOCATE_EXECUTABLE_DIR,
    LOCATE_WORKING_DIR,
    "tree/build",
    "tree",
    "tree/build/install",
    "tree/work/install",
)


def _locate_directories(classic_data_in):
    """Return the complete directory tree a locate runner creates and must leave unchanged."""
    found = set()
    for path in (
            LOCATE_EXECUTABLE_DIR,
            LOCATE_WORKING_DIR,
            *(location + "/CLASSIC Data" for location in classic_data_in),
    ):
        parts = path.split("/")
        found.update("/".join(parts[:index]) for index in range(1, len(parts) + 1))
    return sorted(found)


def _located(observation):
    """Require a candidate-relative root (or null) and a read-only, runner-shaped tree."""
    if set(observation) != {"installationRoot", "directories"}:
        return False
    located, directories = observation["installationRoot"], observation["directories"]
    if located is not None and located not in LOCATE_CANDIDATES:
        return False
    if not isinstance(directories, list) or directories != sorted(set(directories)):
        return False
    if not all(isinstance(path, str) for path in directories):
        return False
    # Every CLASSIC Data folder must sit in a candidate, and the root must hold one.
    holders = {
        path[: -len("/CLASSIC Data")]
        for path in directories
        if path.endswith("/CLASSIC Data")
    }
    if not holders <= set(LOCATE_CANDIDATES):
        return False
    if directories != _locate_directories(sorted(holders)):
        return False
    # The first candidate holding CLASSIC Data wins; none means no Installation Root.
    expected = next((c for c in LOCATE_CANDIDATES if c in holders), None)
    return located == expected


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
                    "validate_settings_path",
                    "validate_required_files",
                ),
                (
                    "PathValidator.validate_settings_path",
                    "validateSettingsPath",
                    "path_validate_required_files",
                    "validateRequiredFiles",
                    "PathValidator.validate_required_files",
                ),
            ),
        )
    )
    # Custom-scan folder policy (restricted-path rejection, custom-scan and
    # combined settings-path validation) is owned by classic-scanlog-core
    # (#254 follow-up). The same scenarios exercise it; a separate capability
    # keeps each row bound to its actual owner.
    + (
        CoveragePredicate(
            id="installation-paths.custom-scan",
            capability_id="installation-paths.custom-scan",
            action="installation-paths.inspect",
            observation_family="installation-results",
            rust_symbols=(
                "validate_custom_scan_path",
                "validate_settings_paths",
                "is_restricted_path",
            ),
            matches=partial(_observed, "custom-scan"),
            runtime_operations=(
                "PathValidator.validate_custom_scan_path",
                "PathValidator.validate_settings_paths",
                "PathValidator.is_restricted_path",
                "validateCustomScanPath",
                "validateSettingsPaths",
                "isRestrictedPath",
                "check_restricted_path",
                "is_restricted_path",
                "path_validate_custom_scan",
            ),
        ),
    )
    # The generic existence, kind, permission, drive, and read-only checks are
    # classic-shared-core primitives (#245). The same scenarios exercise them,
    # but a separate capability keeps each row bound to its actual owner.
    + (
        CoveragePredicate(
            id="installation-paths.primitives",
            capability_id="installation-paths.primitives",
            action="installation-paths.inspect",
            observation_family="installation-results",
            rust_symbols=(
                "check_drive_exists",
                "check_read_permissions",
                "check_write_permissions",
                "validate_path_with_permissions",
                "is_executable_file_path",
                "validate_path_exists",
                "validate_is_directory",
                "validate_is_file",
                "remove_readonly",
                "is_valid_path",
            ),
            matches=partial(_observed, "primitives"),
            runtime_operations=(
                "PathValidator.check_drive_exists",
                "PathValidator.check_read_permissions",
                "PathValidator.check_write_permissions",
                "PathValidator.validate_path_with_permissions",
                "PathValidator.is_valid_executable_path",
                "checkDriveExists",
                "checkReadPermissions",
                "checkWritePermissions",
                "validatePathWithPermissions",
                "isValidExecutablePath",
                "path_validate_exists",
                "path_validate_is_directory",
                "path_validate_is_file",
                "removeReadonly",
                "remove_readonly",
                "isValidPath",
                "PathValidator.is_valid_path",
            ),
        ),
    )
    # Installation Root location is owned by classic-config-core (#275). Its
    # own scenarios observe only the located root and the untouched tree.
    + (
        CoveragePredicate(
            id="installation-paths.locate",
            capability_id="installation-paths.locate",
            action="installation-paths.locate",
            observation_family="installation-root",
            rust_symbols=("locate_installation_root",),
            matches=_located,
            runtime_operations=(
                "locate_installation_root",
                "locateInstallationRoot",
            ),
        ),
    ),
)


def _validate_locate_case(case, fixture):
    """Reject locate inputs that could reach outside the runner-owned tree."""
    if set(fixture) != {"operation", "executableDir", "workingDir", "classicDataIn"}:
        raise ValueError("unsupported installation root fixture")
    if fixture["operation"] != "locate" or case["capabilityIds"] != [
        "installation-paths.locate"
    ]:
        raise ValueError("installation root fixture disagrees with its action")
    if (fixture["executableDir"], fixture["workingDir"]) != (
            LOCATE_EXECUTABLE_DIR,
            LOCATE_WORKING_DIR,
    ):
        raise ValueError("installation root search must start inside the owned tree")
    classic_data_in = fixture["classicDataIn"]
    if (
            not isinstance(classic_data_in, list)
            or len(set(classic_data_in)) != len(classic_data_in)
            or not set(classic_data_in) <= set(LOCATE_CANDIDATES)
    ):
        raise ValueError("CLASSIC Data may only be placed in a locator candidate")
    expected = case["expected"]
    if not _located(expected) or expected["directories"] != _locate_directories(
            classic_data_in
    ):
        raise ValueError("installation root requires complete public observations")


def validate_installation_paths_pack(document, root):
    """Reject invalid caches and metadata before any public discovery call can run."""
    paths = []
    fixture_root = (root / document["fixtureRoot"]).resolve()
    for case in document["scenarios"]:
        reference = case["input"].get("fixtureRef")
        if (
            case["input"] != {"fixtureRef": reference}
            or case["fixtureRefs"] != [reference]
            or case["action"]
            not in {"installation-paths.inspect", "installation-paths.locate"}
        ):
            raise ValueError("installation paths requires one declared input")
        path = (fixture_root / document["fixtures"][reference]).resolve()
        if not path.is_relative_to(fixture_root):
            raise ValueError("installation paths fixture escapes root")
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if case["action"] == "installation-paths.locate":
            _validate_locate_case(case, fixture)
            paths.append(path)
            continue
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

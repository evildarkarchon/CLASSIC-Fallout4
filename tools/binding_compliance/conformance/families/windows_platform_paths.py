"""Read-only Windows platform comparisons that do not persist personal paths."""

import json

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _observed(value):
    """Require native/.NET agreement and documented negative platform results."""
    return set(value) == {
        "documentsAgree",
        "registryMissing",
        "steamUnavailable",
    } and all(item is True for item in value.values())


WINDOWS_PLATFORM_PATHS_POLICY = FamilyCoveragePolicy(
    "windows-platform-paths",
    (
        CoveragePredicate(
            id="windows-platform-paths.observed",
            capability_id="windows-platform-paths.observe",
            action="windows-platform-paths.observe",
            observation_family="platform-comparison",
            rust_symbols=(
                "get_system_documents_path",
                "query_game_registry",
                "parse_steam_library",
            ),
            runtime_operations=(
                "getSystemDocumentsPath",
                "queryGameRegistry",
                "parseSteamLibrary",
            ),
            matches=_observed,
        ),
    ),
)


def validate_windows_platform_paths(document, root):
    """Allow only the reserved absent registry key and the Windows Steam stub query."""
    paths = []
    fixture_root = (root / document["fixtureRoot"]).resolve()
    for case in document["scenarios"]:
        reference = case["input"].get("fixtureRef")
        if (
            case["action"] != "windows-platform-paths.observe"
            or case["input"] != {"fixtureRef": reference}
            or case["fixtureRefs"] != [reference]
        ):
            raise ValueError("invalid platform scenario input")
        path = (fixture_root / document["fixtures"][reference]).resolve()
        if not path.is_relative_to(fixture_root):
            raise ValueError("platform fixture escapes root")
        if json.loads(path.read_text(encoding="utf-8")) != {
            "registryGame": "CLASSIC_Conformance_Missing_216",
            "steamId": 377160,
        } or not _observed(case["expected"]):
            raise ValueError(
                "platform comparison must remain read-only and path-redacted"
            )
        paths.append(path)
    return tuple(paths)

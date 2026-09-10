"""Integrity facts from independent executable and installation-location results."""

from collections.abc import Mapping

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def matches_integrity(observation: Mapping) -> bool:
    """Require both typed checks, their exact report concatenation, and final files."""
    checks = observation.get("checks")
    files = observation.get("files")
    return (
        set(observation) == {"checks", "report", "files"}
        and isinstance(checks, list)
        and len(checks) == 2
        and all(
            isinstance(check, Mapping)
            and set(check) == {"isValid", "message", "checkType"}
            and type(check["isValid"]) is bool
            and isinstance(check["message"], str)
            for check in checks
        )
        and [check["checkType"] for check in checks]
        == ["ExecutableVersion", "InstallationLocation"]
        and observation["report"] == "".join(check["message"] for check in checks)
        and isinstance(files, list)
        and all(
            set(file) == {"path", "content"} and isinstance(file["content"], str)
            for file in files
        )
        and [file["path"] for file in files] == sorted({file["path"] for file in files})
    )


GAME_INTEGRITY_COVERAGE_POLICY = FamilyCoveragePolicy(
    "game-integrity",
    (
        CoveragePredicate(
            "game-integrity.basic",
            "game-integrity.basic",
            "game-integrity.basic",
            "values",
            (
                "GameIntegrityChecker",
                "run_all_checks",
                "CheckType",
                "IntegrityCheckResult",
            ),
            matches_integrity,
            runtime_operations=(
                None,
                "__init__",
                "integrity_run_all_checks",
                "check_executable_version",
                "check_installation_location",
                "run_all_checks",
                "run_full_check",
                "executable_version",
                "installation_location",
                "is_executable_version",
                "is_installation_location",
            ),
        ),
        CoveragePredicate(
            "game-integrity.options",
            "game-integrity.options",
            "game-integrity.options",
            "values",
            ("IntegrityConfig",),
            matches_integrity,
            runtime_operations=(None, "__init__", "with_root_warn", "with_steam_ini"),
        ),
    ),
)

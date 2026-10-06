"""Read-only setup intake and primitive selection normalization observations."""

from collections.abc import Mapping

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _matches_read_only_run(observation: Mapping, path_updates: list) -> bool:
    """Require resolved setup paths, complete diagnostics, the given proposals, and no writes.

    Both run scenarios resolve the same Starfield fixture installation; they differ
    only in which saved facts were supplied and therefore in which Game Setup Path
    Updates intake proposes. ``unchanged`` must be ``True`` either way: a proposal
    is returned to the caller, never persisted by intake.
    """
    return (
        set(observation)
        == {
            "status",
            "hasErrors",
            "totalChecks",
            "failedChecks",
            "actionCount",
            "pathUpdateCount",
            "pathUpdates",
            "gameRoot",
            "docsRoot",
            "gameExecutable",
            "reportFlags",
            "files",
            "unchanged",
        }
        and observation["status"] == "ready"
        and observation["hasErrors"] is True
        and observation["totalChecks"] == 11
        and observation["failedChecks"] == 1
        and observation["actionCount"] == 0
        and observation["pathUpdateCount"] == len(path_updates)
        and observation["pathUpdates"] == path_updates
        and observation["gameRoot"] == "Game"
        and observation["docsRoot"] == "Docs"
        and observation["gameExecutable"] == "Game/Starfield.exe"
        and observation["reportFlags"]
        == {
            "gameNamed": True,
            "metadataUnsupported": True,
            "versionWarning": True,
            "documentsPassed": True,
            "loaderFailed": True,
        }
        and observation["unchanged"] is True
        and isinstance(observation["files"], list)
    )


def matches_intake(observation: Mapping) -> bool:
    """Require explicit resolved paths, complete diagnostics, and an unchanged installation."""
    return _matches_read_only_run(observation, [])


def matches_proposal(observation: Mapping) -> bool:
    """Require a discovered game-root proposal that intake returns without persisting it."""
    return _matches_read_only_run(observation, [{"kind": "game_root", "path": "Game"}])


def matches_normalization(observation: Mapping) -> bool:
    """Require public alias normalization and missing-versus-present path decisions."""
    return observation == {
        "versions": ["auto", "Original", "NextGen", "AnniversaryEdition", "VR", "auto"],
        "needs": [[True, True], [True, False], [False, True]],
    }


GAME_SETUP_INTAKE_COVERAGE_POLICY = FamilyCoveragePolicy(
    "game-setup-intake",
    (
        CoveragePredicate(
            "game-setup-intake.resolved",
            "game-setup-intake.run",
            "game-setup-intake.run",
            "values",
            ("GameSetupIntake", "GameSetupIntakeResult", "from_user_settings", "run"),
            matches_intake,
            runtime_operations=(
                None,
                "__init__",
                "combined",
                "run_game_setup_intake",
                "runGameSetupIntake",
                "runGameSetupIntakeFromUserSettings",
                "run_game_setup_intake_from_user_settings",
            ),
        ),
        CoveragePredicate(
            "game-setup-intake.proposal",
            "game-setup-intake.run",
            "game-setup-intake.run",
            "values",
            ("GameSetupIntake", "GameSetupIntakeResult", "from_user_settings", "run"),
            matches_proposal,
            runtime_operations=(
                None,
                "__init__",
                "combined",
                "run_game_setup_intake",
                "runGameSetupIntake",
                "runGameSetupIntakeFromUserSettings",
                "run_game_setup_intake_from_user_settings",
            ),
        ),
        CoveragePredicate(
            "game-setup-intake.normalization",
            "game-setup-intake.normalize",
            "game-setup-intake.normalize",
            "values",
            (
                "normalize_game_setup_version_selection",
                "game_setup_needs_path_detection",
            ),
            matches_normalization,
            runtime_operations=(
                None,
                "normalize_game_setup_version_selection",
                "normalizeGameSetupVersionSelection",
                "game_setup_needs_path_detection",
                "gameSetupNeedsPathDetection",
            ),
        ),
    ),
)

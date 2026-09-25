"""Real geometry publication and stable lock-error observations."""

from collections.abc import Mapping

from ..coverage import CoveragePredicate


def geometry_committed(observation: Mapping) -> bool:
    """Require the committed geometry and an independently authenticated revision."""
    return (
        set(observation) == {"transition", "geometry", "files"}
        and observation["transition"]
        == {
            "status": "committed",
            "code": None,
            "hasMessage": None,
            "revisionMatches": True,
        }
        and observation["geometry"] == {"maximized": False, "width": 900, "height": 650}
        and observation["files"]
        == [
            {"path": "CLASSIC Settings.yaml", "kind": "file"},
            {"path": "CLASSIC Settings.yaml.commit.lock", "kind": "file"},
        ]
    )


def geometry_lock_failed(observation: Mapping) -> bool:
    """A typed lock error leaves the source geometry unchanged and reports context."""
    return (
        set(observation) == {"transition", "geometry", "files"}
        and observation["transition"]
        == {
            "status": "error",
            "code": "commit_lock_open_failed",
            "hasMessage": True,
            "revisionMatches": None,
        }
        and observation["geometry"] == {"maximized": False, "width": 640, "height": 500}
        and observation["files"]
        == [
            {"path": "CLASSIC Settings.yaml", "kind": "file"},
            {"path": "CLASSIC Settings.yaml.commit.lock", "kind": "directory"},
        ]
    )


GEOMETRY_PREDICATES = (
    CoveragePredicate(
        "user-settings.geometry-committed",
        "user-settings.geometry",
        "user-settings.geometry",
        "durable-effects",
        (
            "commit_frontend_geometry_transition",
            "UserSettingsFrontendTransitionOutcome",
        ),
        geometry_committed,
        runtime_operations=(
            None,
            "user_settings_commit_frontend_geometry_transition",
            "commitFrontendGeometryTransition",
            "UserSettingsSnapshot.commit_frontend_geometry_transition",
        ),
    ),
    CoveragePredicate(
        "user-settings.geometry-lock-failed",
        "user-settings.geometry-error",
        "user-settings.geometry",
        "diagnostics",
        ("UserSettingsCommitError", "code", "message"),
        geometry_lock_failed,
        runtime_operations=(None, "code", "message"),
    ),
)

"""Compile User Settings read observations from its independent compatibility oracle."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy

_DEFAULT_FIELDS = {
    "update_check": "Update Check",
    "game_version": "Game Version",
    "move_unsolved_logs": "Move Unsolved Logs",
    "max_concurrent_scans": "Max Concurrent Scans",
    "fcx_mode": "FCX Mode",
    "simplify_logs": "Simplify Logs",
    "show_formid_values": "Show FormID Values",
}


def compile_compatibility_expectations(
    pack: Mapping[str, Any], oracle: Mapping[str, Any]
) -> dict[str, Any]:
    """Resolve case references into exact observations without querying Rust.

    The existing compatibility corpus remains the only authored value oracle.
    Field selection is input-only; the receipt comparator still rejects every
    missing or extra observation field. Invalid references raise ``ValueError``.
    """

    if oracle.get("contract_version") != 1:
        raise ValueError("unsupported User Settings compatibility contract version")
    cases = {case["id"]: case for case in oracle["cases"]}
    if len(cases) != len(oracle["cases"]):
        raise ValueError("duplicate User Settings compatibility case identity")
    result = copy.deepcopy(dict(pack))
    selected_cases = [
        scenario["expected"].get("compatibilityCase")
        for scenario in result["scenarios"]
    ]
    required_cases = set(cases) - {
        "tui_remembered_state",
        "concurrent_revision_conflict",
    }
    if (
        len(selected_cases) != len(set(selected_cases))
        or set(selected_cases) != required_cases
    ):
        raise ValueError(
            "User Settings pack must cover every ordinary open compatibility case exactly once"
        )
    for scenario in result["scenarios"]:
        reference = scenario["expected"]
        if set(reference) != {"compatibilityCase"}:
            raise ValueError(
                "User Settings expectations must reference a compatibilityCase"
            )
        case_id = reference["compatibilityCase"]
        if case_id not in cases:
            raise ValueError(f"unknown User Settings compatibility case: {case_id}")
        case = cases[case_id]
        if case_id in {"tui_remembered_state", "concurrent_revision_conflict"}:
            raise ValueError(
                "User Settings open scenarios cannot cover mutating operations"
            )
        if scenario["action"] != "user-settings.open":
            raise ValueError("User Settings read pack requires the open action")
        view = copy.deepcopy(case.get("expected_view", {}))
        if case.get("uses_canonical_defaults") or case.get("uses_degraded_fallbacks"):
            defaults = oracle["canonical_defaults"]["CLASSIC_Settings"]
            fallbacks = oracle["degraded_fallbacks"]["CLASSIC_Settings"]
            view = {field: defaults[label] for field, label in _DEFAULT_FIELDS.items()}
            if case.get("uses_degraded_fallbacks"):
                for field, label in _DEFAULT_FIELDS.items():
                    if label in fallbacks:
                        view[field] = fallbacks[label]["value"]
        inputs = scenario["input"]
        if set(inputs) != {"installationData", "observationFields"}:
            raise ValueError(
                "User Settings open input must contain only installationData and observationFields"
            )
        if inputs["observationFields"] != sorted(view):
            raise ValueError(
                "User Settings observationFields must exactly select the oracle view"
            )
        fixture = case["fixture"]
        installed = inputs["installationData"]
        if fixture is None:
            if installed or scenario["fixtureRefs"]:
                raise ValueError("missing User Settings case cannot install a fixture")
        elif (
            len(installed) != 1
            or set(installed[0]) != {"fixtureRef", "path"}
            or installed[0]["path"] != case["source"]["relative_path"]
            or pack["fixtures"].get(installed[0]["fixtureRef"]) != fixture
            or scenario["fixtureRefs"] != [installed[0]["fixtureRef"]]
        ):
            raise ValueError(
                "User Settings installed input does not match its compatibility case"
            )
        present = fixture is not None
        classification = case["source"]["classification"]
        classification = {
            "canonical_current": "current",
            "current": "current",
            "current_with_diagnostics": "current",
            "current_with_alias": "current",
            "current_with_unknown_entries": "current",
            # This corpus case is the historical nested shape without schema_version.
            "legacy_location": "unversioned",
            "legacy_flat_shape": "legacy_flat",
            "missing": "missing",
            "malformed": "malformed",
            "future_major": "future_major",
        }[classification]
        eligibility = (
            "eligible"
            if case["commit_eligible"]
            else (
                "requires_migration"
                if case["migration_required"]
                else "blocked_untrusted"
            )
        )
        scenario["expected"] = {
            "source": {
                "location": {
                    "classic_root": "canonical",
                    "classic_data_directory": "legacy",
                    "none": "missing",
                }[case["source"]["location"]],
                "path": {"path": case["source"]["relative_path"]} if present else None,
                "classification": classification,
            },
            "commitEligibility": eligibility,
            "diagnostics": copy.deepcopy(case["diagnostics"]),
            "view": view,
            "durableEffects": {"treeUnchanged": True},
            "revision": {
                "kind": "sha256" if present else "missing",
                "matchesSourceBytes": True,
            },
            "originalContent": {"present": present, "matchesSourceBytes": True},
        }
    return result


def _source(observation: Mapping[str, Any]) -> bool:
    """Recognize actual typed source, revision, and retained-byte observations."""

    source = observation.get("source")
    revision = observation.get("revision")
    original = observation.get("originalContent")
    return (
        isinstance(source, Mapping)
        and source.get("location") in {"canonical", "legacy", "missing"}
        and isinstance(revision, Mapping)
        and revision.get("matchesSourceBytes") is True
        and isinstance(original, Mapping)
        and original.get("matchesSourceBytes") is True
    )


def _update_projection(observation: Mapping[str, Any]) -> bool:
    """Recognize the observed update preference independently of other groups."""

    view = observation.get("view")
    return isinstance(view, Mapping) and type(view.get("update_check")) is bool


def _scan_projection(observation: Mapping[str, Any]) -> bool:
    """Require the observed game-version, movement, and concurrency projection."""

    view = observation.get("view")
    return (
        isinstance(view, Mapping)
        and view.get("game_version") in {"auto", "Original", "NextGen"}
        and type(view.get("move_unsolved_logs")) is bool
        and type(view.get("max_concurrent_scans")) is int
        and view["max_concurrent_scans"] >= 0
    )


def _frontend_projection(observation: Mapping[str, Any]) -> bool:
    """Require complete typed window geometry before covering frontend carriers."""

    view = observation.get("view")
    geometry = view.get("main_tab") if isinstance(view, Mapping) else None
    return (
        isinstance(geometry, Mapping)
        and set(geometry) == {"maximized", "width", "height"}
        and type(geometry["maximized"]) is bool
        and type(geometry["width"]) is int
        and type(geometry["height"]) is int
    )


def _diagnostics(observation: Mapping[str, Any]) -> bool:
    """Recognize explicit ordered diagnostic codes, including an empty list."""

    diagnostics = observation.get("diagnostics")
    return isinstance(diagnostics, list) and all(
        isinstance(code, str) for code in diagnostics
    )


def _read_only(observation: Mapping[str, Any]) -> bool:
    """Require an observed unchanged installation tree after opening settings."""

    return observation.get("durableEffects") == {"treeUnchanged": True}


USER_SETTINGS_COVERAGE_POLICY = FamilyCoveragePolicy(
    family_id="user-settings",
    predicates=(
        CoveragePredicate(
            "user-settings.source",
            "user-settings.open",
            "user-settings.open",
            "source",
            (
                "UserSettings",
                "SettingsSource",
                "SourceLocation",
                "DocumentClassification",
                "CommitEligibility",
                "Revision",
            ),
            _source,
        ),
        CoveragePredicate(
            "user-settings.update-preferences",
            "user-settings.open",
            "user-settings.open",
            "projection",
            ("UpdatePreferences",),
            _update_projection,
        ),
        CoveragePredicate(
            "user-settings.scan-settings",
            "user-settings.open",
            "user-settings.open",
            "projection",
            ("CrashLogScanSettings",),
            _scan_projection,
        ),
        CoveragePredicate(
            "user-settings.frontend-state",
            "user-settings.open",
            "user-settings.open",
            "projection",
            ("FrontendState", "WindowGeometry"),
            _frontend_projection,
        ),
        CoveragePredicate(
            "user-settings.diagnostics",
            "user-settings.open",
            "user-settings.open",
            "diagnostics",
            ("Diagnostic",),
            _diagnostics,
        ),
        CoveragePredicate(
            "user-settings.read-only",
            "user-settings.open",
            "user-settings.open",
            "durable-effects",
            (),
            _read_only,
        ),
    ),
)

"""Data-backed compliance scenario catalog for the Python CLI."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Scenario:
    """Stable scenario metadata used by listing, explanation, runs, and reports."""

    id: str
    purpose: str
    owner: str
    covered_exports: list[str]
    command: list[str]
    fixture_requirements: list[str]
    expected_exit_code: int
    profiles: list[str]
    failure_classifications: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable scenario metadata."""

        return asdict(self)


SCENARIOS = [
    Scenario("bindings-list", "Verify maintained binding inventory diagnostics.", "classic_py_cli", ["bindings.list"], ["bindings", "list", "--json"], [], 0, ["smoke", "python-ci"], ["local-environment-failure"]),
    Scenario("version-parse", "Parse a deterministic semantic version through classic_version.", "classic_version", ["parse_version", "format_version"], ["version", "parse", "1.10.163.0"], [], 0, ["smoke", "python-ci", "surface:classic_version"], ["missing-runtime-coverage", "true-binding-compliance-gap"]),
    Scenario("config-main-version", "Read the bundled main YAML version through classic_config.", "classic_config", ["load_main_yaml_version"], ["config", "main-version"], ["CLASSIC Data/databases"], 0, ["smoke", "python-ci", "surface:classic_config"], ["stale-generated-artifact", "policy-source-contradiction"]),
    Scenario("path-validate-fixture", "Validate a deterministic fixture path through classic_path.", "classic_path", ["PathValidator.is_valid_path"], ["path", "validate", "python-bindings/tests/fixtures"], ["python-bindings/tests/fixtures"], 0, ["smoke", "python-ci", "surface:classic_path"], ["local-environment-failure"]),
    Scenario("file-hash", "Hash a deterministic repository file through classic_file_io.", "classic_file_io", ["FileHasher.hash_file"], ["file", "hash", "Cargo.toml"], [], 0, ["smoke", "python-ci", "surface:classic_file_io"], ["true-binding-compliance-gap"]),
    Scenario(
        "scanlog-addictol-newer-than-floor",
        "Scan an Addictol crash log newer than the configured floor and prove it remains valid.",
        "classic_scanlog",
        ["scan_run_execute", "ScanRunLogResult.autoscan_report_path"],
        ["scan", "logs", "--path", "python-bindings/tests/fixtures/scanlogs/addictol-newer-than-floor.log"],
        ["python-bindings/tests/fixtures/scanlogs/addictol-newer-than-floor.log"],
        0,
        ["smoke", "python-ci", "surface:classic_scanlog"],
        ["missing-runtime-coverage", "true-binding-compliance-gap"],
    ),
]


def all_scenarios() -> list[Scenario]:
    """Return the maintained scenario catalog."""

    return list(SCENARIOS)


def get_scenario(scenario_id: str) -> Scenario | None:
    """Find a scenario by stable ID."""

    return next((scenario for scenario in SCENARIOS if scenario.id == scenario_id), None)


def scenarios_for_profile(profile: str) -> list[Scenario]:
    """Select scenarios for a named, python-ci, smoke, or surface profile."""

    if profile.startswith("surface:"):
        surface = profile.removeprefix("surface:")
        return [scenario for scenario in SCENARIOS if scenario.owner == surface or profile in scenario.profiles]
    return [scenario for scenario in SCENARIOS if profile in scenario.profiles]


def validate_catalog() -> list[str]:
    """Return validation errors for missing required scenario metadata."""

    errors: list[str] = []
    for scenario in SCENARIOS:
        if not scenario.owner:
            errors.append(f"{scenario.id}: missing owner")
        if not scenario.covered_exports:
            errors.append(f"{scenario.id}: missing covered exports")
        if scenario.expected_exit_code not in {0, 1, 2, 3, 4}:
            errors.append(f"{scenario.id}: invalid expected exit code")
        if not scenario.profiles:
            errors.append(f"{scenario.id}: missing profiles")
        if scenario.fixture_requirements is None:
            errors.append(f"{scenario.id}: missing fixture metadata")
    return errors
